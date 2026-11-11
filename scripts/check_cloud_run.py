"""Check the private service with a locally authenticated gcloud account."""

import argparse
import json
import math
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from urllib.parse import urlparse


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def request(base, path, token=None, payload=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    call = urllib.request.Request(base + path, data=data, headers=headers)
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(call, timeout=120) as response:
            return {"status": response.status, "body": json.load(response)}
    except urllib.error.HTTPError as error:
        # The anonymous 403 response is HTML; retain only its status.
        if error.code == 422:
            return {"status": error.code, "body": json.load(error)}
        return {"status": error.code}


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
                parsed.query,
                parsed.fragment,
                parsed.path,
            ]
        )
    ):
        parser.error("base URL must be an HTTPS origin without credentials")
    result = subprocess.run(
        [args.gcloud, "auth", "print-identity-token"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode or not result.stdout.strip():
        parser.exit(2, "Authentication failed; run gcloud auth login first.\n")
    token = result.stdout.strip()
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
    health = request(base, "/health", token)
    prediction = request(base, "/predict", token, payload)
    invalid = request(base, "/predict", token, {**payload, "hr": 24})
    anonymous = request(base, "/health")
    health_body = health.get("body", {})
    prediction_body = prediction.get("body", {})
    value = prediction_body.get("prediction")
    passed = (
        health["status"] == 200
        and health_body.get("status") == "ok"
        and health_body.get("model_version") == args.expect_model
        and prediction["status"] == 200
        and prediction_body.get("model_version") == args.expect_model
        and isinstance(value, (float, int))
        and math.isfinite(value)
        and value >= 0
        and invalid["status"] == 422
        and any(
            error.get("loc") == ["body", "hr"]
            for error in invalid.get("body", {}).get("detail", [])
        )
        and anonymous["status"] == 403
    )
    print(
        json.dumps(
            {
                "verified_at": datetime.now(UTC).isoformat(),
                "base_url": base,
                "expected_model_version": args.expect_model,
                "health": health,
                "prediction": prediction,
                "invalid_hour": invalid,
                "anonymous": anonymous,
                "result": "passed" if passed else "failed",
            },
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
