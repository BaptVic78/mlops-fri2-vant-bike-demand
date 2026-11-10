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

## Canonical candidate attempt 1

The candidate command ran from clean commit `5957a2f` on Linux under WSL,
using the existing trusted bundle at
`/home/victor/mlops-fri2-vant-bike-demand/artifacts`. Its reference model
checksum matched the policy. The command exited 0 and produced run
`06c4291bb9bc`. The [evaluation record](lab7-evidence/pipeline-evaluation.json)
and [tracking ID](lab7-evidence/pipeline-tracking.json) preserve the results.

- Reference validation MAE: 86.84685685591091.
- Candidate validation MAE: 86.84685685591091.
- Training-mean validation MAE: 154.23179306864967.
- Candidate checksum: `de2ccb247c32ade78dcd7c43be6209ca03b7065de42fe8578c1b6e25f93482c3`.
- Candidate size: 5,243,809 bytes.
- Saved model readback MAE: 86.84685685591091.
- The accepted reference model checksum remained
  `d24c050e3631d5b4c2feb8cb571bef6382d8c975c42a5c11edd28de78a0b8c07`.

This is the first canonical candidate attempt under policy version 1. Retain
it in the gate's three-candidate budget. The quality evidence shows zero
improvement; the gate must record its formal decision in the subsequent PR.
The candidate model bytes remain in the ignored candidate directory.

Full local verification at this implementation commit used
`uv sync --locked`, locked Ruff lint and formatting, then
`uv run --locked pytest -q`: 168 passed, 2 warnings in 147.19 seconds.
The warnings concern Starlette's test client and SQLAlchemy's loader strategy.
Docker verification is blocked locally because the Docker Desktop Linux
engine pipe is unavailable. The PR image job provides separate runner evidence.

## Second attempt during retry verification

The duplicate-run probe was launched before the evidence commit, but its
Python startup completed after that commit. It therefore read the new clean
commit `b48f810` and produced run `26d505134be8`. The commit is part of the
run identity, so this is a distinct attempt, even with the same model config.
The [second evaluation](lab7-evidence/pipeline-evaluation-retry.json) and
[tracking ID](lab7-evidence/pipeline-tracking-retry.json) retain its evidence.
Count both attempts against policy version 1's budget of three.
Both candidate MAEs equal the reference MAE. Gate decisions remain pending.
The synthetic immutable-output test covers duplicate-run refusal. No further
canonical candidate is needed for this pipeline implementation.
