# Week 1, Labs 1–2: team evidence

## Team and roles

## Repository and pull requests

## Setup, preflight and quality checks (commands and actual results)

## Data identity, validator checks and added test

- Data: `data/raw/hour.csv`, sha256 `e03de4ee...f829504f`, unchanged.
- `uv run --locked python -m bike_demand.validate --data data/raw/hour.csv` -> `Validated 17379 rows; input bytes unchanged.`
- `check_domains` checks integer categorical domains, finite `[0, 1]` normalised values, nonnegative integer counts and dates in 2011-2012.
- Added test: `tests/exercise/test_fault_b.py` (Fault B below).


## Partition counts, boundaries and held test rows

| Partition | Rows | Dates |
|---|---|---|
| train | 8645 | 2011-01-01 to 2011-12-31 |
| validation | 4358 | 2012-01-01 to 2012-06-30 |
| test (held, not evaluated) | 4376 | 2012-07-01 to 2012-12-31 |

Sorted by `(dteday, hr, instant)`; split fails if a partition is empty or a row is unassigned.


## Comparator and RF: run IDs, validation MAEs, metadata/readback

`uv run --locked python -m bike_demand.train --config configs/baseline.yaml` on commit `1826404` (`working_tree_dirty: false`):

| Run | MLflow run ID | Validation MAE (rentals/hour) |
|---|---|---|
| naive train mean (143.79) | `3d0ca97d016d426b89e858e463e87573` | 154.23 |
| random forest | `ff34d9e151844c3a822b0852905dbcd1` | 86.85 |

Model version `baseline-055641b0ef05`. Readback: reload MAE delta 0.0, metadata matches, logged model bytes match. No test MAE computed.


## Optional stretch, after the core: unchanged-config repeat (new run IDs, history, differences)

Leave blank or write "not attempted" if the core is unfinished.

Not attempted.

## Fault diagnosis and your own Fault B

Three lines: Choice (which rule did you break?), Reason (what risk does it protect?), Result (actual rejection, valid control, remaining limitation).

- Choice: `weathersit = 5` on one row of a 2-row copy (`tests/fixtures/weathersit-out-of-range.csv`), above the upper bound 4 (supplied tests only check 0).
- Reason: an unknown weather code would be used as a real category by the model without any error.
- Result: rejected with `weathersit: require integers in [1, 4]`; the same file with `weathersit = 4` is accepted (control). Limitation: only checks the range, not that the code matches the real weather.


## Review observation and author's response

## Contribution and assistance/recovery acknowledgement

- Lab 2 implementation, Fault B and baseline run: Axel Alacache (`axou947`).


## Blockers and next action

## Screenshots

Save images in `reports/images/`; embed each with a caption naming the commit or run
it shows (for example PR checks, MLflow runs, validator output). Hide tokens and
personal data.
