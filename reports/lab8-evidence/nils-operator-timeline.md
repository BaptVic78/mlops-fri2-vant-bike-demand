# Lab 8 operator timeline — Nils Giraud

All timestamps are UTC. The operator used the merged runbook and live service
observations, without reading Victor's injector implementation or incident
explanation. Raw initial observations were saved locally before analysis.

## First observations

- 2026-11-11T23:14:09Z: started read-only observation of the private service.
  The first service description showed 100% traffic on
  `bike-demand-lab7-lab8-victor-01`, rather than the accepted
  `bike-demand-lab7-refcurrent80f31db`. The service still reported Ready.
- 2026-11-11T23:14:35Z: the serial contract check passed: health and prediction
  200, expected `baseline-28fdf1958b8a`, invalid hour 422, anonymous 403.
  A passing serial check therefore does not explain the revision change or
  establish that concurrent requests work.
- The first service description also showed the accepted image digest and an
  environment entry `UVICORN_LIMIT_CONCURRENCY=2`. This is an observed
  configuration difference to investigate, not yet a demonstrated cause.

## Hypotheses recorded before recovery

| Hypothesis | Expected signature | Discriminating check | Initial status |
|---|---|---|---|
| A different or unloadable model is serving | Different image/model version or startup/model-load errors; serial valid calls may fail | Compare revision digests and startup logs with the accepted revision | Serial version matches; image and logs still to compare |
| Runtime configuration restricts concurrent requests | Serial calls pass but simultaneous valid requests produce 503; server reports concurrency limit | Compare revision configuration and send a small fixed concurrent workload | Pending live workload and logs |
| Invalid client input causes the incident | Failures are validation 422, with no valid-request 5xx | Use only the known valid README example and distinguish deliberate invalid-hour checks | Pending live workload and logs |

No traffic, deployment, model, configuration or IAM change has been made.

## Diagnosis recorded before recovery (2026-11-11T23:17:25.9078553Z)

The fixed concurrent workload at 2026-11-11T23:16:16.653431Z to
2026-11-11T23:16:17.130013Z returned 3 HTTP 200 and 13 HTTP 503 (16 requests,
availability 0.1875). The scoped Cloud Run request logs record the same
13 HTTP 503 responses, and Uvicorn writes 13
`WARNING: Exceeded concurrency limit.` messages on the suspect revision.
These rejections happen before the application middleware, so application
JSON request logs alone would miss them.

The suspect and accepted revisions have identical image digests, resources,
container concurrency (8), ports and startup probe. The suspect revision adds
`UVICORN_LIMIT_CONCURRENCY=2`; the accepted target has no such override.
The successful requests return the accepted model version. The model-change
hypothesis is rejected for the observed failures; no new image/model is
involved. The invalid-input hypothesis is rejected because the failing workload
contains only the valid README example, and the failures are 503, not 422.

The runtime concurrency configuration explains the mismatch between passing
serial checks and failed simultaneous requests. The controlled recovery will
route 100% of traffic to the retained accepted
`bike-demand-lab7-refcurrent80f31db`. Its Ready condition is True and its
image digest matches the recorded accepted image. The suspect revision will
remain available with zero traffic. No retraining or deployment is required.
Fresh results on the identical workload will test this causal explanation.

A fresh pre-injection baseline was not collected by the operator: injection
was already active at first observation. The retained Lab 7 evidence establishes
the previously accepted identity and serial contract. It does not establish
pre-injection concurrent availability for this probe.

## Controlled recovery and fresh checks

- 2026-11-11T23:19:34.380199Z: rechecked that the suspect revision still had
  100% traffic, then ran the runbook's traffic rollback to
  `bike-demand-lab7-refcurrent80f31db=100`. The command succeeded. No revision,
  image, environment setting or IAM policy was changed or deleted.
- Cloud Run recorded the route becoming Ready at 23:19:45.634174Z.
  `status.traffic` names the accepted revision at 100%. The latest-created
  revision field still names the faulty revision; it is not the traffic target.
- Five fresh serial contract checks exited 0. Health and prediction returned
  200 with the expected model version, invalid hour returned 422 and anonymous
  health returned 403 in every check.
- 23:20:17.468358Z–23:20:18.034842Z: repeated the identical operator workload
  (four batches of four valid predictions). All 16 requests returned 200 and
  the expected version. Availability was 1.0, versus 0.1875 during the incident.
- The first post-rollback log query failed with `INVALID_ARGUMENT` because
  Windows removed the timestamp's inner quotes. Retried with the escaped
  timestamp syntax from the runbook and the service-specific log-view flags.
  The successful fresh export contains 27 eligible application events, all
  200, and five deliberate 422 events. There are no concurrency warnings or
  model-load errors. The target is Ready and the faulty revision is retained.

## Additional comparison after the diagnosis was written

After the diagnosis and initial recovery were recorded, read Victor's handoff
at PR #28 head `703e09a`. Its historical baseline and incident use five rounds
of eight concurrent valid predictions. These were collected by Victor, not by
the operator. They show 40/40 successes before injection and 7/40 during it.

At 23:24:29.390563Z–23:24:30.508985Z, ran that exact workload implementation
unchanged from commit `703e09a`, using this checkout's virtual environment and
the shared `check_cloud_run.request` helper. It exited 0 with 40/40 successes,
expected version `baseline-28fdf1958b8a`, and zero 503 responses. A separate
fresh export contains 41 platform HTTP 200 events (40 predictions and the
separate health warm-up), all on the accepted revision, with no concurrency
warning. Raw output is `nils-recovery-original-workload.json`.

The recovery supports the runtime-configuration diagnosis. A new 5xx, an
unexpected model version, renewed concurrency warnings or traffic on the
suspect revision would disprove the current recovery claim. The small sample
does not prove production capacity or predictive quality.

## Evidence and coordination

The two screenshots show the operator's saved observation and recovery records
in Notepad. Their results come from the linked raw JSON and log exports; they
are not screenshots of the Cloud Run console. Personal screenshots stay in
the personal report repository. Axel can use these raw records to assemble
the shared incident timeline.

Feedback for Thomas's runbook: add a bounded concurrent probe, inspect platform
request logs and Uvicorn warnings alongside application logs, retain the
service-scoped logging-view flags, and distinguish `status.traffic` from the
latest-ready revision name. Serial readiness and application-only availability
missed this fault.
