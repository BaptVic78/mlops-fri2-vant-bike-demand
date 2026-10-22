"""Lab 4 API contract, using temporary artifacts and real startup/loading."""

import json

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.tree import DecisionTreeRegressor

from bike_demand.api import create_app
from bike_demand.preflight import sha256

# Explicit contract: changing the implementation must not redefine the tests.
VALID_REQUEST = {
    "season": 1,
    "yr": 0,
    "mnth": 1,
    "hr": 12,
    "holiday": 0,
    "weekday": 1,
    "workingday": 1,
    "weathersit": 1,
    "temp": 0.4,
    "atemp": 0.4,
    "hum": 0.5,
    "windspeed": 0.2,
}
BOUNDS = {
    "season": (1, 4),
    "yr": (0, 1),
    "mnth": (1, 12),
    "hr": (0, 23),
    "holiday": (0, 1),
    "weekday": (0, 6),
    "workingday": (0, 1),
    "weathersit": (1, 4),
    "temp": (0.0, 1.0),
    "atemp": (0.0, 1.0),
    "hum": (0.0, 1.0),
    "windspeed": (0.0, 1.0),
}
VERSION = "lab4-test-artifact-v1"


@pytest.fixture
def payload():
    return VALID_REQUEST.copy()


@pytest.fixture(scope="module")
def artifact(tmp_path_factory):
    root = tmp_path_factory.mktemp("api-artifact")
    model_path = root / "model.joblib"
    metadata_path = root / "model-metadata.json"
    # Synthetic data only; no course data, MLflow or production training pipeline.
    frame = pd.DataFrame([{**VALID_REQUEST, "hr": 0}, VALID_REQUEST])
    model = DecisionTreeRegressor(random_state=42).fit(frame, [10.0, 120.0])
    joblib.dump(model, model_path)
    metadata_path.write_text(
        json.dumps(
            {
                "features": list(VALID_REQUEST),
                "model_version": VERSION,
                "model_sha256": sha256(model_path),
            }
        ),
        encoding="utf-8",
    )
    return model_path, metadata_path


@pytest.fixture
def client(artifact):
    # Entering the context runs lifespan, including the real artifact loader.
    with TestClient(create_app(*artifact)) as client:
        yield client


def assert_field_rejected(response, field, error_type):
    assert response.status_code == 422, response.text
    assert any(
        error["loc"] == ["body", field] and error["type"] == error_type
        for error in response.json()["detail"]
    ), response.text


def test_health_reports_artifact_version(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_version": VERSION}


def test_prediction_and_feature_order(client, payload):
    # JSON key order must not change the fitted feature order.
    response = client.post("/predict", json=dict(reversed(list(payload.items()))))
    assert response.status_code == 200, response.text
    assert response.json() == {"prediction": 120.0, "model_version": VERSION}
    payload["hr"] = 0
    response = client.post("/predict", json=payload)
    assert response.status_code == 200, response.text
    assert response.json() == {"prediction": 10.0, "model_version": VERSION}


@pytest.mark.parametrize("field", VALID_REQUEST)
def test_missing_fields(client, payload, field):
    del payload[field]
    assert_field_rejected(client.post("/predict", json=payload), field, "missing")


@pytest.mark.parametrize("field", VALID_REQUEST)
def test_numeric_strings_are_not_coerced(client, payload, field):
    payload[field] = str(payload[field])
    error_type = "int_type" if field in list(VALID_REQUEST)[:8] else "float_type"
    assert_field_rejected(client.post("/predict", json=payload), field, error_type)


@pytest.mark.parametrize("field", VALID_REQUEST)
def test_booleans_are_not_numbers(client, payload, field):
    payload[field] = True
    error_type = "int_type" if field in list(VALID_REQUEST)[:8] else "float_type"
    assert_field_rejected(client.post("/predict", json=payload), field, error_type)


@pytest.mark.parametrize("field", ["temp", "atemp", "hum", "windspeed"])
@pytest.mark.parametrize("number", ["1e309", "-1e309"])
def test_nonfinite_weather_is_rejected(client, payload, field, number):
    # Valid JSON numbers which overflow a Python float, without emitting NaN JSON.
    payload[field] = "__overflow__"
    body = json.dumps(payload).replace('"__overflow__"', number)
    response = client.post(
        "/predict", content=body, headers={"Content-Type": "application/json"}
    )
    assert_field_rejected(response, field, "finite_number")


@pytest.mark.parametrize("field", BOUNDS)
@pytest.mark.parametrize("side", ["below", "above"])
def test_out_of_range_values(client, payload, field, side):
    lower, upper = BOUNDS[field]
    payload[field] = lower - 1 if side == "below" else upper + 1
    error_type = "greater_than_equal" if side == "below" else "less_than_equal"
    assert_field_rejected(client.post("/predict", json=payload), field, error_type)


@pytest.mark.parametrize("field", BOUNDS)
@pytest.mark.parametrize("side", [0, 1], ids=["lower", "upper"])
def test_boundary_values_are_accepted(client, payload, field, side):
    payload[field] = BOUNDS[field][side]
    response = client.post("/predict", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["model_version"] == VERSION


@pytest.mark.parametrize("field", ["cnt", "casual", "registered", "unexpected"])
def test_targets_and_other_extra_fields_are_forbidden(client, payload, field):
    payload[field] = 1
    assert_field_rejected(
        client.post("/predict", json=payload), field, "extra_forbidden"
    )


@pytest.mark.parametrize("missing", ["model", "metadata"])
def test_missing_artifact_returns_503(artifact, tmp_path, payload, missing):
    model_path, metadata_path = artifact
    if missing == "model":
        model_path = tmp_path / "missing-model.joblib"
    else:
        metadata_path = tmp_path / "missing-metadata.json"
    with TestClient(create_app(model_path, metadata_path)) as client:
        for response in (
            client.get("/health"),
            client.post("/predict", json=payload),
        ):
            assert response.status_code == 503, response.text
            assert "Model not available" in response.json()["detail"]
            assert "FileNotFoundError" in response.json()["detail"]
            assert "prediction" not in response.json()
