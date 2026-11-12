"""Score the already accepted reference once on the held-out test partition.

The Lab 7 gate has already rejected every evaluated candidate. This command
checks that fact, checks the model bytes, and only then reads the test rows.
It does not train a candidate and it does not choose another model.
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import yaml
from sklearn.metrics import mean_absolute_error

from bike_demand.preflight import sha256
from bike_demand.split import split_data
from bike_demand.tracking import training_commit, working_tree_dirty, write_json
from bike_demand.validate import FEATURES, load_data

EVALUATED_CANDIDATES = (
    "06c4291bb9bc",
    "26d505134be8",
    "c898c95692c8",
)


def reference_remains_accepted(decision_dir: Path) -> list[str]:
    """Return the rejected candidate ids. An acceptance blocks the held test."""
    rejected = []
    for path in sorted(decision_dir.glob("*.json")):
        decision = json.loads(path.read_text()).get("decision")
        if decision == "accept":
            raise ValueError(f"held test refused: {path.stem} was accepted")
        if path.stem in EVALUATED_CANDIDATES:
            if decision != "reject":
                raise ValueError(f"held test refused: {path.stem} is {decision}")
            rejected.append(path.stem)
    if set(rejected) != set(EVALUATED_CANDIDATES):
        raise ValueError("held test refused: a Lab 7 candidate decision is missing")
    return rejected


def refuse_second_evaluation(output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"held test already recorded: {output}")


def partition_mae(model, frame, features: list[str]) -> float:
    predictions = np.asarray(model.predict(frame.loc[:, features]), dtype=float)
    if not np.isfinite(predictions).all():
        raise ValueError("held test: predictions must be finite")
    return float(mean_absolute_error(frame["cnt"], predictions))


def score_accepted_model(
    model_path: Path,
    expected_sha256: str,
    validation,
    test,
    features: list[str],
    recorded_validation_mae: float,
) -> dict:
    """Score validation, then the test rows, only for the accepted checksum."""
    observed_sha256 = sha256(model_path)
    if observed_sha256 != expected_sha256:
        raise ValueError("held test refused: model is not the accepted reference")
    model = joblib.load(model_path)
    validation_mae = partition_mae(model, validation, features)
    if validation_mae != recorded_validation_mae:
        raise ValueError("held test refused: validation rescore differs")
    return {
        "model_sha256": observed_sha256,
        "validation_rescore_mae": validation_mae,
        "test_mae": partition_mae(model, test, features),
    }


def evaluate(root: Path, policy_path: Path, model_path: Path, output: Path) -> dict:
    refuse_second_evaluation(output)
    policy = yaml.safe_load(policy_path.read_text())
    reference = policy["reference"]
    evaluation = policy["evaluation"]
    rejected = reference_remains_accepted(root / "reports/lab7-decisions")
    frame = load_data(root / evaluation["data"])
    if sha256(root / evaluation["data"]) != evaluation["data_sha256"]:
        raise ValueError("held test refused: data snapshot differs")
    partitions = split_data(frame)
    scored = score_accepted_model(
        model_path,
        reference["model_sha256"],
        partitions["validation"],
        partitions["test"],
        list(FEATURES),
        reference["recorded_validation_mae"],
    )
    test = partitions["test"]
    record = {
        "selected_model": "reference retained",
        "used_to_choose_a_model": False,
        "rejected_candidates": rejected,
        "model_sha256": scored["model_sha256"],
        "data_sha256": evaluation["data_sha256"],
        "commit": training_commit(root),
        "working_tree_dirty": working_tree_dirty(root),
        "command": (
            "uv run --locked python -m bike_demand.held_test "
            "--model <accepted model.joblib>"
        ),
        "recorded_validation_mae": reference["recorded_validation_mae"],
        "validation_rescore_mae": scored["validation_rescore_mae"],
        "test": {
            "rows": len(test),
            "date_min": str(test["dteday"].min())[:10],
            "date_max": str(test["dteday"].max())[:10],
        },
        "test_mae": scored["test_mae"],
        "unit": "rentals/hour",
    }
    write_json(output, record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=Path("configs/gate-policy.yaml"))
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("reports/final-held-test.json")
    )
    args = parser.parse_args()
    try:
        record = evaluate(Path.cwd(), args.policy, args.model, args.output)
    except (ValueError, OSError, FileExistsError) as error:
        parser.exit(1, f"Held test failed: {error}\n")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
