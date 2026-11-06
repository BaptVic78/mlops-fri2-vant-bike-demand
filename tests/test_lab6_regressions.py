import json
from pathlib import Path

import pandas as pd
import pytest

from bike_demand.split import split_data
from bike_demand.train import compare_mean
from bike_demand.validate import load_data

ROOT = Path(__file__).resolve().parents[1]


def test_naive_validation_mae_matches_lab2_record():
    record = json.loads((ROOT / "reports/metrics.json").read_text())
    parts = split_data(load_data(ROOT / "data/raw/hour.csv"))
    mean, mae = compare_mean(parts["train"]["cnt"], parts["validation"]["cnt"])
    assert mean == record["train_mean"]
    assert mae == record["validation_mae"]["naive_train_mean"]


@pytest.mark.parametrize("field", ["cnt", "workingday", "hum"])
def test_boolean_csv_column_is_rejected(tmp_path, field):
    frame = pd.read_csv(ROOT / "tests/fixtures/missing-hours.csv")
    frame[field] = [True, False] * 3
    path = tmp_path / "boolean-column.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match=field):
        load_data(path)
