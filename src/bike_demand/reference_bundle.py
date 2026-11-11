"""Recover and retain the trusted reference named by the Lab 7 policy."""

import argparse
import json
from pathlib import Path

import yaml

from bike_demand.gate import gate_lock, retain_bundle
from bike_demand.preflight import sha256


def prepare_reference(root: Path, source: Path) -> dict:
    root, source = root.resolve(), source.resolve()
    with gate_lock(root):
        policy = yaml.safe_load((root / "configs/gate-policy.yaml").read_text())
        expected = policy["reference"]["model_sha256"]
        if sha256(source / "model.joblib") != expected:
            raise ValueError("reference: checksum differs from the accepted policy")
        store = root / "artifacts/accepted"
        digest = retain_bundle(source, store)
        bundle = store / "versions" / digest
        metadata_path = bundle / "model-metadata.json"
        metadata = json.loads(metadata_path.read_text())
        return {
            "model_sha256": digest,
            "model_version": metadata["model_version"],
            "metadata_sha256": sha256(metadata_path),
            "bundle": bundle.relative_to(root).as_posix(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare_reference(Path.cwd(), args.source)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"Reference recovery blocked: {error}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
