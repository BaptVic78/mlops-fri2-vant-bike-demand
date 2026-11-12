# Lab 8 — shared incident timeline

Recorder: Axel Alacache (`axou947`). Injector: Victor Rouleau. Operator: Nils
Giraud. Runbook: Thomas Soubagne.

This record joins the original observations with the diagnosis, rollback and
fresh recovery checks. Historical files are kept unchanged. The recorder did
not observe the injection live: its times and results come from Victor's
saved output, Cloud Run events and the GitHub handoff. Nils's investigation
and rollback are attributed to his operator record.

## Scope and accepted state

- Service: `bike-demand-lab7`, project `fourth-eon-424715-k1`, region `europe-west1`.
- Private URL: `https://bike-demand-lab7-obot7iy6yq-ew.a.run.app`.
- Expected model version: `baseline-28fdf1958b8a`.
- Accepted revision: `bike-demand-lab7-refcurrent80f31db`.
- Fallback revision: `bike-demand-lab7-refbase80f31db`.
- Model SHA-256: `d24c050e3631d5b4c2feb8cb571bef6382d8c975c42a5c11edd28de78a0b8c07`.
- Accepted image digest: `sha256:6dd4148b94859b21b05769af5971892e604fee3c2a3f201c411910a080f932ff`.

The [Lab 7 report](lab-07.md), [gate decisions](lab7-decisions/) and
[accepted handoff](lab7-evidence/accepted-handoff.json) give the retained
identity and integrity records. All three real candidates were rejected;
the incident did not promote or train a model.

## Timeline and sources

All times are UTC. Client timestamps and Cloud Run timestamps are separate;
they are not exact per-request joins.

| Time | Owner / observation | Raw source |
|---|---|---|
| 2026-11-11 22:43:36 | Thomas's runbook merged before injection. | [PR #27 merge](lab8-evidence/axel-runbook-merge.json) |
| 22:45:48.856–22:45:50.274 | Victor's baseline: 40 valid predictions, all successful. | [Baseline output](lab8-evidence/victor-baseline-workload.json) |
| 22:46:06–22:46:59 | Cloud Run service-change events surround the new revision and traffic change. The file is not a client-side command transcript. | [Original Cloud Run export](lab8-evidence/victor-request-logs.json) |
| 22:47:02.398–22:47:03.811 | Victor repeated the workload: 7 HTTP 200 and 33 HTTP 503. The sequential contract check still passed. | [Concurrent requests](lab8-evidence/victor-incident-workload.json), [serial check](lab8-evidence/victor-incident-contract-check.json), [traffic](lab8-evidence/victor-incident-traffic.json) |
| 22:50:39 | Victor notified `axou947` of the first measured affected window without naming the fault. This is the saved notification time, not an earlier acknowledgement. | [GitHub handoff](lab8-evidence/axel-coordination-record.json) |
| 23:14:09 | Nils first noticed traffic on the unexpected revision; Cloud Run still reported Ready. | [First observation](lab8-evidence/nils-incident-observation.txt), [operator timeline](lab8-evidence/nils-operator-timeline.md) |
| 23:16:16.653–23:16:17.130 | Nils's separate 16-request probe: 3 successful answers and 13 HTTP 503. | [Operator probe](lab8-evidence/nils-incident-workload.json), [incident logs](lab8-evidence/nils-incident-logs.json) |
| 23:17:25 | Nils recorded his diagnosis before recovery. | [Diagnosis and hypotheses](lab8-evidence/nils-operator-timeline.md) |
| 23:19:34 | Nils started one traffic rollback to the verified accepted revision. | [Start time](lab8-evidence/nils-rollback-start.txt), [command result](lab8-evidence/nils-rollback-command.txt), [target](lab8-evidence/nils-rollback-target.json) |
| 23:19:45.634 | The route became Ready with 100% accepted traffic; the incident revision was retained at zero traffic. | [Recovery service](lab8-evidence/nils-recovery-service.json), [retained revision](lab8-evidence/nils-retained-faulty-revision.json) |
| 23:20:17.468–23:20:18.035 | Nils repeated his own probe: 16/16 successful answers. Five fresh serial checks also passed. | [Concurrent recovery](lab8-evidence/nils-recovery-workload.json), [serial checks](lab8-evidence/nils-recovery-contract-checks.json), [fresh logs](lab8-evidence/nils-recovery-logs.json) |
| 23:24:29.391–23:24:30.509 | After his diagnosis, Nils ran Victor's original script unchanged: 40/40 successful answers. | [Original-workload recovery](lab8-evidence/nils-recovery-original-workload.json), [matching log export](lab8-evidence/nils-recovery-original-workload-logs.json) |
| 2026-11-12 08:33:46–08:34:19 | Recorder verification from merged source `6002252`: accepted traffic, retained revisions, five passing contract checks and 40/40 successful predictions. No service change. | [Run and commands](lab8-evidence/axel-verification-run.json), [summary](lab8-evidence/axel-verification-summary.json) |

The earliest failed client row in Victor's file is at 22:47:02.399983 UTC.
The first signal noticed by the operator was later, at 23:14:09. These are
different observations; the timeline does not claim immediate detection.

## Explanation and controlled recovery

Nils tested a changed or unloadable model, a configuration problem and invalid
input. The revision image and successful response version matched the accepted
state. Valid inputs failed with 503, rather than validation 422. The suspect
revision added `UVICORN_LIMIT_CONCURRENCY=2`, while Cloud Run could send eight
requests at once. Platform logs showed 13 failures and 13 concurrency warnings
for his probe. Application middleware did not record those early rejections.

This supported a configuration fault. Nils checked the retained target, then
changed only traffic. No rebuild, retraining, IAM change or model replacement
was used for recovery. His [timeline](lab8-evidence/nils-operator-timeline.md)
also preserves the failed log query and the successful retry.

## Same-workload comparison

A good prediction is HTTP 200, the independently expected version and a finite
nonnegative value. All 40 valid attempts count, including any transport failure.
Five rounds of eight requests use the fixed README input, without retries.
The separate health warm-up and intentional invalid-input checks are excluded.

| Period / observer | Valid attempts | Good answers | HTTP 503 | Good fraction |
|---|---:|---:|---:|---:|
| Baseline / Victor | 40 | 40 | 0 | 100% |
| Incident / Victor | 40 | 7 | 33 | 17.5% |
| After rollback / Nils | 40 | 40 | 0 | 100% |
| Later verification / recorder | 40 | 40 | 0 | 100% |

The [historical comparison](lab8-evidence/nils-original-workload-comparison.json)
and [recorder output](lab8-evidence/axel-recovery-workload.json) retain the
windows and individual requests. Nils's 16-request probe is a separate sample;
its counts are not added to this table. His [summary](lab8-evidence/nils-observation-summary.json)
keeps server-side durations separate from client latency.

## Fresh recorder verification

The three sources agree on recovery:

1. **Identity:** [service state](lab8-evidence/axel-service-state.json) shows
   100% traffic on `refcurrent80f31db`. All three [retained revisions](lab8-evidence/axel-retained-revisions.json)
   are Ready and use the accepted image digest.
2. **Behaviour:** five [contract checks](lab8-evidence/axel-contract-checks.json)
   pass health 200, valid prediction 200, invalid hour 422 and anonymous 403.
   The original [40-request workload](lab8-evidence/axel-recovery-workload.json)
   passes with `baseline-28fdf1958b8a`.
3. **Signals:** the [new raw export](lab8-evidence/axel-live-logs.json) contains
   51 eligible platform events after the verification start, all HTTP 200 on
   the accepted revision. There are 56 application events: 51 successful events
   and five intentional 422 responses. All name the expected version; no
   concurrency or model-load warning appears in that window.

The log window is 08:33:55.506489–08:34:18.570182 UTC. The 51 successes include
40 concurrent predictions, five serial predictions, five serial health checks
and one health warm-up. They are not a 51-request concurrent workload. The raw
export covers a wider period; the [summary](lab8-evidence/axel-verification-summary.json)
selects events after the recorded verification start. Empty logs would mean
unknown, not success. New files were used rather than replacing earlier output.

The [SHA-256 index](lab8-evidence/axel-evidence-index.json) lists the saved raw
records and summaries. Identity tokens are not included. This PR collects raw
records directly; screenshots are optional support under the three-image limit.

## Limits and remaining handoff

- The recorder joined after the incident and reconstructed earlier events from
  the named sources. Nils did not collect his own baseline before injection.
- A passing serial readiness check missed this fault. Thomas's next runbook
  update should include the concurrent probe and platform request logs, and
  distinguish serving traffic from the latest revision name.
- Traffic recovery leaves the faulty override in the latest revision template.
  Before a future deployment, its owner must remove that override in reviewed
  work. This recorder PR does not deploy or change configuration.
- A new valid-request 5xx, unexpected version, concurrency warning or traffic
  on the incident revision would challenge the recovery claim. Small samples
  do not prove production capacity or predictive quality. No held-test metric
  was computed for this record.
- After peer review, merge this recorder PR and check main CI before creating
  the annotated `m4` checkpoint. `v1.0.0`, the final verification and the
  presentation belong to the later project handover.
