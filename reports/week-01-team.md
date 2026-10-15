# Week 1, Labs 1–2: team evidence

## Team and roles

## Repository and pull requests

## Setup, preflight and quality checks (commands and actual results)

## Data identity, validator checks and added test

## Partition counts, boundaries and held test rows

## Comparator and RF: run IDs, validation MAEs, metadata/readback

## Optional stretch, after the core: unchanged-config repeat (new run IDs, history, differences)

Leave blank or write "not attempted" if the core is unfinished.

## Fault diagnosis and your own Fault B

Choice: Fault B changes exactly one cell, `hr`, to 24 on a temporary copy of the six-row `tests/fixtures/missing-hours.csv` fixture, breaking the allowed 0–23 hour range.

Reason: Reject impossible hours before they reach model training or evaluation.

Result: `.venv/bin/python -m pytest -q tests/exercise/test_fault_b.py` passed (1 test). The unchanged valid control loaded all six rows; the faulty copy raised `ValueError` mentioning `hr` and remained byte-for-byte unchanged after rejection. The test uses temporary copies and does not edit `data/raw/hour.csv`. This experiment checks one hour-range fault, not every validation rule.

## Review observation and author's response

## Contribution and assistance/recovery acknowledgement

Codex assisted with implementing the data-domain checks and added and ran the Fault B test and its report entry.

## Blockers and next action

## Screenshots

Save images in `reports/images/`; embed each with a caption naming the commit or run
it shows (for example PR checks, MLflow runs, validator output). Hide tokens and
personal data.
