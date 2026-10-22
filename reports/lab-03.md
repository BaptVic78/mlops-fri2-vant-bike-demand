# Lab 3: Reproducible Docker environment – execution record

Observed facts only. All checks below were run **locally** on one Windows 11
workstation with Docker Desktop; none of them is a GitHub Actions/CI result.
Raw logs are in [`lab3-evidence/`](lab3-evidence/).

## Revision and environment

- Branch: `feature/lab3-docker-reproducibility`, based on `main` at
  `022c3c48af43990ad7440e855a28a4e7706698d5` (merge of PR #7, which added the
  first Dockerfile and `.dockerignore`).
- Checks were run on the working tree = `022c3c4` + the Lab 3 changes listed below
  (uncommitted at the time of the runs).
- Host: Windows 11, uv 0.12.24, Python 3.12.15 (uv-managed), Docker 28.5.1
  (linux/amd64 engine).
- Image `bike-demand:lab3`:
  `sha256:af0942bc3c4cd4096959afe0e960f51428d12303026ff45e87915367eb302501`,
  built 2026-10-22T07:14:33Z with `--no-cache`, 1.54 GB.
- Base images resolved at build time:
  `python:3.12.12-slim@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c`,
  `ghcr.io/astral-sh/uv:0.12.24@sha256:3af4716e991d6956a41e573eab705d0ee08500cd829ed30293eb8472f372c65a`.
- In the image: Python 3.12.12, uv 0.12.24, git 2.47.3; scikit-learn 1.9.1,
  pandas 2.3.3, numpy 2.5.3, mlflow 3.17.0, joblib 1.6.0 (same library versions
  as the host `.venv`).

## uv.lock state

- `uv.lock` unchanged by Lab 3 (git blob `8478e0e0`, content SHA-256
  `8598f1f2…0330` in LF form). `uv lock --check` passes on the host and inside
  the image (`--offline`); 98 packages resolved.
- No `uv lock` was run; the lock was never regenerated.

## Audit of the PR #7 Dockerfile ([00](lab3-evidence/00-pr7-dockerfile-audit.log))

| Observation | Consequence | Lab 3 change |
| --- | --- | --- |
| `.dockerignore` patterns `.venv/`, `__pycache__/` only match the root | Untracked `mlops-course/` (607 MB, with its own Windows `.venv`) and host `__pycache__` copied; build context 591 MB | `**/` patterns, exclude `mlops-course/`, `reports/lab3-evidence/` |
| `COPY . .` | Everything not ignored enters the image | Targeted `COPY` of `data/`, `configs/`, `README.md`, `ci.yml`, `reports/`, `tests/`, `src/` |
| `CMD ["uv", "run", "--locked", ...]` | Every container rebuilt and reinstalled the project at start (`Building bike-demand @ file:///app`), using a cached PyPI index response | `CMD` runs `/app/.venv/bin/python` directly |
| No `UV_PYTHON_DOWNLOADS=never` | uv could fetch another interpreter | Set; uv must use the image's 3.12.12 |
| uv cache kept in image | Larger image (2.16 GB) | Build-only cache mount (1.54 GB) |

Kept from PR #7: pinned `python:3.12.12-slim`, pinned uv 0.12.24, `WORKDIR /app`,
manifests + lock copied first, `uv sync --locked --no-install-project`, `git`
package (required: `training_commit()` raises `OSError` if the binary is missing).

## Commands and results

| # | Command | Result | Log |
| --- | --- | --- | --- |
| 1 | `uv lock --check` | exit 0 | [01](lab3-evidence/01-local-uv-checks.log) |
| 2 | `uv sync --locked` | exit 0 | [01](lab3-evidence/01-local-uv-checks.log) |
| 3 | `uv run --locked pytest -q` | 49 passed, 1 warning | [01](lab3-evidence/01-local-uv-checks.log) |
| 4 | `uv run --locked ruff check .` / `ruff format --check .` | pass / pass | [01](lab3-evidence/01-local-uv-checks.log) |
| 5 | `docker build --no-cache --progress=plain -t bike-demand:lab3 .` | exit 0; 94 packages installed by `uv sync --locked` | [02](lab3-evidence/02-docker-build.log) |
| 6 | `docker run --rm bike-demand:lab3` | exit 0 | [03](lab3-evidence/03-docker-run.stdout.json) |
| 7 | `docker run --rm --network none bike-demand:lab3` | exit 0 | [04](lab3-evidence/04-docker-run-no-network.stdout.json) |
| 8 | `docker run --rm --network none bike-demand:lab3 python -m bike_demand.preflight` | passed | [05](lab3-evidence/05-docker-tests.log) |
| 9 | `docker run --rm --network none bike-demand:lab3 pytest -q` | 49 passed, 1 warning | [05](lab3-evidence/05-docker-tests.log) |
| 10 | `docker run --rm --network none bike-demand:lab3 ruff check .` | pass | [05](lab3-evidence/05-docker-tests.log) |
| 11 | `docker run --rm --network none bike-demand:lab3 uv lock --check --offline` | exit 0 | [05](lab3-evidence/05-docker-tests.log) |
| 12 | train + list outputs inside the container | `reports/metrics.json`, `metrics-history.jsonl` (2 lines), `artifacts/model.joblib` written | [06](lab3-evidence/06-docker-metrics-files.log) |

The one pytest warning is an MLflow/SQLAlchemy `SADeprecationWarning`, identical
on host and image. Runtime stderr in 6–7 contains only MLflow INFO lines; no
build, install or resolve line.

## Reproducibility: Lab 2 vs Docker

| Field | Lab 2 reference (committed `reports/metrics.json`) | Host rerun, clean copy of `022c3c4` (Windows) | Docker (network) | Docker (`--network none`) |
| --- | --- | --- | --- | --- |
| Validation MAE, random forest | 86.84685685591091 | 86.84685685591091 | 86.84685685591091 | 86.84685685591091 |
| Validation MAE, naive train mean | 154.23179306864967 | 154.23179306864967 | 154.23179306864967 | 154.23179306864967 |
| `train_mean` | 143.79444765760556 | same | same | same |
| `data_sha256` | `e03de4ee…504f` | same | same | same |
| Partitions (rows) | 8645 / 4358 / 4376 | same | same | same |
| Config / effective RF settings | n_estimators 50, max_depth 10, random_state 42, n_jobs 1 | same | same | same |
| Readback (reload MAE delta, max abs prediction delta) | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| `model_sha256` | `d24c050e…8c07` | `fd98ceaf…304` | `d24c050e…8c07` | `d24c050e…8c07` |
| `training_commit` | `c4ba1825…` (dirty) | `unavailable` (no `.git` in copy) | `unavailable` | `unavailable` |
| `model_run_id` | `ba0ece8cf43541edb4da633481c1f3c5` | `0989a2247a894593a9282b713e4aa8de` | `5a9e754e417a48e586cebc1c719d664f` | `1f7af4b38c494eb6b0885555c94c8c12` |
| `naive_run_id` | `9226418acc914919b61a5640300d6da7` | `c287562efd8a4f2695940aeaf8690470` | `15ff596929eb4c33849eb5f6b0263294` | `6b575c742e21430890ad389b171c32a6` |

Interpretation:

- Metrics are bit-for-bit identical; no data, split, feature or model setting
  was changed. No tuning, no test-set scoring.
- Run IDs and `model_version` are random UUIDs per run, so they differ by design.
- `model_sha256` matches the Lab 2 reference in both Linux container runs, and
  matches an earlier Windows Lab 2 run (`8da42b7`, `fd98ceaf…`) on the host. The
  serialized pickle differs between Windows and Linux while predictions and MAE
  are identical; byte-identical models across OSes are not claimed.
- `training_commit` is `unavailable` in the container because `.git` is
  excluded; the code identity is the image ID above plus the branch commit.

## Negative lock tests ([07](lab3-evidence/07-negative-lock-tests.log))

Run on a temporary `git archive` copy outside the repository, deleted afterwards.

1. `uv.lock` absent → `uv sync --locked`: `error: Unable to find lockfile at uv.lock,
   but --locked was provided`, exit 1, no lock created. `docker build`: fails at
   `COPY` (`"/uv.lock": not found`).
2. `uv.lock` stale (`tabulate>=0.9,<1` added to `pyproject.toml` only) →
   `uv lock --check` and `uv sync --locked`: `error: The lockfile at uv.lock needs
   to be updated, but --locked was provided`, exit 1. `docker build`: fails at
   `RUN uv sync --locked --no-install-project`, exit code 1.

The log line "lock unchanged … NO" compared LF and CRLF forms; the appended note
in the log shows the temp lock equal to the git blob, and `git status` shows the
real `uv.lock` unmodified.

## Errors met and corrections

- Docker Desktop was not running at first (`dockerDesktopLinuxEngine` pipe not
  found); started it, then all Docker steps ran.
- Host rerun in a deep temp directory failed with
  `ModuleNotFoundError: joblib.externals.loky.backend.stdlib_py314_resource_tracker`:
  the path exceeded the Windows 260-character limit. Rerun in a short path
  succeeded. This is a host limitation, not a project defect.
- A first image (`9a5f6f11a2c2`) also contained `reports/lab-*.md` and
  `reports/images/`, so editing this report would have changed the image it
  documents. Those paths are now in `.dockerignore`; the image was rebuilt with
  `--no-cache` and logs 02–06 and 08 were regenerated on the final files (same
  metrics as the first image).
- The local checkout was on an outdated branch (`a44e591`, without Lab 2 merge
  or PR #7); work restarted from `origin/main` `022c3c4`.

## Remaining limits

- Not verified in GitHub Actions; the CI workflow is unchanged and does not
  build the image.
- Only linux/amd64 tested; Debian `git` package and base images are not pinned
  by digest in the Dockerfile.
- Container runs as root; outputs disappear with `--rm` unless copied out.
