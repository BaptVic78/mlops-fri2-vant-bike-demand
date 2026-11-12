"""The held test scores only the model that was already accepted."""

import json

import joblib
import numpy as np
import pandas as pd
import pytest

from bike_demand import held_test
from bike_demand.preflight import sha256


class _Constant:
    def predict(self, frame):
        return np.ones(len(frame))


def _frame(values):
    return pd.DataFrame({"cnt": values, "season": values})


def test_checksum_failure_does_not_open_the_test_partition(tmp_path):
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"different-model")
    with pytest.raises(ValueError, match="not the accepted reference"):
        held_test.score_accepted_model(
            model_path,
            "d24c050e3631d5b4c2feb8cb571bef6382d8c975c42a5c11edd28de78a0b8c07",
            _frame([1]),
            _frame([1, 2, 3]),
            ["season"],
            0.0,
        )


def test_second_evaluation_is_refused(tmp_path):
    output = tmp_path / "final-held-test.json"
    output.write_text("{}\n")
    with pytest.raises(FileExistsError, match="already recorded"):
        held_test.refuse_second_evaluation(output)


def test_an_accepted_candidate_blocks_the_held_test(tmp_path):
    for name in held_test.EVALUATED_CANDIDATES:
        (tmp_path / f"{name}.json").write_text(
            json.dumps({"decision": "reject"}), encoding="utf-8"
        )
    (tmp_path / "extra.json").write_text(
        json.dumps({"decision": "accept"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="was accepted"):
        held_test.reference_remains_accepted(tmp_path)


def test_matching_checksum_scores_validation_before_the_test(tmp_path):
    model_path = tmp_path / "model.joblib"
    joblib.dump(_Constant(), model_path)
    validation = _frame([1, 1])
    test = _frame([1, 3])
    scored = held_test.score_accepted_model(
        model_path,
        sha256(model_path),
        validation,
        test,
        ["season"],
        0.0,
    )
    assert scored["validation_rescore_mae"] == 0.0
    assert scored["test_mae"] == 1.0
