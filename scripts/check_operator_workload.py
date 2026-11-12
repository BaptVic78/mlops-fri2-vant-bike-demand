"""Measure a small, fixed concurrent workload without changing the service."""

import argparse
import json
import math
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from time import perf_counter

from check_cloud_run import request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gcloud", default="gcloud")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expect-model", required=True)
    args = parser.parse_args()
    # Pin the drill endpoint so credentials cannot be sent to another host.
    if args.base_url != "https://bike-demand-lab7-obot7iy6yq-ew.a.run.app":
        parser.error("This probe is restricted to the agreed lab service")
    auth = subprocess.run(
        [args.gcloud, "auth", "print-identity-token"],
        capture_output=True,
        text=True,
        check=False,
    )
    if auth.returncode or not auth.stdout.strip():
        parser.exit(2, "Authentication unavailable; no requests sent.\n")
    token = auth.stdout.strip()
    payload = {
        "season": 1,
        "yr": 0,
        "mnth": 1,
        "hr": 8,
        "holiday": 0,
        "weekday": 1,
        "workingday": 1,
        "weathersit": 1,
        "temp": 0.3,
        "atemp": 0.3,
        "hum": 0.6,
        "windspeed": 0.2,
    }
    started_at = datetime.now(UTC).isoformat()
    rows = []
    for batch in range(4):
        barrier = Barrier(4)

        def send(index):
            barrier.wait(timeout=10)
            sent_at = datetime.now(UTC).isoformat()
            started = perf_counter()
            try:
                response = request(args.base_url, "/predict", token, payload)
                body = response.get("body", {})
                value = body.get("prediction")
                good = (
                    response["status"] == 200
                    and body.get("model_version") == args.expect_model
                    and type(value) in (int, float)
                    and math.isfinite(value)
                    and value >= 0
                )
                return {
                    "batch": batch + 1,
                    "request": index + 1,
                    "sent_at": sent_at,
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                    "status": response["status"],
                    "model_version": body.get("model_version"),
                    "passed": good,
                }
            except (OSError, ValueError) as error:
                return {
                    "batch": batch + 1,
                    "request": index + 1,
                    "sent_at": sent_at,
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                    "status": "transport_error",
                    "error_type": type(error).__name__,
                    "passed": False,
                }

        with ThreadPoolExecutor(max_workers=4) as pool:
            rows.extend(pool.map(send, range(4)))
    good_count = sum(row["passed"] for row in rows)
    result = {
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "expected_model_version": args.expect_model,
        "workload": "README valid example; 4 batches of 4 simultaneous POST /predict",
        "requests": rows,
        "count": len(rows),
        "status_counts": dict(Counter(str(row["status"]) for row in rows)),
        "good_count": good_count,
        "availability": good_count / len(rows),
        "result": "passed" if good_count == len(rows) else "failed",
    }
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
