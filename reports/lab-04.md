# Lab 4: prediction API in the container

Evidence for image commit `a560fac2f3f435f54c30b62cd07767f98a885d90`.
This image is the Lab 3 image plus a declared `uvicorn` dependency. Training
runs once during `docker build`. The running server only loads the artifact.

## Image

- Command: `docker build -t bike-demand:lab4 .`
- Image ID: `sha256:4fd2d802ba25fe4f715515ba80d0455f499c7fd55c49edfd63ab2b489a734f61`
- Default command: `.venv/bin/uvicorn bike_demand.api:app --host 0.0.0.0 --port 8000`

## Calls

`docker run --name lab4api -p 127.0.0.1:8000:8000 bike-demand:lab4`

The server log shows `Application startup complete` and does not train again.
Raw notes: [api.txt](lab4-evidence/api.txt).

| Call | Result |
|---|---|
| `GET /health` | 200 `{"status":"ok","model_version":"baseline-bcfe5dc5b701"}` |
| `POST /predict` with the README example | 200 `{"prediction":146.59529728935132,"model_version":"baseline-bcfe5dc5b701"}` |
| `POST /predict` with only `season` | 422, missing fields |

The prediction is one served response, not a test-set MAE. The July–December
2012 rows stay unused.

## Tests in the image

Command: `docker run --rm --network none --entrypoint .venv/bin/pytest bike-demand:lab4 -q`

Exit 0. [pytest.txt](lab4-evidence/pytest.txt): 149 passed, 2 warnings, 14.32s.
