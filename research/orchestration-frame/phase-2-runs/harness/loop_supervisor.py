#!/usr/bin/env python3
"""External supervisor for the loop control plane.

Runs outside any interactive Claude/Codex session and keeps the loop state
aligned with the actual runtime state of the active work-scoped agent.
Task-specific role mappings are loaded from task_model.yaml in the instance directory.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import sys
import time
from pathlib import Path

import yaml


ROOT = Path(__file__).absolute().parent
CONTROL_PLANE = ROOT / "control_plane.py"
LOCK_PATH = ROOT / ".loop-supervisor.lock"
TASK_MODEL_PATH = ROOT / "task_model.yaml"

RUNNING_STATES = {"booting", "running"}
TERMINAL_DONE_STATE = "done"
TERMINAL_FAILED_STATES = {"failed", "cancelled"}


def _load_task_model() -> dict:
    """Load the task model for role definitions."""
    if not TASK_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"task_model.yaml not found at {TASK_MODEL_PATH}. "
            "Each instance must provide a task_model.yaml."
        )
    with TASK_MODEL_PATH.open("r", encoding="utf-8") as handle:
        model = yaml.safe_load(handle)
    if not isinstance(model, dict):
        raise ValueError("task_model.yaml did not parse to a mapping")
    return model


def _derive_role_map(task_model: dict) -> dict[str, dict[str, object]]:
    """Derive role definitions from the task model.

    Validates that each role has the required ``active_state`` and ``done_state``
    fields and that all referenced states exist in the state list.
    """
    roles = task_model.get("roles")
    if not isinstance(roles, dict):
        return {}
    all_states = {str(s) for s in task_model.get("states", [])}
    result: dict[str, dict[str, object]] = {}
    for role_name, role_def in roles.items():
        if not isinstance(role_def, dict):
            raise ValueError(f"role {role_name!r} definition must be a mapping, got {type(role_def).__name__}")
        parsed: dict[str, object] = {}
        for k, v in role_def.items():
            sk = str(k)
            if isinstance(v, dict):
                parsed[sk] = v
            else:
                parsed[sk] = str(v)
        for required_field in ("active_state", "done_state"):
            if required_field not in parsed:
                raise ValueError(f"role {role_name!r} is missing required field {required_field!r}")
            if str(parsed[required_field]) not in all_states:
                raise ValueError(
                    f"role {role_name!r} field {required_field}={parsed[required_field]!r} "
                    f"is not in the states list"
                )
        infra_state = parsed.get("infrastructure_failure_state")
        if infra_state and str(infra_state) not in all_states:
            raise ValueError(
                f"role {role_name!r} field infrastructure_failure_state={infra_state!r} "
                f"is not in the states list"
            )
        result[str(role_name)] = parsed
    return result


_TASK_MODEL = _load_task_model()
ROLE_MAP = _derive_role_map(_TASK_MODEL)


def run_json(argv: list[str]) -> dict:
    completed = subprocess.run(argv, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "command failed"
        raise RuntimeError(detail)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON from {' '.join(argv)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected non-object JSON from {' '.join(argv)}")
    return payload


def load_manifest() -> dict:
    with (ROOT / "manifest.yaml").open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError("manifest.yaml did not parse to an object")
    return payload


def load_ledger() -> list[dict]:
    path = ROOT / "run-ledger.jsonl"
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    return rows


def observe_subagent(subagent_id: str) -> dict:
    return run_json(
        [
            "python3",
            str(find_work_scoped_agent_script()),
            "observe",
            "--subagent-id",
            subagent_id,
            "--json",
        ]
    )


def probe_active() -> dict:
    return run_json(["python3", str(CONTROL_PLANE), "probe-active"])


def transition(manifest: dict, ledger: list[dict], *, state: str, event: str, summary: str, next_owner: str,
               next_kind: str, next_trigger: str, on_trigger: list[str], role: str | None,
               runtime_state: str | None, semantic_state: str | None, subagent_id: str | None,
               turn_id: str | None, session_id: str | None, extraordinary_condition_open: bool = False,
               user_dependency: bool = False, artifacts: list[str] | None = None) -> dict:
    argv = [
        "python3",
        str(CONTROL_PLANE),
        "transition",
        "--expected-state",
        str(manifest.get("status")),
        "--expected-ledger-entries",
        str(len(ledger)),
        "--state",
        state,
        "--event",
        event,
        "--actor",
        "loop_supervisor",
        "--summary",
        summary,
        "--next-owner",
        next_owner,
        "--next-kind",
        next_kind,
        "--next-trigger",
        next_trigger,
    ]
    active_actor = manifest.get("active_actor", {}) if isinstance(manifest.get("active_actor"), dict) else {}
    active_subagent = active_actor.get("subagent_id")
    if active_subagent:
        argv.extend(["--expected-active-subagent", str(active_subagent)])
    owner_token = manifest.get("watchdog", {}).get("owner_token") if isinstance(manifest.get("watchdog"), dict) else None
    if owner_token:
        argv.extend(["--expected-owner-token", str(owner_token)])
    for item in on_trigger:
        argv.extend(["--on-trigger", item])
    if extraordinary_condition_open:
        argv.append("--extraordinary-condition-open")
    if user_dependency:
        argv.append("--user-dependency")
    current_round = manifest.get("current_round")
    if current_round is not None:
        argv.extend(["--current-round", str(current_round)])
    current_round_path = manifest.get("current_round_path")
    if current_round_path:
        argv.extend(["--current-round-path", str(current_round_path)])
    if role:
        argv.extend(["--role", role])
    if runtime_state:
        argv.extend(["--runtime-state", runtime_state])
    if semantic_state:
        argv.extend(["--semantic-state", semantic_state])
    if subagent_id:
        argv.extend(["--subagent-id", subagent_id])
    if turn_id:
        argv.extend(["--turn-id", turn_id])
    if session_id:
        argv.extend(["--session-id", session_id])
    for artifact in artifacts or []:
        argv.extend(["--artifact", artifact])
    completed = subprocess.run(argv, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "transition failed"
        raise RuntimeError(detail)
    return {
        "ok": True,
        "state": state,
        "event": event,
        "summary": summary,
    }


def find_life_os_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "core/system/scripts/work_scoped_agent.py").exists():
            return candidate
    raise RuntimeError("could not locate Life-os root")


def find_work_scoped_agent_script() -> Path:
    return find_life_os_root(ROOT) / "core/system/scripts/work_scoped_agent.py"


def classify_auth_failure(observe_payload: dict) -> bool:
    fragments: list[str] = []
    result = observe_payload.get("result")
    if isinstance(result, dict):
        for key in ("summary", "stdout", "stderr"):
            value = result.get(key)
            if isinstance(value, str):
                fragments.append(value)
    status = observe_payload.get("status")
    if isinstance(status, dict):
        for key in ("status_summary",):
            value = status.get(key)
            if isinstance(value, str):
                fragments.append(value)
    haystack = "\n".join(fragments)
    return "authentication_error" in haystack or "Invalid authentication credentials" in haystack


def summarize_failure(observe_payload: dict) -> str:
    status = observe_payload.get("status", {})
    result = observe_payload.get("result", {})
    if not isinstance(status, dict):
        status = {}
    if not isinstance(result, dict):
        result = {}
    result_stdout = result.get("stdout")
    if isinstance(result_stdout, str) and "Invalid authentication credentials" in result_stdout:
        return "Active Claude work-scoped agent failed with backend authentication error (401 Invalid authentication credentials)."
    status_summary = status.get("status_summary")
    if isinstance(status_summary, str) and status_summary:
        return f"Active work-scoped agent terminated with status_summary={status_summary!r}."
    summary = result.get("summary")
    if isinstance(summary, str) and summary:
        return f"Active work-scoped agent terminated with summary={summary!r}."
    return "Active work-scoped agent terminated unexpectedly."


def terminal_reconciliation_needed(manifest: dict, observe_payload: dict) -> bool:
    active_actor = manifest.get("active_actor", {}) if isinstance(manifest.get("active_actor"), dict) else {}
    role = active_actor.get("role")
    current_state = str(manifest.get("status"))
    status = observe_payload.get("status", {})
    if not isinstance(status, dict):
        return False
    runtime_state = str(status.get("state"))

    role_def = ROLE_MAP.get(str(role), {})
    active_state = role_def.get("active_state")
    done_state = role_def.get("done_state")
    infra_failure_state = role_def.get("infrastructure_failure_state")

    if runtime_state == TERMINAL_DONE_STATE:
        if not active_state or not done_state:
            return False
        return current_state == active_state

    if runtime_state in TERMINAL_FAILED_STATES:
        if infra_failure_state and classify_auth_failure(observe_payload):
            return current_state == active_state
        excluded = {"blocked", "cancelled"}
        if infra_failure_state:
            excluded.add(infra_failure_state)
        return current_state not in excluded

    return False


def handle_terminal_state(manifest: dict, ledger: list[dict], observe_payload: dict) -> dict:
    active_actor = manifest.get("active_actor", {}) if isinstance(manifest.get("active_actor"), dict) else {}
    role = active_actor.get("role")
    subagent_id = active_actor.get("subagent_id")
    turn_id = active_actor.get("turn_id")
    session_id = active_actor.get("session_id")
    current_state = str(manifest.get("status"))
    status = observe_payload.get("status", {})
    turn = observe_payload.get("turn", {})
    if not isinstance(status, dict):
        status = {}
    if not isinstance(turn, dict):
        turn = {}
    runtime_state = str(status.get("state"))
    result_path = None
    worker = status.get("worker")
    if isinstance(worker, dict):
        result_path = worker.get("result_path")
    if not result_path:
        result_path = turn.get("result_path")
    artifacts = [str(result_path)] if isinstance(result_path, str) and result_path else []

    role_def = ROLE_MAP.get(str(role), {})
    active_state = role_def.get("active_state")
    done_state = role_def.get("done_state")
    infra_failure_state = role_def.get("infrastructure_failure_state")

    if runtime_state == TERMINAL_DONE_STATE:
        if active_state and done_state and current_state == active_state:
            return transition(
                manifest,
                ledger,
                state=done_state,
                event=f"supervisor_detected_{role}_done",
                summary=f"External supervisor observed {role} reach done and advanced the loop from waiting to result-capture state.",
                next_owner="loop_runner",
                next_kind=f"capture_{role}_result",
                next_trigger="immediate",
                on_trigger=[
                    f"capture the {role} result artifact from the active turn",
                    f"record {role} completion in iteration-log.md",
                    "adjudicate the result and commit the next state transition",
                ],
                role=role,
                runtime_state="done",
                semantic_state="result_ready",
                subagent_id=subagent_id,
                turn_id=turn_id,
                session_id=session_id,
                artifacts=artifacts,
            )
        return {
            "action": "no_transition_needed",
            "reason": f"terminal done state already reconciled for role={role!r}, state={current_state!r}",
        }

    failure_summary = summarize_failure(observe_payload)
    if infra_failure_state and classify_auth_failure(observe_payload):
        if current_state != active_state:
            return {
                "action": "no_transition_needed",
                "reason": f"auth failure already reconciled for role={role!r}, state={current_state!r}",
            }
        return transition(
            manifest,
            ledger,
            state=infra_failure_state,
            event=f"supervisor_detected_{role}_auth_failure",
            summary=(
                f"{failure_summary} The loop is blocked on backend auth repair, not on task quality. "
                "The active wait state has been replaced with an explicit infrastructure-failure state."
            ),
            next_owner="user",
            next_kind="ask_user",
            next_trigger="auth_repaired",
            on_trigger=[
                "repair backend authentication credentials",
                f"respawn the {role} from {manifest.get('current_round_path')}/{role}-delegation-prompt.md",
                "resume external supervision after the respawn",
            ],
            role=role,
            runtime_state=runtime_state,
            semantic_state="auth_failed",
            subagent_id=subagent_id,
            turn_id=turn_id,
            session_id=session_id,
            extraordinary_condition_open=True,
            user_dependency=True,
            artifacts=artifacts,
        )

    already_reconciled = {"blocked", "cancelled"}
    if infra_failure_state:
        already_reconciled.add(infra_failure_state)
    if current_state in already_reconciled:
        return {
            "action": "no_transition_needed",
            "reason": f"terminal failure already reconciled for role={role!r}, state={current_state!r}",
        }

    return transition(
        manifest,
        ledger,
        state="blocked",
        event="supervisor_detected_terminal_failure",
        summary=(
            f"{failure_summary} The loop has been moved out of a stale wait state and into blocked "
            "so a repair or respawn decision can be made explicitly."
        ),
        next_owner="loop_runner",
        next_kind="investigate_failed_actor",
        next_trigger="immediate",
        on_trigger=[
            "inspect the failed actor result and log tail",
            "decide whether to respawn the same role or classify an external blocker",
            "record the failure mode in architecture findings before resuming the loop",
        ],
        role=role if isinstance(role, str) else None,
        runtime_state=runtime_state,
        semantic_state="terminal_failure",
        subagent_id=subagent_id if isinstance(subagent_id, str) else None,
        turn_id=turn_id if isinstance(turn_id, str) else None,
        session_id=session_id if isinstance(session_id, str) else None,
        artifacts=artifacts,
    )


def supervise_once() -> dict:
    manifest = load_manifest()
    ledger = load_ledger()
    active_actor = manifest.get("active_actor")
    if not isinstance(active_actor, dict):
        return {"action": "idle", "reason": "no active_actor in manifest"}
    subagent_id = active_actor.get("subagent_id")
    if not isinstance(subagent_id, str) or not subagent_id:
        return {"action": "idle", "reason": "active_actor has no subagent_id"}

    observe_payload = observe_subagent(subagent_id)
    status = observe_payload.get("status")
    if not isinstance(status, dict):
        raise RuntimeError("observe payload missing status object")
    runtime_state = str(status.get("state"))

    if runtime_state in RUNNING_STATES:
        probe_payload = probe_active()
        return {
            "action": "probed_running",
            "runtime_state": runtime_state,
            "probe": probe_payload,
        }

    if runtime_state in TERMINAL_FAILED_STATES or runtime_state == TERMINAL_DONE_STATE:
        if not terminal_reconciliation_needed(manifest, observe_payload):
            return {
                "action": "terminal_state_already_reconciled",
                "runtime_state": runtime_state,
                "state": manifest.get("status"),
            }
        probe_payload = probe_active()
        manifest = load_manifest()
        ledger = load_ledger()
        transition_payload = handle_terminal_state(manifest, ledger, observe_payload)
        return {
            "action": "reconciled_terminal_state",
            "runtime_state": runtime_state,
            "probe": probe_payload,
            "transition": transition_payload,
        }

    return {
        "action": "unknown_state",
        "runtime_state": runtime_state,
    }


def with_lock(nonblocking: bool):
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK_PATH.open("w", encoding="utf-8")
    flags = fcntl.LOCK_EX
    if nonblocking:
        flags |= fcntl.LOCK_NB
    fcntl.flock(handle.fileno(), flags)
    return handle


def main() -> int:
    parser = argparse.ArgumentParser(description="External supervisor for the loop control plane")
    parser.add_argument("--watch", action="store_true", help="run continuously")
    parser.add_argument("--interval-s", type=float, default=30.0, help="polling interval in watch mode")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--lock-blocking", action="store_true", help="wait for supervisor lock instead of failing immediately")
    args = parser.parse_args()

    try:
        lock_handle = with_lock(nonblocking=not args.lock_blocking)
    except BlockingIOError:
        message = {"error": "another loop_supervisor instance already holds the lock", "lock_path": str(LOCK_PATH)}
        if args.json:
            print(json.dumps(message, indent=2))
        else:
            print(message["error"])
        return 1

    with lock_handle:
        if not args.watch:
            payload = supervise_once()
            if args.json:
                print(json.dumps(payload, indent=2))
            else:
                print(payload)
            return 0

        while True:
            payload = supervise_once()
            if args.json:
                print(json.dumps(payload, indent=2))
            else:
                print(payload)
            sys.stdout.flush()
            time.sleep(args.interval_s)


if __name__ == "__main__":
    sys.exit(main())
