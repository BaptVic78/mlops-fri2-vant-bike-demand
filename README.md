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
CI currently checks only infrastructure/quality; expand it in Week 3.

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
use a POSIX shell and Docker with Linux containers.

```sh
docker build -t bike-demand:lab5 .
docker run --rm -d --name bike-lab5 -e UVICORN_PORT=8080 -p 127.0.0.1:8000:8080 bike-demand:lab5
```

On a laptop, Uvicorn normally listens on loopback. Inside the image it listens
on all container interfaces so Docker can forward traffic. The publish rule
exposes the service only on the laptop's loopback address. The image defaults
to port 8000. Setting `UVICORN_PORT` at startup lets the same image listen on
8080 without a rebuild. The last port in the publish rule must match it.

From the host, wait for the model to load, then send one prediction:

```sh
curl --fail --retry 15 --retry-connrefused --retry-delay 1 http://127.0.0.1:8000/health
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
