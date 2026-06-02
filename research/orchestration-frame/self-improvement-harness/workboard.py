#!/usr/bin/env python3
"""Structured workboard helper for the self-improvement harness."""

from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
WORKBOARD_PATH = ROOT / "WORKBOARD.yaml"
WORKBOARD_LOCK_PATH = ROOT / ".workboard.lock"

BOARD_STATUSES = {"inactive", "underutilized", "saturated", "oversubscribed"}
STREAM_STATUSES = {"planned", "active", "waiting", "completed", "blocked", "cancelled"}
COUNTABLE_STATUSES = {"active", "waiting"}
REQUIRED_TOP_LEVEL_KEYS = {
    "version",
    "objective",
    "owner",
    "last_reconciled_at",
    "status",
    "saturation",
    "streams",
}
REQUIRED_SATURATION_KEYS = {
    "minimum_active_streams",
    "preferred_active_streams",
    "maximum_active_streams",
}
REQUIRED_STREAM_KEYS = {
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
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def normalize_scalars(value):
    if isinstance(value, dict):
        return {key: normalize_scalars(subvalue) for key, subvalue in value.items()}
    if isinstance(value, list):
        return [normalize_scalars(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def load_board() -> dict:
    with WORKBOARD_PATH.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("WORKBOARD.yaml did not parse to a mapping")
    return normalize_scalars(payload)


def save_board(board: dict) -> None:
    temp_path = WORKBOARD_PATH.with_name(f".{WORKBOARD_PATH.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(normalize_scalars(board), handle, sort_keys=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, WORKBOARD_PATH)


@contextmanager
def workboard_lock(*, shared: bool):
    WORKBOARD_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with WORKBOARD_LOCK_PATH.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def derive_summary(board: dict) -> dict:
    streams = board.get("streams", [])
    if not isinstance(streams, list):
        streams = []

    active_count = 0
    unresolved_count = 0
    by_status: dict[str, int] = {}
    owners: list[str] = []
    for raw_stream in streams:
        if not isinstance(raw_stream, dict):
            continue
        status = str(raw_stream.get("status"))
        by_status[status] = by_status.get(status, 0) + 1
        if status in COUNTABLE_STATUSES:
            active_count += 1
        if status not in {"completed", "cancelled"}:
            unresolved_count += 1
        owner = raw_stream.get("owner")
        if isinstance(owner, str) and owner and owner != "unassigned" and owner not in owners:
            owners.append(owner)

    saturation = board.get("saturation", {})
    minimum_active = saturation.get("minimum_active_streams", 0) if isinstance(saturation, dict) else 0
    preferred_active = saturation.get("preferred_active_streams", 0) if isinstance(saturation, dict) else 0
    maximum_active = saturation.get("maximum_active_streams", 0) if isinstance(saturation, dict) else 0

    if unresolved_count == 0:
        derived_status = "inactive"
    elif isinstance(maximum_active, int) and maximum_active > 0 and active_count > maximum_active:
        derived_status = "oversubscribed"
    elif isinstance(minimum_active, int) and minimum_active > 0 and active_count < minimum_active:
        derived_status = "underutilized"
    else:
        derived_status = "saturated"

    return {
        "status": board.get("status"),
        "derived_status": derived_status,
        "active_stream_count": active_count,
        "unresolved_stream_count": unresolved_count,
        "stream_count": len(streams),
        "streams_by_status": by_status,
        "owners": owners,
        "preferred_active_streams": preferred_active,
        "minimum_active_streams": minimum_active,
        "maximum_active_streams": maximum_active,
        "last_reconciled_at": board.get("last_reconciled_at"),
    }


def validate_board(board: dict) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in board:
            errors.append(f"WORKBOARD.yaml missing required key: {key}")

    version = board.get("version")
    if not isinstance(version, int) or version < 1:
        errors.append("WORKBOARD.yaml version must be an integer >= 1")

    if not isinstance(board.get("objective"), str) or not board["objective"].strip():
        errors.append("WORKBOARD.yaml objective must be a non-empty string")
    if not isinstance(board.get("owner"), str) or not board["owner"].strip():
        errors.append("WORKBOARD.yaml owner must be a non-empty string")
    if board.get("status") not in BOARD_STATUSES:
        errors.append(f"WORKBOARD.yaml status must be one of {sorted(BOARD_STATUSES)}")
    if parse_iso(board.get("last_reconciled_at")) is None:
        errors.append("WORKBOARD.yaml last_reconciled_at must be an ISO timestamp")

    saturation = board.get("saturation")
    if not isinstance(saturation, dict):
        errors.append("WORKBOARD.yaml saturation must be a mapping")
    else:
        for key in REQUIRED_SATURATION_KEYS:
            if key not in saturation:
                errors.append(f"WORKBOARD.yaml saturation missing required key: {key}")
        minimum_active = saturation.get("minimum_active_streams")
        preferred_active = saturation.get("preferred_active_streams")
        maximum_active = saturation.get("maximum_active_streams")
        for key, value in (
            ("minimum_active_streams", minimum_active),
            ("preferred_active_streams", preferred_active),
            ("maximum_active_streams", maximum_active),
        ):
            if not isinstance(value, int) or value < 0:
                errors.append(f"WORKBOARD.yaml saturation.{key} must be an integer >= 0")
        if (
            isinstance(minimum_active, int)
            and isinstance(preferred_active, int)
            and minimum_active > preferred_active
        ):
            errors.append("WORKBOARD.yaml minimum_active_streams cannot exceed preferred_active_streams")
        if (
            isinstance(preferred_active, int)
            and isinstance(maximum_active, int)
            and preferred_active > maximum_active
        ):
            errors.append("WORKBOARD.yaml preferred_active_streams cannot exceed maximum_active_streams")

    streams = board.get("streams")
    if not isinstance(streams, list) or not streams:
        errors.append("WORKBOARD.yaml streams must be a non-empty list")
        streams = []

    seen_ids: set[str] = set()
    for index, raw_stream in enumerate(streams, start=1):
        prefix = f"WORKBOARD.yaml streams[{index}]"
        if not isinstance(raw_stream, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        for key in REQUIRED_STREAM_KEYS:
            if key not in raw_stream:
                errors.append(f"{prefix} missing required key: {key}")
        stream_id = raw_stream.get("stream_id")
        if not isinstance(stream_id, str) or not stream_id.strip():
            errors.append(f"{prefix}.stream_id must be a non-empty string")
        elif stream_id in seen_ids:
            errors.append(f"duplicate stream_id in WORKBOARD.yaml: {stream_id}")
        else:
            seen_ids.add(stream_id)

        if raw_stream.get("status") not in STREAM_STATUSES:
            errors.append(f"{prefix}.status must be one of {sorted(STREAM_STATUSES)}")
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
            if parse_iso(raw_stream.get(key)) is None:
                errors.append(f"{prefix}.{key} must be an ISO timestamp")
        if (
            parse_iso(raw_stream.get("opened_at")) is not None
            and parse_iso(raw_stream.get("updated_at")) is not None
            and parse_iso(raw_stream["updated_at"]) < parse_iso(raw_stream["opened_at"])
        ):
            errors.append(f"{prefix}.updated_at cannot be earlier than opened_at")

    summary = derive_summary(board)
    if board.get("status") != summary["derived_status"]:
        warnings.append(
            f"WORKBOARD.yaml status {board.get('status')!r} does not match derived status {summary['derived_status']!r}"
        )
    if summary["active_stream_count"] < summary["minimum_active_streams"] and summary["unresolved_stream_count"] > 1:
        warnings.append(
            "WORKBOARD.yaml is under the configured minimum active-stream target while multiple unresolved streams remain"
        )

    return errors, warnings, summary


def find_stream(board: dict, stream_id: str) -> dict:
    streams = board.get("streams")
    if not isinstance(streams, list):
        raise ValueError("WORKBOARD.yaml streams is not a list")
    for stream in streams:
        if isinstance(stream, dict) and stream.get("stream_id") == stream_id:
            return stream
    raise ValueError(f"unknown stream_id: {stream_id}")


def cmd_validate(args: argparse.Namespace) -> int:
    with workboard_lock(shared=True):
        board = load_board()
    errors, warnings, summary = validate_board(board)
    print(json.dumps({"errors": errors, "warnings": warnings, "summary": summary}, indent=2))
    return 1 if errors else 0


def cmd_show(args: argparse.Namespace) -> int:
    with workboard_lock(shared=True):
        board = load_board()
    errors, warnings, summary = validate_board(board)
    payload = {"board": board, "errors": errors, "warnings": warnings, "summary": summary}
    print(json.dumps(payload, indent=2))
    return 1 if errors else 0


def cmd_touch(args: argparse.Namespace) -> int:
    with workboard_lock(shared=False):
        board = load_board()
        board = copy.deepcopy(board)
        board["last_reconciled_at"] = now_iso()
        if args.owner:
            board["owner"] = args.owner
        if args.status:
            board["status"] = args.status
        if args.note:
            notes = board.setdefault("notes", [])
            if not isinstance(notes, list):
                raise ValueError("WORKBOARD.yaml notes must be a list before touch can append to it")
            notes.append(args.note)
        errors, warnings, _summary = validate_board(board)
        if errors:
            print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
            return 1
        save_board(board)
        print(json.dumps({"errors": [], "warnings": warnings}, indent=2))
        return 0


def cmd_set_stream(args: argparse.Namespace) -> int:
    with workboard_lock(shared=False):
        board = load_board()
        board = copy.deepcopy(board)
        stream = find_stream(board, args.stream_id)
        touched_at = now_iso()

        if args.status:
            stream["status"] = args.status
        if args.owner:
            stream["owner"] = args.owner
        if args.next_action:
            stream["next_action"] = args.next_action
        if args.objective:
            stream["objective"] = args.objective
        if args.stop_condition:
            stream["stop_condition"] = args.stop_condition
        if args.add_evidence_ref:
            evidence_refs = stream.setdefault("evidence_refs", [])
            if not isinstance(evidence_refs, list):
                raise ValueError(f"{args.stream_id}.evidence_refs must be a list")
            evidence_refs.append(args.add_evidence_ref)
        if args.add_write_target:
            write_targets = stream.setdefault("write_targets", [])
            if not isinstance(write_targets, list):
                raise ValueError(f"{args.stream_id}.write_targets must be a list")
            write_targets.append(args.add_write_target)
        if args.note:
            notes = stream.setdefault("notes", [])
            if not isinstance(notes, list):
                raise ValueError(f"{args.stream_id}.notes must be a list")
            notes.append(args.note)

        stream["updated_at"] = touched_at
        board["last_reconciled_at"] = touched_at

        errors, warnings, _summary = validate_board(board)
        if errors:
            print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
            return 1
        save_board(board)
        print(json.dumps({"errors": [], "warnings": warnings}, indent=2))
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Structured workboard helper for the self-improvement harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate WORKBOARD.yaml")
    validate_parser.set_defaults(func=cmd_validate)

    show_parser = subparsers.add_parser("show", help="show WORKBOARD.yaml plus derived summary")
    show_parser.set_defaults(func=cmd_show)

    touch_parser = subparsers.add_parser("touch", help="update top-level board metadata")
    touch_parser.add_argument("--owner")
    touch_parser.add_argument("--status", choices=sorted(BOARD_STATUSES))
    touch_parser.add_argument("--note")
    touch_parser.set_defaults(func=cmd_touch)

    set_stream_parser = subparsers.add_parser("set-stream", help="update a single stream in WORKBOARD.yaml")
    set_stream_parser.add_argument("--stream-id", required=True)
    set_stream_parser.add_argument("--status", choices=sorted(STREAM_STATUSES))
    set_stream_parser.add_argument("--owner")
    set_stream_parser.add_argument("--next-action")
    set_stream_parser.add_argument("--objective")
    set_stream_parser.add_argument("--stop-condition")
    set_stream_parser.add_argument("--add-evidence-ref")
    set_stream_parser.add_argument("--add-write-target")
    set_stream_parser.add_argument("--note")
    set_stream_parser.set_defaults(func=cmd_set_stream)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
