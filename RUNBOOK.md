# Runbook: Bike Demand service on Cloud Run

Who this is for: the person on duty for `bike-demand-lab7` who has to tell
whether the service is healthy, explain a change, and return it to the last
accepted version. You do not need the author or the incident scenario to
follow it. Run the commands from the repository root, in Windows PowerShell 5.1,
with your own authorized Google account. Each step names the raw evidence to
save. The incident record (timeline, hypotheses and conclusion) goes in
`reports/lab8-evidence/`. This runbook describes how to work an incident. It
does not record what happened.

Order of work: **observe → record the first signal → test hypotheses →
name the rollback target → one controlled change → fresh verification**.

## 0. Last verified context

These are the values to compare against. Do not read them from the live
service and pass them back. Each one comes from a record made before any
incident.

| Item | Accepted value | Source |
|---|---|---|
| Project / region / service | `fourth-eon-424715-k1` / `europe-west1` / `bike-demand-lab7` | [README](README.md#serve-and-recover-the-accepted-reference) |
| URL (authenticated only) | `https://bike-demand-lab7-obot7iy6yq-ew.a.run.app` | same |
| Accepted serving revision (100 %) | `bike-demand-lab7-refcurrent80f31db` | [revisions record](reports/lab7-evidence/cloud-run-nils-revisions.json) |
| Retained previous revision (0 %, Ready) | `bike-demand-lab7-refbase80f31db` | same |
| Latest template revision (0 %, no concurrency override) | `bike-demand-lab7-00004-bmn` | [template cleanup](reports/lab8-evidence/template-cleanup-2026-11-12.json) |
| Retained incident revision (0 %, still has `UVICORN_LIMIT_CONCURRENCY=2`) | `bike-demand-lab7-lab8-victor-01` | same |
| Image digest (both revisions) | `europe-west1-docker.pkg.dev/fourth-eon-424715-k1/bike-demand/service@sha256:6dd4148b94859b21b05769af5971892e604fee3c2a3f201c411910a080f932ff` | same |
| Expected `model_version` | `baseline-28fdf1958b8a` | [handoff record](reports/lab7-evidence/accepted-handoff.json) |
| Model SHA-256 | `d24c050e3631d5b4c2feb8cb571bef6382d8c975c42a5c11edd28de78a0b8c07` | [`configs/gate-policy.yaml`](configs/gate-policy.yaml) |
| Metadata SHA-256 | `bef55cb388d8d784f41b029269fc41a1d7e555a820714d46429d3fcd66fdc8bc` | [README](README.md#serve-and-recover-the-accepted-reference) |
| Code commit of the accepted image | `80f31db` (`80f31dbb63503e618ee65450962f85e76466c8e4`) | [Dockerfile.accepted](reports/lab7-evidence/Dockerfile.accepted) |
| Gate decisions (all three candidates rejected) | `reports/lab7-decisions/*.json` | [Lab 7 report](reports/lab-07.md) |

Last verified on 2026-11-11 at 21:03 UTC by Nils Giraud. He ran
`check_cloud_run.py` and `gcloud run services describe`, with no traffic
change. On 2026-11-12 Axel removed `UVICORN_LIMIT_CONCURRENCY` from the latest
template with `--no-traffic`. Traffic stayed at 100% on
`bike-demand-lab7-refcurrent80f31db`. The new revision
`bike-demand-lab7-00004-bmn` has no traffic and no concurrency override. The
earlier revisions remain. `check_cloud_run.py` passed with
`baseline-28fdf1958b8a`. Record:
[template cleanup](reports/lab8-evidence/template-cleanup-2026-11-12.json).
If this context is out of date (a new promotion, a new revision),
update this table in a reviewed pull request before the next incident.

Set these once per PowerShell session. The commands below use them:

```powershell
$Project  = 'fourth-eon-424715-k1'
$Region   = 'europe-west1'
$Service  = 'bike-demand-lab7'
$Url      = 'https://bike-demand-lab7-obot7iy6yq-ew.a.run.app'
$Expected = 'baseline-28fdf1958b8a'
$Evidence = 'reports/lab8-evidence'
New-Item -ItemType Directory -Force $Evidence | Out-Null
gcloud auth login
uv sync --locked
```

Never save an identity token, a `gcloud auth print-*` output, a request body
or a response body containing feature values in the evidence folder. The
checker output below is fine. It contains only the fixed README example.

## 1. What the service promises

| Contract | Normal answer |
|---|---|
| `GET /health` with a token | 200, `{"status":"ok","model_version":"<expected>"}` |
| `POST /predict` valid body with a token | 200, finite `prediction` ≥ 0 and the same `model_version` |
| `POST /predict` invalid body (e.g. `hr=24`) | 422, error located at `["body","hr"]` |
| Any request without a token | 403 from Cloud Run (the request never reaches the container) |
| Model not loadable | 503 on `/health` and on a valid `/predict`, detail `Model not available: <cause>` |

The service never trains. Restarting it or retraining is not a recovery
action.

## 2. Signals and their definitions

Each request writes one JSON line to stdout, which Cloud Run stores as
`jsonPayload`: `event="http_request"`, `method`, `route`, `status_code`,
`outcome` (`accepted` < 400, `rejected` 4xx, `error` 5xx), `duration_ms`
and `model_version`. A startup failure writes a separate error line
`Model not loaded: <cause>`.

| Signal | Population (eligible) | Good | Unit / window | Missing data |
|---|---|---|---|---|
| **Availability** | Log lines with `route` in `/health`, `/predict` and `status_code` not in `401, 403, 404, 405, 422` | `status_code` = 200 | good ÷ eligible, per UTC window, with `n` | `n = 0` means **unknown**, not healthy |
| **Identity** | Same eligible lines | `model_version` = `$Expected` **and** `revision_name` = the revision expected to serve | share of eligible lines | `model_version: null` counts as not good |
| **Errors** | Same eligible lines | — | count of `outcome="error"` (5xx) | — |
| **Intentional rejections** | `/predict` lines with 422 | — | count, reported separately | Not a failure: invalid input is meant to be refused |
| **Server latency** | Eligible `/predict` with 200 | — | median and max `duration_ms`, in ms | Excludes cold start and network time |
| **External check** | One `check_cloud_run.py` run | `"result": "passed"` | pass/fail per run, with UTC time | Exit 2 (no token) is a blocker, not a failure |

Why this split: a 422 shows the validation works and must not lower
availability. A 503 or 500 on a *valid* request is a failed eligible attempt.
A 403 is produced by Cloud Run IAM, not by our code, so it never shows up in
the application log.

## 3. Observe: baseline before anything changes

Record normal behaviour **before** any fault is injected, using the same
commands you will use during the incident.

```powershell
# 3a. External behaviour, repeated N times (keep N the same in every period)
1..5 | ForEach-Object {
  uv run --locked python scripts/check_cloud_run.py --base-url $Url --expect-model $Expected
} | Out-File -Encoding utf8 "$Evidence/baseline-check.json"

# 3b. Which revision serves, with what image
gcloud run services describe $Service --project=$Project --region=$Region `
  --format="yaml(status.traffic,status.latestReadyRevisionName,status.conditions)" `
  | Out-File -Encoding utf8 "$Evidence/baseline-service.yaml"
gcloud run revisions list --service=$Service --project=$Project --region=$Region `
  --format="table(metadata.name,metadata.creationTimestamp,status.conditions[0].status,status.imageDigest)" `
  | Out-File -Encoding utf8 "$Evidence/baseline-revisions.txt"

# 3c. Raw request events for the same window
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$Service AND jsonPayload.event=http_request" `
  --project=$Project --freshness=30m --format=json `
  | Out-File -Encoding utf8 "$Evidence/baseline-logs.json"
```

Summarize the saved raw logs. This reads the file and does not change it:

```powershell
$Logs = Get-Content -Raw "$Evidence/baseline-logs.json" | ConvertFrom-Json
$Logs | Group-Object { $_.resource.labels.revision_name },
                     { $_.jsonPayload.route },
                     { $_.jsonPayload.status_code },
                     { $_.jsonPayload.model_version } |
  Select-Object Count, Name | Format-Table -AutoSize
$Logs | Measure-Object -Property timestamp -Minimum -Maximum   # the window
```

Write in the record: UTC window (first and last timestamp), `n` per route,
status counts, revisions seen, `model_version` values, median `duration_ms`
for `/predict`. Use the same definitions and the same command for the
incident and recovery periods (section 7).

## 4. Notice: record the first signal

Watch for any of these:

- `check_cloud_run.py` prints `"result": "failed"` or exits non-zero;
- `/health` is not 200, or its `model_version` differs from `$Expected`;
- logs show `outcome="error"`, `model_version` null or unexpected, or a
  `revision_name` that is not the accepted one;
- `/predict` returns a value that is not finite or is negative, or `duration_ms`
  far outside the baseline;
- `gcloud logging read` finds a `Model not loaded` line (query below).

**Before guessing a cause**, save the evidence that made you look:

```powershell
uv run --locked python scripts/check_cloud_run.py --base-url $Url --expect-model $Expected `
  | Out-File -Encoding utf8 "$Evidence/incident-first-check.json"
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$Service" `
  --project=$Project --freshness=30m --format=json `
  | Out-File -Encoding utf8 "$Evidence/incident-logs.json"
```

In the timeline, write: UTC time of the first signal, what exactly was
observed (status, body detail, field values), the scope (which route, which
revision, all requests or some), and the file that holds it. Do not edit raw
files afterwards to match the conclusion. A signal you noticed late or
missed is part of the result. Write it down.

## 5. Explain: check each boundary, cheapest first

A mismatch is evidence. It becomes a cause only once you show that it
produces the observed symptom. For each boundary, record what you checked and
the result, and say so if you did not check it.

| # | Boundary | Command | Compare with |
|---|---|---|---|
| 1 | **Service: revision and traffic** | `gcloud run services describe $Service --project=$Project --region=$Region --format="yaml(status.traffic,status.latestReadyRevisionName,status.conditions)"` | Section 0: 100 % on the accepted revision, conditions `Ready=True` |
| 2 | **Service: image** | `gcloud run revisions list --service=$Service --project=$Project --region=$Region --format="table(metadata.name,metadata.creationTimestamp,status.imageDigest)"` | Accepted digest `sha256:6dd4148b…`. Note any revision newer than the accepted one |
| 3 | **Configuration** | `gcloud run revisions describe <revision> --project=$Project --region=$Region --format="yaml(spec.containers[0].image,spec.containers[0].env,spec.containers[0].command,spec.containers[0].args,spec.containers[0].ports,spec.containers[0].resources)"` | Run the same command on `bike-demand-lab7-refcurrent80f31db` and diff the two outputs |
| 4 | **Model identity** | `/health` body and `model_version` in the log lines | `$Expected`. `null` means the model did not load |
| 5 | **Startup** | `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$Service AND textPayload:Model AND textPayload:loaded" --project=$Project --freshness=1h` | No line expected. A line gives the cause (`FileNotFoundError`, checksum mismatch, …) |
| 6 | **Model bytes** (only if 4 or 5 point at the model) | Pull the suspect revision's image and hash its `artifacts/model.joblib` and `artifacts/model-metadata.json`, as in [README → recover the exact package](README.md#serve-and-recover-the-accepted-reference) | Model `d24c050e…`, metadata `bef55cb3…` |
| 7 | **Inputs** | Group the log lines by `route` and `status_code` (section 3 snippet), and compare with the baseline | A rise in 422 alone means callers send invalid input, not that the service is broken |

Write **at least two hypotheses** before you act. For each one, record:

| Hypothesis | Expected signature if true | Discriminating check (row above) | Actual result | Kept / rejected | Still uncertain |
|---|---|---|---|---|---|

Typical pairs to separate: *new revision/image* versus *configuration change
on the same image*; *model not loadable* versus *model loaded but different*;
*service fault* versus *callers sending invalid input*. Keep rejected
hypotheses and failed checks in the record.

## 6. Recover: roll back to a named, compatible target

Roll back when the evidence points to a release or artifact change: a
revision, image, configuration or model that differs from section 0. Do not
roll back when the evidence points to input only (rising 422s, expected
behaviour), or when no boundary differs. In those cases, escalate (section 8).
Never retrain, rebuild or redeploy as the recovery action.

### 6a. Name the target before switching

The target is the most recent revision **verified as accepted**, not the one
deployed just before. By default it is `bike-demand-lab7-refcurrent80f31db`,
with `bike-demand-lab7-refbase80f31db` as the fallback (same image, same
model). Before you switch, confirm on the target:

```powershell
$Target = 'bike-demand-lab7-refcurrent80f31db'
gcloud run revisions describe $Target --project=$Project --region=$Region `
  --format="yaml(metadata.name,status.conditions,status.imageDigest,spec.containers[0].env)" `
  | Out-File -Encoding utf8 "$Evidence/rollback-target.yaml"
```

All of these must hold. If one fails, do not switch: try the fallback
revision, or escalate.

- [ ] `Ready` condition is `True`;
- [ ] `imageDigest` ends with `sha256:6dd4148b94859b21b05769af5971892e604fee3c2a3f201c411910a080f932ff`;
- [ ] its configuration matches the accepted one (row 3 above). It must not carry the suspect change;
- [ ] that image holds model `d24c050e…`, which the accepted-image build checked with `sha256sum -c`. If you doubt it, extract and hash it (row 6). **A checksum mismatch fails closed**: do not route traffic to it and do not relabel it.

### 6b. One controlled change

```powershell
$Since = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$Since   # write this time in the timeline
gcloud run services update-traffic $Service --project=$Project --region=$Region `
  --to-revisions="$Target=100" `
  | Out-File -Encoding utf8 "$Evidence/rollback-command.txt"
```

Make only this change. Do not delete the faulty revision: it is evidence and
it stays available, with 0 % traffic, for the diagnosis. Do not change the
image, environment variables or IAM in the same step.

## 7. Verify after the change

A successful command is not a recovery. Collect **fresh** evidence from
three independent sources, over a window that starts after the traffic change:

```powershell
# Identity: who serves now
gcloud run services describe $Service --project=$Project --region=$Region `
  --format="yaml(status.traffic,status.conditions)" `
  | Out-File -Encoding utf8 "$Evidence/recovery-service.yaml"

# Behaviour: same N external checks as the baseline
1..5 | ForEach-Object {
  uv run --locked python scripts/check_cloud_run.py --base-url $Url --expect-model $Expected
} | Out-File -Encoding utf8 "$Evidence/recovery-check.json"

# Signals: post-change request events only ($Since was set in 6b).
# PowerShell 5.1 drops bare inner quotes when calling gcloud, hence \".
$Filter = "resource.type=cloud_run_revision AND resource.labels.service_name=$Service AND jsonPayload.event=http_request AND " + 'timestamp>=\"' + $Since + '\"'
gcloud logging read $Filter --project=$Project --format=json `
  | Out-File -Encoding utf8 "$Evidence/recovery-logs.json"
```

Recovered means all three agree:

1. **Identity**: 100 % traffic on `$Target`, which is `Ready`;
2. **Behaviour**: every check prints `"result": "passed"` with `$Expected`;
3. **Signals**: after the change, every eligible line comes from `$Target`
   with `model_version` = `$Expected`, availability = 1 and no
   `outcome="error"`. Record `n` and the window.

Then fill in the comparison with the same definitions:

| Period | UTC window | n eligible | Availability | Errors (5xx) | 422 | Revision(s) | `model_version` | Median `/predict` ms | External check |
|---|---|---|---|---|---|---|---|---|---|
| Baseline | | | | | | | | | |
| Incident | | | | | | | | | |
| After rollback | | | | | | | | | |

State what improved, what is still unknown, and what would disprove the
recovery claim (for example, a new error line from `$Target`).

## 8. Escalate, and know the limits

Stop and escalate to the team channel, naming the failing step, the exact
message, the current traffic split and the next owner, when:

- `gcloud` returns a permission or quota error (`PERMISSION_DENIED`,
  `RESOURCE_EXHAUSTED`). This is a blocker, not a recovery. Rehearse locally
  with the [Deploy section](README.md#deploy) and say so in the record;
- the checker exits 2 (no identity token) after `gcloud auth login`;
- no retained revision passes the 6a checklist;
- verification still fails after the rollback, or the signal returns on `$Target`;
- the evidence points to a forward fix (code, input guard). That needs a
  reviewed pull request, not an operator action.

Owners: Nils Giraud (Cloud Run deployment), Victor Rouleau (accepted image
build), Axel Alacache (incident record). Promotion of a new model stays a
human decision through the gate ([README → Pipeline and gate](README.md#pipeline-and-gate)).

What this runbook does not tell you:

- **Service health is not predictive quality.** A passing check shows that the
  accepted bytes answer within the contract, not that the predictions are
  accurate. Quality comparisons use only the January–June 2012 validation
  rows. No metric is ever computed on July–December 2012.
- `duration_ms` measures the server side only. Cold starts and network time
  are not in it.
- Cloud Run logs can arrive a few seconds late. An empty window means
  "unknown", not "no traffic".
- Both retained revisions use the same image. A fault inside that image
  could not be undone by switching between them. Recovery would then need
  the image to be rebuilt from the retained bundle in a reviewed change
  ([README](README.md#serve-and-recover-the-accepted-reference)).

After each drill, revise this runbook from what the operator missed or
needed, and update section 0 if the accepted state changed.
