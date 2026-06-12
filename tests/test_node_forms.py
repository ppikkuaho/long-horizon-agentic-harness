"""#30 — pre-instantiated node forms (user mental model, 2026-06-12: "they get everything in
front of them" — the unfailable-convention machine, deterministically).

The chokepoint drops INSTANTIATED report.md + plan.md skeletons into every child node at
brief-write time: header pre-filled from the address, the GIVEN requirement IDs pre-listed
(derived from brief.md/acceptance.md — the same sources the E2 walker reads), the L5+ seat
getting the verified-not-discharged variant. Filling the form is the only path; zero
transcription ambiguity.

THE GATE STAYS HONEST: a skeleton would otherwise auto-satisfy E2's MISSING-REPORT (file
exists, non-empty) AND the citation check (IDs pre-filled) — so every instantiated form
carries the ``form:unfilled`` sentinel, and the walker refuses a DONE whose report still
carries it (UNFILLED-REPORT-FORM). Mutants: no instantiation -> forms absent -> caught;
sentinel dropped -> skeleton passes E2 -> caught; overwrite-on-respawn -> prior
incarnation's filled report lost -> caught.
"""

import copy
import shutil

import pytest

import harnessd.addressing as addressing
import harnessd.config as config
import harnessd.fencing as fencing
import harnessd.ledger as ledger
import harnessd.spawn.chokepoint as chokepoint
from harnessd.spawn.adapters.base import SpawnResult

LEAF = "proj/widget/task#exec"
PARENT = "proj/widget#exec"


@pytest.fixture
def runtime(tmp_path):
    previous = ledger.RUNTIME_ROOT
    ledger.RUNTIME_ROOT = tmp_path
    try:
        yield tmp_path
    finally:
        ledger.RUNTIME_ROOT = previous


@pytest.fixture(autouse=True)
def _reset_chokepoint_adapter():
    previous = chokepoint.ADAPTER
    try:
        yield
    finally:
        chokepoint.set_adapter(previous)


class _Tmux:
    def kill(self, target):
        pass

    def send_keys(self, target, text):
        return True

    def capture_pane(self, target):
        from harnessd import watchdog
        return f"{watchdog.FORK_PROMPT} \n? for shortcuts"


class FakeAdapter:
    def __init__(self):
        self.tmux = _Tmux()

    def pin_and_open(self, neutral_brief, level_config, tmux_target, env):
        return SpawnResult(
            ok=True,
            session_uuid="sess-forms-0001",
            model_used="m / r",
            role_variant=getattr(level_config, "role_variant", "L5"),
            system_prompt_file="x",
            system_prompt_file_hash="h",
            tmux_target=addressing.session_name_for(tmux_target) + ":0.0",
            transcript_path="/tmp/sess-forms-0001.jsonl",
            failure_class=None,
        )


def _seed_parent():
    token = fencing.mint_owner_token(PARENT, "sa", "uuid", 1)
    ws = addressing.node_dir(PARENT, ledger.RUNTIME_ROOT)
    ws.mkdir(parents=True, exist_ok=True)
    rec = {
        "node_address": PARENT, "parent_address": None, "level": "L4",
        "subagent_id": "sa", "session_uuid": "uuid", "state": "running",
        "generation": 1, "lease_epoch": 1, "owner_token": token,
        "last_applied_seq": 0, "spec_pointer": "design/intent-spec.md",
        "frozen_acceptance_ref": "acceptance.md", "liveness_state": "working",
        "terminal_signal": None, "terminal_signal_at": None, "gate_crossed_at": None,
        "paused_at": None, "transcript_path": None, "workspace": str(ws),
        "tmux_target": addressing.session_name_for(PARENT) + ":0.0",
    }
    live = dict(ledger.all_nodes())
    live[PARENT] = copy.deepcopy(rec)
    ledger.write_binding(live, _lock_held=True)


def _prepare_child_acceptance():
    d = addressing.node_dir(LEAF, ledger.RUNTIME_ROOT)
    d.mkdir(parents=True, exist_ok=True)
    (d / "acceptance.md").write_text(
        "# acceptance\n- R-009.1.1: renders headings\n- R-009.1.2: escapes html\n",
        encoding="utf-8",
    )
    return d


def _drive(level="L5", brief="do the task serving R-009.1.1 and R-009.1.2"):
    chokepoint.set_adapter(FakeAdapter())
    return chokepoint.register_and_spawn_child(
        PARENT, LEAF,
        child_level_config=config.LevelConfig.for_level(level),
        brief_content=brief,
    )


def test_spawn_pre_instantiates_report_and_plan_forms(runtime):
    """The fresh child node receives report.md + plan.md skeletons: header pre-filled
    (address, parent), the GIVEN IDs pre-listed in the Requirement-IDs section, the
    template prompts' identity placeholders resolved, the unfilled sentinel present."""
    _seed_parent()
    child_dir = _prepare_child_acceptance()

    result = _drive()
    assert getattr(result, "ok", False) is True, f"spawn must succeed: {result!r}"

    report = (child_dir / "report.md").read_text(encoding="utf-8")
    assert LEAF in report and PARENT in report, "the From/To header is pre-filled"
    assert "<node-address>" not in report and "<parent-address>" not in report
    assert "R-009.1.1" in report and "R-009.1.2" in report, (
        "the GIVEN requirement IDs are pre-listed — zero transcription ambiguity"
    )
    assert "form:unfilled" in report, (
        "the skeleton must carry the unfilled sentinel — otherwise it auto-defeats E2"
    )

    plan = (child_dir / "plan.md").read_text(encoding="utf-8")
    assert LEAF in plan, "the plan skeleton names the node"
    assert "report.md" in plan and "Sign off" in plan, "the standing final-three items survive"


def test_forms_never_overwrite_a_prior_incarnation(runtime):
    """Respawn at a node whose prior incarnation filled its forms: the files are inherited,
    never clobbered (stateless respawn — the successor continues the plan)."""
    _seed_parent()
    child_dir = _prepare_child_acceptance()
    (child_dir / "report.md").write_text("PRIOR-REPORT-CONTENT\n", encoding="utf-8")
    (child_dir / "plan.md").write_text("PRIOR-PLAN-CONTENT\n", encoding="utf-8")

    result = _drive()
    assert getattr(result, "ok", False) is True
    assert (child_dir / "report.md").read_text(encoding="utf-8") == "PRIOR-REPORT-CONTENT\n"
    assert (child_dir / "plan.md").read_text(encoding="utf-8") == "PRIOR-PLAN-CONTENT\n"


def test_l5_plus_seat_gets_the_verified_variant(runtime):
    """The reviewer's form says VERIFIED, never discharged (the registry's named adaptation)."""
    _seed_parent()
    child_dir = _prepare_child_acceptance()

    result = _drive(level="L5+")
    assert getattr(result, "ok", False) is True
    report = (child_dir / "report.md").read_text(encoding="utf-8")
    assert "verified" in report.lower(), "the L5+ seat gets the verified-variant template"


def test_e2_refuses_a_done_on_an_unfilled_form(runtime):
    """THE GATE STAYS HONEST: a DONE whose report.md still carries the form:unfilled sentinel
    is refused (UNFILLED-REPORT-FORM) — the pre-instantiated skeleton must never auto-satisfy
    MISSING-REPORT or the citation check. (Mutant: sentinel unchecked -> skeleton sails
    through E2 -> caught.)"""
    from harnessd import return_contract

    _seed_parent()
    child_dir = _prepare_child_acceptance()
    result = _drive()
    assert getattr(result, "ok", False) is True

    binding = ledger.read_binding(LEAF)
    verdict = return_contract.check_done_contract(LEAF, binding)
    assert verdict.ok is False
    assert any("UNFILLED-REPORT-FORM" in d for d in verdict.defects), (
        f"an untouched skeleton must be refused as UNFILLED-REPORT-FORM; got {verdict.defects!r}"
    )

    # the agent fills the form (sentinel removed, IDs kept as citations) -> the walker passes
    report = (child_dir / "report.md").read_text(encoding="utf-8")
    filled = "\n".join(
        line for line in report.splitlines() if "form:unfilled" not in line
    ).replace("<", "").replace(">", "")
    (child_dir / "report.md").write_text(filled + "\nDid the work.\n", encoding="utf-8")
    verdict2 = return_contract.check_done_contract(LEAF, binding)
    assert verdict2.ok is True, f"a filled form must pass; got {verdict2.defects!r}"
