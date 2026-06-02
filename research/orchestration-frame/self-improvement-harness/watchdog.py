#!/usr/bin/env python3
"""External watchdog for the self-improvement harness."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
CONTROL_PLANE = ROOT / "control_plane.py"
LOCK_PATH = ROOT / ".watchdog.lock"
RUNTIME_DIR = ROOT / ".watchdog"
STATUS_PATH = RUNTIME_DIR / "status.json"
RUNTIME_PATH = RUNTIME_DIR / "runtime.json"

TERMINAL_STATES = {"stopped", "blocked", "cancelled"}
STALE_FAMILY = {"stale_suspect", "recovery_required", "recovery_in_progress"}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def current_pid() -> str:
    return str(os.getpid())


def run_json(argv: list[str], *, allow_nonzero: bool = False) -> tuple[int, dict]:
    completed = subprocess.run(argv, capture_output=True, text=True, check=False)
    stdout = completed.stdout.strip()
    payload: dict = {}
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid JSON from {' '.join(argv)}: {exc}") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError(f"unexpected non-object JSON from {' '.join(argv)}")
        payload = parsed
    if completed.returncode != 0 and not allow_nonzero:
        detail = completed.stderr.strip() or stdout or "command failed"
        raise RuntimeError(detail)
    return completed.returncode, payload


def load_manifest() -> dict:
    with (ROOT / "manifest.yaml").open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError("manifest.yaml did not parse to a mapping")
    return payload


def write_status(payload: dict) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_runtime(payload: dict) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def with_lock(nonblocking: bool):
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK_PATH.open("w", encoding="utf-8")
    flags = fcntl.LOCK_EX
    if nonblocking:
        flags |= fcntl.LOCK_NB
    fcntl.flock(handle.fileno(), flags)
    return handle


def launch_recovery(command: list[str]) -> dict:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%S")
    log_path = RUNTIME_DIR / f"recovery-{ts}.log"
    with log_path.open("a", encoding="utf-8") as handle:
        process = subprocess.Popen(  # noqa: S603
            command,
            cwd=ROOT,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
        )
    return {
        "launched": True,
        "pid": process.pid,
        "log_path": str(log_path),
        "command": command,
    }


def derive_checkpoint(show_payload: dict, manifest: dict, *, allow_recovery: bool) -> tuple[dict, dict | None]:
    summary = show_payload.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}

    watchdog = manifest.get("watchdog", {})
    if not isinstance(watchdog, dict):
        watchdog = {}
    lease_health = summary.get("lease_health", {})
    if not isinstance(lease_health, dict):
        lease_health = {}
    next_action = summary.get("next_action", {})
    if not isinstance(next_action, dict):
        next_action = {}
    workboard = summary.get("workboard", {})
    if not isinstance(workboard, dict):
        workboard = {}

    status = str(summary.get("status"))
    lease_status = str(lease_health.get("status", "invalid"))
    heartbeat_at = lease_health.get("last_heartbeat_at")
    progress_at = lease_health.get("last_progress_at")
    manifest_errors = show_payload.get("errors", [])
    if not isinstance(manifest_errors, list):
        manifest_errors = []

    current_condition = str(watchdog.get("condition", "never_checked"))
    stale_count = int(watchdog.get("stale_check_count", 0)) if isinstance(watchdog.get("stale_check_count"), int) else 0
    stale_grace_checks = int(watchdog.get("stale_grace_checks", 2)) if isinstance(watchdog.get("stale_grace_checks"), int) else 2
    auto_resume_command = watchdog.get("auto_resume_command")
    evidence_ref = manifest.get("current_round_brief") or "manifest.yaml"

    checkpoint: dict[str, object] = {
        "lease_status": lease_status,
        "heartbeat_at": heartbeat_at,
        "progress_at": progress_at,
        "source": "watchdog_poll",
        "blocker_class": None,
        "evidence_ref": evidence_ref,
        "poll_interval_s": watchdog.get("poll_interval_s"),
        "stale_grace_checks": stale_grace_checks,
    }
    recovery_payload = None

    if manifest_errors:
        checkpoint.update(
            {
                "condition": "invalid",
                "observation_status": "invalid",
                "summary": "Control-plane validation is failing; watchdog cannot safely reconcile runtime state until the manifest is repaired.",
                "recommended_action": "repair the manifest/control-plane errors shown by control_plane.py show",
            }
        )
        return checkpoint, recovery_payload

    if status in TERMINAL_STATES:
        checkpoint.update(
            {
                "condition": "terminal",
                "observation_status": "terminal",
                "summary": f"Harness is in terminal state {status!r}; watchdog is only observing.",
                "recommended_action": "none",
            }
        )
        return checkpoint, recovery_payload

    if lease_status == "active":
        checkpoint.update(
            {
                "condition": "healthy",
                "observation_status": "healthy",
                "summary": "Active lease is healthy and the watchdog sees ongoing ownership.",
                "recommended_action": "continue current next_action execution",
            }
        )
        return checkpoint, recovery_payload

    if lease_status == "inactive":
        unresolved_stream_count = workboard.get("unresolved_stream_count", 0)
        if isinstance(unresolved_stream_count, int) and unresolved_stream_count > 0:
            checkpoint.update(
                {
                    "condition": "inactive",
                    "observation_status": "inactive",
                    "blocker_class": "unowned_open_work",
                    "summary": "No active lease is held even though unresolved workboard streams remain; the harness is currently unowned rather than complete.",
                    "recommended_action": f"acquire a fresh lease and resume next_action.kind={next_action.get('kind')!r}, or explicitly reduce the open streams if the harness is intentionally parking",
                }
            )
        else:
            checkpoint.update(
                {
                    "condition": "inactive",
                    "observation_status": "inactive",
                    "summary": "No active lease is currently held; the harness is parked rather than stalled.",
                    "recommended_action": f"launch the next owner described by next_action.kind={next_action.get('kind')!r} when work should resume",
                }
            )
        return checkpoint, recovery_payload

    if lease_status == "stale":
        stale_count = stale_count + 1 if current_condition in STALE_FAMILY else 1
        checkpoint["stale_check_count"] = stale_count
        checkpoint["suspect_since"] = watchdog.get("suspect_since") or heartbeat_at
        checkpoint["blocker_class"] = "stale_session"

        if stale_count >= stale_grace_checks:
            if current_condition == "recovery_in_progress":
                checkpoint.update(
                    {
                        "condition": "recovery_in_progress",
                        "observation_status": "recovery",
                        "summary": "Lease is still stale, but a recovery command was already launched; watchdog is waiting for takeover instead of relaunching.",
                        "recommended_action": "observe the existing recovery process and confirm that a fresh lease is acquired before retrying",
                        "recovery_attempts": int(watchdog.get("recovery_attempts", 0)) if isinstance(watchdog.get("recovery_attempts"), int) else 1,
                        "last_recovery_at": watchdog.get("last_recovery_at"),
                    }
                )
                return checkpoint, recovery_payload
            if allow_recovery and isinstance(auto_resume_command, list) and auto_resume_command:
                try:
                    recovery_payload = launch_recovery([str(item) for item in auto_resume_command])
                except Exception as exc:  # noqa: BLE001
                    checkpoint.update(
                        {
                            "condition": "recovery_required",
                            "observation_status": "stale",
                            "summary": f"Lease is stale and auto-resume launch failed: {exc}",
                            "recommended_action": "inspect the watchdog recovery command and respawn a fresh orchestrator manually",
                        }
                    )
                else:
                    checkpoint.update(
                        {
                            "condition": "recovery_in_progress",
                            "observation_status": "recovery",
                            "summary": "Lease stayed stale past the grace window; watchdog launched the configured recovery command.",
                            "recommended_action": "observe the recovery log and confirm that a fresh lease is acquired",
                            "evidence_ref": recovery_payload["log_path"],
                            "recovery_attempts": int(watchdog.get("recovery_attempts", 0)) + 1 if isinstance(watchdog.get("recovery_attempts"), int) else 1,
                            "last_recovery_at": now_iso(),
                        }
                    )
            else:
                checkpoint.update(
                    {
                        "condition": "recovery_required",
                        "observation_status": "stale",
                        "summary": "Lease stayed stale past the grace window; watchdog escalated to recovery_required.",
                        "recommended_action": "spawn a fresh orchestrator from the resume_packet or configure watchdog.auto_resume_command for automatic recovery",
                    }
                )
        else:
            checkpoint.update(
                {
                    "condition": "stale_suspect",
                    "observation_status": "stale",
                    "summary": "Lease is stale on this poll; watchdog opened a stale suspicion instead of escalating immediately.",
                    "recommended_action": "recheck on the next poll before forcing recovery",
                }
            )
        return checkpoint, recovery_payload

    checkpoint.update(
        {
            "condition": "invalid",
            "observation_status": "invalid",
            "summary": f"Lease health is {lease_status!r}, which the watchdog does not recognize as a healthy or recoverable runtime state.",
            "recommended_action": "repair the activity_lease schema and rerun the watchdog",
        }
    )
    return checkpoint, recovery_payload


def checkpoint_manifest(checkpoint: dict) -> tuple[int, dict]:
    argv = [
        "python3",
        str(CONTROL_PLANE),
        "watchdog-checkpoint",
        "--condition",
        str(checkpoint["condition"]),
        "--observation-status",
        str(checkpoint["observation_status"]),
        "--summary",
        str(checkpoint["summary"]),
        "--source",
        str(checkpoint["source"]),
        "--lease-status",
        str(checkpoint["lease_status"]),
        "--recommended-action",
        str(checkpoint["recommended_action"]),
    ]
    if checkpoint.get("heartbeat_at"):
        argv.extend(["--heartbeat-at", str(checkpoint["heartbeat_at"])])
    if checkpoint.get("progress_at"):
        argv.extend(["--progress-at", str(checkpoint["progress_at"])])
    if checkpoint.get("blocker_class"):
        argv.extend(["--blocker-class", str(checkpoint["blocker_class"])])
    if checkpoint.get("evidence_ref"):
        argv.extend(["--evidence-ref", str(checkpoint["evidence_ref"])])
    if checkpoint.get("poll_interval_s") is not None:
        argv.extend(["--poll-interval-s", str(checkpoint["poll_interval_s"])])
    if checkpoint.get("stale_grace_checks") is not None:
        argv.extend(["--stale-grace-checks", str(checkpoint["stale_grace_checks"])])
    if checkpoint.get("stale_check_count") is not None:
        argv.extend(["--stale-check-count", str(checkpoint["stale_check_count"])])
    if checkpoint.get("suspect_since"):
        argv.extend(["--suspect-since", str(checkpoint["suspect_since"])])
    if checkpoint.get("recovery_attempts") is not None:
        argv.extend(["--recovery-attempts", str(checkpoint["recovery_attempts"])])
    if checkpoint.get("last_recovery_at"):
        argv.extend(["--last-recovery-at", str(checkpoint["last_recovery_at"])])
    if checkpoint.get("event"):
        argv.extend(["--event", str(checkpoint["event"])])
    if checkpoint.get("record_stable"):
        argv.append("--record-stable")

    return run_json(argv, allow_nonzero=True)


def supervise_once(*, allow_recovery: bool) -> dict:
    manifest = load_manifest()
    show_code, show_payload = run_json(
        ["python3", str(CONTROL_PLANE), "show"],
        allow_nonzero=True,
    )
    checkpoint, recovery_payload = derive_checkpoint(show_payload, manifest, allow_recovery=allow_recovery)
    checkpoint_code, checkpoint_payload = checkpoint_manifest(checkpoint)

    payload = {
        "checked_at": now_iso(),
        "control_plane_show_returncode": show_code,
        "summary": show_payload.get("summary"),
        "errors": show_payload.get("errors", []),
        "warnings": show_payload.get("warnings", []),
        "checkpoint": checkpoint,
        "checkpoint_returncode": checkpoint_code,
        "checkpoint_result": checkpoint_payload,
        "recovery": recovery_payload,
    }
    write_status(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="External watchdog for the self-improvement harness")
    parser.add_argument("--watch", action="store_true", help="run continuously")
    parser.add_argument("--interval-s", type=float, help="polling interval override")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--lock-blocking", action="store_true", help="wait for the watchdog lock instead of failing immediately")
    parser.add_argument("--run-recovery", action="store_true", help="allow execution of watchdog.auto_resume_command when stale grace is exceeded")
    args = parser.parse_args()

    try:
        lock_handle = with_lock(nonblocking=not args.lock_blocking)
    except BlockingIOError:
        message = {"error": "another watchdog instance already holds the lock", "lock_path": str(LOCK_PATH)}
        if args.json:
            print(json.dumps(message, indent=2))
        else:
            print(message["error"])
        return 1

    with lock_handle:
        manifest = load_manifest()
        watchdog = manifest.get("watchdog", {})
        default_interval = watchdog.get("poll_interval_s", 60) if isinstance(watchdog, dict) else 60
        interval_s = args.interval_s if args.interval_s is not None else float(default_interval)
        started_at = now_iso()

        if not args.watch:
            write_runtime(
                {
                    "pid": current_pid(),
                    "mode": "oneshot",
                    "started_at": started_at,
                    "interval_s": interval_s,
                    "lock_path": str(LOCK_PATH),
                    "status_path": str(STATUS_PATH),
                    "updated_at": started_at,
                }
            )
            payload = supervise_once(allow_recovery=args.run_recovery)
            write_runtime(
                {
                    "pid": current_pid(),
                    "mode": "oneshot",
                    "started_at": started_at,
                    "interval_s": interval_s,
                    "lock_path": str(LOCK_PATH),
                    "status_path": str(STATUS_PATH),
                    "updated_at": now_iso(),
                    "last_checked_at": payload.get("checked_at"),
                }
            )
            if args.json:
                print(json.dumps(payload, indent=2))
            else:
                print(payload["checkpoint"]["summary"])
            return 0 if payload.get("checkpoint_returncode", 1) == 0 else 1

        try:
            while True:
                payload = supervise_once(allow_recovery=args.run_recovery)
                write_runtime(
                    {
                        "pid": current_pid(),
                        "mode": "watch",
                        "started_at": started_at,
                        "interval_s": interval_s,
                        "lock_path": str(LOCK_PATH),
                        "status_path": str(STATUS_PATH),
                        "updated_at": now_iso(),
                        "last_checked_at": payload.get("checked_at"),
                        "last_condition": payload.get("checkpoint", {}).get("condition"),
                    }
                )
                if args.json:
                    print(json.dumps(payload, indent=2))
                else:
                    print(payload["checkpoint"]["summary"])
                sys.stdout.flush()
                time.sleep(interval_s)
        except KeyboardInterrupt:
            write_runtime(
                {
                    "pid": current_pid(),
                    "mode": "watch",
                    "started_at": started_at,
                    "interval_s": interval_s,
                    "lock_path": str(LOCK_PATH),
                    "status_path": str(STATUS_PATH),
                    "updated_at": now_iso(),
                    "stopped_at": now_iso(),
                    "last_condition": "interrupted",
                }
            )
            return 130


if __name__ == "__main__":
    sys.exit(main())
