"""Check a running Lab 5 container from the host.

This does not import the app and does not use TestClient. HTTP goes to the
loopback port published by the container being inspected, not to another port.
"""

import argparse
import json
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlparse


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


def published_loopback_url(running, ports, supplied_url=None):
    """Return the inspected container's loopback URL, or a failure line.

    A supplied URL is accepted only when it is that same binding. Requests must
    not go to a different port, even if another container is serving there.
    """
    if not running:
        return None, "claim container expected running observed stopped result FAIL"
    bindings = _loopback_bindings(ports)
    if len(bindings) != 1:
        return None, (
            "claim port expected one loopback binding "
            f"observed {len(bindings)} result FAIL"
        )
    host, port = bindings[0]
    derived = _binding_url(host, port)
    if supplied_url is None:
        return derived, None
    if _same_binding(supplied_url, host, port):
        return derived, None
    return None, (
        f"claim endpoint expected {derived} observed {supplied_url} result FAIL"
    )


def _image_id(value):
    text = (value or "").strip()
    if text.startswith("sha256:"):
        return text
    if text:
        return f"sha256:{text}"
    return ""


def _loopback_bindings(ports):
    found = []
    for bindings in (ports or {}).values():
        for binding in bindings or []:
            host = (binding.get("HostIp") or "").lower()
            port = str(binding.get("HostPort") or "")
            if host in {"127.0.0.1", "::1"} and port.isdigit():
                found.append((host, port))
    return found


def _binding_url(host, port):
    if host == "::1":
        return f"http://[::1]:{port}"
    return f"http://{host}:{port}"


def _same_binding(url, host, port):
    parsed = urlparse(url.strip())
    if parsed.scheme != "http" or parsed.username or parsed.password:
        return False
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        return False
    if parsed.port is None or str(parsed.port) != str(port):
        return False
    supplied = (parsed.hostname or "").lower()
    if host == "127.0.0.1" and supplied in {"127.0.0.1", "localhost"}:
        return True
    return supplied == host


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


def _container_facts(container):
    result = subprocess.run(
        ["docker", "inspect", container],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "docker inspect failed"
        raise SystemExit(
            f"claim container expected inspect observed {message} result FAIL"
        )
    payload = json.loads(result.stdout)
    if not payload:
        raise SystemExit("claim container expected inspect observed empty result FAIL")
    info = payload[0]
    state = info["State"]
    running = state.get("Running") is True and state.get("Paused") is not True
    return running, info["Image"], info["NetworkSettings"]["Ports"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--container", required=True)
    parser.add_argument("--expect-model", required=True)
    parser.add_argument("--expect-image", required=True)
    args = parser.parse_args(argv)
    running, image, ports = _container_facts(args.container)
    base_url, error = published_loopback_url(running, ports, args.base_url)
    if error:
        print(error)
        return 1
    lines, failed = claims(
        args.expect_model,
        _observed_model(base_url),
        args.expect_image,
        image,
    )
    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
