# Lab 5: run it, log it, check it

Evidence for the service built from `main` at commit
`461c86705930a81ac81951ddbed44c637239261e` (Lab 4, plus Victor's start-up
settings from PR #15 and Nils' request logs from PR #16). The run was local, on one laptop
(Windows, Docker Desktop 28.5.1). It is not a CI run. The design choices are in the
README, section [Deploy](../README.md#deploy).

| Part | Owner | Reviewer | PR |
|---|---|---|---|
| Start-up | Victor Rouleau | Nils Giraud | #15 |
| Logs | Nils Giraud | Thomas Soubagne | #16 |
| External check | Axel Alacache | Victor Rouleau | pending |
| README Deploy and this report | Thomas Soubagne | Axel Alacache | this PR |

## Commit → image

- Commit: `461c86705930a81ac81951ddbed44c637239261e`, built from a clean checkout of that commit.
- Command: `docker build -t bike-demand:lab5 .` (exit 0)
- Image ID: `sha256:76962f6103dab76d24a6b3d2d26705a41ea32cf10cc2367cb8879f166a3f88af`
- Expected model, recorded after the build: `baseline-462260e47aa9`

Raw record: [image-id.txt](lab5-evidence/image-id.txt).

## Image → run

```sh
docker run --rm -d --name bike-lab5 -e UVICORN_PORT=8080 -p 127.0.0.1:8000:8080 bike-demand:lab5
```

The port is set at run time (`UVICORN_PORT=8080`) and published on loopback only.
The container did not train. Its log goes from `Waiting for application startup` to
`Application startup complete` in 6 s, which is the time it took to load the model.

## Run → requests and log lines

Raw requests and responses: [requests.txt](lab5-evidence/requests.txt).
Raw `docker logs -t`: [logs.txt](lab5-evidence/logs.txt).

| Request | Response | Log line (from `docker logs`) |
|---|---|---|
| `GET /health` | 200 `{"status":"ok","model_version":"baseline-462260e47aa9"}` | `"route": "/health", "status_code": 200, "outcome": "accepted", "duration_ms": 5.518, "model_version": "baseline-462260e47aa9"` |
| `POST /predict`, README example | 200 `{"prediction":146.59529728935132,"model_version":"baseline-462260e47aa9"}` | `"route": "/predict", "status_code": 200, "outcome": "accepted", "duration_ms": 68.359, "model_version": "baseline-462260e47aa9"` |
| `POST /predict`, same example with `hr: 24` | 422, `hr` must be ≤ 23 | `"route": "/predict", "status_code": 422, "outcome": "rejected", "duration_ms": 1.891, "model_version": "baseline-462260e47aa9"` |

There is one log line per request. Someone who reads only the logs can tell
the accepted prediction from the rejected one, the duration and the model.
No request body, header or IP address appears. The prediction is a single
served value, not a metric. The July–December 2012 test rows are not used.

The `model_version` in the responses and log lines matches the value recorded
after the build. Comparing it with an independent expected value is the job of
Axel's external check, still pending (see below).

## Deliberate failure

We started the same image without its model file:

```sh
docker run --rm -d --name bike-lab5-broken -e UVICORN_PORT=8080 -p 127.0.0.1:8000:8080 --entrypoint sh bike-demand:lab5 -c "rm artifacts/model.joblib && exec .venv/bin/uvicorn bike_demand.api:app --no-access-log"
```

Raw output: [failure.txt](lab5-evidence/failure.txt).

- `GET /health` and a valid `POST /predict` returned **503**, with the detail
  `Model not available: FileNotFoundError: [Errno 2] No such file or directory: '/app/artifacts/model.joblib'`.
- The README readiness wait (`curl --fail --retry-all-errors`) exited **22**, not 0.
- `docker logs` showed `Model not loaded: FileNotFoundError: ...` at start-up,
  then `"status_code": 503, "outcome": "error", "model_version": null` for each request.
- **What it left behind:** after `docker stop`, nothing. `--rm` removed the container
  and its logs, and `docker ps -a` lists no `bike-lab5` container. The image is
  unchanged (same ID, `artifacts/` still has `model.joblib`). The logs exist
  only because we saved them before stopping.

A stranger can name the cause from the 503 detail and the log alone.

## Observations

- **README fix.** The first README wait (`curl --retry 15 --retry-connrefused`)
  failed here with `curl: (52) Empty reply from server`. Docker Desktop accepts the
  connection while the model is still loading and then closes it. In one run, loading
  took about 40 s. The README now uses `--retry 60 --retry-all-errors --retry-delay 2`.
- **Windows shell (review by Axel).** The evidence above was recorded with `curl` in
  Git Bash. In PowerShell, `curl` is `Invoke-WebRequest`, so the README now uses `curl.exe`.
  These README commands were rerun in PowerShell 5.1 on the same image: health 200,
  predict 200, and 503 for the failure. With single-quoted JSON, PowerShell 5.1 sent an
  invalid body and `/predict` returned 422, so the README escapes the quotes (`\"`).
- The start-up line `Model not loaded: ...` is plain text, not JSON like the request
  lines. It is still readable with `docker logs`.

## External check (pending)

Axel's script, run from the host against the running container, is not merged
yet. We report no check result until it has run. When it is merged, this
section will cite: the command, its output against `bike-demand:lab5` (expected exit 0),
and one deliberately wrong expected value (expected non-zero exit, naming the
claim that fails).
