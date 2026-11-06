# Lab 6: workflow and regression tests

Axel Alacache owns the workflow and Victor Rouleau owns the regression tests.

## Run

Pull request #19, commit `cb273b95f7e5e342b9e64f58df571abf636a4959`.

- Workflow: `CI`
- Event: `pull_request`
- Run: https://github.com/BaptVic78/mlops-fri2-vant-bike-demand/actions/runs/42254284603
- Conclusion: `success`
- `lock` success, 2026-11-06T16:38:35Z to 2026-11-06T16:38:55Z
- `style` success, 2026-11-06T16:38:58Z to 2026-11-06T16:39:15Z
- `tests` success, 2026-11-06T16:39:17Z to 2026-11-06T16:39:42Z

The tests job printed:

```text
156 passed, 2 warnings in 14.14s
```

That line is from the runner log of job `128017586991`, step `uv run --locked pytest -q`. The suite fitted fixture models on the runner. Image verification belongs to the separate build job.

The choices are in the README, section [CI](../README.md#ci).

## Victor's regression tests (PR #20)

GitHub Actions ran `uv run --locked pytest -q` twice on the same PR:

| Commit | CI run | Result |
|---|---|---|
| `267424d` | [Before the repair](https://github.com/BaptVic78/mlops-fri2-vant-bike-demand/actions/runs/42256002361) | 3 failed, 157 passed, 2 warnings |
| `81d6632` | [After the repair](https://github.com/BaptVic78/mlops-fri2-vant-bike-demand/actions/runs/42256255529) | 160 passed, 2 warnings in 14.87 s |

`test_boolean_csv_column_is_rejected` failed with `DID NOT RAISE ValueError`
for `cnt`, `workingday` and `hum`. pandas inferred a boolean column from CSV
literals, and numeric range checks accepted the values as zero and one.
The repair rejects boolean columns before numeric conversion. Both commits
use identical tests. The [failing pytest log](lab6-evidence/boolean-csv-red.txt)
preserves the assertions and exit code.

`test_naive_validation_mae_matches_lab2_record` recomputes the training mean
and validation MAE from the frozen CSV and compares both to the Lab 2 record.
The check uses only the training and validation targets.
