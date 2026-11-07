# Bike Demand: Week 1 starter

Teams of 3–4 use one private GitHub repository throughout the course. Lab 1 is
repository setup, Git workflow and quality checks. Lab 2 adds validated data,
chronological splitting, a baseline comparison and local MLflow tracking.
No Docker, cloud account or MLflow server is needed this week.

## Setup: Lab 1

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/)
(`>=0.12.19,<0.13`). Python **3.12** is required; uv can download it. From the
`bike-demand/` root:

```bash
uv python install 3.12
uv sync --locked
uv run --locked python -m bike_demand.preflight
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest -q -m infra
uv run --locked pytest -q -m lab1
```

First setup requires internet for Python and the locked dependencies, unless
these exact distributions are already cached. The frozen UCI CSV ships here;
preflight does not download/repair it. `uv.lock` is shared across platforms;
that is not evidence that every OS has been tested. macOS setup has been checked;
Windows and Linux remain unverified. Remote CI is unavailable until a permitted
repository is configured and a workflow actually runs on the checked revision.
Do not regenerate the lock just to bypass an installation failure.

## Expected failure and exercise: Lab 1

`pytest -m infra` must pass immediately. `pytest -m lab1` has **one intentional
behavior failure** in `src/bike_demand/team.py`: the helper
`normalize_team_slug` does not yet meet the contract in `tests/lab1/test_team.py`
(trim, lowercase, join whitespace with hyphens, reject blank names with
`ValueError`). Read the assertion, diagnose the cause, make a small repair and add
one useful test of your own. Do not weaken assertions, skip tests or disable
checks. Sync or import errors, or failures outside `lab1`, are setup problems:
diagnose them separately.

Fill in `WORKING-AGREEMENT.md`. Use a task branch, open a pull request, and get a
review from another member before merging. Rotate driver/reviewer roles and the
main PR author between labs. Keep actual evidence in `reports/lab-01.md` and
`reports/week-01-team.md`; templates contain no pre-filled results.

## Expected failures: Lab 2

The student export has bounded TODOs in `src/bike_demand/`:

| File | Your task |
| --- | --- |
| `validate.py` | Categorical domains, finite normalised ranges, nonnegative counts, date windows |
| `split.py` | Chronological nonempty/disjoint/complete partitions; sort `(dteday, hr, instant)` |
| `train.py` | Ordered predictors, train-mean comparator, RF fit and validation MAE |

`NotImplementedError("TODO(Week 1, Lab 2): ...")` and failing exercise tests are
**expected before implementation**, not environment failures. Infra must pass
immediately. Do not skip/mute exercise tests or fabricate metrics to get green.
Tracking, metadata/history, configuration and input parsing are already supplied.
Read the failing test, inspect the contract, implement one TODO, and rerun:

```bash
uv run --locked pytest -q -m exercise
uv run --locked python -m bike_demand.validate --data data/raw/hour.csv
uv run --locked python -m bike_demand.train --config configs/baseline.yaml
uv run --locked pytest -q
```

Keep `data/raw/hour.csv` unchanged; use copies and `tests/fixtures/` for deliberate
faults. `missing-temp.csv` is the worked Fault A; design your own Fault B by
breaking exactly one contract rule or split boundary on a tiny copy, with a valid
control and a test of your own. The supplied `hum-out-of-range.csv` is another
worked example, not your Fault B. Missing hours are valid. Features and splits are fixed in the config and
code. Fit only on 2011 training rows; compare both predictors on the same
2012 January–June validation rows. Hold July–December 2012 test rows throughout
Weeks 1–4; do not compute test metrics. MAE is rentals/hour, not accuracy, and
RF is not required to beat the comparator. The task uses supplied weather;
it does not forecast future weather or station-level demand.

## Outputs and readback

Each successful train execution creates two separate MLflow runs, a saved
`artifacts/model.joblib` and `model-metadata.json`, latest `reports/metrics.json`,
and one appended `reports/metrics-history.jsonl` line. Metadata records feature
order, data identity, model version and run ID. A commit is recorded when Git is
available; `working_tree_dirty` prevents uncommitted code being mistaken for a
committed revision. Train reloads the trusted local model and verifies validation
MAE/metadata and logged artifact bytes. Never load untrusted joblib files.
Optional stretch, only after the core is complete and reviewed: run train again
unchanged and compare both run IDs and observed MAEs/history. Do not promise
byte-identical models across systems/library versions.

Viewer is optional; training does not depend on it:

```bash
uv run --locked mlflow server --backend-store-uri sqlite:///tracking/mlflow.db --default-artifact-root tracking/artifacts --no-serve-artifacts --host 127.0.0.1 --port 5000 --workers 1
```

`artifacts/`, `tracking/` and `.venv/` are ignored by Git. Team metrics may be
committed as evidence; never commit credentials or individual private reports.
The CI section below describes the checks that run on pull requests and on main.

## Lab 3: build and rerun

The image installs only `uv.lock` (`uv sync --locked`) and does not use the
laptop `.venv`. `.git`, `.venv`, `artifacts/` and `tracking/` stay out of the
build context (`.dockerignore`). Because `.git` is not in the image, a training
run records no commit SHA. That is a property of the package, not a different
dataset or config.

Build and rerun the Lab 2 baseline from a clean checkout. The run needs no
network: dependencies were installed at build time, and the command calls
`.venv/bin/python` directly.

```bash
docker build -t bike-demand:lab3 .
docker image inspect bike-demand:lab3 --format "{{.Id}}"
docker run --rm --network none bike-demand:lab3
docker run --rm --network none --entrypoint .venv/bin/pytest bike-demand:lab3 -q
```

A missing or stale lock must fail. On a throwaway copy, not in this checkout:

```bash
uv lock --check
# delete uv.lock, or change pyproject.toml without updating the lock
uv sync --locked
```

`uv sync --locked` exits non-zero and does not write a new lock. Do not run
`uv lock` to turn that failure into a pass.

## Lab 4: run and test the service

The Lab 4 image is the Lab 3 image with two changes: `uvicorn` is a declared
dependency, and the image trains once during the build. The default command
loads that artifact. It does not train on startup or on a request.

Publish the port only on this machine:

```bash
docker build -t bike-demand:lab4 .
docker run --rm -p 127.0.0.1:8000:8000 bike-demand:lab4
```

`GET /health` returns 200 and the artifact's `model_version` when the model
loaded, and 503 when it did not. `POST /predict` returns 200 with a finite
non-negative `prediction` and the same `model_version`. Invalid JSON returns
422. A valid request with no model returns 503.

```bash
curl.exe http://127.0.0.1:8000/health
curl.exe -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" -d "{\"season\":1,\"yr\":0,\"mnth\":1,\"hr\":8,\"holiday\":0,\"weekday\":1,\"workingday\":1,\"weathersit\":1,\"temp\":0.3,\"atemp\":0.3,\"hum\":0.6,\"windspeed\":0.2}"
```

Run the tests in the image, not only on the laptop:

```bash
docker run --rm --network none --entrypoint .venv/bin/pytest bike-demand:lab4 -q
```

To rerun training instead of serving, replace the command:

```bash
docker run --rm --network none --entrypoint .venv/bin/python bike-demand:lab4 -m bike_demand.train --config configs/baseline.yaml
```

## Deploy

From the repository root, build the image and start the service. These commands
were run in Windows PowerShell 5.1 with Docker Desktop (Linux containers). In
PowerShell, `curl` is an alias of `Invoke-WebRequest` and rejects `--fail`, so
the commands call `curl.exe`. A POSIX version of the `curl` lines follows.

```powershell
docker build -t bike-demand:lab5 .
docker run --rm -d --name bike-lab5 -e UVICORN_PORT=8080 -p 127.0.0.1:8000:8080 bike-demand:lab5
```

On a laptop, Uvicorn normally listens on loopback. Inside the image it listens
on all container interfaces so Docker can forward traffic. The publish rule
exposes the service only on the laptop's loopback address. The image defaults
to port 8000. Setting `UVICORN_PORT` at startup lets the same image listen on
8080 without a rebuild. The last port in the publish rule must match it.

From the host, wait for the model to load, then send one prediction.
Loading the model took 6 s to 40 s on our laptops. While it loads, Docker
Desktop accepts the connection and closes it (`curl: (52) Empty reply from
server`), which `--retry-connrefused` does not retry. `--retry-all-errors`
(curl 7.71 or later) retries it, and also retries a 503, so the wait fails
after about two minutes if the model never loads:

```powershell
curl.exe --fail --retry 60 --retry-all-errors --retry-delay 2 http://127.0.0.1:8000/health
curl.exe --fail -H "Content-Type: application/json" -d '{\"season\":1,\"yr\":0,\"mnth\":1,\"hr\":8,\"holiday\":0,\"weekday\":1,\"workingday\":1,\"weathersit\":1,\"temp\":0.3,\"atemp\":0.3,\"hum\":0.6,\"windspeed\":0.2}' http://127.0.0.1:8000/predict
```

PowerShell 5.1 strips the inner double quotes when it calls `curl.exe`, so
the JSON keeps `\"`. Without them the body is not valid JSON and `/predict`
returns 422. In a POSIX shell (Git Bash, macOS, Linux), use plain quotes instead:

```sh
curl --fail --retry 60 --retry-all-errors --retry-delay 2 http://127.0.0.1:8000/health
curl --fail -H 'Content-Type: application/json' -d '{"season":1,"yr":0,"mnth":1,"hr":8,"holiday":0,"weekday":1,"workingday":1,"weathersit":1,"temp":0.3,"atemp":0.3,"hum":0.6,"windspeed":0.2}' http://127.0.0.1:8000/predict
```

The Lab 4 build packages the trained model and its metadata in
`/app/artifacts`. Keeping them in the image lets a teammate run it without
mounting files from the training laptop. At startup the service checks the
metadata, feature order and model checksum, then loads the model once.
It is ready when `/health` returns HTTP 200 with `status: ok` and a
`model_version`. The prediction must include that version and a finite,
non-negative value. If the model is missing, the process stays up so the
operator can see the cause: both health and a valid prediction return HTTP 503
with a detail beginning `Model not available`. The service never retrains at
startup or during a request.

For this lab, “deployed” means a teammate can start the image from these
instructions and the external check confirms that the expected model and code
serve requests. Axel runs that final check from the host. A successful health
response alone establishes readiness. After verification, stop the container:

```sh
docker stop bike-lab5
```

Each HTTP request produces one JSON log entry with the method, route template, HTTP status, outcome, duration in milliseconds, and loaded model version. The model version is null when no model is loaded. Request and response bodies, query strings, headers, client IP addresses, and credentials are excluded to protect sensitive data.

### Deploy: design choices

Each answer gives the choice we kept, the option we rejected, and why.
The evidence for the Lab 5 run is in [reports/lab-05.md](reports/lab-05.md).

| Question | Kept | Rejected | Why |
|---|---|---|---|
| **Settings**: what changes between laptop and container? | Only run-time settings passed with `-e`: `UVICORN_HOST` (`0.0.0.0` in the image, loopback on a laptop) and `UVICORN_PORT`. The port is published on `127.0.0.1` only. | Rebuilding the image for each port, or publishing with `-p 8000:8000` on every interface. | One image serves every environment, so the image ID stays the identity of what runs. Publishing on loopback keeps the service off the local network. |
| **Model**: where does it come from at start-up? | From `/app/artifacts` inside the image. `docker build` trains it once, before the service exists. | Mounting `artifacts/` from the laptop with `-v`, or training when the container starts. | A mount makes the model depend on whose laptop runs it. Training at start-up is forbidden and slow. Baked in, the model is fixed by the image. |
| **Ready**: when is the service ready? | When `GET /health` returns HTTP 200 with `status: ok` and a `model_version`. This happens only after `load_artifact` checked the metadata, the feature order and the model SHA-256. | "The process is up" or the Uvicorn line `Application startup complete`. | Uvicorn starts even when the model failed to load. Only `/health` says that the model is usable. |
| **Broken**: what does it say if the model is missing? | The process stays up. `/health` and a valid `/predict` return HTTP 503 with `Model not available: <cause>`. Start-up writes `Model not loaded: <cause>` to the log. | Crash the container at start-up. | A crashed container hides the reason and a restart loop hides it again. A 503 with the cause lets an operator diagnose without a shell in the container. |
| **Log line**: what must one request tell an operator? | One JSON line per request on stdout, read with `docker logs`: `event`, `method`, `route`, `status_code`, `outcome` (`accepted`, `rejected`, `error`), `duration_ms` and `model_version`. Uvicorn's access log is off, so there is exactly one line per request. | Uvicorn's default access log alone, or one line per processing step. | The access log has no model version and no outcome. Several lines per request are hard to read without a request id. |
| **Secrets**: what must never appear in a log? | Never: request and response bodies (feature values, predictions), query strings, headers, client IP addresses, credentials, environment variables, and any metric on the July–December 2012 test rows. | Logging the request body "to debug". | The status, route and outcome are enough to separate a valid request from a rejected one. A body in a log is data we would then have to protect. |
| **Identity**: which id shows which model is running? | `model_version` (from `model-metadata.json`, returned by `/health`, `/predict` and each log line) for the model. The image ID (`docker image inspect`) and the Git commit it was built from for the code. | Trusting the image tag `bike-demand:lab5`. | A tag can be moved to another build. The image ID and `model_version` are derived from the content. `.git` is not copied into the image, so the commit is recorded outside the image, in the report next to the image ID. |
| **Expected**: who knows the expected model, and when? | The person who builds the image records the commit, the image ID and the `model_version` right after `docker build`, before any request. Axel's external check compares the running container against these values. | Reading the expected value from the running service itself. | A check that asks the service what to expect always passes. The expected values must be fixed before the run and come from outside the container. The command is in [Check from outside the container](#check-from-outside-the-container). |
| **Promise**: what does "deployed" promise to others? | The image built from a named commit starts from this README, answers `/health` and `/predict` as in Lab 4, writes one log line per request, and the external check passes against the expected model and code. | "The container is running." | A running container is not a verified deployment. "Deployed" here is local to one laptop: it does not promise model quality, a CI run, or a cloud URL (Lab 6). |
| **Failure**: break it once, what does it leave behind? | We start the same image without its model (the `rm` runs inside the throwaway container, the image is not changed). `/health` and a valid `/predict` answer 503 with `Model not available: FileNotFoundError: ... model.joblib`. `docker logs` shows `Model not loaded: ...` at start-up, then one line per request with `"outcome": "error"` and `"model_version": null`. The readiness `curl` exits 22. After `docker stop` nothing is left: `--rm` removes the container and its logs, and the image still contains `model.joblib`. Keep the logs before stopping. Raw output: [failure.txt](reports/lab5-evidence/failure.txt). | Corrupting the model file, or stopping the container mid-request. | A missing model is the most likely start-up fault, and it tests the "broken" answer above. A stranger can name the cause from the 503 detail and the log alone. |

To reproduce the failure:

```powershell
docker run --rm -d --name bike-lab5-broken -e UVICORN_PORT=8080 -p 127.0.0.1:8000:8080 --entrypoint sh bike-demand:lab5 -c "rm artifacts/model.joblib && exec .venv/bin/uvicorn bike_demand.api:app --no-access-log"
Start-Sleep 15   # wait until the process listens
curl.exe -i http://127.0.0.1:8000/health
docker logs bike-lab5-broken
docker stop bike-lab5-broken
```

### Check from outside the container

From the host, not from inside the container and not with TestClient. Pass the
expected model from the build output and the expected image from
`docker image inspect bike-demand:lab5 --format "{{.Id}}"`. Do not read
`model_version` from the live `/health` body and pass that value back in.

```bash
uv run --locked python scripts/check_deployment.py --container bike-lab5 --expect-model <model_version> --expect-image <image id>
```

The script inspects `--container` and sends `GET /health` and the README
`POST /predict` example to that container's published `127.0.0.1` port. A
stopped container exits 1 before any request. `--base-url` is optional; if you
pass one, it must be that same binding, or the check names the endpoint and
does not call another port. Exit 0 when the model and image claims match. A
wrong `--expect-model` exits 1 and the output names the model claim. On Windows,
`uv` must be at least 0.12.19. The recorded run is in
[reports/lab-05.md](reports/lab-05.md).

## CI

Workflow questions for Lab 6. The file is
[`.github/workflows/ci.yml`](.github/workflows/ci.yml). Image build and Cloud Run
deployment are separate parts of Lab 6.

| Question | Kept | Rejected | Why |
|---|---|---|---|
| **Trigger**: which changes start which checks? | Every pull request to `main`, every push to `main`, and a manual `workflow_dispatch` start the same four jobs. | Path filters, and a shorter suite on pull requests than on `main`. | A pull request can change a test and a report together. A filter that skips `reports/` would skip the test. The merge commit must not be the first time the full suite runs. |
| **Order**: which check fails first? | `lock`, then `style`, then `tests`, then `image`. `lock` is `uv sync --locked` and `bike_demand.preflight`. `style` is `ruff check` and `ruff format --check`. `tests` is `pytest -q`. Each job uses a fresh runner. The first three jobs install from the lock directly. The image job installs dependencies through the Dockerfile. `needs` only decides which job is allowed to start. | One job that runs every step, or `style` and `tests` in parallel. Also the old selection `pytest -q -m infra`, `pytest -q -m lab1` and `pytest -q tests/test_api.py`. | A bad lock should fail before Ruff, and a format error should fail before pytest. Parallel jobs can both be red. The old pytest commands left the other tests in this repository unrun. |
| **Evidence**: what can CI claim about the model? | A green run confirms locked installation, preflight, Ruff, pytest, and a successful Docker image build on the runner. | Treating CI as proof of a live Cloud Run revision or model quality. | Tests use fixtures and permitted training and validation data. The image build trains the packaged model. The live service requires a separate identity check. |

Permissions are `contents: read`. Actions are pinned to a commit, not a moving tag: `actions/checkout` at `v6.1.0` (`d23441a48e516b6c34aea4fa41551a30e30af803`) and `astral-sh/setup-uv` at `bec219d24cd3e171d82865faccec33120bb574f4`. `uv` is `0.12.23`, Python is `3.12`. Timeouts are 10, 10, 15 and 20 minutes for lock, style, tests and image respectively. A newer push on a pull request cancels the run it replaces. A push to `main` does not cancel another run.

The same order on a laptop, which is not a CI result:

```bash
uv sync --locked
uv run --locked python -m bike_demand.preflight
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest -q
docker build --progress=plain --tag bike-demand:ci-local .
```

Nils Giraud owns the Lab 6 image job. It builds the root Dockerfile after
the tests pass, tags the image with the checked-out revision, and records
its image ID. A build failure fails the job. Using a fresh runner verifies
that the build works without the laptop's virtual environment or artifacts.
For pull requests, the image tag uses the temporary merge revision checked
out by GitHub Actions. The run also identifies the pull request head commit.

### Lab 6 regression tests

Run `uv run --locked pytest -q tests/test_lab6_regressions.py`.

| Test | Defect it catches | How to reproduce the failure |
|---|---|---|
| `test_naive_validation_mae_matches_lab2_record` | A change to the split, train mean or validation scoring that changes the recorded baseline. | In a disposable checkout, round the naive validation MAE in `reports/metrics.json` to two decimals and run the test. |
| `test_boolean_csv_column_is_rejected` | A column containing only boolean literals passes numeric checks as zeros and ones. | Run at commit `267424d`, before the validator fix. The cases cover a count, a binary feature and a normalized weather feature. |

The Lab 2 and Lab 3 records agree exactly on this deterministic baseline
(validation MAE 154.23179306864967). The test uses exact equality with the
Lab 2 record instead of a percentage tolerance that could hide small changes.
The input snapshot and dependency lock are fixed. A new baseline requires
reviewing the recorded value. The [Lab 6 report](reports/lab-06.md) preserves
the failing assertion and both CI runs.

## Lab 4 prediction input contract

`src/bike_demand/schemas.py` defines `PredictionRequest`, the Pydantic request
model for the prediction API. All twelve fields are required in one flat JSON
object. Extra fields are rejected, including the target/leakage columns `cnt`,
`casual` and `registered`.

| Fields | Accepted values (inclusive) |
| --- | --- |
| `season` | Integer 1–4 |
| `yr`, `holiday`, `workingday` | Integer 0–1 |
| `mnth` | Integer 1–12 |
| `hr` | Integer 0–23 |
| `weekday` | Integer 0–6 |
| `weathersit` | Integer 1–4 |
| `temp`, `atemp`, `hum`, `windspeed` | Finite numbers 0–1 |

Validation is strict: numeric strings, booleans and null values are rejected.
Integer fields also reject floating-point values. Weather fields accept JSON
numbers (including integers) on the dataset's normalized scale, not Celsius or
percentages. Field order follows `configs/baseline.yaml`.

Example valid input:

```json
{
  "season": 1, "yr": 0, "mnth": 1, "hr": 8,
  "holiday": 0, "weekday": 1, "workingday": 1, "weathersit": 1,
  "temp": 0.3, "atemp": 0.3, "hum": 0.6, "windspeed": 0.2
}
```

`POST /predict` uses `PredictionRequest` from `bike_demand.schemas` as its
body. The handlers live in `src/bike_demand/api.py` and load the artifact saved
by `bike_demand.train`.

## Support and individual reports

If setup remains blocked after five minutes, contact the instructor using the
support route recorded in your working agreement. Do not spend the whole lab
repairing a laptop. Ask for an approved recovery function only if coding remains
blocked; acknowledge the supplied code and assistance in your report. Recovery
is instructor-controlled, not bundled here.

## Names, reports and screenshots

Repository names (lowercase, hyphens, the same for the whole course):

- Team repository: `mlops-<session>-<team-name>-bike-demand`, for example
  `mlops-thu1-sparrows-bike-demand`. Sessions: `thu1`, `thu2`, `fri1`, `fri2`
  (1 = morning, 2 = afternoon).
- Your private report repository: `mlops-<session>-<github-username>`, for example
  `mlops-thu1-minhtc`. You create it and invite the instructor (`minhtc-uca`). Start from the
  [report template](../report-template/README.md) and commit to `main`; no report
  pull request or CI is used.

Reports mix writing and images. Save screenshots in `reports/images/` and embed
them in the report (see the template). A screenshot supports, but does not replace,
the command, revision and your explanation. Never show tokens, passwords or
personal data. Team evidence goes in `reports/lab-01.md` and
`reports/week-01-team.md`, with team screenshots in `reports/images/`.
Each weekly report is due Sunday 23:59 of the same week (published time zone).
Assessment policy comes from the instructor, not this repository.
See `BACKLOG.md` for later labs.
