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
