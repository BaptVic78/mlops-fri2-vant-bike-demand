import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import joblib
import pandas as pd
import pytest
import yaml

from bike_demand import pipeline
from bike_demand.preflight import sha256
from bike_demand.split import partition_summary, split_data
from bike_demand.train import fit_evaluate
from bike_demand.validate import FEATURES, load_data

ROOT = Path(__file__).resolve().parents[1]


def test_policy_checkout_matches_git_bytes_with_autocrlf(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    git = ["git", "-C", str(tmp_path), "-c", "core.autocrlf=true"]
    (tmp_path / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
    policy_path = tmp_path / "configs/gate-policy.yaml"
    policy_path.parent.mkdir()
    policy_path.write_bytes(
        (ROOT / "configs/gate-policy.yaml").read_bytes().replace(b"\r\n", b"\n")
    )
    subprocess.run(
        git + ["add", ".gitattributes", "configs/gate-policy.yaml"], check=True
    )
    policy_path.unlink()
    subprocess.run(git + ["checkout-index", "--all", "--force"], check=True)
    indexed_policy = subprocess.run(
        git + ["show", ":configs/gate-policy.yaml"], check=True, capture_output=True
    ).stdout
    assert policy_path.read_bytes() == indexed_policy


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    (tmp_path / "configs").mkdir()
    (tmp_path / "data/raw").mkdir(parents=True)
    data = tmp_path / "data/raw/hour.csv"
    data.write_bytes((ROOT / "tests/fixtures/missing-hours.csv").read_bytes())
    parts = split_data(load_data(data))
    config = yaml.safe_load((ROOT / "configs/baseline.yaml").read_text())
    config_path = tmp_path / "configs/candidate.yaml"
    config_path.write_text(yaml.safe_dump(config))
    policy = yaml.safe_load((ROOT / "configs/gate-policy.yaml").read_text())
    summary = partition_summary(parts)
    for key in ("fit_partition", "score_partition", "held_out_partition"):
        name = policy["evaluation"][key]["name"]
        policy["evaluation"][key] = {"name": name, **summary[name]}
    policy["evaluation"]["data_sha256"] = sha256(data)
    model, _, mae = fit_evaluate(parts["train"], parts["validation"], config)
    reference = tmp_path / "reference"
    reference.mkdir()
    joblib.dump(model, reference / "model.joblib")
    digest = sha256(reference / "model.joblib")
    (reference / "model-metadata.json").write_text(
        json.dumps(
            {
                "model_version": "fixture",
                "model_sha256": digest,
                "features": list(FEATURES),
            }
        )
    )
    policy["reference"].update(model_sha256=digest, recorded_validation_mae=mae)
    policy_path = tmp_path / "configs/gate-policy.yaml"
    policy_path.write_text(yaml.safe_dump(policy))
    (tmp_path / "uv.lock").write_text("fixture lock")
    pd_frame = pd.read_csv(data)
    (tmp_path / "data/manifest.json").write_text(
        json.dumps(
            {
                "sha256": sha256(data),
                "bytes": data.stat().st_size,
                "header": list(pd_frame.columns),
                "rows": len(pd_frame),
            }
        )
    )
    monkeypatch.setattr(pipeline, "working_tree_dirty", lambda root: False)
    monkeypatch.setattr(pipeline, "training_commit", lambda root: "fixture-commit")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=policy_path.read_bytes()),
    )

    class FixtureTracking:
        def __init__(self, root):
            pass

        def start_run(self, *args):
            return "fixture-tracking"

        def finish(self, *args):
            pass

    monkeypatch.setattr(pipeline, "Tracking", FixtureTracking)
    return tmp_path, config_path, reference


def test_candidate_preserves_accepted_files_and_is_immutable(workspace):
    root, config, reference = workspace
    accepted = root / "artifacts"
    accepted.mkdir()
    (accepted / "model.joblib").write_bytes(b"accepted bytes")
    (accepted / "model-metadata.json").write_bytes(b"accepted metadata")
    result = pipeline.produce_candidate(root, config, reference)
    assert (accepted / "model.joblib").read_bytes() == b"accepted bytes"
    assert (accepted / "model-metadata.json").read_bytes() == b"accepted metadata"
    evaluation = json.loads((result / "evaluation.json").read_text())
    assert evaluation["model_sha256"] == sha256(result / "model.joblib")
    assert evaluation["readback_mae"] == evaluation["validation_mae"]["random_forest"]
    assert "test_mae" not in json.dumps(evaluation)
    before = (result / "evaluation.json").read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        pipeline.produce_candidate(root, config, reference)
    assert (result / "evaluation.json").read_bytes() == before
    assert not list(result.parent.glob(".tmp-*"))


def test_wrong_reference_stops_before_candidate(workspace):
    root, config, reference = workspace
    (reference / "model.joblib").write_bytes(b"wrong")
    with pytest.raises(ValueError, match="reference: checksum"):
        pipeline.produce_candidate(root, config, reference)
    assert not (root / "artifacts/candidates").exists()


def test_dirty_tree_is_blocked(workspace, monkeypatch):
    root, config, reference = workspace
    monkeypatch.setattr(pipeline, "working_tree_dirty", lambda root: True)
    with pytest.raises(ValueError, match="clean Git checkout"):
        pipeline.produce_candidate(root, config, reference)


@pytest.mark.parametrize(
    ("key", "value"),
    [("n_estimators", 301), ("max_depth", True), ("random_state", 7), ("n_jobs", True)],
)
def test_disallowed_settings(workspace, key, value):
    root, config_path, reference = workspace
    config = yaml.safe_load(config_path.read_text())
    config["model"][key] = value
    config_path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="config:"):
        pipeline.produce_candidate(root, config_path, reference)


def test_failed_training_removes_partial_bundle(workspace, monkeypatch):
    root, config, reference = workspace

    def fail(*args):
        raise ValueError("training interrupted")

    monkeypatch.setattr(pipeline, "fit_evaluate", fail)
    with pytest.raises(ValueError, match="training interrupted"):
        pipeline.produce_candidate(root, config, reference)
    assert list((root / "artifacts/candidates").iterdir()) == []
