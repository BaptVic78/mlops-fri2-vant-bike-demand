# Lab 8 — operator diagnosis and verified rollback

The [shared recorder timeline](lab8-timeline.md) joins the first signal,
diagnosis, traffic rollback and fresh verification with links to the raw
records. It also records the later recorder checks and the remaining handoff.

Operator: Nils Giraud. Injector: Victor Rouleau. Recorder: Axel Alacache.
Thomas Soubagne owns the [runbook](../RUNBOOK.md), merged before the incident.
All timestamps below are UTC (the operator session was on 12 November in Paris).

## First signal and hypotheses

At 23:14:09 on 11 November 2026, the service description showed 100% traffic
on `bike-demand-lab7-lab8-victor-01`, rather than the accepted revision.
The sequential API check still passed. Nils recorded hypotheses covering
a changed/unloadable model, runtime configuration and invalid client input
before making any recovery change.

The [operator timeline](lab8-evidence/nils-operator-timeline.md) records the
checks in order. The [first contract result](lab8-evidence/nils-first-contract-check.json)
preserves the passing low-load check. A separate bounded concurrent probe
then returned 13 HTTP 503 and three HTTP 200 responses from 16 valid requests.
Its [individual observations](lab8-evidence/nils-incident-workload.json)
are retained, including the failed result.

## Diagnosis before recovery

The suspect and [accepted target](lab8-evidence/nils-rollback-target.json)
use the same image digest, model, resources and Cloud Run concurrency of 8.
The [suspect revision](lab8-evidence/nils-incident-revision.json) adds
`UVICORN_LIMIT_CONCURRENCY=2`. The [incident logs](lab8-evidence/nils-incident-logs.json)
contain 13 platform 503 responses and 13 `Exceeded concurrency limit` warnings.
The valid requests that succeeded returned `baseline-28fdf1958b8a`.

The added Uvicorn limit explains the concurrent failures. Model-change and
invalid-input hypotheses do not explain this symptom: the immutable image
is unchanged and the failing valid requests return 503, rather than 422.
The diagnosis was written at 23:17:25, before the traffic change at 23:19:34.
Victor's handoff records were read only after the diagnosis existed.

## Recovery and comparison

The verified target was `bike-demand-lab7-refcurrent80f31db`, Ready, with the
accepted digest `sha256:6dd4148b94859b21b05769af5971892e604fee3c2a3f201c411910a080f932ff`.
One change restored 100% of traffic to it:

```sh
gcloud run services update-traffic bike-demand-lab7 --project=fourth-eon-424715-k1 --region=europe-west1 --to-revisions=bike-demand-lab7-refcurrent80f31db=100
```

The [command result](lab8-evidence/nils-rollback-command.txt),
[service traffic](lab8-evidence/nils-recovery-service.json),
[target readiness](lab8-evidence/nils-recovery-target.json) and
[retained faulty revision](lab8-evidence/nils-retained-faulty-revision.json)
show the resulting state. The faulty revision remains at zero traffic.
There was no rebuild, deployment, retraining or IAM change.

Five [fresh contract checks](lab8-evidence/nils-recovery-contract-checks.json)
passed. The identical 16-request operator probe improved from 3/16 to
[16/16 successes](lab8-evidence/nils-recovery-workload.json).
The [fresh logs](lab8-evidence/nils-recovery-logs.json) show the accepted
revision and version, no 5xx and no concurrency warnings. The five intentional
422 responses are recorded separately.

After recording the diagnosis, Nils also ran Victor's original 40-request
workload unchanged from PR #28 head `703e09a`. Its historical baseline and
incident were collected by Victor; the recovery below was collected by Nils.

| Period / observer | Client UTC window, 2026-11-11 | Valid attempts | Good answers | HTTP 503 | Availability |
|---|---|---:|---:|---:|---:|
| Baseline / Victor | 22:45:48.856064–22:45:50.274142 | 40 | 40 | 0 | 100% |
| Incident / Victor | 22:47:02.397980–22:47:03.811297 | 40 | 7 | 33 | 17.5% |
| After rollback / Nils | 23:24:29.390563–23:24:30.508985 | 40 | 40 | 0 | 100% |

The [comparison record](lab8-evidence/nils-original-workload-comparison.json)
links the historical sources at their immutable commit. The
[recovery requests](lab8-evidence/nils-recovery-original-workload.json) and
[corresponding fresh logs](lab8-evidence/nils-recovery-original-workload-logs.json)
are committed here. The latter contain 41 platform HTTP 200 events: the 40
predictions plus the separate health warm-up. These counts are not mixed.

## Signal definitions and limits

A good external prediction is HTTP 200, the independently expected version
and a finite nonnegative value. Availability uses all attempts, including
transport errors. The two operator periods use the same four-by-four workload;
the historical comparison uses the same five-by-eight workload in all periods.
No deliberate invalid-input request enters either prediction denominator.

The [operator summary](lab8-evidence/nils-observation-summary.json) also records
the request-log windows and server-side prediction medians: 24.156 ms during
the incident and 44.456 ms after initial recovery. Their populations contain
only successful application predictions; they are not client latency or a
like-for-like capacity benchmark. The application-only incident population
contains six eligible events and no 5xx, despite the 13 external failures.
Uvicorn rejects those requests before the logging middleware. Platform request
logs and the external probe are therefore needed to see the whole failure.

A fresh pre-injection operator baseline was unavailable because injection was
already active. Historical baseline results are attributed to Victor. Client
and server clocks are separate; no exact per-request timestamp join is claimed.
The small samples establish this drill's observed recovery, not production
capacity or model quality. No July–December 2012 test metric was computed.

The first post-recovery log query failed due to Windows timestamp quoting;
the successful retry and required scoped log-view flags are recorded in the
timeline. Feedback for the runbook is to include concurrent checks and platform
errors, and to use actual traffic rather than the latest-ready revision name
when identifying the serving revision. Axel remains the shared evidence recorder.
