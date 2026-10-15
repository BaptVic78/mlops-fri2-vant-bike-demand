# Week 1, Labs 1–2: team evidence

## Team and roles

Our team, vant, has four members: Nils Giraud, Victor Rouleau, Axel Alacache and Thomas.

| Lab | Drivers | Reviewer | Evidence recorder |
|---|---|---|---|
| Lab 1 | Nils and Victor | Axel | Thomas |
| Lab 2 | Victor and Axel | Thomas | Nils |

## Repository and pull requests

Team repository: [mlops-fri2-vant-bike-demand](https://github.com/BaptVic78/mlops-fri2-vant-bike-demand)

For Lab 1, Victor and Nils both proposed a fix for the team slug normalization bug:
- [Victor's PR #1](https://github.com/BaptVic78/mlops-fri2-vant-bike-demand/pull/1) was reviewed and merged by Axel.
- [Nils's PR #3](https://github.com/BaptVic78/mlops-fri2-vant-bike-demand/pull/3) was closed without merging after PR #1 was selected.

For Lab 2:
- [Victor's PR #6](https://github.com/BaptVic78/mlops-fri2-vant-bike-demand/pull/6) was merged by Thomas.
- [Axel's PR #4](https://github.com/BaptVic78/mlops-fri2-vant-bike-demand/pull/4) contained an alternative implementation and was closed without merging.

## Setup, preflight and quality checks (commands and actual results)

For Lab 1, the checks recorded for Victor's commit `0024097` included:

- `uv run --locked python -m bike_demand.preflight`: passed.
- `uv run --locked ruff check .`: passed.
- `uv run --locked pytest -q -m infra`: 9 passed.
- `uv run --locked pytest -q -m lab1`: 4 passed.

One test file initially needed formatting. This was corrected, and Axel confirmed that the formatting check and CI passed before merging.

For Lab 2, Victor's PR #6 reported:

- `.venv/bin/python -m pytest -q`: 49 passed, with one SQLAlchemy deprecation warning.
- Successful Ruff lint and formatting checks.

The final PR commit shown, `8a9b48b`, also had a successful check indicator.

Separately, Axel's PR #4 reported 50 passing tests and successful preflight, lint and formatting checks. These results relate to his alternative branch.

## Data identity, validator checks and added test

We used the dataset `data/raw/hour.csv`, containing 17,379 rows.

The validator checks that:
- Categorical values are within their allowed ranges.
- Normalised values are finite and between 0 and 1.
- Counts are nonnegative integers.
- Dates are within the expected 2011–2012 period.

An additional test checks that an invalid hour is rejected while a valid control dataset is accepted.

Data SHA-256: [copy data_sha256 from reports/metrics.json]

## Partition counts, boundaries and held test rows

The data was split chronologically:

| Partition | Rows | Date range |
|---|---:|---|
| Train | 8,645 | January–December 2011 |
| Validation | 4,358 | January–June 2012 |
| Test | 4,376 | July–December 2012 |

Rows are sorted by `dteday`, `hr` and `instant`. The implementation checks that the partitions are nonempty and cover the full dataset.

The model was trained on the training partition and evaluated on the validation partition. The test partition was kept aside, and no test MAE is reported.

## Comparator and RF: run IDs, validation MAEs, metadata/readback

We compared a training-mean baseline with a random forest.

| Model | Validation MAE (rentals/hour) |
|---|---:|
| Training-mean comparator | 154.23 |
| Random forest | 86.85 |

The comparator predicts the mean rental count calculated from the training data. The random forest uses the ordered predictors defined in the configuration, excluding the target.

The random forest achieved a lower validation error than the comparator. It used 50 trees, a maximum depth of 10 and a random seed of 42.

- Comparator run ID: [copy naive_run_id from reports/metrics.json]
- Random forest run ID: [copy model_run_id from reports/metrics.json]

After reloading the saved model, the validation MAE and predictions matched the original results, with a difference of 0.0. The metadata checks also matched.

The results are recorded in `reports/metrics.json` and `reports/metrics-history.jsonl`. The training metadata indicates that uncommitted changes were present during the run.

## Optional stretch, after the core: unchanged-config repeat (new run IDs, history, differences)

No separate unchanged-configuration repeat is documented in the evidence collected so far.

## Fault diagnosis and your own Fault B

Choice: in PR #6, one hour value was changed to `24` in a temporary copy of a six-row fixture. The allowed range is 0–23.

Reason: an impossible hour should be rejected before the data reaches model training.

Result: the valid control loaded all six rows, while the modified copy raised a `ValueError` mentioning `hr`. The dedicated test passed and checked that validation did not modify either input file.

This experiment covers the hour-range rule. Axel also proposed a separate Fault B using an out-of-range weather category in PR #4, which was not merged.

## Review observation and author's response

For Lab 1, Axel selected Victor's PR #1 because its additional newline test directly covered the whitespace bug.

For Nils's PR #3, Axel confirmed that the fix worked and the checks passed. However, the added test covered whitespace-only input, which was already rejected before the fix. He recommended testing whitespace between words instead. PR #3 was then closed without merging.

For Lab 2, Thomas merged PR #6. The collected screenshots do not show a detailed review comment followed by an author response, so this part of the review record remains to be completed.

## Contribution and assistance/recovery acknowledgement

Victor and Nils implemented the two Lab 1 fixes. Axel reviewed them and selected the version to merge, while Thomas recorded the evidence.

For Lab 2, Victor and Axel worked on the validation, splitting and training tasks in their respective branches. Victor's implementation was merged. Thomas handled the review and merge, and Nils collected the results and prepared the team evidence report.

## Blockers and next action

The Lab 2 implementation was merged and the reported checks passed.

The remaining tasks are to complete the run IDs and data hash, add the screenshots, and complete the Lab 2 review record.

A further improvement would be to repeat the training from a clean committed version so that the results can be linked to an exact code state.

## Screenshots

The screenshots will be added under `reports/images/`, with captions identifying the relevant PR, commit or run.

For Lab 1, we have screenshots of the branch creation and passing tests, Nils's code changes, and the push of commit `a168d55`.

For Lab 2, we don't have any screenshots for the moment
