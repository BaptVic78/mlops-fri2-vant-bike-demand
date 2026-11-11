"""Decide on saved candidate evidence and preserve accepted bundle history."""

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

import yaml

from bike_demand.api import load_artifact
from bike_demand.pipeline import candidate_config
from bike_demand.preflight import sha256
from bike_demand.tracking import timestamp, training_commit

IDENTITY_KEYS = (
    "training_commit",
    "lock_sha256",
    "data_sha256",
    "config_sha256",
    "policy_sha256",
)


@contextmanager
def gate_lock(root: Path):
    lock = root / "artifacts/.gate-lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.mkdir()
    try:
        yield
    finally:
        lock.rmdir()


def write_once(path: Path, record: dict) -> None:
    """Publish a complete JSON record without replacing an earlier decision."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write((json.dumps(record, indent=2, allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink()


def committed_bytes(root: Path, commit: str, path: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("training_commit: require a complete Git SHA")
    return subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{path}"],
        capture_output=True,
        check=True,
    ).stdout


def assess(root: Path, candidate: Path, policy: dict) -> tuple[dict, list, list]:
    evidence = json.loads((candidate / "evaluation.json").read_text())
    missing, failed = [], []

    def check(name, observed, expected, valid):
        row = {"claim": name, "observed": observed, "expected": expected}
        if not valid:
            failed.append(row)

    # Invalid/missing provenance prevents a quality decision.
    identity = {key: evidence[key] for key in IDENTITY_KEYS}
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[
        :12
    ]
    if evidence["run_id"] != candidate.name or run_id != candidate.name:
        raise ValueError("run_id: does not match the declared inputs")
    stored_policy = candidate / "gate-policy.yaml"
    if sha256(stored_policy) != evidence["policy_sha256"]:
        raise ValueError("policy_sha256: candidate policy bytes changed")
    if yaml.safe_load(stored_policy.read_text()) != policy:
        raise ValueError("policy: candidate and current policy differ")
    old_policy = committed_bytes(
        root, evidence["training_commit"], "configs/gate-policy.yaml"
    )
    if yaml.safe_load(old_policy) != policy:
        raise ValueError("policy_on_training_commit: policy differs")
    old_lock = committed_bytes(root, evidence["training_commit"], "uv.lock")
    if hashlib.sha256(old_lock).hexdigest() != evidence["lock_sha256"]:
        raise ValueError("lock_sha256: differs from the training commit")
    if evidence["policy_version"] != policy["policy_version"]:
        raise ValueError("policy_version: mismatch")
    config = candidate_config(candidate / "config.json", policy)
    if config != evidence["config"]:
        raise ValueError("config: evidence and candidate configuration differ")
    original_config = candidate / "input-config.yaml"
    if original_config.exists():
        if sha256(original_config) != evidence["config_sha256"]:
            raise ValueError("config_sha256: original configuration changed")
        if candidate_config(original_config, policy) != config:
            raise ValueError("config: original and effective settings differ")
    else:
        # The two pre-gate pipeline runs used the tracked baseline preset.
        original = committed_bytes(
            root, evidence["training_commit"], "configs/baseline.yaml"
        )
        variants = (original, original.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        if evidence["config_sha256"] not in {
            hashlib.sha256(value).hexdigest() for value in variants
        }:
            raise ValueError("config_sha256: original configuration is unavailable")
    if sha256(root / policy["evaluation"]["data"]) != evidence["data_sha256"]:
        raise ValueError("data_sha256_matches: local snapshot differs")
    if evidence["data_sha256"] != policy["evaluation"]["data_sha256"]:
        raise ValueError("data_sha256_matches: policy differs")
    if evidence["features"] != policy["evaluation"]["features"]:
        raise ValueError("features_match_in_order: mismatch")
    if evidence["working_tree_dirty"] is not False:
        raise ValueError("clean_working_tree: training was dirty or unknown")
    if not evidence["platform"] or not evidence["python_version"]:
        raise ValueError("platform: missing execution environment")
    for key in ("fit_partition", "score_partition", "held_out_partition"):
        expected = dict(policy["evaluation"][key])
        name = expected.pop("name")
        if evidence["partitions"][name] != expected:
            raise ValueError(f"partitions_match: {name}")
    metadata = json.loads((candidate / "model-metadata.json").read_text())
    for key in (
        *IDENTITY_KEYS,
        "run_id",
        "model_sha256",
        "model_version",
        "config",
        "features",
    ):
        if metadata[key] != evidence[key]:
            raise ValueError(f"metadata: {key} mismatch")
    model = candidate / "model.joblib"
    if sha256(model) != evidence["model_sha256"]:
        raise ValueError("evaluated_bytes_are_decided_bytes: checksum mismatch")
    if model.stat().st_size != evidence["model_bytes"]:
        raise ValueError("model_bytes: evidence differs from saved bytes")
    load_artifact(model, candidate / "model-metadata.json")
    values = {
        "candidate_mae": evidence["validation_mae"]["random_forest"],
        "naive_mae": evidence["validation_mae"]["naive_train_mean"],
        "reference_mae": evidence["reference"]["validation_mae"],
        "readback_mae": evidence["readback_mae"],
    }
    if any(
        type(value) not in (int, float) or not math.isfinite(value) or value < 0
        for value in values.values()
    ):
        raise ValueError("metrics: require finite nonnegative numbers")
    if evidence["reference"]["model_sha256"] != policy["reference"]["model_sha256"]:
        raise ValueError("reference: accepted checksum mismatch")
    if values["reference_mae"] != policy["reference"]["recorded_validation_mae"]:
        raise ValueError("reference_rescore_must_equal_record: mismatch")
    if values["readback_mae"] != values["candidate_mae"]:
        raise ValueError("readback_mae_equals_measured: mismatch")
    # Enumerate the supported policy contract so new rules cannot silently pass.
    supported = {
        "quality": {
            "beat_naive_by",
            "beat_reference_by",
            "reference_rescore_must_equal_record",
        },
        "operation": {
            "max_model_bytes",
            "loads_with_service_checks",
            "predictions_finite_non_negative",
        },
        "integrity": {
            "data_sha256_matches",
            "features_match_in_order",
            "partitions_match",
            "clean_working_tree",
            "policy_on_training_commit",
            "evaluated_bytes_are_decided_bytes",
            "readback_mae_equals_measured",
        },
    }
    for group, keys in supported.items():
        if set(policy["criteria"][group]) != keys:
            raise ValueError(f"policy: unsupported or missing {group} criteria")
    for group, keys in supported.items():
        for key in keys - {"beat_naive_by", "beat_reference_by", "max_model_bytes"}:
            if policy["criteria"][group][key] is not True:
                raise ValueError(f"policy: {key} must remain enabled")
    quality = policy["criteria"]["quality"]
    for claim, comparator in (
        ("beat_naive_by", "naive_mae"),
        ("beat_reference_by", "reference_mae"),
    ):
        limit = values[comparator] - quality[claim]
        check(
            claim,
            values["candidate_mae"],
            {"maximum_mae": limit},
            values["candidate_mae"] <= limit,
        )
    operation = policy["criteria"]["operation"]
    check(
        "max_model_bytes",
        evidence["model_bytes"],
        operation["max_model_bytes"],
        evidence["model_bytes"] <= operation["max_model_bytes"],
    )
    for key in ("loads_with_service_checks", "predictions_finite_non_negative"):
        if type(evidence[key]) is not bool:
            raise ValueError(f"{key}: missing measured boolean")
        check(key, evidence[key], True, evidence[key] is True)
    return evidence, missing, failed


def decide(root: Path, candidate: Path) -> dict:
    root, candidate = root.resolve(), candidate.resolve()
    if not re.fullmatch(r"[0-9a-f]{12}", candidate.name):
        raise ValueError("candidate: directory must be named by its run_id")
    policy_path = root / "configs/gate-policy.yaml"
    policy = yaml.safe_load(policy_path.read_text())
    record_dir = root / policy["decisions"]["record_dir"]
    record_path = record_dir / f"{candidate.name}.json"
    with gate_lock(root):
        if record_path.exists():
            raise FileExistsError(f"decision already exists: {record_path}")
        evidence, missing, failed = {}, [], []
        try:
            evidence, missing, failed = assess(root, candidate, policy)
            # Include retained pipeline attempts, even before they receive decisions.
            attempts = {candidate.name}
            paths = list((root / "reports/lab7-evidence").glob("*evaluation*.json"))
            paths += list((root / "artifacts/candidates").glob("*/evaluation.json"))
            paths += list(record_dir.glob("*.json"))
            for path in paths:
                previous = json.loads(path.read_text())
                if previous["policy_version"] == policy["policy_version"]:
                    attempts.add(previous["run_id"])
            if len(attempts) > policy["candidate_settings"]["budget"]:
                raise ValueError("candidate_budget: evaluated attempts exceed policy")
        except (
            KeyError,
            ValueError,
            OSError,
            TypeError,
            subprocess.CalledProcessError,
        ) as error:
            claim = str(error).split(":")[0]
            if isinstance(error, KeyError):
                claim = str(error.args[0])
            if isinstance(error, FileNotFoundError):
                claim = Path(error.filename).name
            missing.append({"claim": claim, "reason": str(error)})
        outcome = "blocked" if missing else ("reject" if failed else "accept")
        record = {
            "run_id": candidate.name,
            "policy_version": policy["policy_version"],
            "policy_sha256": sha256(policy_path),
            "gate_commit": training_commit(root),
            "timestamp": timestamp(),
            "decision": outcome,
            "exit_code": policy["decisions"]["outcomes"][outcome],
            "evaluation_sha256": sha256(candidate / "evaluation.json")
            if (candidate / "evaluation.json").is_file()
            else None,
            "model_sha256": evidence.get("model_sha256"),
            "missing": missing,
            "failed": failed,
        }
        write_once(record_path, record)
        return record


def retain_bundle(source: Path, store: Path) -> str:
    model = source / "model.joblib"
    digest = sha256(model)
    load_artifact(model, source / "model-metadata.json")
    target = store / "versions" / digest
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256(target / "model.joblib") != digest:
            raise ValueError("accepted_store: corrupted retained version")
        load_artifact(target / "model.joblib", target / "model-metadata.json")
        return digest
    temporary = Path(tempfile.mkdtemp(prefix=".tmp-", dir=target.parent))
    try:
        shutil.copyfile(model, temporary / "model.joblib")
        shutil.copyfile(
            source / "model-metadata.json", temporary / "model-metadata.json"
        )
        if sha256(temporary / "model.joblib") != digest:
            raise ValueError("accepted_store: model changed during copy")
        load_artifact(temporary / "model.joblib", temporary / "model-metadata.json")
        temporary.rename(target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return digest


def promote(root: Path, candidate: Path, previous: Path) -> dict:
    """Manual local handoff: retain both bundles, atomically advance a pointer."""
    root, candidate = root.resolve(), candidate.resolve()
    policy = yaml.safe_load((root / "configs/gate-policy.yaml").read_text())
    with gate_lock(root):
        record = json.loads(
            (
                root / policy["decisions"]["record_dir"] / f"{candidate.name}.json"
            ).read_text()
        )
        if record["decision"] != "accept" or record["exit_code"] != 0:
            raise ValueError("promotion: require an accept decision")
        if record["policy_sha256"] != sha256(root / "configs/gate-policy.yaml"):
            raise ValueError("promotion: policy changed since decision")
        if record["evaluation_sha256"] != sha256(candidate / "evaluation.json"):
            raise ValueError("promotion: evaluated evidence changed")
        if record["model_sha256"] != sha256(candidate / "model.joblib"):
            raise ValueError("promotion: candidate bytes changed")
        _, missing, failed = assess(root, candidate, policy)
        if missing or failed:
            raise ValueError("promotion: candidate no longer satisfies the policy")
        store = root / "artifacts/accepted"
        pointer = store / "current.json"
        previous_sha = sha256(previous / "model.joblib")
        if pointer.exists():
            current = json.loads(pointer.read_text())
            if current["model_sha256"] != previous_sha:
                raise ValueError(
                    "promotion: previous bundle differs from current accepted version"
                )
        elif previous_sha != policy["reference"]["model_sha256"]:
            raise ValueError(
                "promotion: initial previous bundle differs from policy reference"
            )
        old = retain_bundle(previous, store)
        new = retain_bundle(candidate, store)
        result = {
            "run_id": candidate.name,
            "model_sha256": new,
            "previous_model_sha256": old,
            "bundle": f"versions/{new}",
            "previous_bundle": f"versions/{old}",
            "decision_sha256": sha256(
                root / policy["decisions"]["record_dir"] / f"{candidate.name}.json"
            ),
        }
        history = store / "promotions" / f"{candidate.name}.json"
        # An interrupted promotion can resume only with identical recorded inputs.
        if history.exists():
            if json.loads(history.read_text()) != result:
                raise ValueError("promotion: existing history has different inputs")
        else:
            write_once(history, result)
        temporary = store / ".current.tmp"
        temporary.write_text(json.dumps(result, indent=2) + "\n")
        os.replace(temporary, pointer)
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    try:
        if args.promote:
            if args.previous is None:
                parser.error("--promote requires --previous")
            result = promote(Path.cwd(), args.candidate, args.previous)
            code = 0
        else:
            result = decide(Path.cwd(), args.candidate)
            code = result["exit_code"]
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Gate blocked: {error}")
        return 2
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
