from pathlib import Path

import pandas as pd
import pytest

from bike_demand.validate import load_data

pytestmark = pytest.mark.exercise
FAULT = Path(__file__).parents[1] / "fixtures/weathersit-out-of-range.csv"


def test_fault_b_rejects_weathersit_above_4():
    with pytest.raises(ValueError, match="weathersit"):
        load_data(FAULT)


def test_fault_b_control_accepts_weathersit_4(tmp_path):
    frame = pd.read_csv(FAULT)
    frame.loc[0, "weathersit"] = 4
    path = tmp_path / "control.csv"
    frame.to_csv(path, index=False)
    assert len(load_data(path)) == 2
