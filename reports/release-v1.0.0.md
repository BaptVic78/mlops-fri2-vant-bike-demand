# Release v1.0.0

The accepted model is the Week 1 reference. The three Lab 7 candidates were
rejected before this release, and the held-out score below was not used to
choose another model.

Held-out test, July–December 2012, 4,376 rows: **93.73505906420367**
rentals/hour. Validation rescore of the same file:
**86.84685685591091**, equal to the recorded reference. Command, commit and
identity: [reports/final-held-test.json](final-held-test.json). The scored
file was extracted from local image `bike-demand:lab5`
(`sha256:28a5889ca38184e65a9cd7d78f9f4b64aafd0b622d5b7fd75787c21e5b8d8621`),
path `/app/artifacts/model.joblib`, after its SHA-256 matched the accepted
reference.

## Cloud Run template

On 2026-11-12 the latest template no longer sets `UVICORN_LIMIT_CONCURRENCY`.
The update used `--no-traffic`. Serving traffic stayed at 100% on
`bike-demand-lab7-refcurrent80f31db`. New revision
`bike-demand-lab7-00004-bmn` receives no traffic and uses the same accepted
image digest. Revisions `bike-demand-lab7-lab8-victor-01`,
`bike-demand-lab7-refcurrent80f31db` and `bike-demand-lab7-refbase80f31db`
remain. The live check passed for `baseline-28fdf1958b8a`.
[Record](lab8-evidence/template-cleanup-2026-11-12.json).

## Links

| Item | Where |
|---|---|
| Code | commit `93ed51e14eadc49783283bfab3e6ae59e5ebbe21` and `main` after this release merges |
| Configuration | [configs/baseline.yaml](../configs/baseline.yaml), [configs/gate-policy.yaml](../configs/gate-policy.yaml), [configs/candidate-lab7.yaml](../configs/candidate-lab7.yaml) |
| Accepted model | SHA-256 `d24c050e3631d5b4c2feb8cb571bef6382d8c975c42a5c11edd28de78a0b8c07`; service label `baseline-28fdf1958b8a` |
| Tests | [tests/](../tests/), workflow [.github/workflows/ci.yml](../.github/workflows/ci.yml) |
| Gate | [reports/lab7-decisions/](lab7-decisions/), [reports/lab-07.md](lab-07.md) |
| Incident evidence | [reports/lab8-timeline.md](lab8-timeline.md), [reports/lab8-evidence/](lab8-evidence/) |
| README | [README.md](../README.md) |
| Runbook | [RUNBOOK.md](../RUNBOOK.md) |

The GitHub release page is
https://github.com/BaptVic78/mlops-fri2-vant-bike-demand/releases/tag/v1.0.0.
It is published after this pull request is reviewed, merged, and main CI is
green. The existing `m4` tag is not moved.
