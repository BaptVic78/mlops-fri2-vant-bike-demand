# Lab 7 pipeline preparation

The policy was merged in PR #23 before candidate evaluation.
The pipeline implementation is on the local branch
`lab7-candidate-pipeline`, based on `10b01d4`.

## Candidate command

```sh
uv sync --locked
uv run --locked python -m bike_demand.pipeline --config configs/baseline.yaml --reference artifacts/reference
```

The reference directory must contain the accepted model and metadata. Its
checksum is verified against the policy before unpickling. The model is
rescored on validation before a candidate is trained. The pipeline stages
write into a temporary candidate directory and publish the directory after
the complete evidence and MLflow tracking are saved.

The command produces evidence for the gate. It leaves the accepted model
and metadata intact. Gate decisions, budget accounting and promotion are
the subsequent team tasks.

## Local evidence

The eight synthetic regression cases passed in the locked checkout environment:

```text
.venv/bin/python -m pytest -q tests/test_pipeline.py
8 passed in 113.23s
```

An additional run using the existing Linux environment and this branch's
source via `PYTHONPATH` passed all eight cases in 6.35 seconds.
Ruff lint and formatting passed for the new code and tests.

The tests exercise accepted model and metadata preservation, immutable
candidate output, wrong reference bytes, dirty source, disallowed model
settings and failed-training cleanup. They use a six-row synthetic fixture
and a fixture policy. They consume no real candidate attempts.

Docker verification is blocked locally because the Docker Desktop Linux
engine pipe is unavailable. The local team checkout does contain model bytes
matching the policy reference checksum, but a canonical candidate run from
the final clean commit remains to be recorded after commit attribution is
settled. No real candidate was evaluated by this preparation.
