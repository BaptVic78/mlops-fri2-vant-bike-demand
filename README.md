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

## Pipeline and gate

Lab 7 split: policy (Thomas), pipeline command (Axel), gate (Victor),
promotion and Cloud Run (Nils). This section is the shared contract. It was
written and merged before any candidate was trained.

- Policy: [`configs/gate-policy.yaml`](configs/gate-policy.yaml), version 1.
  The values are there and the reasons are below.
- Reference evidence: [`reports/lab7-evidence/reference-baseline.txt`](reports/lab7-evidence/reference-baseline.txt).
- Decision records: `reports/lab7-decisions/`, one JSON per candidate (gate PR).
- Pipeline command: `uv run --locked python -m bike_demand.pipeline`.

### Produce a candidate

Start from a clean checkout and install with `uv sync --locked`. Supply a trusted
accepted bundle containing `model.joblib` and `model-metadata.json`. Its model
checksum must match the reference in the policy. For the initial reference,
the builder can recover these files from the retained Lab 7 reference image:

```sh
docker create --name lab7-reference bike-demand:lab7-ref
mkdir -p artifacts/reference
docker cp lab7-reference:/app/artifacts/model.joblib artifacts/reference/model.joblib
docker cp lab7-reference:/app/artifacts/model-metadata.json artifacts/reference/model-metadata.json
docker rm lab7-reference
sha256sum artifacts/reference/model.joblib
uv run --locked python -m bike_demand.pipeline --config configs/baseline.yaml --reference artifacts/reference
```

The retained image must have ID
`sha256:f4177c160cff1b9e6233e77ca24b48a9e20bbe5ffb530c06217c15d44d7a0935`.
Ask its builder for that image or the trusted bundle if it is unavailable locally.
The reference checksum is checked before loading its bytes. Keep downloaded
joblib files restricted to trusted sources.

The command prints `artifacts/candidates/<run_id>/`. This contains the model,
metadata, effective config, policy copy, MLflow run ID and `evaluation.json`.
The evaluation includes rescored reference, train-mean and candidate MAEs on the
same validation rows. Model readback uses the service's loading checks.
Exit 0 means candidate evidence is complete. Pass that evidence to the gate
for its accept/reject/blocked decision and candidate-budget accounting.

A repeat with identical inputs refuses to overwrite the completed directory.
For an interrupted run, partial output is removed. A stale `.tmp-<run_id>`
left by a killed process requires confirming the process has stopped before
removing that partial directory and retrying. Completed candidates stay intact.
The legacy baseline command keeps its Week 1 behavior. Use the pipeline command
for Lab 7 candidates so training leaves `artifacts/model.joblib` untouched.

To exercise a blocked run, supply an empty reference directory. The command
exits 2 and names the missing model file. Synthetic regression tests cover
reference mismatch, dirty source, invalid settings, interruption cleanup and
preservation of accepted model bytes:

```sh
uv run --locked pytest -q tests/test_pipeline.py
```

Today `python -m bike_demand.train` always writes `artifacts/model.joblib`,
and the service loads that same path. Running training is therefore already
an unreviewed promotion on that machine. This is the overwrite risk that the
pipeline must remove.

### Pipeline boundary

| Question | Kept | Rejected | Why |
|---|---|---|---|
| **Stage**: what does each stage consume and produce? | Four stages. `validate`: CSV and candidate config, produces the snapshot hash and partition summary. `train`: train rows and config, produces a candidate bundle (`model.joblib` and `model-metadata.json`) in `artifacts/candidates/<run_id>/`. `evaluate`: candidate bundle, reference bundle and validation rows, produces `evaluation.json`. `gate`: `evaluation.json` and the policy, produces the decision record. Promotion is a fifth, manual step outside the pipeline. | One script that trains, scores and replaces `artifacts/model.joblib`. | Each stage leaves a file a reviewer can open. The gate reads evidence, not a live model, so a rejection cannot have already replaced anything. |
| **Entry point**: what does a clean checkout need? | One command run with `uv run --locked` after `uv sync --locked`, given a candidate config file. It needs the frozen CSV (tracked), the policy (tracked) and the reference bytes `d24c050e…` fetched from the accepted store and checked against their SHA-256. | Needing the author's `artifacts/` or `tracking/` folder. | A clean runner does not inherit laptop models or the local MLflow store. If the reference bytes cannot be fetched, the run is blocked rather than compared with nothing. |
| **Failure**: what can safely be retried? | `validate`, `train` and `evaluate` can be rerun as often as needed: they write only inside their own run directory, and the same inputs on the same platform give the same bytes (`random_state=42`, `n_jobs=1`). An existing decision record is never overwritten. Promotion is never retried automatically. | Retrying the whole pipeline, decision included, until it passes. | Retrying training cannot change the outcome. Retrying a decision would let someone retry until the result is accepted. |
| **Partial**: what happens to incomplete output? | A stage writes to `artifacts/candidates/.tmp-<run_id>/` and renames it only after the metadata and checksum are written. A run directory without a complete `model-metadata.json` is incomplete: the gate answers `blocked` and the directory is deleted before the rerun. | Reusing a half-written bundle, or trusting that a file exists. | A truncated `model.joblib` can still exist and even load. Only the recorded checksum shows that the evaluated bytes are complete. |
| **Identity**: which inputs determine this run? | `run_id` = first 12 hex characters of a SHA-256 over: training commit, `uv.lock` hash, `data_sha256`, candidate config hash and policy hash. The record also stores the platform (image ID or OS) because bytes depend on it. The output identity is `model_sha256`. | `model_version` (`baseline-<random>`), or a timestamp. | `model_version` is drawn at random at each build: the same bytes got `bb0954a06404` in Lab 5 and `83202f56543b` today. Two runs with identical inputs should share an id, and different inputs must not. |

### Decide and retain accepted versions

After producing a complete candidate, run:

```sh
uv run --locked python -m bike_demand.gate --candidate artifacts/candidates/<run_id>
```

The gate writes `reports/lab7-decisions/<run_id>.json` once. It exits 0 for
accept, 1 for a measured rejection, and 2 for missing or invalid evidence.
The record names failed claims with observations and thresholds. Repeating a
decision refuses to replace its record. A missing bundle or changed checksum
blocks the decision before model loading.

The gate checks the training commit's policy and lock, the input identity,
saved model bytes and metadata, ordered features, frozen data, date partitions,
finite scores and readback evidence. The pipeline now retains the original
config bytes in `input-config.yaml`; earlier baseline runs are checked against
the preset in their training commit. Recorded and locally completed candidates
count toward the policy budget, including attempts awaiting a decision.
Evaluation scores remain claims produced by the pipeline, whose code is reviewed.

After an accept decision, a reviewed manual operation can prepare the local
accepted package for the deployment owner:

```sh
uv run --locked python -m bike_demand.gate --candidate artifacts/candidates/<run_id> --promote --previous artifacts/reference
```

Both the previous and new trusted bundles are retained under
`artifacts/accepted/versions/<model_sha256>/`. A promotion record is saved in
`artifacts/accepted/promotions/`, then `artifacts/accepted/current.json` is
atomically replaced. Use the pointer's `bundle` and `previous_bundle` paths
to recover either package. Nils uses these retained bytes for the Cloud Run
handoff. The original `artifacts/model.joblib` is kept intact during gate work.
Subsequent promotions must supply the bundle currently named by the pointer.

One exclusive `artifacts/.gate-lock` serializes decisions and promotions.
After a hard kill, confirm the owning process has stopped before removing a
stale lock. An interrupted promotion retains the old pointer and can resume
with the same inputs. Model versions are archived before advancing the pointer.
Promotion refuses rejected decisions or changed policy, evidence and model bytes.

For the final remaining canonical attempt, `configs/candidate-lab7.yaml`
declares 150 trees, depth 20, minimum leaf size 2, and all features at each split.
The hypothesis is that deeper trees can capture calendar/weather interactions
while a two-observation leaf and more trees reduce unstable predictions.
The fixed seed and single worker follow policy version 1. Both earlier attempts
and this one count toward its budget of three. Results and gate records are
linked from [the Lab 7 report](reports/lab-07.md).

```sh
uv run --locked pytest -q tests/test_gate.py tests/test_pipeline.py
```

### Serve and recover the accepted reference

All three canonical candidates were rejected under policy version 1. Keep the
accepted reference checksum `d24c050e3631d5b4c2feb8cb571bef6382d8c975c42a5c11edd28de78a0b8c07`.
The three-attempt budget is exhausted. Victor deployed the retained reference
from reviewed main `80f31db`, and Nils independently verified the private service.

| Deployment | Observed value |
|---|---|
| Project / region / service | `fourth-eon-424715-k1` / `europe-west1` / `bike-demand-lab7` |
| Authenticated URL | `https://bike-demand-lab7-obot7iy6yq-ew.a.run.app` |
| Serving revision, 100% traffic | `bike-demand-lab7-refcurrent80f31db` |
| Previous revision, retained and Ready | `bike-demand-lab7-refbase80f31db` |
| Expected model version | `baseline-28fdf1958b8a` |
| Immutable image | `europe-west1-docker.pkg.dev/fourth-eon-424715-k1/bike-demand/service@sha256:6dd4148b94859b21b05769af5971892e604fee3c2a3f201c411910a080f932ff` |

The [HTTP results](reports/lab7-evidence/cloud-run-nils-http.json) show 200 for
health and prediction, 422 for `hr=24`, and 403 without authentication.
The [revision record](reports/lab7-evidence/cloud-run-nils-revisions.json) links
both Ready revisions to this image. The previous revision receives no traffic;
its inactive/retired state is normal at zero traffic and it remains available.
Both revisions contain the same accepted model; this is retention of the
reference, not a promotion of a rejected candidate.

Authenticate with your own authorized account, then run from the repository:

```powershell
gcloud auth login
uv sync --locked
uv run --locked python scripts/check_cloud_run.py --base-url https://bike-demand-lab7-obot7iy6yq-ew.a.run.app --expect-model baseline-28fdf1958b8a
gcloud run services describe bike-demand-lab7 --project=fourth-eon-424715-k1 --region=europe-west1 --format="yaml(status.traffic,status.conditions)"
gcloud run revisions describe bike-demand-lab7-refbase80f31db --project=fourth-eon-424715-k1 --region=europe-west1 --format="yaml(metadata.name,status.conditions,status.imageDigest)"
```

Use `--gcloud <absolute-path-to-gcloud.cmd>` if the CLI is outside PATH.
The checker keeps the identity token in memory, refuses HTTP redirects and
prints no credentials. It checks the independently supplied model version,
finite nonnegative prediction, invalid-hour rejection and anonymous denial.
Exit 0 means all HTTP checks passed; an incorrect expected version exits 1.
This checks the API contract, not predictive quality on unseen data.

Recover the exact deployed package from the digest above:

```powershell
gcloud auth configure-docker europe-west1-docker.pkg.dev
$AcceptedImage = 'europe-west1-docker.pkg.dev/fourth-eon-424715-k1/bike-demand/service@sha256:6dd4148b94859b21b05769af5971892e604fee3c2a3f201c411910a080f932ff'
docker pull $AcceptedImage
New-Item -ItemType Directory -Force artifacts/cloud-reference | Out-Null
docker create --name lab7-cloud-recovery $AcceptedImage
docker cp lab7-cloud-recovery:/app/artifacts/model.joblib artifacts/cloud-reference/model.joblib
docker cp lab7-cloud-recovery:/app/artifacts/model-metadata.json artifacts/cloud-reference/model-metadata.json
docker rm lab7-cloud-recovery
Get-FileHash artifacts/cloud-reference/model.joblib,artifacts/cloud-reference/model-metadata.json -Algorithm SHA256
```

Before loading, compare the model checksum with the policy above and metadata
checksum with `bef55cb388d8d784f41b029269fc41a1d7e555a820714d46429d3fcd66fdc8bc`.
The deployed metadata uses `baseline-28fdf1958b8a`; the earlier local archive
below uses `baseline-f4459fc6e2a4` for identical model bytes. Retention is keyed
by model checksum and reuses an existing verified package's metadata. Keep the
separate `artifacts/cloud-reference` directory to preserve the exact deployed
metadata alongside the immutable registry image.

The accepted-image build copies the existing bundle, checks its checksum and
calls the service loader. Victor supplied the archived
[Dockerfile](reports/lab7-evidence/Dockerfile.accepted) and
[Cloud Build configuration](reports/lab7-evidence/cloudbuild-accepted.yaml),
used from a build context at `80f31db` with an `accepted/` bundle directory.
These are deployment records, not the root CI Dockerfile, which still trains
at build time. Do not use a fresh training run to replace accepted bytes.
The [handoff record](reports/lab7-evidence/accepted-handoff.json) separates
Victor's reported Cloud Build result from Nils's independent image and API checks.

Keep both revisions and their registry image. If a later live deployment fails,
return traffic to the retained revision and rerun the HTTP checker:

```powershell
gcloud run services update-traffic bike-demand-lab7 --project=fourth-eon-424715-k1 --region=europe-west1 --to-revisions=bike-demand-lab7-refbase80f31db=100
uv run --locked python scripts/check_cloud_run.py --base-url https://bike-demand-lab7-obot7iy6yq-ew.a.run.app --expect-model baseline-28fdf1958b8a
```

Restoring the current revision uses the same traffic command with
`bike-demand-lab7-refcurrent80f31db=100`. No traffic was changed during Nils's
verification. The Lab 8 rollback procedure is in [RUNBOOK.md](RUNBOOK.md).

#### Earlier local recovery

Obtain the trusted image or bundle from its builder. Restore a saved image with
`docker load --input artifacts/accepted-image.tar`. Use the independently
recorded image ID when extracting the files. The local recovery check used
the retained Lab 6 image in
[accepted-handoff.json](reports/lab7-evidence/accepted-handoff.json), whose model
checksum matches the policy. These PowerShell commands recover that bundle:

```powershell
$AcceptedImage = 'sha256:13594e76dc0fcd196df50b3f21c9a707e92a1cdca11aad759be25a7430a7f369'
New-Item -ItemType Directory -Force artifacts/reference | Out-Null
docker create --name lab7-reference-recovery $AcceptedImage
docker cp lab7-reference-recovery:/app/artifacts/model.joblib artifacts/reference/model.joblib
docker cp lab7-reference-recovery:/app/artifacts/model-metadata.json artifacts/reference/model-metadata.json
docker rm lab7-reference-recovery
uv sync --locked
uv run --locked python -m bike_demand.reference_bundle --source artifacts/reference
```

The command verifies the model checksum before loading, applies the existing
service-loader checks and retains the package under
`artifacts/accepted/versions/<model_sha256>/`. It prints the model version,
model checksum, metadata checksum and recovery path. Repeating the command
reuses the verified retained package. It leaves the accepted pointer in place.
Keep bundles, saved images and the virtual environment outside Git.

The [Lab 7 report](reports/lab-07.md) records both local recovery and the live
verification completed after Victor's deployment handoff.
Deployment and traffic changes follow the official
[Cloud Run deployment guide](https://cloud.google.com/run/docs/deploying) and
[revision rollback guide](https://cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration).

### Fair comparison

| Question | Kept | Rejected | Why |
|---|---|---|---|
| **Reference**: which accepted version is frozen? | The Week 1 RF preset (`n_estimators=50, max_depth=10, random_state=42, n_jobs=1`), identified by `model_sha256` `d24c050e3631d5b4c2feb8cb571bef6382d8c975c42a5c11edd28de78a0b8c07`. The Docker build reproduces these exact bytes (Lab 3, Lab 5 and the reference evidence above). | Whatever `artifacts/model.joblib` holds on a laptop. | On Windows the same config gave other bytes (`fd98ceaf…`) with the same MAE. A file named `model.joblib` is not a version; the hash is. |
| **Observations**: same rows and labels for both? | Yes. Candidate, reference and the train-mean baseline are scored in the same run on the same 4,358 validation rows (2012-01-01 to 2012-06-30), `cnt` as label. The run checks the row count and date bounds before scoring. | Reusing the reference MAE from an old report without rescoring. | A score from another run only compares if nothing in its context changed. Rescoring the reference bytes costs a few seconds. |
| **Metric**: what does the score mean, in what unit? | Validation MAE on `cnt`, in rentals per hour: on average, how far a prediction is from the observed hourly count. Lower is better. Reference 86.85, train-mean baseline 154.23. | RMSE or R². | MAE is in the same unit as the prediction the API returns, so a difference reads directly as bikes per hour. It is the metric already recorded since Lab 2. |
| **Margin**: what size of change matters, and why? | A candidate must be at least **1.0 rental/hour** better than the reference and than the train-mean baseline. | Any improvement (`<`), or a percentage. | The service predicts a count of bikes: an average gain below one bike per hour changes no operational decision. Without a margin, a model that is equivalent but has different bytes would replace the reference and add a promotion with no benefit. A fixed number is simple to check and does not depend on the reference score. |
| **Provenance**: what makes an old score reusable? | Only as a cross-check: the rescored reference MAE must equal `recorded_validation_mae` (86.84685685591091) exactly. If not, the run is `blocked`: data, lock or bytes changed and must be explained first. | Treating a stored number as the reference result. | The Lab 2 record, the Lab 3 rerun and today's rebuild all give exactly 86.84685685591091. A difference means that the evaluation context moved, and then no comparison is fair. |

### Gate criteria

All criteria are mandatory. A better MAE cannot make up for a missing check.

| Claim | Criteria (policy keys) | Why this form and threshold |
|---|---|---|
| **Quality** | `beat_naive_by`, `beat_reference_by`, `reference_rescore_must_equal_record` | Two references measured on the same rows: the baseline any model must beat, and the version currently accepted. The margin is explained above. |
| **Operation** | `max_model_bytes` 50 MiB, `loads_with_service_checks`, `predictions_finite_non_negative` | The reference file is 5.0 MiB and loading already takes 6 s to 40 s on our laptops. 50 MiB (10 times the reference) still fits easily in Cloud Run's default 512 MiB memory with the Python process. The bundle must pass the same `load_artifact` checks as the service, otherwise it would start with a 503. A count cannot be negative or infinite. |
| **Integrity** | `data_sha256_matches`, `features_match_in_order`, `partitions_match`, `clean_working_tree`, `policy_on_training_commit`, `evaluated_bytes_are_decided_bytes`, `readback_mae_equals_measured` | These are the Lecture 7 data checks, plus a link from the decision to the exact bytes. A dirty tree means that the code that trained the model is unknown (the Lab 2 record has `working_tree_dirty: true`). The policy must already exist in the training commit. |

**Settings guard.** A candidate may change only `n_estimators` (10 to 300),
`max_depth` (4 to 30), `min_samples_leaf` (1 to 20) and `max_features`
(`1.0`, `0.5`, `sqrt`). `random_state=42` and `n_jobs=1` stay fixed, as do the
CSV, the twelve ordered features and the split. `load_config` in `train.py`
already rejects any other `data` and `features`. The pipeline PR must keep
these checks and allow only these keys. Budget: **3 candidates** under policy
version 1, rejections included. Every attempt gets a decision record.

### What failure means

| Question | Kept | Rejected | Why |
|---|---|---|---|
| **Invalid**: what evidence must never count as pass? | A score on rows other than the 4,358 validation rows, any metric on the July–December 2012 test rows, a bundle whose SHA-256 differs from the decided one, a run from a dirty tree, a laptop result presented as a CI result. | Accepting "close enough" evidence. | Each of these changes what the score means. The gate would then decide on something other than the bytes it promotes. |
| **Missing**: what if a required check did not run? | The outcome is `blocked` (exit 2). The record lists the missing check by name. | Skipping it, or counting it as passed. | An unavailable check is not a passed check. |
| **Reject**: which measured rule failed? | `reject` (exit 1) only when every check ran. The record names each failed rule with the measured value and the threshold, for example `beat_reference_by: candidate 86.20, needed <= 85.85`. | One message such as "quality too low". | A reviewer must be able to check the reason from the numbers without rerunning the pipeline. |
| **Blocked**: what must be repaired before deciding? | The cause in the record: unreachable or mismatched reference bytes, an incomplete run directory, a changed data hash, a dirty tree. After the repair, a new run gets a new record. The blocked record stays. | Editing the old record so that it shows a decision. | Records are evidence. A blocked run that becomes "accept" in the same file hides what happened. |
| **Status**: how does CI observe the outcome? | Exit code: `0` accept, `1` reject, `2` blocked, and the `decision` field in the record. `accept` only means eligible: promotion stays a reviewed manual step from `main`. | Exit 0 for every outcome, with the decision in a log line. | A job that is green whatever the decision would hide a blocked gate. The three codes let CI tell a measured rejection from an evaluation that did not finish. |

**What the gate cannot know.** It sees six months of 2012 validation data,
not the July–December rows nor live traffic, so it cannot promise accuracy in
production. It compares MAE averages, not errors at peak hours. Its operating
check is file size, not latency measured on Cloud Run. Promotion and the
revision serving the accepted bytes are checked separately (promotion PR).

## Operate and recover

Lab 8 split: runbook (Thomas), injector (Victor), operator (Nils), recorder
(Axel). The runbook was merged before any fault was injected.

- Runbook: [RUNBOOK.md](RUNBOOK.md). It covers the last verified context,
  signal definitions, baseline, first checks by boundary, rollback target,
  the single traffic change, fresh verification and escalation.
- Incident evidence: [shared timeline and fresh recovery verification](reports/lab8-timeline.md).
  The [original injector handoff](reports/lab8-evidence/README.md) is kept as a historical record.
  The evidence folder holds the raw
  checker output, `gcloud` describes and Cloud Run log exports for the
  baseline, incident and recovery periods, plus the timeline. The recorder
  links it from the Lab 8 section of the team report.

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

## Lab 8: incident diagnosis and recovery

The [shared timeline](reports/lab8-timeline.md), recorded by Axel, links
Victor's baseline and incident, Nils's diagnosis and rollback, and fresh
recorder verification. The accepted revision serves 100% of traffic; the
incident revision is retained at zero traffic. On 2026-11-12 the latest
template was replaced by `bike-demand-lab7-00004-bmn` with `--no-traffic` and
without `UVICORN_LIMIT_CONCURRENCY`. That revision receives no traffic. The
earlier revisions remain, including the incident revision, which still carries
the override. A fresh check still sees `baseline-28fdf1958b8a`. Record:
[template cleanup](reports/lab8-evidence/template-cleanup-2026-11-12.json).

The recorder kept raw JSON and log exports with a SHA-256 index. A single
linked timeline keeps each result with its source and owner; screenshots alone
would not preserve individual failures or the different request populations.

Follow [RUNBOOK.md](RUNBOOK.md) to observe the private service, record hypotheses
before recovery and verify a named accepted traffic target. Nils's
[operator report](reports/lab-08.md) links the timeline and raw observations
under `reports/lab8-evidence/nils-*`. Axel remains the incident recorder.

The serial checker passed during this drill, while a bounded concurrent
workload exposed 503 responses. After one traffic rollback, the same workload
passed. Application middleware logs omit Uvicorn-level rejections; inspect
platform request logs and server warnings as well.

```powershell
uv run --locked python scripts/check_operator_workload.py --base-url https://bike-demand-lab7-obot7iy6yq-ew.a.run.app --expect-model baseline-28fdf1958b8a
```

This sends four batches of four valid README predictions, without retries.
It prints statuses and durations, keeps the identity token in memory, and
exits 0 only when every response meets the contract. Use `--gcloud` for a CLI
outside PATH. A passing small workload does not establish production capacity.
The report separately compares Victor's original five-by-eight baseline and
incident with Nils's fresh recovery on that unchanged workload.

## Release v1.0.0

The Lab 7 gate rejected `06c4291bb9bc`, `26d505134be8` and `c898c95692c8`.
The accepted model stays the Week 1 reference, identified by SHA-256
`d24c050e3631d5b4c2feb8cb571bef6382d8c975c42a5c11edd28de78a0b8c07`, not by a
`model_version` label. The held-out test is scored once, after that choice,
and the score is not used to pick another model.

```bash
uv run --locked python -m bike_demand.held_test --model <accepted model.joblib>
```

Pass the accepted file, the one whose SHA-256 is the reference above. A local
refit is a different file and is refused before the test rows are scored. The
command checks the checksum and the recorded validation MAE, then scores
July–December 2012.
A second run refuses to overwrite `reports/final-held-test.json`.
The one recorded score is **93.73505906420367** rentals/hour, on commit
`93ed51e`, from the accepted file. Details:
[reports/final-held-test.json](reports/final-held-test.json).
The release notes are in [reports/release-v1.0.0.md](reports/release-v1.0.0.md).
The oral guide is in [reports/oral-guide.md](reports/oral-guide.md).
The latest Cloud Run template no longer sets `UVICORN_LIMIT_CONCURRENCY`.
Traffic stayed on the accepted revision.

## Support and individual reports

### Week 4 checkpoint and final release

After all Lab 7–8 PRs are reviewed and merged, verify main CI and create an
annotated `m4` tag on that reviewed commit. Submit its link with the short
checkpoint note. Each member submits `reports/week-4.md` in their own private
repository. The recorder PR alone does not complete peer review or submission.

The later project handover requires a `v1.0.0` GitHub Release linking code,
configuration, accepted model, checks, incident evidence, README, runbook and
release notes, plus final verification and the team presentation. The selected
candidate's held test is evaluated once at that later stage, never to choose
between models. No held-test evaluation is performed by this Lab 8 PR.

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
