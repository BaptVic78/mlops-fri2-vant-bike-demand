# Lab 8 incident handoff

> Historical injector handoff from PR #28. The statements below describe the
> injection-time state. Recovery has since been recorded in PR #29; use the
> [shared timeline and latest verification](../lab8-timeline.md) for current
> status. Original request and log files have not been changed.

Owner: Victor Rouleau (injector). Operator: Nils Giraud. Recorder: Axel.

Thomas's runbook [PR #27](https://github.com/BaptVic78/mlops-fri2-vant-bike-demand/pull/27)
was merged at **2026-11-11 22:43:36 UTC**, before this drill.
The scope is only our private `bike-demand-lab7` service in
`fourth-eon-424715-k1`, `europe-west1`.

## Observation and handoff

I recorded a baseline, introduced one reversible runtime configuration fault,
and repeated exactly the same workload. I kept the accepted model, image,
API code, data, IAM and retained accepted revisions unchanged. The fault is
active; no recovery or operator diagnosis is claimed here.

| Period | UTC start | UTC end | Valid prediction attempts | Successful expected-version answers | HTTP 503 |
|---|---|---|---|---|---|
| Baseline | 2026-11-11 22:45:48.856064 | 2026-11-11 22:45:50.274142 | 40 | 40 (100%) | 0 |
| Incident | 2026-11-11 22:47:02.397980 | 2026-11-11 22:47:03.811297 | 40 | 7 (17.5%) | 33 |
| Recovery | Not run | Not run | — | — | — |

The first failing request is timestamped in the incident workload file.
The change took effect after the baseline and before the incident window.
For Axel: use **22:47:02 UTC on 2026-11-11** as the first measured affected
window, then refine the timeline from the raw request and platform events.
The recorder has not yet acknowledged this handoff.

These are five rounds of eight concurrent valid predictions, without retries,
using the fixed README input. A separate health warm-up is outside the 40
attempts. A good attempt is HTTP 200, the independently expected version,
and a finite nonnegative prediction. The denominator includes all 40
attempts, including transport failures if any. Client durations include
network time; they are not application `duration_ms`.

The sequential contract checker **still passes during the incident**. A
passing low-load check alone therefore does not establish service health
under this workload. Preserve this result as well as the failures.

## Raw evidence

- [Baseline workload](victor-baseline-workload.json).
- [Incident workload, individual request timestamps and statuses](victor-incident-workload.json).
- [Incident traffic and service readiness](victor-incident-traffic.json).
- [Separate sequential contract check](victor-incident-contract-check.json).
- [Unedited Cloud Run log export](victor-request-logs.json): 194 entries,
  from 22:42:42.053124 to 22:47:03.412188 UTC. This wider export includes
  baseline, incident and other checks; filter by window, route and revision
  before computing a cohort. It is not itself the 40-request denominator.

Application request events alone can omit failures returned before the
application handler. Compare external observations with Cloud Run request
logs (`httpRequest.status`) as well as application events; report any
population difference instead of treating missing events as success.
Log ingestion may lag. Later exports should use new filenames.

## Repeat the observation

From the repository root, authenticated with your own authorized Google account:

```powershell
uv run --locked python scripts/check_incident_workload.py `
  --base-url https://bike-demand-lab7-obot7iy6yq-ew.a.run.app `
  --expect-model baseline-28fdf1958b8a
```

Save stdout under a new filename. Exit 0 means all 40 attempts met the
contract; exit 1 means at least one did not; exit 2 is an authentication
blocker. The workload is bounded to 40 valid predictions plus one warm-up.
It does not mutate Cloud Run. It uses a token in memory and never prints it.

## Next owners

Nils: use [RUNBOOK.md](../../RUNBOOK.md), retain the first signal, test at
least two hypotheses and write the diagnosis timeline before requesting
the injector's explanation. Name and verify the accepted rollback target,
then make the single traffic change and collect fresh recovery evidence.
Keep this workload unchanged for the recovery comparison.

Axel: preserve the actual timeline, raw evidence, recovery and fresh checks;
use at most three screenshots across the incident report. The incident
revision stays retained at 0% traffic after recovery.

Thomas: review this handoff and the workload tool. The injection details are
withheld until Nils's diagnosis record exists, as agreed in the work split.
After that record, Victor will disclose the exact change and reversal.

The accepted rollback target remains `bike-demand-lab7-refcurrent80f31db`,
with `bike-demand-lab7-refbase80f31db` retained as fallback. Both use the
accepted image and model documented in the runbook. No candidate was promoted,
no training was performed and no held-test metric was computed.
