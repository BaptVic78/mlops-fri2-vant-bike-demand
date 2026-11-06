"""The host check names the claim that failed. It does not call the app."""

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_deployment",
    Path(__file__).resolve().parents[1] / "scripts" / "check_deployment.py",
)
_CHECK = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CHECK)
claims = _CHECK.claims


def test_matching_model_and_image_pass():
    lines, failed = claims(
        "baseline-abc",
        "baseline-abc",
        "sha256:abc",
        "sha256:abc",
    )
    assert failed is False
    assert lines == [
        "claim model expected baseline-abc observed baseline-abc result ok",
        "claim image expected sha256:abc observed sha256:abc result ok",
    ]


def test_wrong_model_is_named():
    lines, failed = claims("baseline-abc", "baseline-other", "sha256:abc", "abc")
    assert failed is True
    assert (
        "claim model expected baseline-abc observed baseline-other result FAIL" in lines
    )
    assert lines[1].endswith("result ok")


def test_wrong_image_is_named():
    lines, failed = claims("baseline-abc", "baseline-abc", "sha256:abc", "sha256:def")
    assert failed is True
    assert lines[0].endswith("result ok")
    assert "claim image expected sha256:abc observed sha256:def result FAIL" in lines
