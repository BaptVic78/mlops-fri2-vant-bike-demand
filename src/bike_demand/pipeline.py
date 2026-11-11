"""Produce an isolated Lab 7 candidate and evaluation evidence."""

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
from pathlib import Path

import joblib
import numpy as np
import yaml

from bike_demand.api import load_artifact
from bike_demand.preflight import check_snapshot, sha256
from bike_demand.split import partition_summary, split_data
from bike_demand.tracking import (
    Tracking,
    timestamp,
    training_commit,
    working_tree_dirty,
    write_json,
)
from bike_demand.train import DEFAULT_MODEL, compare_mean, fit_evaluate
from bike_demand.validate import FEATURES, load_data


def candidate_config(path: Path, policy: dict) -> dict:
    config = yaml.safe_load(path.read_text())
    if not isinstance(config, dict) or set(config) != {"data", "features", "model"}:
        raise ValueError("config: require data, features and model")
    if config["data"] != policy["evaluation"]["data"]:
        raise ValueError("config: require the frozen dataset")
    if config["features"] != list(FEATURES):
        raise ValueError("config: require the ordered features")
    settings = config["model"]
    rules = policy["candidate_settings"]
    if not isinstance(settings, dict) or set(settings) - (
        set(rules["fixed"]) | set(rules["may_vary"])
    ):
        raise ValueError("config: unsupported model settings")
    settings = {**DEFAULT_MODEL, **settings}
    if any(
        type(settings[key]) is not int or settings[key] != value
        for key, value in rules["fixed"].items()
    ):
        raise ValueError("config: random_state and n_jobs are fixed")
    for key, rule in rules["may_vary"].items():
        value = settings.get(key, {"min_samples_leaf": 1, "max_features": 1.0}.get(key))
        if isinstance(rule, dict):
            valid = type(value) is int and rule["min"] <= value <= rule["max"]
        else:
            valid = type(value) in (float, int, str) and value in rule
        if not valid:
            raise ValueError(f"config: {key} is outside the policy")
        settings[key] = value
    config["model"] = settings
    return config


def score(model, validation) -> tuple[np.ndarray, float]:
    predictions = np.asarray(model.predict(validation.loc[:, list(FEATURES)]))
    if not np.isfinite(predictions).all() or (predictions < 0).any():
        raise ValueError("predictions: require finite nonnegative values")
    mae = float(np.mean(np.abs(validation["cnt"].to_numpy() - predictions)))
    return predictions, mae


def produce_candidate(root: Path, config_path: Path, reference: Path) -> Path:
    root = root.resolve()
    policy_path = root / "configs/gate-policy.yaml"
    policy = yaml.safe_load(policy_path.read_text())
    if working_tree_dirty(root) is not False:
        raise ValueError("provenance: require a clean Git checkout")
    commit = training_commit(root)
    committed_policy = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:configs/gate-policy.yaml"],
        check=True,
        capture_output=True,
    ).stdout
    # A clean Git checkout may convert LF to CRLF on Windows.
    checked_out_policy = policy_path.read_bytes()
    if committed_policy.replace(b"\r\n", b"\n") != checked_out_policy.replace(
        b"\r\n", b"\n"
    ):
        raise ValueError("policy: differs from the training commit")
    config = candidate_config(config_path, policy)
    snapshot = check_snapshot(root)
    if snapshot["sha256"] != policy["evaluation"]["data_sha256"]:
        raise ValueError("data: differs from the policy snapshot")
    parts = split_data(load_data(root / config["data"]))
    summaries = partition_summary(parts)
    for key in ("fit_partition", "score_partition", "held_out_partition"):
        expected = dict(policy["evaluation"][key])
        name = expected.pop("name")
        if summaries[name] != expected:
            raise ValueError(f"partitions: {name} differs from the policy")
    reference_path = reference / "model.joblib"
    if sha256(reference_path) != policy["reference"]["model_sha256"]:
        raise ValueError("reference: checksum differs from the accepted version")
    reference_model, reference_version = load_artifact(
        reference_path, reference / "model-metadata.json"
    )
    validation = parts["validation"]
    _, reference_mae = score(reference_model, validation)
    if reference_mae != policy["reference"]["recorded_validation_mae"]:
        raise ValueError("reference: rescored MAE differs from the policy record")
    identity = {
        "training_commit": commit,
        "lock_sha256": sha256(root / "uv.lock"),
        "data_sha256": snapshot["sha256"],
        "config_sha256": sha256(config_path),
        "policy_sha256": sha256(policy_path),
    }
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[
        :12
    ]
    parent = root / "artifacts/candidates"
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / run_id
    temporary = parent / f".tmp-{run_id}"
    if destination.exists():
        raise ValueError(f"run: {destination} already exists; retained unchanged")
    # Exclusive mkdir also excludes concurrent attempts with identical inputs.
    temporary.mkdir()
    try:
        mean, naive_mae = compare_mean(parts["train"]["cnt"], validation["cnt"])
        model, predictions, measured_mae = fit_evaluate(
            parts["train"], validation, config
        )
        model_path = temporary / "model.joblib"
        joblib.dump(model, model_path)
        context = {
            **identity,
            "run_id": run_id,
            "timestamp": timestamp(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "working_tree_dirty": False,
            "features": list(FEATURES),
            "partitions": summaries,
            "config": config,
            "effective_model_settings": model.get_params(),
            "model_version": f"candidate-{run_id}",
            "model_sha256": sha256(model_path),
        }
        metadata_path = temporary / "model-metadata.json"
        write_json(metadata_path, context)
        loaded, _ = load_artifact(model_path, metadata_path)
        reloaded_predictions, reloaded_mae = score(loaded, validation)
        if not np.array_equal(predictions, reloaded_predictions):
            raise ValueError("readback: saved predictions differ")
        if reloaded_mae != measured_mae:
            raise ValueError("readback: saved MAE differs")
        evaluation = {
            **context,
            "policy_version": policy["policy_version"],
            "reference": {
                "model_sha256": sha256(reference_path),
                "model_version": reference_version,
                "validation_mae": reference_mae,
            },
            "train_mean": mean,
            "validation_mae": {
                "naive_train_mean": naive_mae,
                "random_forest": measured_mae,
            },
            "model_bytes": model_path.stat().st_size,
            "readback_mae": reloaded_mae,
            "loads_with_service_checks": True,
            "predictions_finite_non_negative": True,
        }
        write_json(temporary / "evaluation.json", evaluation)
        write_json(temporary / "config.json", config)
        shutil.copyfile(config_path, temporary / "input-config.yaml")
        shutil.copyfile(policy_path, temporary / "gate-policy.yaml")
        tracking = Tracking(root)
        tracking_id = tracking.start_run("candidate", context, model.get_params())
        tracking.finish(
            tracking_id,
            measured_mae,
            [model_path, metadata_path, temporary / "evaluation.json"],
        )
        write_json(temporary / "tracking.json", {"model_run_id": tracking_id})
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary)
        raise
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = produce_candidate(Path.cwd(), args.config, args.reference)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Pipeline blocked: {error}\n")
    print(f"Candidate evidence: {result}")
    print("Next step: gate review of evaluation.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
