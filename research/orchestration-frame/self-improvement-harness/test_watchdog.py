#!/usr/bin/env python3
"""Repeatable smoke tests for the self-improvement harness watchdog."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "test-fixtures"


def run_json(argv: list[str], *, cwd: Path) -> tuple[int, dict]:
    completed = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    stdout = completed.stdout.strip()
    payload: dict = {}
    if stdout:
        payload = json.loads(stdout)
    return completed.returncode, payload


def read_ledger(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rows.append(json.loads(raw))
    return rows


def clone_fixture(name: str, tmp_root: Path) -> Path:
    source = FIXTURES / name
    target = tmp_root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    shutil.copy2(ROOT / "watchdog.py", target / "watchdog.py")
    shutil.copy2(ROOT / "watchdog-service.sh", target / "watchdog-service.sh")
    return target


def refresh_healthy_fixture(path: Path) -> None:
    manifest_path = path / "manifest.yaml"
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    now = datetime.now().astimezone()
    payload["last_control_plane_update_at"] = now.isoformat(timespec="seconds")
    lease = payload.setdefault("activity_lease", {})
    lease["last_heartbeat_at"] = (now - timedelta(seconds=60)).isoformat(timespec="seconds")
    lease["last_progress_at"] = (now - timedelta(seconds=120)).isoformat(timespec="seconds")
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_fixture(path: Path) -> None:
    code, payload = run_json(["python3", "control_plane.py", "validate"], cwd=path)
    expected_invalid = path.name == "global-stop-guard-invalid"
    if expected_invalid:
        assert_true(code == 1, f"{path.name}: expected validate to fail")
        assert_true(
            any("local_loop_stopped" in err for err in payload.get("errors", [])),
            f"{path.name}: expected false-stop validation errors",
        )
    else:
        assert_true(code == 0, f"{path.name}: validate failed: {payload}")


def test_inactive_fixture(path: Path) -> None:
    code, payload = run_json(["python3", "watchdog.py", "--json"], cwd=path)
    assert_true(code == 0, f"{path.name}: inactive watchdog run failed")
    checkpoint = payload.get("checkpoint", {})
    assert_true(checkpoint.get("condition") == "inactive", f"{path.name}: expected inactive condition")
    assert_true(payload.get("checkpoint_result", {}).get("ledger_appended") is True, f"{path.name}: first inactive poll should append")


def test_healthy_fixture(path: Path) -> None:
    refresh_healthy_fixture(path)
    initial_len = len(read_ledger(path / "run-ledger.jsonl"))
    code, payload = run_json(["python3", "watchdog.py", "--json"], cwd=path)
    assert_true(code == 0, f"{path.name}: watchdog run failed")
    checkpoint = payload.get("checkpoint", {})
    assert_true(checkpoint.get("condition") == "healthy", f"{path.name}: expected healthy condition")
    assert_true(payload.get("checkpoint_result", {}).get("ledger_appended") is True, f"{path.name}: first healthy poll should append")
    after_first_len = len(read_ledger(path / "run-ledger.jsonl"))
    assert_true(after_first_len == initial_len + 1, f"{path.name}: expected one new ledger row on first healthy poll")

    code, payload = run_json(["python3", "watchdog.py", "--json"], cwd=path)
    assert_true(code == 0, f"{path.name}: second watchdog run failed")
    assert_true(payload.get("checkpoint_result", {}).get("ledger_appended") is False, f"{path.name}: repeated healthy poll should not append")
    after_second_len = len(read_ledger(path / "run-ledger.jsonl"))
    assert_true(after_second_len == after_first_len, f"{path.name}: repeated healthy poll should not change ledger length")


def test_stale_recovery_fixture(path: Path) -> None:
    code, payload = run_json(["python3", "watchdog.py", "--run-recovery", "--json"], cwd=path)
    assert_true(code == 0, f"{path.name}: watchdog recovery run failed")
    checkpoint = payload.get("checkpoint", {})
    assert_true(checkpoint.get("condition") == "recovery_in_progress", f"{path.name}: expected recovery_in_progress")
    assert_true(payload.get("recovery", {}).get("launched") is True, f"{path.name}: recovery command was not launched")
    sentinel = path / ".watchdog" / "recovery-sentinel"
    assert_true(sentinel.exists(), f"{path.name}: recovery sentinel missing")
    recovery_logs_after_first = sorted((path / ".watchdog").glob("recovery-*.log"))

    code, payload = run_json(["python3", "watchdog.py", "--run-recovery", "--json"], cwd=path)
    assert_true(code == 0, f"{path.name}: second watchdog recovery run failed")
    checkpoint = payload.get("checkpoint", {})
    assert_true(checkpoint.get("condition") == "recovery_in_progress", f"{path.name}: expected recovery_in_progress on second poll")
    assert_true(payload.get("recovery") is None, f"{path.name}: second stale poll should not relaunch recovery")
    recovery_logs_after_second = sorted((path / ".watchdog").glob("recovery-*.log"))
    assert_true(
        len(recovery_logs_after_second) == len(recovery_logs_after_first),
        f"{path.name}: repeated stale polls should not create extra recovery logs",
    )


def test_terminal_fixture(path: Path) -> None:
    code, payload = run_json(["python3", "watchdog.py", "--json"], cwd=path)
    assert_true(code == 0, f"{path.name}: terminal watchdog run failed")
    checkpoint = payload.get("checkpoint", {})
    assert_true(checkpoint.get("condition") == "terminal", f"{path.name}: expected terminal condition")
    assert_true(checkpoint.get("observation_status") == "terminal", f"{path.name}: expected terminal observation status")


def test_service_wrapper(path: Path) -> None:
    completed = subprocess.run(
        ["bash", "watchdog-service.sh", "run-once"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert_true(completed.returncode == 0, f"{path.name}: watchdog-service run-once failed: {completed.stdout} {completed.stderr}")
    payload = json.loads(completed.stdout)
    assert_true("checked_at" in payload, f"{path.name}: watchdog-service output missing checked_at")


def main() -> int:
    validate_fixture(FIXTURES / "global-stop-guard-valid")
    validate_fixture(FIXTURES / "global-stop-guard-invalid")
    validate_fixture(FIXTURES / "global-stop-terminal-valid")
    validate_fixture(FIXTURES / "watchdog-healthy")
    validate_fixture(FIXTURES / "watchdog-stale-recovery")

    with tempfile.TemporaryDirectory(prefix="self-improvement-watchdog-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        inactive_service = clone_fixture("global-stop-guard-valid", tmp_root / "service")
        inactive = clone_fixture("global-stop-guard-valid", tmp_root)
        healthy = clone_fixture("watchdog-healthy", tmp_root)
        stale = clone_fixture("watchdog-stale-recovery", tmp_root)
        terminal = clone_fixture("global-stop-terminal-valid", tmp_root)

        test_service_wrapper(inactive_service)
        test_inactive_fixture(inactive)
        test_healthy_fixture(healthy)
        test_stale_recovery_fixture(stale)
        test_terminal_fixture(terminal)

    print(json.dumps({"ok": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
