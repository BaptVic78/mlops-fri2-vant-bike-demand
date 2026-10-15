from pathlib import Path

import pandas as pd
import pytest

from bike_demand.validate import load_data

pytestmark = pytest.mark.exercise
FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_fault_b_invalid_hour_with_valid_control(tmp_path):
    source = FIXTURES / "missing-hours.csv"
    control = tmp_path / "valid-control.csv"
    control.write_bytes(source.read_bytes())
    assert len(load_data(control)) == 6

    # Change exactly one cell; all other values stay identical to the control.
    frame = pd.read_csv(control)
    frame.loc[0, "hr"] = 24
    fault = tmp_path / "invalid-hour.csv"
    frame.to_csv(fault, index=False)
    before = fault.read_bytes()

    with pytest.raises(ValueError, match="hr"):
        load_data(fault)

    assert fault.read_bytes() == before
    assert control.read_bytes() == source.read_bytes()
