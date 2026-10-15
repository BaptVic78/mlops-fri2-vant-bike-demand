
"""Fault B: reject an invalid hour while accepting valid control data."""

from pathlib import Path

import pytest

from bike_demand.validate import load_data

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_fault_b_valid_control():
    """The unchanged control must pass validation."""
    frame = load_data(FIXTURES / "fault-b-control.csv")

    assert len(frame) == 3
    assert frame["hr"].between(0, 23).all()


def test_fault_b_rejects_invalid_hour():
    """An hour of 24 violates the categorical domain contract."""
    with pytest.raises(ValueError, match="hr"):
        load_data(FIXTURES / "fault-b-invalid-hour.csv")
