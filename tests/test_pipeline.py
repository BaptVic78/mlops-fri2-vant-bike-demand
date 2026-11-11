import json
import subprocess
from types import SimpleNamespace

import pytest
import yaml

from bike_demand import pipeline
from bike_demand.preflight import sha256


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


def test_crlf_policy_matches_committed_lf(workspace, monkeypatch):
    root, config, reference = workspace
    policy_path = root / "configs/gate-policy.yaml"
    committed_policy = policy_path.read_bytes().replace(b"\r\n", b"\n")
    policy_path.write_bytes(committed_policy.replace(b"\n", b"\r\n"))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=committed_policy),
    )
    result = pipeline.produce_candidate(root, config, reference)
    assert (result / "evaluation.json").is_file()


def test_changed_policy_is_blocked(workspace, monkeypatch):
    root, config, reference = workspace
    policy_path = root / "configs/gate-policy.yaml"
    committed_policy = policy_path.read_bytes()
    policy_path.write_bytes(committed_policy + b"\n# Changed policy\n")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=committed_policy),
    )
    with pytest.raises(ValueError, match="policy: differs"):
        pipeline.produce_candidate(root, config, reference)
    assert not (root / "artifacts/candidates").exists()
