# Continuation Template

Use this as the render contract for a fresh session taking over an already-running harness.

This is not the same artifact as a fresh launch brief.

The goal is to preserve exact current state, not to restate setup intent.

`CONTINUATION.md` is control-plane-generated. Direct changes belong in source truth or this template contract, not in the generated packet itself.

Source mapping:

- program state and next action: `manifest.yaml`
- recently completed: `run-ledger.jsonl`
- live ownership and open-work context: lease, watchdog, observation window, and workboard surfaces
- read-now artifact pointers: current/last round pointers plus resume surfaces from `manifest.yaml`

```md
# Continuation Packet

Updated at:
- <ISO timestamp>

Program state:
- status: <manifest status>
- current iteration: <N>
- current round path: <path>
- current round brief: <path>

Why the program is still open:
- <open workstream 1>
- <open workstream 2>

Recently completed:
- <completed stream or artifact 1>
- <completed stream or artifact 2>

Current live ownership:
- lease owner: <owner or none>
- watchdog state: <healthy|inactive|...>
- workboard status: <inactive|underutilized|saturated|oversubscribed>

Exact next action:
- owner: <next_action.owner>
- kind: <next_action.kind>
- trigger: <next_action.trigger>
- what to do now: <plain-language restatement grounded in control-plane truth>

Read now:
- <required file 1>
- <required file 2>

Do not reconstruct from:
- <unneeded history surface 1>
- <unneeded history surface 2>

Open risks or defects:
- <risk 1>
- <risk 2>

Evidence surfaces:
- <artifact or command output 1>
- <artifact or command output 2>
```
