import json

import pytest

from bike_demand.preflight import sha256
from bike_demand.reference_bundle import prepare_reference


def test_recovery_retains_reference_and_preserves_existing_pointer(workspace):
    root, _, source = workspace
    store = root / "artifacts/accepted"
    store.mkdir(parents=True)
    pointer = store / "current.json"
    pointer.write_text(json.dumps({"model_sha256": "existing-accepted-version"}))
    before_pointer = pointer.read_bytes()
    before_source = {path.name: path.read_bytes() for path in source.iterdir()}

    result = prepare_reference(root, source)
    retained = root / result["bundle"]
    assert sha256(retained / "model.joblib") == sha256(source / "model.joblib")
    assert result["metadata_sha256"] == sha256(retained / "model-metadata.json")
    assert result["model_version"] == "fixture"
    assert pointer.read_bytes() == before_pointer
    assert {path.name: path.read_bytes() for path in source.iterdir()} == before_source
    assert not (root / "artifacts/candidates").exists()

    assert prepare_reference(root, source) == result
    assert len(list((store / "versions").iterdir())) == 1


def test_mismatched_reference_is_refused_before_loading(workspace):
    root, _, source = workspace
    (source / "model.joblib").write_bytes(b"untrusted bytes")
    with pytest.raises(ValueError, match="reference: checksum"):
        prepare_reference(root, source)
    assert not (root / "artifacts/accepted/versions").exists()
    assert not (root / "artifacts/.gate-lock").exists()


def test_corrupted_retained_reference_is_refused(workspace):
    root, _, source = workspace
    result = prepare_reference(root, source)
    retained = root / result["bundle"]
    (retained / "model.joblib").write_bytes(b"changed retained bytes")
    with pytest.raises(ValueError, match="corrupted retained version"):
        prepare_reference(root, source)
    assert not (root / "artifacts/.gate-lock").exists()
