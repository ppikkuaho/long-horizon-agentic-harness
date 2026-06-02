#!/usr/bin/env python3
"""Self-improvement-harness control-plane helper."""

from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
import sys
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.yaml"
LEDGER_PATH = ROOT / "run-ledger.jsonl"
WORKBOARD_PATH = ROOT / "WORKBOARD.yaml"
CONTINUATION_PATH = ROOT / "CONTINUATION.md"
CONTROL_PLANE_LOCK_PATH = ROOT / ".control-plane.lock"

KNOWN_STATES = {
    "planned",
    "builder_in_progress",
    "reviewer_1_pending",
    "reviewer_1_continue",
    "reviewer_1_pass",
    "reviewer_2_pending",
    "reviewer_2_continue",
    "global_reconciliation_pending",
    "stopped",
    "blocked",
    "cancelled",
}

TERMINAL_STATES = {"stopped", "blocked", "cancelled"}
LEASE_STATUSES = {"active", "inactive"}
WATCHDOG_CONDITIONS = {
    "never_checked",
    "healthy",
    "inactive",
    "stale_suspect",
    "recovery_required",
    "recovery_in_progress",
    "terminal",
    "invalid",
}
OBSERVATION_WINDOW_STATUSES = {
    "unknown",
    "healthy",
    "inactive",
    "stale",
    "recovery",
    "terminal",
    "invalid",
}

ALLOWED_TRANSITIONS = {
    "planned": {"planned", "builder_in_progress", "blocked", "cancelled"},
    "builder_in_progress": {"builder_in_progress", "reviewer_1_pending", "blocked", "cancelled"},
    "reviewer_1_pending": {"reviewer_1_pending", "reviewer_1_continue", "reviewer_1_pass", "blocked", "cancelled"},
    "reviewer_1_continue": {"reviewer_1_continue", "planned", "builder_in_progress", "blocked", "cancelled"},
    "reviewer_1_pass": {"reviewer_1_pass", "reviewer_2_pending", "blocked", "cancelled"},
    "reviewer_2_pending": {
        "reviewer_2_pending",
        "reviewer_2_continue",
        "global_reconciliation_pending",
        "stopped",
        "blocked",
        "cancelled",
    },
    "reviewer_2_continue": {"reviewer_2_continue", "planned", "builder_in_progress", "blocked", "cancelled"},
    "global_reconciliation_pending": {
        "global_reconciliation_pending",
        "planned",
        "builder_in_progress",
        "stopped",
        "blocked",
        "cancelled",
    },
    "stopped": {"stopped"},
    "blocked": {"blocked", "cancelled"},
    "cancelled": {"cancelled"},
}

REQUIRED_MANIFEST_KEYS = {
    "name",
    "status",
    "state_entered_at",
    "last_control_plane_update_at",
    "objective",
    "current_iteration",
    "current_iteration_path",
    "next_action",
    "user_contact_policy",
    "reporting_policy",
    "extraordinary_condition_open",
    "global_completion",
    "activity_lease",
    "watchdog",
    "observation_window",
    "resume_packet",
}

REQUIRED_NEXT_ACTION_KEYS = {
    "owner",
    "kind",
    "trigger",
    "on_trigger",
    "user_dependency",
}

REQUIRED_GLOBAL_COMPLETION_KEYS = {
    "satisfied",
    "authority",
    "reason",
    "evidence",
    "open_workstreams",
    "open_stream_ids",
}

REQUIRED_ACTIVITY_LEASE_KEYS = {
    "enabled",
    "owner",
    "heartbeat_interval_s",
    "stale_after_s",
    "last_heartbeat_at",
    "last_progress_at",
    "status",
}

REQUIRED_WATCHDOG_KEYS = {
    "enabled",
    "poll_interval_s",
    "stale_grace_checks",
    "condition",
    "last_checked_at",
    "suspect_since",
    "stale_check_count",
    "recovery_attempts",
    "auto_resume_command",
    "last_recovery_at",
    "last_evidence",
}

REQUIRED_OBSERVATION_WINDOW_KEYS = {
    "status",
    "observed_at",
    "lease_status",
    "heartbeat_at",
    "progress_at",
    "blocker_class",
    "summary",
    "evidence_ref",
    "recommended_action",
}

WORKBOARD_STATUSES = {"inactive", "underutilized", "saturated", "oversubscribed"}
WORKBOARD_STREAM_STATUSES = {"planned", "active", "waiting", "completed", "blocked", "cancelled"}
WORKBOARD_COUNTABLE_STATUSES = {"active", "waiting"}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def normalize_scalars(value):
    if isinstance(value, dict):
        return {key: normalize_scalars(subvalue) for key, subvalue in value.items()}
    if isinstance(value, list):
        return [normalize_scalars(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def load_manifest() -> dict:
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("manifest.yaml did not parse to a mapping")
    return normalize_scalars(data)


def save_manifest(manifest: dict) -> None:
    temp_path = MANIFEST_PATH.with_name(f".{MANIFEST_PATH.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(normalize_scalars(manifest), handle, sort_keys=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, MANIFEST_PATH)


def save_continuation(markdown: str) -> None:
    temp_path = CONTINUATION_PATH.with_name(f".{CONTINUATION_PATH.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        handle.write(markdown)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, CONTINUATION_PATH)


def load_ledger() -> list[dict]:
    if not LEDGER_PATH.exists():
        return []
    entries: list[dict] = []
    with LEDGER_PATH.open("r", encoding="utf-8") as handle:
        for lineno, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"run-ledger.jsonl line {lineno} is invalid JSON: {exc}") from exc
            if not isinstance(entry, dict):
                raise ValueError(f"run-ledger.jsonl line {lineno} is not a JSON object")
            entries.append(entry)
    return entries


def load_workboard() -> tuple[dict | None, str | None]:
    if not WORKBOARD_PATH.exists():
        return None, None
    try:
        with WORKBOARD_PATH.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
    except Exception as exc:  # noqa: BLE001
        return None, f"WORKBOARD.yaml could not be read: {exc}"
    if not isinstance(payload, dict):
        return None, "WORKBOARD.yaml did not parse to a mapping"
    return normalize_scalars(payload), None


def append_ledger(entry: dict) -> None:
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


@contextmanager
def control_plane_lock(*, shared: bool):
    CONTROL_PLANE_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONTROL_PLANE_LOCK_PATH.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def normalize_resume_packet(paths: list[str] | None) -> list[str] | None:
    if not paths:
        return None
    return list(paths)


def parse_iso_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def resolve_artifact_path(raw_path: object) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT / path


def load_markdown_frontmatter(raw_path: object) -> tuple[dict | None, str | None]:
    path = resolve_artifact_path(raw_path)
    if path is None:
        return None, "artifact path is missing or invalid"
    if not path.exists():
        return None, f"artifact does not exist: {path}"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"artifact could not be read: {path}: {exc}"
    if not text.startswith("---\n"):
        return None, f"artifact is missing YAML frontmatter: {path}"
    end_marker = text.find("\n---\n", 4)
    if end_marker == -1:
        return None, f"artifact frontmatter is not closed with ---: {path}"
    payload = text[4:end_marker]
    try:
        frontmatter = yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        return None, f"artifact frontmatter is invalid YAML: {path}: {exc}"
    if not isinstance(frontmatter, dict):
        return None, f"artifact frontmatter is not a mapping: {path}"
    return normalize_scalars(frontmatter), None


def summarize_workboard(workboard: dict | None) -> dict | None:
    if not isinstance(workboard, dict):
        return None

    streams = workboard.get("streams", [])
    if not isinstance(streams, list):
        streams = []

    active_stream_count = 0
    unresolved_stream_count = 0
    streams_by_status: dict[str, int] = {}
    owners: list[str] = []
    for raw_stream in streams:
        if not isinstance(raw_stream, dict):
            continue
        stream_status = str(raw_stream.get("status"))
        streams_by_status[stream_status] = streams_by_status.get(stream_status, 0) + 1
        if stream_status in WORKBOARD_COUNTABLE_STATUSES:
            active_stream_count += 1
        if stream_status not in {"completed", "cancelled"}:
            unresolved_stream_count += 1
        owner = raw_stream.get("owner")
        if isinstance(owner, str) and owner and owner != "unassigned" and owner not in owners:
            owners.append(owner)

    saturation = workboard.get("saturation", {})
    if not isinstance(saturation, dict):
        saturation = {}
    minimum_active_streams = saturation.get("minimum_active_streams", 0)
    preferred_active_streams = saturation.get("preferred_active_streams", 0)
    maximum_active_streams = saturation.get("maximum_active_streams", 0)

    if unresolved_stream_count == 0:
        derived_status = "inactive"
    elif isinstance(maximum_active_streams, int) and maximum_active_streams > 0 and active_stream_count > maximum_active_streams:
        derived_status = "oversubscribed"
    elif isinstance(minimum_active_streams, int) and minimum_active_streams > 0 and active_stream_count < minimum_active_streams:
        derived_status = "underutilized"
    else:
        derived_status = "saturated"

    return {
        "status": workboard.get("status"),
        "derived_status": derived_status,
        "active_stream_count": active_stream_count,
        "unresolved_stream_count": unresolved_stream_count,
        "stream_count": len(streams),
        "streams_by_status": streams_by_status,
        "owners": owners,
        "minimum_active_streams": minimum_active_streams,
        "preferred_active_streams": preferred_active_streams,
        "maximum_active_streams": maximum_active_streams,
        "last_reconciled_at": workboard.get("last_reconciled_at"),
    }


def unresolved_workboard_stream_ids(workboard: dict | None) -> list[str]:
    if not isinstance(workboard, dict):
        return []

    streams = workboard.get("streams", [])
    if not isinstance(streams, list):
        return []

    unresolved_ids: list[str] = []
    for raw_stream in streams:
        if not isinstance(raw_stream, dict):
            continue
        stream_id = raw_stream.get("stream_id")
        stream_status = raw_stream.get("status")
        if (
            isinstance(stream_id, str)
            and stream_id.strip()
            and stream_status not in {"completed", "cancelled"}
        ):
            unresolved_ids.append(stream_id)
    return unresolved_ids


def validate_workboard(workboard: dict | None) -> tuple[list[str], list[str], dict | None]:
    if workboard is None:
        return [], [], None

    errors: list[str] = []
    warnings: list[str] = []
    summary = summarize_workboard(workboard)

    for key in ("version", "objective", "owner", "last_reconciled_at", "status", "saturation", "streams"):
        if key not in workboard:
            errors.append(f"WORKBOARD.yaml missing required key: {key}")

    if not isinstance(workboard.get("version"), int) or workboard.get("version", 0) < 1:
        errors.append("WORKBOARD.yaml version must be an integer >= 1")
    if not isinstance(workboard.get("objective"), str) or not workboard["objective"].strip():
        errors.append("WORKBOARD.yaml objective must be a non-empty string")
    if not isinstance(workboard.get("owner"), str) or not workboard["owner"].strip():
        errors.append("WORKBOARD.yaml owner must be a non-empty string")
    if workboard.get("status") not in WORKBOARD_STATUSES:
        errors.append(f"WORKBOARD.yaml status must be one of {sorted(WORKBOARD_STATUSES)}")
    if parse_iso_timestamp(workboard.get("last_reconciled_at")) is None:
        errors.append("WORKBOARD.yaml last_reconciled_at must be an ISO timestamp")

    saturation = workboard.get("saturation")
    if not isinstance(saturation, dict):
        errors.append("WORKBOARD.yaml saturation must be a mapping")
    else:
        minimum_active_streams = saturation.get("minimum_active_streams")
        preferred_active_streams = saturation.get("preferred_active_streams")
        maximum_active_streams = saturation.get("maximum_active_streams")
        for key, value in (
            ("minimum_active_streams", minimum_active_streams),
            ("preferred_active_streams", preferred_active_streams),
            ("maximum_active_streams", maximum_active_streams),
        ):
            if not isinstance(value, int) or value < 0:
                errors.append(f"WORKBOARD.yaml saturation.{key} must be an integer >= 0")
        if (
            isinstance(minimum_active_streams, int)
            and isinstance(preferred_active_streams, int)
            and minimum_active_streams > preferred_active_streams
        ):
            errors.append("WORKBOARD.yaml minimum_active_streams cannot exceed preferred_active_streams")
        if (
            isinstance(preferred_active_streams, int)
            and isinstance(maximum_active_streams, int)
            and preferred_active_streams > maximum_active_streams
        ):
            errors.append("WORKBOARD.yaml preferred_active_streams cannot exceed maximum_active_streams")

    streams = workboard.get("streams")
    if not isinstance(streams, list) or not streams:
        errors.append("WORKBOARD.yaml streams must be a non-empty list")
        streams = []

    seen_stream_ids: set[str] = set()
    for index, raw_stream in enumerate(streams, start=1):
        prefix = f"WORKBOARD.yaml streams[{index}]"
        if not isinstance(raw_stream, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        for key in (
            "stream_id",
            "kind",
            "status",
            "owner",
            "objective",
            "stop_condition",
            "write_targets",
            "evidence_refs",
            "next_action",
            "opened_at",
            "updated_at",
            "notes",
        ):
            if key not in raw_stream:
                errors.append(f"{prefix} missing required key: {key}")
        stream_id = raw_stream.get("stream_id")
        if not isinstance(stream_id, str) or not stream_id.strip():
            errors.append(f"{prefix}.stream_id must be a non-empty string")
        elif stream_id in seen_stream_ids:
            errors.append(f"duplicate stream_id in WORKBOARD.yaml: {stream_id}")
        else:
            seen_stream_ids.add(stream_id)

        if raw_stream.get("status") not in WORKBOARD_STREAM_STATUSES:
            errors.append(f"{prefix}.status must be one of {sorted(WORKBOARD_STREAM_STATUSES)}")
        for key in ("kind", "owner", "objective", "stop_condition", "next_action"):
            value = raw_stream.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{key} must be a non-empty string")
        for key in ("write_targets", "evidence_refs", "notes"):
            value = raw_stream.get(key)
            if not isinstance(value, list):
                errors.append(f"{prefix}.{key} must be a list")
            elif any(not isinstance(item, str) or not item.strip() for item in value):
                errors.append(f"{prefix}.{key} items must be non-empty strings")
        for key in ("opened_at", "updated_at"):
            if parse_iso_timestamp(raw_stream.get(key)) is None:
                errors.append(f"{prefix}.{key} must be an ISO timestamp")

    if summary is not None and workboard.get("status") != summary.get("derived_status"):
        warnings.append(
            f"WORKBOARD.yaml status {workboard.get('status')!r} does not match derived status {summary.get('derived_status')!r}"
        )

    return errors, warnings, summary


def derive_contact_permission(manifest: dict) -> dict[str, object]:
    reporting_policy = manifest.get("reporting_policy")
    if not isinstance(reporting_policy, dict):
        return {
            "allowed": False,
            "reason": "reporting_policy_missing",
            "terminal_states": [],
        }

    terminal_states = reporting_policy.get("terminal_states")
    if not isinstance(terminal_states, list):
        terminal_states = []
    normalized_terminal_states = [str(state) for state in terminal_states]

    extraordinary_condition_open = bool(manifest.get("extraordinary_condition_open"))
    status = str(manifest.get("status"))
    if extraordinary_condition_open:
        return {
            "allowed": True,
            "reason": "extraordinary_condition_open",
            "terminal_states": normalized_terminal_states,
        }
    if status in normalized_terminal_states:
        return {
            "allowed": True,
            "reason": f"terminal_state:{status}",
            "terminal_states": normalized_terminal_states,
        }
    return {
        "allowed": False,
        "reason": "suppressed_until_extraordinary_or_terminal",
        "terminal_states": normalized_terminal_states,
    }


def derive_lease_health(manifest: dict) -> dict[str, object]:
    lease = manifest.get("activity_lease")
    if not isinstance(lease, dict):
        return {"status": "missing", "reason": "activity_lease_missing"}

    enabled = lease.get("enabled")
    status = lease.get("status")
    if enabled is False or status == "inactive":
        return {
            "status": "inactive",
            "reason": "lease_not_active",
            "owner": lease.get("owner"),
            "last_heartbeat_at": lease.get("last_heartbeat_at"),
            "last_progress_at": lease.get("last_progress_at"),
        }

    stale_after_s = lease.get("stale_after_s")
    if not isinstance(stale_after_s, int) or stale_after_s <= 0:
        return {"status": "invalid", "reason": "stale_after_s_invalid"}

    last_heartbeat_at = lease.get("last_heartbeat_at")
    heartbeat_dt = parse_iso_timestamp(last_heartbeat_at)
    if heartbeat_dt is None:
        return {
            "status": "invalid",
            "reason": "last_heartbeat_at_missing_or_invalid",
            "owner": lease.get("owner"),
        }

    now_dt = datetime.now().astimezone()
    heartbeat_age_s = int((now_dt - heartbeat_dt.astimezone()).total_seconds())
    last_progress_at = lease.get("last_progress_at")
    progress_dt = parse_iso_timestamp(last_progress_at)
    if progress_dt is None:
        return {
            "status": "invalid",
            "reason": "last_progress_at_missing_or_invalid",
            "owner": lease.get("owner"),
            "last_heartbeat_at": last_heartbeat_at,
        }
    progress_age_s = int((now_dt - progress_dt.astimezone()).total_seconds())

    if heartbeat_age_s > stale_after_s:
        return {
            "status": "stale",
            "reason": "heartbeat_older_than_stale_after",
            "owner": lease.get("owner"),
            "heartbeat_age_s": heartbeat_age_s,
            "progress_age_s": progress_age_s,
            "last_heartbeat_at": last_heartbeat_at,
            "last_progress_at": last_progress_at,
        }
    if progress_age_s > stale_after_s:
        return {
            "status": "stale",
            "reason": "progress_older_than_stale_after",
            "owner": lease.get("owner"),
            "heartbeat_age_s": heartbeat_age_s,
            "progress_age_s": progress_age_s,
            "last_heartbeat_at": last_heartbeat_at,
            "last_progress_at": last_progress_at,
        }

    return {
        "status": "active",
        "reason": "lease_healthy",
        "owner": lease.get("owner"),
        "heartbeat_age_s": heartbeat_age_s,
        "progress_age_s": progress_age_s,
        "last_heartbeat_at": last_heartbeat_at,
        "last_progress_at": last_progress_at,
    }


def watchdog_event_name(condition: str) -> str:
    return {
        "never_checked": "watchdog_never_checked",
        "healthy": "watchdog_healthy",
        "inactive": "watchdog_inactive",
        "stale_suspect": "watchdog_stale_suspect",
        "recovery_required": "watchdog_recovery_required",
        "recovery_in_progress": "watchdog_recovery_in_progress",
        "terminal": "watchdog_terminal",
        "invalid": "watchdog_invalid",
    }[condition]


def validate(manifest: dict, ledger: list[dict]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    workboard, workboard_load_error = load_workboard()
    if workboard_load_error:
        errors.append(workboard_load_error)
        workboard = None

    for key in REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            errors.append(f"manifest missing required key: {key}")

    status = manifest.get("status")
    if status not in KNOWN_STATES:
        errors.append(f"manifest status is not recognized: {status!r}")

    user_contact_policy = manifest.get("user_contact_policy")
    if not isinstance(user_contact_policy, dict):
        errors.append("user_contact_policy must be a mapping")
    else:
        if user_contact_policy.get("mode") != "extraordinary_only":
            errors.append("user_contact_policy.mode must be 'extraordinary_only'")

    if not isinstance(manifest.get("extraordinary_condition_open"), bool):
        errors.append("extraordinary_condition_open must be a boolean")

    reporting_policy = manifest.get("reporting_policy")
    if not isinstance(reporting_policy, dict):
        errors.append("reporting_policy must be a mapping")
    else:
        if reporting_policy.get("mode") != "extraordinary_or_terminal":
            errors.append("reporting_policy.mode must be 'extraordinary_or_terminal'")
        terminal_states = reporting_policy.get("terminal_states")
        if not isinstance(terminal_states, list):
            errors.append("reporting_policy.terminal_states must be a list")
        else:
            unknown_terminal_states = [
                repr(state)
                for state in terminal_states
                if str(state) not in KNOWN_STATES
            ]
            if unknown_terminal_states:
                errors.append(
                    "reporting_policy.terminal_states contains unknown states: "
                    + ", ".join(unknown_terminal_states)
                )

    next_action = manifest.get("next_action")
    if not isinstance(next_action, dict):
        errors.append("next_action must be a mapping")
    else:
        for key in REQUIRED_NEXT_ACTION_KEYS:
            if key not in next_action:
                errors.append(f"next_action missing required key: {key}")
        if next_action.get("user_dependency") not in (False, 0):
            errors.append("next_action.user_dependency must be false unless an extraordinary condition is open")
        if (
            manifest.get("extraordinary_condition_open") is False
            and next_action.get("kind") == "ask_user"
        ):
            errors.append("next_action.kind cannot be 'ask_user' when no extraordinary condition is open")
        contact_permission = derive_contact_permission(manifest)
        if (
            next_action.get("kind") == "report_to_user"
            and not bool(contact_permission.get("allowed"))
        ):
            errors.append(
                "next_action.kind cannot be 'report_to_user' unless contact-check allows it"
            )
        on_trigger = next_action.get("on_trigger")
        if (
            isinstance(on_trigger, list)
            and len(on_trigger) == 1
            and isinstance(on_trigger[0], str)
            and "|" in on_trigger[0]
        ):
            warnings.append(
                "next_action.on_trigger appears pipe-joined into a single item; expected repeated list entries"
            )

    global_completion = manifest.get("global_completion")
    open_workstreams = []
    open_stream_ids = []
    if not isinstance(global_completion, dict):
        errors.append("global_completion must be a mapping")
    else:
        for key in REQUIRED_GLOBAL_COMPLETION_KEYS:
            if key not in global_completion:
                errors.append(f"global_completion missing required key: {key}")

        if not isinstance(global_completion.get("satisfied"), bool):
            errors.append("global_completion.satisfied must be a boolean")

        evidence = global_completion.get("evidence")
        if not isinstance(evidence, list):
            errors.append("global_completion.evidence must be a list")

        open_workstreams = global_completion.get("open_workstreams")
        if not isinstance(open_workstreams, list):
            errors.append("global_completion.open_workstreams must be a list")
            open_workstreams = []
        elif any(not isinstance(item, str) or not item.strip() for item in open_workstreams):
            errors.append("global_completion.open_workstreams items must be non-empty strings")

        open_stream_ids = global_completion.get("open_stream_ids")
        if not isinstance(open_stream_ids, list):
            errors.append("global_completion.open_stream_ids must be a list")
            open_stream_ids = []
        elif any(not isinstance(item, str) or not item.strip() for item in open_stream_ids):
            errors.append("global_completion.open_stream_ids items must be non-empty strings")
        elif len(set(open_stream_ids)) != len(open_stream_ids):
            errors.append("global_completion.open_stream_ids must not contain duplicates")

        authority = global_completion.get("authority")
        if global_completion.get("satisfied") is True:
            if not isinstance(authority, str) or not authority.strip():
                errors.append("global_completion.authority must be a non-empty string when satisfied is true")
            if not isinstance(evidence, list) or not evidence:
                errors.append("global_completion.evidence must be non-empty when satisfied is true")
            if isinstance(open_workstreams, list) and open_workstreams:
                errors.append("global_completion.open_workstreams must be empty when satisfied is true")
            if isinstance(open_stream_ids, list) and open_stream_ids:
                errors.append("global_completion.open_stream_ids must be empty when satisfied is true")

    activity_lease = manifest.get("activity_lease")
    if not isinstance(activity_lease, dict):
        errors.append("activity_lease must be a mapping")
    else:
        for key in REQUIRED_ACTIVITY_LEASE_KEYS:
            if key not in activity_lease:
                errors.append(f"activity_lease missing required key: {key}")

        if not isinstance(activity_lease.get("enabled"), bool):
            errors.append("activity_lease.enabled must be a boolean")
        if activity_lease.get("status") not in LEASE_STATUSES:
            errors.append(f"activity_lease.status must be one of {sorted(LEASE_STATUSES)}")

        heartbeat_interval_s = activity_lease.get("heartbeat_interval_s")
        stale_after_s = activity_lease.get("stale_after_s")
        if not isinstance(heartbeat_interval_s, int) or heartbeat_interval_s <= 0:
            errors.append("activity_lease.heartbeat_interval_s must be a positive integer")
        if not isinstance(stale_after_s, int) or stale_after_s <= 0:
            errors.append("activity_lease.stale_after_s must be a positive integer")
        elif isinstance(heartbeat_interval_s, int) and stale_after_s <= heartbeat_interval_s:
            errors.append("activity_lease.stale_after_s must be greater than heartbeat_interval_s")

        if activity_lease.get("status") == "active":
            if not isinstance(activity_lease.get("owner"), str) or not activity_lease["owner"].strip():
                errors.append("activity_lease.owner must be a non-empty string when lease status is active")
            if parse_iso_timestamp(activity_lease.get("last_heartbeat_at")) is None:
                errors.append("activity_lease.last_heartbeat_at must be an ISO timestamp when lease status is active")
            if parse_iso_timestamp(activity_lease.get("last_progress_at")) is None:
                errors.append("activity_lease.last_progress_at must be an ISO timestamp when lease status is active")

    lease_health = derive_lease_health(manifest)
    if status in TERMINAL_STATES and isinstance(activity_lease, dict) and activity_lease.get("status") == "active":
        errors.append("activity_lease.status cannot be active when the harness is in a terminal state")
    if lease_health.get("status") == "invalid" and isinstance(activity_lease, dict) and activity_lease.get("status") == "active":
        errors.append(
            f"active lease is not healthy: {lease_health.get('reason')}"
        )
    if lease_health.get("status") == "stale" and isinstance(activity_lease, dict) and activity_lease.get("status") == "active":
        warnings.append(
            f"active lease is stale: {lease_health.get('reason')}"
        )

    watchdog = manifest.get("watchdog")
    if not isinstance(watchdog, dict):
        errors.append("watchdog must be a mapping")
    else:
        for key in REQUIRED_WATCHDOG_KEYS:
            if key not in watchdog:
                errors.append(f"watchdog missing required key: {key}")

        if not isinstance(watchdog.get("enabled"), bool):
            errors.append("watchdog.enabled must be a boolean")
        if not isinstance(watchdog.get("poll_interval_s"), int) or watchdog.get("poll_interval_s", 0) <= 0:
            errors.append("watchdog.poll_interval_s must be a positive integer")
        if not isinstance(watchdog.get("stale_grace_checks"), int) or watchdog.get("stale_grace_checks", 0) < 1:
            errors.append("watchdog.stale_grace_checks must be an integer >= 1")
        if watchdog.get("condition") not in WATCHDOG_CONDITIONS:
            errors.append(f"watchdog.condition must be one of {sorted(WATCHDOG_CONDITIONS)}")

        auto_resume_command = watchdog.get("auto_resume_command")
        if auto_resume_command is not None:
            if not isinstance(auto_resume_command, list) or not auto_resume_command:
                errors.append("watchdog.auto_resume_command must be null or a non-empty list")
            elif any(not isinstance(item, str) or not item.strip() for item in auto_resume_command):
                errors.append("watchdog.auto_resume_command items must be non-empty strings")

        for key in ("last_checked_at", "suspect_since", "last_recovery_at"):
            value = watchdog.get(key)
            if value is not None and parse_iso_timestamp(value) is None:
                errors.append(f"watchdog.{key} must be null or an ISO timestamp")

        for key in ("stale_check_count", "recovery_attempts"):
            value = watchdog.get(key)
            if not isinstance(value, int) or value < 0:
                errors.append(f"watchdog.{key} must be an integer >= 0")

        last_evidence = watchdog.get("last_evidence")
        if not isinstance(last_evidence, dict):
            errors.append("watchdog.last_evidence must be a mapping")
        else:
            for key in ("source", "heartbeat_at", "progress_at", "lease_status", "next_action_kind"):
                if key not in last_evidence:
                    errors.append(f"watchdog.last_evidence missing required key: {key}")

        condition = watchdog.get("condition")
        if condition in {"stale_suspect", "recovery_required", "recovery_in_progress"}:
            if watchdog.get("suspect_since") is None:
                errors.append(f"watchdog.suspect_since must be set when condition is {condition!r}")
            if not isinstance(watchdog.get("stale_check_count"), int) or watchdog.get("stale_check_count", 0) < 1:
                errors.append(f"watchdog.stale_check_count must be >= 1 when condition is {condition!r}")
        if condition == "recovery_in_progress":
            if watchdog.get("last_recovery_at") is None:
                errors.append("watchdog.last_recovery_at must be set when condition is 'recovery_in_progress'")
            if not isinstance(watchdog.get("recovery_attempts"), int) or watchdog.get("recovery_attempts", 0) < 1:
                errors.append("watchdog.recovery_attempts must be >= 1 when condition is 'recovery_in_progress'")

    observation_window = manifest.get("observation_window")
    if not isinstance(observation_window, dict):
        errors.append("observation_window must be a mapping")
    else:
        for key in REQUIRED_OBSERVATION_WINDOW_KEYS:
            if key not in observation_window:
                errors.append(f"observation_window missing required key: {key}")
        if observation_window.get("status") not in OBSERVATION_WINDOW_STATUSES:
            errors.append(
                f"observation_window.status must be one of {sorted(OBSERVATION_WINDOW_STATUSES)}"
            )
        for key in ("observed_at", "heartbeat_at", "progress_at"):
            value = observation_window.get(key)
            if value is not None and parse_iso_timestamp(value) is None:
                errors.append(f"observation_window.{key} must be null or an ISO timestamp")

    if isinstance(watchdog, dict) and isinstance(observation_window, dict):
        condition = watchdog.get("condition")
        observation_status = observation_window.get("status")
        expected_observation_status = {
            "never_checked": "unknown",
            "healthy": "healthy",
            "inactive": "inactive",
            "stale_suspect": "stale",
            "recovery_required": "stale",
            "recovery_in_progress": "recovery",
            "terminal": "terminal",
            "invalid": "invalid",
        }.get(condition)
        if expected_observation_status and observation_status != expected_observation_status:
            errors.append(
                f"observation_window.status {observation_status!r} is inconsistent with watchdog.condition {condition!r}"
            )
        if condition == "terminal" and status not in TERMINAL_STATES:
            errors.append("watchdog.condition 'terminal' requires a terminal harness state")
        if condition != "terminal" and status in TERMINAL_STATES and condition not in {"never_checked", "inactive"}:
            warnings.append("terminal harness state should usually carry watchdog.condition 'terminal'")

    if isinstance(next_action, dict) and isinstance(global_completion, dict):
        next_action_kind = next_action.get("kind")
        if next_action_kind == "local_loop_stopped":
            if status != "global_reconciliation_pending":
                errors.append("next_action.kind 'local_loop_stopped' requires status 'global_reconciliation_pending'")
            if global_completion.get("satisfied") is True:
                errors.append("next_action.kind 'local_loop_stopped' is incompatible with a satisfied global completion gate")

        if status == "stopped":
            if next_action_kind != "done":
                errors.append("status 'stopped' requires next_action.kind 'done'")
            if global_completion.get("satisfied") is not True:
                errors.append("status 'stopped' requires global_completion.satisfied to be true")
            open_workstreams = global_completion.get("open_workstreams")
            if isinstance(open_workstreams, list) and open_workstreams:
                errors.append("status 'stopped' requires global_completion.open_workstreams to be empty")
        elif next_action_kind == "done":
            errors.append("next_action.kind 'done' is only valid when status is 'stopped'")

    if not isinstance(manifest.get("resume_packet"), list) or not manifest["resume_packet"]:
        errors.append("resume_packet must be a non-empty list")

    workboard_errors, workboard_warnings, workboard_summary = validate_workboard(workboard)
    errors.extend(workboard_errors)
    warnings.extend(workboard_warnings)

    global_completion = manifest.get("global_completion")
    open_workstreams = []
    open_stream_ids = []
    if isinstance(global_completion, dict) and isinstance(global_completion.get("open_workstreams"), list):
        open_workstreams = global_completion["open_workstreams"]
    if isinstance(global_completion, dict) and isinstance(global_completion.get("open_stream_ids"), list):
        open_stream_ids = global_completion["open_stream_ids"]
    if open_workstreams and workboard is None:
        warnings.append(
            "WORKBOARD.yaml is missing while global_completion.open_workstreams is non-empty; branch ownership is not materialized into a tracked board"
        )
    if open_workstreams and workboard_summary is not None and workboard_summary.get("unresolved_stream_count", 0) == 0:
        errors.append(
            "WORKBOARD.yaml has no unresolved streams while global_completion.open_workstreams is non-empty"
        )
    unresolved_stream_ids = unresolved_workboard_stream_ids(workboard)
    if workboard is not None and set(open_stream_ids) != set(unresolved_stream_ids):
        missing_from_workboard = [stream_id for stream_id in open_stream_ids if stream_id not in unresolved_stream_ids]
        missing_from_manifest = [stream_id for stream_id in unresolved_stream_ids if stream_id not in open_stream_ids]
        if missing_from_workboard:
            errors.append(
                "global_completion.open_stream_ids names unresolved streams that are not active in WORKBOARD.yaml: "
                + ", ".join(sorted(missing_from_workboard))
            )
        if missing_from_manifest:
            errors.append(
                "global_completion.open_stream_ids is missing unresolved WORKBOARD.yaml streams: "
                + ", ".join(sorted(missing_from_manifest))
            )

    activity_lease = manifest.get("activity_lease")
    if (
        isinstance(activity_lease, dict)
        and activity_lease.get("status") == "active"
        and workboard_summary is not None
        and workboard_summary.get("active_stream_count", 0) < 1
    ):
        errors.append("active lease requires at least one active or waiting stream in WORKBOARD.yaml")
    if (
        isinstance(activity_lease, dict)
        and activity_lease.get("status") == "inactive"
        and workboard_summary is not None
        and workboard_summary.get("unresolved_stream_count", 0) > 0
        and status not in TERMINAL_STATES
    ):
        warnings.append("inactive lease with unresolved workboard streams leaves the harness unowned rather than complete")

    artifact_path_checks = [
        ("current_round_brief", KNOWN_STATES - TERMINAL_STATES, None),
        (
            "current_builder_output",
            {
                "reviewer_1_pending",
                "reviewer_1_continue",
                "reviewer_1_pass",
                "reviewer_2_pending",
                "reviewer_2_continue",
                "global_reconciliation_pending",
                "stopped",
            },
            "builder",
        ),
        (
            "current_reviewer_1_verdict",
            {
                "reviewer_1_pass",
                "reviewer_2_pending",
                "reviewer_2_continue",
                "global_reconciliation_pending",
                "stopped",
            },
            "reviewer_1",
        ),
        (
            "current_reviewer_2_verdict",
            {"reviewer_2_continue", "global_reconciliation_pending", "stopped"},
            "reviewer_2",
        ),
    ]
    for manifest_key, required_states, expected_role in artifact_path_checks:
        if status not in required_states:
            continue
        artifact_path = manifest.get(manifest_key)
        resolved_path = resolve_artifact_path(artifact_path)
        if resolved_path is None:
            errors.append(f"{manifest_key} must be set when status is {status!r}")
            continue
        if not resolved_path.exists():
            errors.append(f"{manifest_key} does not exist: {resolved_path}")
            continue
        if expected_role is None:
            continue
        frontmatter, frontmatter_error = load_markdown_frontmatter(artifact_path)
        if frontmatter_error is not None:
            errors.append(f"{manifest_key} invalid: {frontmatter_error}")
            continue
        if frontmatter.get("role") != expected_role:
            errors.append(
                f"{manifest_key} frontmatter role must be {expected_role!r}, found {frontmatter.get('role')!r}"
            )
        current_iteration_value = manifest.get("current_iteration")
        if current_iteration_value is not None and frontmatter.get("iteration") != current_iteration_value:
            warnings.append(
                f"{manifest_key} frontmatter iteration {frontmatter.get('iteration')!r} does not match current_iteration {current_iteration_value!r}"
            )

    current_iteration = manifest.get("current_iteration")
    current_iteration_path = manifest.get("current_iteration_path")
    if current_iteration is not None and isinstance(current_iteration_path, str):
        expected_iteration_path = f"iterations/iteration-{int(current_iteration):02d}"
        if current_iteration_path != expected_iteration_path:
            warnings.append(
                f"current_iteration_path {current_iteration_path!r} does not match expected {expected_iteration_path!r}"
            )

    if not ledger:
        errors.append("run-ledger.jsonl must contain at least one entry")
    else:
        last_state = ledger[-1].get("state")
        if last_state != status:
            warnings.append(
                f"last ledger state {last_state!r} does not match manifest status {status!r}"
            )
        last_next_action_kind = ledger[-1].get("next_action_kind")
        if (
            isinstance(next_action, dict)
            and last_next_action_kind is not None
            and last_next_action_kind != next_action.get("kind")
        ):
            warnings.append(
                "last ledger next_action_kind does not match manifest next_action.kind"
            )

    return errors, warnings


def make_summary(manifest: dict, ledger: list[dict]) -> dict:
    workboard, workboard_error = load_workboard()
    workboard_summary = summarize_workboard(workboard) if workboard_error is None else {"error": workboard_error}
    return {
        "status": manifest.get("status"),
        "state_entered_at": manifest.get("state_entered_at"),
        "last_control_plane_update_at": manifest.get("last_control_plane_update_at"),
        "current_iteration": manifest.get("current_iteration"),
        "current_iteration_path": manifest.get("current_iteration_path"),
        "next_action": manifest.get("next_action"),
        "global_completion": manifest.get("global_completion"),
        "activity_lease": manifest.get("activity_lease"),
        "lease_health": derive_lease_health(manifest),
        "watchdog": manifest.get("watchdog"),
        "observation_window": manifest.get("observation_window"),
        "workboard": workboard_summary,
        "extraordinary_condition_open": manifest.get("extraordinary_condition_open"),
        "contact_permission": derive_contact_permission(manifest),
        "ledger_entries": len(ledger),
    }


def build_next_packet(manifest: dict, ledger: list[dict]) -> dict:
    workboard, workboard_error = load_workboard()
    workboard_summary = summarize_workboard(workboard) if workboard_error is None else {"error": workboard_error}
    return {
        "status": manifest.get("status"),
        "state_entered_at": manifest.get("state_entered_at"),
        "current_iteration": manifest.get("current_iteration"),
        "current_iteration_path": manifest.get("current_iteration_path"),
        "current_round_brief": manifest.get("current_round_brief"),
        "next_action": manifest.get("next_action"),
        "global_completion": manifest.get("global_completion"),
        "activity_lease": manifest.get("activity_lease"),
        "lease_health": derive_lease_health(manifest),
        "watchdog": manifest.get("watchdog"),
        "observation_window": manifest.get("observation_window"),
        "workboard": workboard_summary,
        "contact_permission": derive_contact_permission(manifest),
        "resume_packet": manifest.get("resume_packet"),
        "extraordinary_condition_open": manifest.get("extraordinary_condition_open"),
        "ledger_length": len(ledger),
        "last_ledger_event": ledger[-1] if ledger else None,
    }


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def display_scalar(value: object, fallback: str = "unknown") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or fallback
    return str(value)


def continuation_read_now(manifest: dict) -> list[str]:
    candidates = [
        "manifest.yaml",
        "CONTINUATION.md",
        manifest.get("current_round_brief"),
        manifest.get("current_builder_output"),
        manifest.get("current_reviewer_1_verdict"),
        manifest.get("current_reviewer_2_verdict"),
        manifest.get("last_reviewer_1_verdict"),
        manifest.get("last_reviewer_2_verdict"),
        "reference-map.md",
    ]
    return dedupe_preserve_order(
        [str(item) for item in candidates if isinstance(item, str) and item.strip()]
    )


def continuation_recently_completed(ledger: list[dict]) -> list[str]:
    summaries: list[str] = []
    for entry in reversed(ledger):
        event = entry.get("event")
        if event in {"heartbeat", "progress_heartbeat"}:
            continue
        if (
            isinstance(event, str)
            and event.startswith("watchdog_")
            and entry.get("watchdog_condition") in {"healthy", "inactive"}
        ):
            continue
        summary = entry.get("summary")
        if isinstance(summary, str) and summary.strip():
            summaries.append(summary.strip())
        if len(summaries) >= 2:
            break
    if not summaries:
        return ["No completed checkpoint summaries are recorded yet."]
    summaries.reverse()
    return summaries


def continuation_open_risks(manifest: dict) -> list[str]:
    open_required_changes = manifest.get("open_required_changes")
    if isinstance(open_required_changes, list):
        risks = [
            str(item).strip()
            for item in open_required_changes
            if isinstance(item, str) and item.strip()
        ]
        if risks:
            return risks[:3]

    global_completion = manifest.get("global_completion")
    if isinstance(global_completion, dict):
        open_workstreams = global_completion.get("open_workstreams")
        if isinstance(open_workstreams, list):
            risks = [
                str(item).strip()
                for item in open_workstreams
                if isinstance(item, str) and item.strip()
            ]
            if risks:
                return risks[:3]

    return ["No additional structural defects are currently recorded."]


def render_continuation(manifest: dict, ledger: list[dict]) -> str:
    summary = make_summary(manifest, ledger)
    next_action = manifest.get("next_action", {})
    if not isinstance(next_action, dict):
        next_action = {}

    global_completion = manifest.get("global_completion", {})
    if not isinstance(global_completion, dict):
        global_completion = {}
    why_open = [
        str(item).strip()
        for item in global_completion.get("open_workstreams", [])
        if isinstance(item, str) and item.strip()
    ]
    if not why_open:
        why_open = [str(global_completion.get("reason") or "Program remains open.") .strip()]

    on_trigger = next_action.get("on_trigger")
    trigger_lines = [
        str(item).strip()
        for item in on_trigger
        if isinstance(item, str) and item.strip()
    ] if isinstance(on_trigger, list) else []
    what_to_do_now = " ".join(trigger_lines) if trigger_lines else "Follow the current next_action from manifest.yaml."

    workboard_summary = summary.get("workboard", {})
    workboard_status = None
    if isinstance(workboard_summary, dict):
        workboard_status = workboard_summary.get("derived_status") or workboard_summary.get("status")

    lines = [
        "# Continuation Packet",
        "",
        "Updated at:",
        f"- {manifest.get('last_control_plane_update_at')}",
        "",
        "Program state:",
        f"- status: `{display_scalar(manifest.get('status'))}`",
        f"- current iteration: `{display_scalar(manifest.get('current_iteration'))}`",
        f"- current round path: `{display_scalar(manifest.get('current_iteration_path'))}`",
        f"- current round brief: `{display_scalar(manifest.get('current_round_brief'))}`",
        "",
        "Why the program is still open:",
    ]
    lines.extend(f"- {item}" for item in why_open)
    lines.extend(
        [
            "",
            "Recently completed:",
        ]
    )
    lines.extend(f"- {item}" for item in continuation_recently_completed(ledger))
    lines.extend(
        [
            "",
            "Current live ownership:",
            f"- lease owner: `{display_scalar(manifest.get('activity_lease', {}).get('owner') if isinstance(manifest.get('activity_lease'), dict) else None, 'none')}`",
            f"- watchdog state: `{display_scalar(manifest.get('watchdog', {}).get('condition') if isinstance(manifest.get('watchdog'), dict) else None)}`",
            f"- workboard status: `{display_scalar(workboard_status)}`",
            "",
            "Exact next action:",
            f"- owner: `{display_scalar(next_action.get('owner'))}`",
            f"- kind: `{display_scalar(next_action.get('kind'))}`",
            f"- trigger: `{display_scalar(next_action.get('trigger'))}`",
            f"- what to do now: {what_to_do_now}",
            "",
            "Read now:",
        ]
    )
    lines.extend(f"- `{item}`" for item in continuation_read_now(manifest))
    lines.extend(
        [
            "",
            "Do not reconstruct from:",
            "- stale conversational status if it disagrees with manifest.yaml",
            "- older round surfaces when current manifest pointers name newer artifacts",
            "",
            "Open risks or defects:",
        ]
    )
    lines.extend(f"- {item}" for item in continuation_open_risks(manifest))
    lines.extend(
        [
            "",
            "Evidence surfaces:",
            "- `python3 control_plane.py show`",
            "- `python3 workboard.py show`",
            "- `manifest.yaml`",
            "- `run-ledger.jsonl`",
        ]
    )
    return "\n".join(lines) + "\n"


def commit_mutation(candidate_manifest: dict, candidate_ledger: list[dict], entry: dict | None = None) -> None:
    save_manifest(candidate_manifest)
    if entry is not None:
        append_ledger(entry)
    save_continuation(render_continuation(candidate_manifest, candidate_ledger))


def cmd_show(args: argparse.Namespace) -> int:
    with control_plane_lock(shared=True):
        manifest = load_manifest()
        ledger = load_ledger()
    errors, warnings = validate(manifest, ledger)
    payload = {"summary": make_summary(manifest, ledger), "errors": errors, "warnings": warnings}
    print(json.dumps(normalize_scalars(payload), indent=2))
    return 1 if errors else 0


def cmd_next(args: argparse.Namespace) -> int:
    with control_plane_lock(shared=True):
        manifest = load_manifest()
        ledger = load_ledger()
    errors, warnings = validate(manifest, ledger)
    payload = {"packet": build_next_packet(manifest, ledger), "errors": errors, "warnings": warnings}
    print(json.dumps(normalize_scalars(payload), indent=2))
    return 1 if errors else 0


def cmd_validate(args: argparse.Namespace) -> int:
    with control_plane_lock(shared=True):
        manifest = load_manifest()
        ledger = load_ledger()
    errors, warnings = validate(manifest, ledger)
    print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
    return 1 if errors else 0


def cmd_contact_check(args: argparse.Namespace) -> int:
    with control_plane_lock(shared=True):
        manifest = load_manifest()
        ledger = load_ledger()
    errors, warnings = validate(manifest, ledger)
    payload = {
        "contact_permission": derive_contact_permission(manifest),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if errors else 0


def cmd_watchdog_checkpoint(args: argparse.Namespace) -> int:
    with control_plane_lock(shared=False):
        manifest = load_manifest()
        ledger = load_ledger()
        checkpoint_ts = now_iso()

        candidate_manifest = copy.deepcopy(manifest)
        watchdog = candidate_manifest.setdefault("watchdog", {})
        previous_condition = watchdog.get("condition")
        previous_stale_check_count = int(watchdog.get("stale_check_count", 0)) if isinstance(watchdog.get("stale_check_count"), int) else 0
        previous_recovery_attempts = int(watchdog.get("recovery_attempts", 0)) if isinstance(watchdog.get("recovery_attempts"), int) else 0

        watchdog["enabled"] = bool(watchdog.get("enabled", True))
        if args.poll_interval_s is not None:
            watchdog["poll_interval_s"] = args.poll_interval_s
        if args.stale_grace_checks is not None:
            watchdog["stale_grace_checks"] = args.stale_grace_checks
        watchdog["condition"] = args.condition
        watchdog["last_checked_at"] = checkpoint_ts

        if args.auto_resume_command is not None:
            watchdog["auto_resume_command"] = args.auto_resume_command

        if args.condition in {"healthy", "inactive", "terminal", "never_checked", "invalid"}:
            watchdog["suspect_since"] = None
            watchdog["stale_check_count"] = 0
        else:
            if args.suspect_since is not None:
                watchdog["suspect_since"] = args.suspect_since
            else:
                watchdog["suspect_since"] = watchdog.get("suspect_since") or checkpoint_ts
            if args.stale_check_count is not None:
                watchdog["stale_check_count"] = args.stale_check_count
            elif previous_condition in {"stale_suspect", "recovery_required", "recovery_in_progress"}:
                watchdog["stale_check_count"] = max(previous_stale_check_count, 1)
            else:
                watchdog["stale_check_count"] = 1

        if args.condition == "recovery_in_progress":
            watchdog["recovery_attempts"] = args.recovery_attempts if args.recovery_attempts is not None else previous_recovery_attempts + 1
            watchdog["last_recovery_at"] = args.last_recovery_at or checkpoint_ts
        else:
            watchdog["recovery_attempts"] = args.recovery_attempts if args.recovery_attempts is not None else previous_recovery_attempts
            if args.last_recovery_at is not None:
                watchdog["last_recovery_at"] = args.last_recovery_at

        watchdog["last_evidence"] = {
            "source": args.source,
            "heartbeat_at": args.heartbeat_at,
            "progress_at": args.progress_at,
            "lease_status": args.lease_status,
            "next_action_kind": candidate_manifest.get("next_action", {}).get("kind"),
        }

        observation_window = candidate_manifest.setdefault("observation_window", {})
        observation_window["status"] = args.observation_status
        observation_window["observed_at"] = checkpoint_ts
        observation_window["lease_status"] = args.lease_status
        observation_window["heartbeat_at"] = args.heartbeat_at
        observation_window["progress_at"] = args.progress_at
        observation_window["blocker_class"] = args.blocker_class
        observation_window["summary"] = args.summary
        observation_window["evidence_ref"] = args.evidence_ref
        observation_window["recommended_action"] = args.recommended_action

        candidate_manifest["last_control_plane_update_at"] = checkpoint_ts

        event_name = args.event or watchdog_event_name(args.condition)
        entry = {
            "ts": checkpoint_ts,
            "iteration": candidate_manifest.get("current_iteration"),
            "event": event_name,
            "actor": args.actor,
            "state": candidate_manifest.get("status"),
            "summary": args.summary,
            "next_action_kind": candidate_manifest.get("next_action", {}).get("kind"),
            "watchdog_condition": args.condition,
            "observation_status": args.observation_status,
        }
        if args.evidence_ref:
            entry["artifacts"] = [args.evidence_ref]

        should_append_ledger = bool(args.record_stable or args.event or args.condition != previous_condition)
        candidate_ledger = ledger + ([entry] if should_append_ledger else [])
        errors, warnings = validate(candidate_manifest, candidate_ledger)
        if errors:
            print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
            return 1

        commit_mutation(
            candidate_manifest,
            candidate_ledger,
            entry if should_append_ledger else None,
        )
        print(
            json.dumps(
                {
                    "errors": [],
                    "warnings": warnings,
                    "ledger_appended": should_append_ledger,
                    "condition": args.condition,
                    "observation_status": args.observation_status,
                },
                indent=2,
            )
        )
        return 0


def cmd_heartbeat(args: argparse.Namespace) -> int:
    with control_plane_lock(shared=False):
        manifest = load_manifest()
        ledger = load_ledger()
        heartbeat_ts = now_iso()

        candidate_manifest = copy.deepcopy(manifest)
        lease = candidate_manifest.setdefault("activity_lease", {})
        lease["enabled"] = True
        if args.heartbeat_interval_s is not None:
            lease["heartbeat_interval_s"] = args.heartbeat_interval_s
        elif "heartbeat_interval_s" not in lease:
            lease["heartbeat_interval_s"] = 900
        if args.stale_after_s is not None:
            lease["stale_after_s"] = args.stale_after_s
        elif "stale_after_s" not in lease:
            lease["stale_after_s"] = 3600
        lease["owner"] = args.owner
        lease["status"] = "active"
        lease["last_heartbeat_at"] = heartbeat_ts
        if args.progress or not lease.get("last_progress_at"):
            lease["last_progress_at"] = heartbeat_ts

        candidate_manifest["last_control_plane_update_at"] = heartbeat_ts

        entry = {
            "ts": heartbeat_ts,
            "iteration": candidate_manifest.get("current_iteration"),
            "event": "progress_heartbeat" if args.progress else "heartbeat",
            "actor": args.owner,
            "state": candidate_manifest.get("status"),
            "summary": args.summary,
            "next_action_kind": candidate_manifest.get("next_action", {}).get("kind"),
        }

        errors, warnings = validate(candidate_manifest, ledger + [entry])
        if errors:
            print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
            return 1

        commit_mutation(candidate_manifest, ledger + [entry], entry)
        print(json.dumps({"errors": [], "warnings": warnings}, indent=2))
        return 0


def cmd_release_lease(args: argparse.Namespace) -> int:
    with control_plane_lock(shared=False):
        manifest = load_manifest()
        ledger = load_ledger()
        release_ts = now_iso()

        candidate_manifest = copy.deepcopy(manifest)
        lease = candidate_manifest.setdefault("activity_lease", {})
        lease["enabled"] = True
        lease["status"] = "inactive"
        lease["owner"] = None
        lease["last_heartbeat_at"] = release_ts
        if not lease.get("last_progress_at"):
            lease["last_progress_at"] = release_ts

        candidate_manifest["last_control_plane_update_at"] = release_ts

        entry = {
            "ts": release_ts,
            "iteration": candidate_manifest.get("current_iteration"),
            "event": "lease_released",
            "actor": args.actor,
            "state": candidate_manifest.get("status"),
            "summary": args.summary,
            "next_action_kind": candidate_manifest.get("next_action", {}).get("kind"),
        }

        errors, warnings = validate(candidate_manifest, ledger + [entry])
        if errors:
            print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
            return 1

        commit_mutation(candidate_manifest, ledger + [entry], entry)
        print(json.dumps({"errors": [], "warnings": warnings}, indent=2))
        return 0


def cmd_transition(args: argparse.Namespace) -> int:
    with control_plane_lock(shared=False):
        manifest = load_manifest()
        ledger = load_ledger()
        current_state = manifest.get("status")
        precondition_errors: list[str] = []
        if current_state != args.expected_state:
            precondition_errors.append(
                f"expected current state {args.expected_state!r}, found {current_state!r}"
            )
        if (
            args.expected_ledger_entries is not None
            and len(ledger) != args.expected_ledger_entries
        ):
            precondition_errors.append(
                f"expected {args.expected_ledger_entries} ledger entries, found {len(ledger)}"
            )
        if precondition_errors:
            print(json.dumps({"errors": precondition_errors, "warnings": []}, indent=2))
            return 1

        allowed_targets = ALLOWED_TRANSITIONS.get(current_state, {current_state})
        if args.state not in allowed_targets:
            print(
                json.dumps(
                    {"errors": [f"illegal transition from {current_state!r} to {args.state!r}"], "warnings": []},
                    indent=2,
                )
            )
            return 1

        transition_ts = now_iso()
        candidate_manifest = copy.deepcopy(manifest)
        candidate_manifest["status"] = args.state
        if args.state != current_state:
            candidate_manifest["state_entered_at"] = transition_ts
        candidate_manifest["last_control_plane_update_at"] = transition_ts
        if args.current_iteration is not None:
            candidate_manifest["current_iteration"] = args.current_iteration
        if args.current_iteration_path:
            candidate_manifest["current_iteration_path"] = args.current_iteration_path
        round_pointer_updates = {
            "current_round_brief": args.current_round_brief,
            "current_builder_output": args.current_builder_output,
            "current_reviewer_1_verdict": args.current_reviewer_1_verdict,
            "current_reviewer_2_verdict": args.current_reviewer_2_verdict,
        }
        for manifest_key, pointer_value in round_pointer_updates.items():
            if pointer_value is not None:
                candidate_manifest[manifest_key] = pointer_value

        round_pointer_clears = {
            "current_round_brief": args.clear_current_round_brief,
            "current_builder_output": args.clear_current_builder_output,
            "current_reviewer_1_verdict": args.clear_current_reviewer_1_verdict,
            "current_reviewer_2_verdict": args.clear_current_reviewer_2_verdict,
        }
        for manifest_key, should_clear in round_pointer_clears.items():
            if should_clear:
                candidate_manifest.pop(manifest_key, None)
        resume_packet = normalize_resume_packet(args.resume_path)
        if resume_packet is not None:
            candidate_manifest["resume_packet"] = resume_packet

        next_action = candidate_manifest.setdefault("next_action", {})
        next_action["owner"] = args.next_owner
        next_action["kind"] = args.next_kind
        next_action["trigger"] = args.next_trigger
        next_action["on_trigger"] = args.on_trigger
        next_action["user_dependency"] = args.user_dependency
        if args.blocking_on:
            next_action["blocking_on"] = args.blocking_on
        elif "blocking_on" in next_action:
            del next_action["blocking_on"]

        candidate_manifest["extraordinary_condition_open"] = args.extraordinary_condition_open
        if args.state in TERMINAL_STATES:
            lease = candidate_manifest.setdefault("activity_lease", {})
            lease["enabled"] = True
            lease.setdefault("heartbeat_interval_s", 900)
            lease.setdefault("stale_after_s", 3600)
            lease["status"] = "inactive"
            lease["owner"] = None
            lease["last_heartbeat_at"] = transition_ts
            lease.setdefault("last_progress_at", transition_ts)

        entry = {
            "ts": transition_ts,
            "iteration": candidate_manifest.get("current_iteration"),
            "event": args.event,
            "actor": args.actor,
            "state": args.state,
            "summary": args.summary,
            "next_action_kind": args.next_kind,
        }
        if args.artifact:
            entry["artifacts"] = args.artifact

        errors, warnings = validate(candidate_manifest, ledger + [entry])
        if errors:
            print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
            return 1

        commit_mutation(candidate_manifest, ledger + [entry], entry)
        print(json.dumps({"errors": [], "warnings": warnings}, indent=2))
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Self-improvement-harness control-plane helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_parser = subparsers.add_parser("show", help="show current control-plane summary")
    show_parser.set_defaults(func=cmd_show)

    next_parser = subparsers.add_parser("next", help="emit the machine-readable next-action packet")
    next_parser.set_defaults(func=cmd_next)

    validate_parser = subparsers.add_parser("validate", help="validate manifest and ledger")
    validate_parser.set_defaults(func=cmd_validate)

    contact_parser = subparsers.add_parser(
        "contact-check",
        help="derive whether user-facing communication is structurally allowed",
    )
    contact_parser.set_defaults(func=cmd_contact_check)

    watchdog_parser = subparsers.add_parser("watchdog-checkpoint", help="update watchdog and observation-window state")
    watchdog_parser.add_argument("--condition", required=True, choices=sorted(WATCHDOG_CONDITIONS))
    watchdog_parser.add_argument("--observation-status", required=True, choices=sorted(OBSERVATION_WINDOW_STATUSES))
    watchdog_parser.add_argument("--summary", required=True)
    watchdog_parser.add_argument("--source", required=True)
    watchdog_parser.add_argument("--lease-status", required=True)
    watchdog_parser.add_argument("--actor", default="watchdog")
    watchdog_parser.add_argument("--event")
    watchdog_parser.add_argument("--heartbeat-at")
    watchdog_parser.add_argument("--progress-at")
    watchdog_parser.add_argument("--blocker-class")
    watchdog_parser.add_argument("--evidence-ref")
    watchdog_parser.add_argument("--recommended-action", required=True)
    watchdog_parser.add_argument("--poll-interval-s", type=int)
    watchdog_parser.add_argument("--stale-grace-checks", type=int)
    watchdog_parser.add_argument("--stale-check-count", type=int)
    watchdog_parser.add_argument("--suspect-since")
    watchdog_parser.add_argument("--recovery-attempts", type=int)
    watchdog_parser.add_argument("--last-recovery-at")
    watchdog_parser.add_argument("--auto-resume-command", action="append")
    watchdog_parser.add_argument("--record-stable", action="store_true", default=False)
    watchdog_parser.set_defaults(func=cmd_watchdog_checkpoint)

    heartbeat_parser = subparsers.add_parser("heartbeat", help="record an active-session heartbeat")
    heartbeat_parser.add_argument("--owner", required=True)
    heartbeat_parser.add_argument("--summary", required=True)
    heartbeat_parser.add_argument("--progress", action="store_true", default=False)
    heartbeat_parser.add_argument("--heartbeat-interval-s", type=int)
    heartbeat_parser.add_argument("--stale-after-s", type=int)
    heartbeat_parser.set_defaults(func=cmd_heartbeat)

    release_parser = subparsers.add_parser("release-lease", help="mark the active-session lease inactive")
    release_parser.add_argument("--actor", default="orchestrator")
    release_parser.add_argument("--summary", required=True)
    release_parser.set_defaults(func=cmd_release_lease)

    transition_parser = subparsers.add_parser("transition", help="update manifest state and append a ledger entry")
    transition_parser.add_argument("--expected-state", required=True)
    transition_parser.add_argument("--expected-ledger-entries", type=int)
    transition_parser.add_argument("--state", required=True)
    transition_parser.add_argument("--event", required=True)
    transition_parser.add_argument("--actor", default="orchestrator")
    transition_parser.add_argument("--summary", required=True)
    transition_parser.add_argument("--next-owner", required=True)
    transition_parser.add_argument("--next-kind", required=True)
    transition_parser.add_argument("--next-trigger", required=True)
    transition_parser.add_argument("--on-trigger", action="append", required=True)
    transition_parser.add_argument("--blocking-on")
    transition_parser.add_argument("--user-dependency", action="store_true", default=False)
    transition_parser.add_argument("--extraordinary-condition-open", action="store_true", default=False)
    transition_parser.add_argument("--current-iteration", type=int)
    transition_parser.add_argument("--current-iteration-path")
    transition_parser.add_argument("--current-round-brief")
    transition_parser.add_argument("--current-builder-output")
    transition_parser.add_argument("--current-reviewer-1-verdict")
    transition_parser.add_argument("--current-reviewer-2-verdict")
    transition_parser.add_argument("--clear-current-round-brief", action="store_true", default=False)
    transition_parser.add_argument("--clear-current-builder-output", action="store_true", default=False)
    transition_parser.add_argument("--clear-current-reviewer-1-verdict", action="store_true", default=False)
    transition_parser.add_argument("--clear-current-reviewer-2-verdict", action="store_true", default=False)
    transition_parser.add_argument("--resume-path", action="append")
    transition_parser.add_argument("--artifact", action="append")
    transition_parser.set_defaults(func=cmd_transition)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
