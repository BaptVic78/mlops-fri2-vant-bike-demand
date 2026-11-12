# Oral guide

Ten minutes. The release is the submission. The repository is already public,
so the slides do not need a second public link. No PowerPoint is stored here.
A local slide file is enough for the room. Do not publish another public copy.

## What to say

1. The service on Cloud Run is `bike-demand-lab7` in `europe-west1`. Anonymous
   calls receive 403. The accepted revision serves `baseline-28fdf1958b8a`.
2. The model identity is the file SHA-256
   `d24c050e3631d5b4c2feb8cb571bef6382d8c975c42a5c11edd28de78a0b8c07`, not the
   version label. A label changes on each build. The checksum does not.
3. Three Lab 7 candidates were rejected. The reference stayed accepted. That
   choice was closed before the test set was opened.
4. One held-out score, July–December 2012, 4,376 rows: **93.73505906420367**
   rentals/hour. The same file still scores **86.84685685591091** on the
   January–June 2012 validation rows. The test score was not used to pick a
   different model.
5. The release page, after review and a green main CI run, is
   https://github.com/BaptVic78/mlops-fri2-vant-bike-demand/releases/tag/v1.0.0.
   It links the code, configuration, accepted model, tests, gate, incident
   evidence, README and runbook. Tag `m4` stays where it is.

## If asked

- Validation MAE of the reference: 86.84685685591091. Test MAE is higher. That
  is the final measurement, not a reason to train again.
- The incident was `UVICORN_LIMIT_CONCURRENCY=2` on a revision that was not
  the accepted traffic target. The runbook says how to observe and roll back.
  The latest template no longer has that override. Traffic was not moved, and
  the incident revision is still kept at zero traffic.
- Evidence lives in `reports/`, not in a screenshot alone.
