"""Prediction service: load the trained baseline once at startup; never train."""

import json
import logging
import math
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from bike_demand.preflight import sha256
from bike_demand.schemas import PredictionRequest
from bike_demand.validate import FEATURES

logger = logging.getLogger(__name__)

# Repository root from this file (src/bike_demand/api.py), not from the shell cwd.
ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "artifacts/model.joblib"
METADATA_PATH = ROOT / "artifacts/model-metadata.json"


def load_artifact(model_path: Path, metadata_path: Path) -> tuple[object, str]:
    """Load the model saved by bike_demand.train after checking its metadata."""
    metadata = json.loads(metadata_path.read_text())
    version = metadata.get("model_version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("metadata: missing or invalid model_version")
    if metadata.get("features") != list(FEATURES):
        raise ValueError("metadata: feature order differs from the data contract")
    if sha256(model_path) != metadata.get("model_sha256"):
        raise ValueError("model: checksum does not match model-metadata.json")
    # Only the trusted, checksum-verified local artifact is unpickled.
    model = joblib.load(model_path)
    if list(getattr(model, "feature_names_in_", [])) != list(FEATURES):
        raise ValueError("model: fitted feature names differ from the data contract")
    return model, version


def create_app(
    model_path: Path = MODEL_PATH, metadata_path: Path = METADATA_PATH
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.model = None
        app.state.model_version = None
        app.state.unavailable_reason = None
        try:
            app.state.model, app.state.model_version = load_artifact(
                model_path, metadata_path
            )
        except Exception as error:
            # Stay up but not ready: both endpoints answer 503 with the reason.
            app.state.unavailable_reason = f"{type(error).__name__}: {error}"
            logger.error("Model not loaded: %s", app.state.unavailable_reason)
        yield

    app = FastAPI(title="Bike demand prediction", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        # Overflowing JSON numbers become inf; keep the error body valid JSON.
        detail = jsonable_encoder(
            error.errors(),
            custom_encoder={
                float: lambda value: value if math.isfinite(value) else str(value)
            },
        )
        return JSONResponse(status_code=422, content={"detail": detail})

    def loaded_model(request: Request) -> tuple[object, str]:
        state = request.app.state
        if getattr(state, "model", None) is None:
            reason = getattr(state, "unavailable_reason", None) or "not loaded"
            raise HTTPException(
                status_code=503, detail=f"Model not available: {reason}"
            )
        return state.model, state.model_version

    @app.get("/health")
    def health(request: Request) -> dict:
        _, version = loaded_model(request)
        return {"status": "ok", "model_version": version}

    @app.post("/predict")
    def predict(payload: PredictionRequest, request: Request) -> dict:
        model, version = loaded_model(request)
        row = pd.DataFrame([payload.model_dump()], columns=list(FEATURES))
        try:
            prediction = float(model.predict(row)[0])
        except Exception as error:
            logger.exception("Inference failed")
            raise HTTPException(status_code=500, detail="Inference failed") from error
        if not math.isfinite(prediction) or prediction < 0:
            logger.error("Invalid model output: %r", prediction)
            raise HTTPException(
                status_code=500, detail="Model returned an invalid prediction"
            )
        return {"prediction": prediction, "model_version": version}

    return app


app = create_app()
