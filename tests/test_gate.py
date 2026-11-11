import json

import joblib
import pandas as pd
import pytest
import yaml

from bike_demand import gate, pipeline
from bike_demand.preflight import sha256


@pytest.fixture
def gate_workspace(workspace, monkeypatch):
    root, config, reference = workspace
    monkeypatch.setattr(
        gate, "committed_bytes", lambda root, commit, path: (root / path).read_bytes()
    )
    monkeypatch.setattr(gate, "training_commit", lambda root: "fixture-gate")
    return root, config, reference


def make_candidate(workspace, accept=False):
    root, config, reference = workspace
    if accept:
        # Synthetic branch coverage only. Canonical runs keep the tracked policy.
        data = root / "data/raw/hour.csv"
        frame = pd.read_csv(data)
        frame.loc[frame["dteday"].between("2012-01-01", "2012-06-30"), "cnt"] = 0
        frame.to_csv(data, index=False)
        manifest_path = root / "data/manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest.update(sha256=sha256(data), bytes=data.stat().st_size)
        manifest_path.write_text(json.dumps(manifest))
        path = root / "configs/gate-policy.yaml"
        policy = yaml.safe_load(path.read_text())
        policy["evaluation"]["data_sha256"] = sha256(data)
        model, _ = gate.load_artifact(
            reference / "model.joblib", reference / "model-metadata.json"
        )
        model.fixture_reference = True
        joblib.dump(model, reference / "model.joblib")
        metadata_path = reference / "model-metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["model_sha256"] = sha256(reference / "model.joblib")
        metadata_path.write_text(json.dumps(metadata))
        policy["reference"]["model_sha256"] = metadata["model_sha256"]
        parts = pipeline.split_data(pipeline.load_data(data))
        _, mae = pipeline.score(model, parts["validation"])
        policy["reference"]["recorded_validation_mae"] = mae
        policy["criteria"]["quality"]["beat_reference_by"] = 0
        path.write_text(yaml.safe_dump(policy))
    return pipeline.produce_candidate(root, config, reference)


def test_rejection_preserves_reference_and_records_failed_rule(gate_workspace):
    root, _, reference = gate_workspace
    before = {p.name: p.read_bytes() for p in reference.iterdir()}
    candidate = make_candidate(gate_workspace)
    record = gate.decide(root, candidate)
    assert record["decision"] == "reject"
    assert record["exit_code"] == 1
    assert any(row["claim"] == "beat_reference_by" for row in record["failed"])
    assert {p.name: p.read_bytes() for p in reference.iterdir()} == before
    assert not (root / "artifacts/accepted").exists()
    with pytest.raises(ValueError, match="require an accept"):
        gate.promote(root, candidate, reference)


def test_missing_evidence_is_blocked_and_record_is_immutable(gate_workspace):
    root, _, _ = gate_workspace
    candidate = root / "artifacts/candidates/000000000000"
    candidate.mkdir(parents=True)
    record = gate.decide(root, candidate)
    assert record["decision"] == "blocked"
    path = root / "reports/lab7-decisions/000000000000.json"
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        gate.decide(root, candidate)
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("working_tree_dirty", True),
        ("readback_mae", float("nan")),
        ("readback_mae", 999),
        ("features", ["cnt"]),
        ("policy_version", 99),
        ("predictions_finite_non_negative", None),
    ],
)
def test_invalid_evidence_never_passes(gate_workspace, field, value):
    root, _, _ = gate_workspace
    candidate = make_candidate(gate_workspace)
    path = candidate / "evaluation.json"
    evidence = json.loads(path.read_text())
    evidence[field] = value
    path.write_text(json.dumps(evidence))
    assert gate.decide(root, candidate)["decision"] == "blocked"


def test_modified_candidate_bytes_are_blocked(gate_workspace):
    root, _, _ = gate_workspace
    candidate = make_candidate(gate_workspace)
    with (candidate / "model.joblib").open("ab") as stream:
        stream.write(b"changed")
    assert gate.decide(root, candidate)["decision"] == "blocked"


def test_budget_includes_undecided_pipeline_attempts(gate_workspace):
    root, _, _ = gate_workspace
    candidate = make_candidate(gate_workspace)
    history = root / "reports/lab7-evidence"
    history.mkdir(parents=True)
    for i in range(3):
        (history / f"evaluation-{i}.json").write_text(
            json.dumps({"policy_version": 1, "run_id": str(i)})
        )
    assert gate.decide(root, candidate)["decision"] == "blocked"


def test_promotion_retains_previous_and_detects_post_decision_tampering(gate_workspace):
    root, _, reference = gate_workspace
    candidate = make_candidate(gate_workspace, accept=True)
    decision = gate.decide(root, candidate)
    assert decision["failed"] == []
    assert decision["decision"] == "accept", decision
    result = gate.promote(root, candidate, reference)
    assert result["model_sha256"] != result["previous_model_sha256"]
    print("Synthetic promotion:", json.dumps(result, sort_keys=True))
    store = root / "artifacts/accepted"
    assert sha256(store / result["previous_bundle"] / "model.joblib") == sha256(
        reference / "model.joblib"
    )
    assert sha256(store / result["bundle"] / "model.joblib") == sha256(
        candidate / "model.joblib"
    )
    before = (store / "current.json").read_bytes()
    with (candidate / "model.joblib").open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(ValueError, match="candidate bytes changed"):
        gate.promote(root, candidate, reference)
    assert (store / "current.json").read_bytes() == before


def test_concurrent_gate_is_refused(gate_workspace):
    root, _, _ = gate_workspace
    candidate = make_candidate(gate_workspace)
    with gate.gate_lock(root):
        with pytest.raises(FileExistsError):
            gate.decide(root, candidate)


def test_incomplete_blocked_record_does_not_consume_evaluated_budget(gate_workspace):
    root, _, _ = gate_workspace
    candidate = make_candidate(gate_workspace)
    incomplete = root / "artifacts/candidates/ffffffffffff"
    incomplete.mkdir()
    assert gate.decide(root, incomplete)["decision"] == "blocked"
    # The existing fixture budget remains three. Add two measured historic runs.
    history = root / "reports/lab7-evidence"
    history.mkdir(parents=True)
    for i in range(2):
        (history / f"evaluation-{i}.json").write_text(
            json.dumps({"policy_version": 1, "run_id": str(i)})
        )
    assert gate.decide(root, candidate)["decision"] == "reject"


def test_interrupted_promotion_keeps_pointer_and_can_resume(
    gate_workspace, monkeypatch
):
    root, _, reference = gate_workspace
    candidate = make_candidate(gate_workspace, accept=True)
    assert gate.decide(root, candidate)["decision"] == "accept"
    replace = gate.os.replace

    def interrupted(*args):
        raise OSError("interrupted before pointer replacement")

    monkeypatch.setattr(gate.os, "replace", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        gate.promote(root, candidate, reference)
    store = root / "artifacts/accepted"
    assert not (store / "current.json").exists()
    assert (
        store / "versions" / sha256(reference / "model.joblib") / "model.joblib"
    ).is_file()
    monkeypatch.setattr(gate.os, "replace", replace)
    result = gate.promote(root, candidate, reference)
    assert json.loads((store / "current.json").read_text()) == result


def test_crlf_lock_matches_git_blob_but_changed_lock_is_blocked(
    gate_workspace, monkeypatch
):
    root, _, _ = gate_workspace
    lock = root / "uv.lock"
    lock.write_bytes(b"fixture lock\r\n")
    candidate = make_candidate(gate_workspace)
    monkeypatch.setattr(
        gate,
        "committed_bytes",
        lambda root, commit, path: (root / path).read_bytes().replace(b"\r\n", b"\n"),
    )
    assert gate.decide(root, candidate)["decision"] == "reject"
    assert not gate.checkout_hash_matches(b"different lock\n", sha256(lock))


def test_model_loading_failure_is_blocked(gate_workspace, monkeypatch):
    root, _, _ = gate_workspace
    candidate = make_candidate(gate_workspace)

    def incompatible(*args):
        raise RuntimeError("incompatible model environment")

    monkeypatch.setattr(gate, "load_artifact", incompatible)
    result = gate.decide(root, candidate)
    assert result["decision"] == "blocked"
    assert result["missing"][0]["claim"] == "loads_with_service_checks"
