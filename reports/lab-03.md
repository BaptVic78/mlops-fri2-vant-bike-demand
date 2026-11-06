# Lab 3: locked image and clean rerun

Evidence for the image built from commit `7cccd50d337e45f6f2599531ce8389b3a2845a4c`.
No laptop `.venv`, source mount, or network was used at run time. No test-set
metric was computed.

## Image

- Command: `docker build -t bike-demand:lab3 .`
- Image ID: `sha256:915c7499209fd39bdbb7bdfd485dbcebe5ecefaed258234f40d47754f15aeab2`
- Base: `python:3.12.12-slim`. uv `0.12.24`. Install: `uv sync --locked`.
- `.git` is excluded. `training_commit` is `unavailable` and `working_tree_dirty`
  is `null` because `git status` has no checkout. The git binary is installed so
  that missing repository is recorded instead of aborting training.

## Baseline rerun

Command: `docker run --rm --network none bike-demand:lab3`

Exit 0. Raw result: [train.json](lab3-evidence/train.json).

| | Lab 2 `reports/metrics.json` | This container |
|---|---|---|
| data SHA-256 | `e03de4ee4ef4dc376ac6e04bf829673c6269e8eba5c60fa121640fa2f829504f` | same |
| train / validation / test rows | 8645 / 4358 / 4376 | same |
| naive validation MAE | 154.23179306864967 | 154.23179306864967 |
| random forest validation MAE | 86.84685685591091 | 86.84685685591091 |
| readback MAE delta | 0.0 | 0.0 |
| run IDs | `9226418acc914919b61a5640300d6da7`, `ba0ece8cf43541edb4da633481c1f3c5` | `4975514a8f4943279930f3d5a27d5824`, `e432c18009b54d859b9e825785672042` |

The validation MAEs match the Lab 2 reference. Run IDs differ, which is expected
for a new MLflow store. The held-out test rows stay unused.

## Tests in the image

Command: `docker run --rm --network none --entrypoint .venv/bin/pytest bike-demand:lab3 -q`

Exit 0. [pytest.txt](lab3-evidence/pytest.txt): 149 passed, 2 warnings, 16.78s.
The warnings are the existing Starlette `httpx` deprecation and the SQLAlchemy
`noload` deprecation.

## Lock failures, throwaway copies

These copies were deleted. The repository lock was not regenerated.

- Missing `uv.lock`, `uv sync --locked`: exit 1, `Unable to find lockfile at uv.lock, but --locked was provided.`
- `httpx` added to a copied `pyproject.toml` without updating the lock, `uv lock --check`: exit 1, `The lockfile at uv.lock needs to be updated, but --check was provided.`
