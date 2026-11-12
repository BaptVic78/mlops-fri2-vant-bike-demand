"""Repeat a bounded, identical workload before, during and after the Lab 8 drill."""

import argparse
import json
import math
import subprocess
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import urlparse

from check_cloud_run import request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gcloud", default="gcloud")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expect-model", required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    parsed = urlparse(base)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or any(
            [
                parsed.username,
                parsed.password,
                parsed.path,
                parsed.query,
                parsed.fragment,
            ]
        )
    ):
        parser.error("base URL must be an HTTPS origin without credentials")
    auth = subprocess.run(
        [args.gcloud, "auth", "print-identity-token"],
        capture_output=True,
        text=True,
        check=False,
    )
    if auth.returncode or not auth.stdout.strip():
        parser.exit(2, "Authentication failed; run gcloud auth login first.\n")
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
    # Warm up separately so the measured cohort does not include cold start.
    warmup = request(base, "/health", token)
    started = datetime.now(UTC).isoformat()
    events = []
    for round_number in range(1, 6):
        barrier = threading.Barrier(8)

        def call(number):
            barrier.wait(timeout=30)
            at = datetime.now(UTC).isoformat()
            begin = perf_counter()
            try:
                response = request(base, "/predict", token, payload)
                body = response.get("body", {})
                value = body.get("prediction")
                good = (
                    response["status"] == 200
                    and body.get("model_version") == args.expect_model
                    and isinstance(value, (int, float))
                    and math.isfinite(value)
                    and value >= 0
                )
                return {
                    "round": round_number,
                    "request": number,
                    "at": at,
                    "status": response["status"],
                    "model_version": body.get("model_version"),
                    "good": good,
                    "client_duration_ms": round((perf_counter() - begin) * 1000, 3),
                }
            except Exception as error:
                # Do not persist exception messages that might include request details.
                return {
                    "round": round_number,
                    "request": number,
                    "at": at,
                    "status": None,
                    "good": False,
                    "error_type": type(error).__name__,
                }

        with ThreadPoolExecutor(max_workers=8) as executor:
            events.extend(executor.map(call, range(1, 9)))
    good = sum(event["good"] for event in events)
    print(
        json.dumps(
            {
                "started_at": started,
                "finished_at": datetime.now(UTC).isoformat(),
                "base_url": base,
                "expected_model_version": args.expect_model,
                "workload": "5 rounds of 8 concurrent valid README predictions; no retries",
                "warmup": warmup,
                "n": len(events),
                "good": good,
                "good_fraction": good / len(events),
                "status_counts": dict(
                    Counter(str(event["status"]) for event in events)
                ),
                "events": events,
                "result": "passed" if good == len(events) else "failed",
            },
            indent=2,
        )
    )
    return 0 if good == len(events) else 1


if __name__ == "__main__":
    raise SystemExit(main())
