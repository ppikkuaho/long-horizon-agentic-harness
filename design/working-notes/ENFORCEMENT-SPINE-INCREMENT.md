# Enforcement-Spine Increment — behavioral wave, item 1 (2026-06-11)

User mandate: "Follow the spec / docs. Everything should be there. It's just about
building it faithfully." Strategy ratified by the user: lift the EXISTING eval
logic into runtime hooks — deterministic parts as hard gates on spawn and
sign-off; judgment parts stay eval-side (tools/eval_*.py).

Grounding (LR-14): the docs' forcing functions exist only as offline eval
instruments; at runtime the report/freeze/spawn paths enforce nothing. This
increment installs the deterministic half on those three paths.

## E1 — pieces-present at the spawn chokepoint (task #17)
- WHERE: chokepoint claim_and_spawn (+ the resume leg), after brief assembly,
  before the adapter opens the pane.
- WHAT: the Inc-18 pieces_present validation — every load-manifest path resolves
  under the harness root; the brief carries every field the receiving level/seat
  needs (spec pointer; frozen acceptance for executor seats); role_variant selects
  the correct per-seat manifest.
- ON FAIL: SpawnFailure('pieces_missing') -> release claim + §6.3 escalation row.
  An under-equipped agent is never booted (agent-lifecycle L13: "you never
  bootstrap yourself" — made true mechanically).
- SPEC: BEHAVIOURAL-VALIDATION Inc 18; ROLE-RESOLUTION (load-manifest);
  agent-lifecycle §How-You-Spawn-a-Child.
- NOTE: absolutize manifest paths at brief-authoring or validate they resolve from
  the NODE CWD (LR-3's dangling-relative-path failure).

## E2 — return-contract walker on the sign-off path (task #18)
- WHERE: watchdog terminal-signal processing (check_terminal_signal), DONE branch,
  BEFORE chokepoint.collapse.
- WHAT (v1 = presence + parseability ONLY): report.md exists; L5/L5+ report cites
  >=1 requirement ID; evidence block present in the signal; trace-block stanzas
  parse on L2/L3 design artifacts (closed field set {id, serves, kind, level,
  node}; dotted-id truncation agrees with declared parent; no dup ids).
- ON FAIL: refuse the collapse (NOOP reason=return_contract_failed), journal ONE
  edge-triggered typed-defect row (MISSING-TRACE-* / MALFORMED-TRACE-* /
  DUP-ID-* / MISSING-REPORT), wake the node with the defect pointer — the agent
  fixes and re-signals. "The hook rejects it — you cannot report complete"
  (L1/L2 role docs, intent-spec-contract) becomes literally true.
- GUARD: per-level applicability map (an L5 smoke node without trace-block duties
  must not be wedged by L2-class checks); a node can always sign FAILED/ESCALATED
  without contract checks (never trap an agent in a failing loop).
- SPEC: PLAN-ALIGNMENT-GATE §Requirements-Traceability (canonical syntax + typed
  defects); intent-spec-contract; L2/L1/L5 role-doc output contracts.

## E3 — freeze-block + promote gate (task #19)
- WHERE: (a) the future freeze edge (gate verb); (b) harnessctl promote / ipc
  promote verb NOW.
- WHAT: PLAN-ALIGNMENT-GATE structural rules — interfaces enter the gate as
  `candidate`, frozen ONLY on the PASS edge; a load-bearing requirement with
  reflect-back=pending is a structural FAIL that blocks freeze; promote
  --decision accept refuses without an intent-spec §8 delivery destination
  (explicit `in-place` allowed) and with pending load-bearing reflect-back rows.
- CARRIES: the L1 closing-protocol hook-point (playback-escalation before DONE) —
  BLOCKED on the user's Stage-5 authority ruling (translation list item B).

## E1 implementation design (settled 2026-06-11, pre-build)
DISCOVERY: spec_pointer/frozen_acceptance_ref flow brief <- work_node <- BINDING,
and no production path ever stamps them onto a binding — the gate verbatim would
refuse every spawn. So E1 = derivation + gate:
 1. DERIVATION at registration (agent-lifecycle: "the daemon derives its
    spec/acceptance pointers from the node you prepared"): when the outbox
    services a spawn request — and when genesis registers the L1 root — stamp on
    the planned binding: spec_pointer := <node>/brief.md if present (genesis's
    _ensure_l1_brief already authors it for L1); frozen_acceptance_ref :=
    <node>/acceptance.md if present. The live run's L4 ALREADY prepared exactly
    these files in its children's nodes — the real cascade passes.
 2. GATE at STEP2.5 (claim_and_spawn, after assemble_neutral; same on the resume
    leg): pieces_present.check_boundary(node_address, level_config, work_node);
    on fail -> release_claim + _emit_spawn_failure_escalation(failure_class=
    'pieces_missing:<...>') + _result_failed. No actor opens under-equipped.
 3. Expected fixture fallout: chokepoint/daemon tests with sparse bindings gain
    spec_pointer (and acceptance for executor seats) — completing fixtures to the
    enforced world is the point, not a regression.

## Order + discipline
E1 -> E2 -> E3, each test-first with revert-mutant verification, full suite
between, real-substrate smoke (preference 2) before declaring the increment done:
boot the daemon on a scratch runtime root, spawn one node with a broken manifest
(E1 fires), one node signing DONE without a report (E2 fires), one promote
without destination (E3 refuses).
