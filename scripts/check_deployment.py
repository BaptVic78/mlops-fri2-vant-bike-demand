"""Check a running Lab 5 container from the host.

This does not import the app and does not use TestClient. It sends HTTP to the
published port and reads the container's image id from Docker.
"""

import argparse
import json
import subprocess
import urllib.error
import urllib.request


def claims(expected_model, observed_model, expected_image, observed_image):
    """Return one result line per claim. A mismatch is a failure."""
    rows = [
        ("model", expected_model, observed_model),
        ("image", _image_id(expected_image), _image_id(observed_image)),
    ]
    lines = []
    failed = False
    for name, expected, observed in rows:
        ok = expected == observed and expected != ""
        failed = failed or not ok
        result = "ok" if ok else "FAIL"
        lines.append(
            f"claim {name} expected {expected} observed {observed} result {result}"
        )
    return lines, failed


def _image_id(value):
    text = (value or "").strip()
    if text.startswith("sha256:"):
        return text
    if text:
        return f"sha256:{text}"
    return ""


# Same body as the README example. The response value is not a test metric.
_PREDICT_BODY = {
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


def _request_json(url, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.load(response)
            status = response.status
    except urllib.error.HTTPError as error:
        raise SystemExit(
            f"claim ready expected 200 observed {error.code} result FAIL"
        ) from error
    except urllib.error.URLError as error:
        raise SystemExit(
            f"claim ready expected reachable observed {error.reason} result FAIL"
        ) from error
    if status != 200:
        raise SystemExit(f"claim ready expected 200 observed {status} result FAIL")
    return body


def _observed_model(base_url):
    root = base_url.rstrip("/")
    health = _request_json(f"{root}/health").get("model_version")
    predict = _request_json(f"{root}/predict", _PREDICT_BODY).get("model_version")
    if health != predict:
        return f"health {health} predict {predict}"
    return health


def _container_image(container):
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.Image}}", container],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "docker inspect failed"
        raise SystemExit(f"claim image expected inspect observed {message} result FAIL")
    return result.stdout.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--container", required=True)
    parser.add_argument("--expect-model", required=True)
    parser.add_argument("--expect-image", required=True)
    args = parser.parse_args(argv)
    lines, failed = claims(
        args.expect_model,
        _observed_model(args.base_url),
        args.expect_image,
        _container_image(args.container),
    )
    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
