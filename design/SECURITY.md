# SECURITY — Containment Floor for Spawned Autonomous Agents

> **Status:** v1 design. Establishes the minimal-but-effective, configurable, mac-native containment floor for agents spawned by the harness. Upgrades WORKSPACE-SCHEMA.md line 74's "filesystem-level ACLs are an available hardening" from convention to a **stated enforcement mechanism**.
>
> **Scope of this doc:** filesystem **writes** + **secret reads**. NOT capability. Spawned agents keep web/search, the full default tool set, and the ability to run code / tests / install deps. Network egress is **deferred-with-trigger**, not built here.
>
> **Register provenance:** V1 / Decision A flagged SECURITY.md as homeless. This doc claims the seat and names the owning build increment for every control so none stays homeless.
>
> **Verified on:** the user's primary dev machine, macOS 26.4 (build 25E246), arm64. All "VERIFIED" claims below were run live on this box.
>
> **Pinned-binary path (single source of truth):** the seatbelt wrapper and the §2.3 read-allow both reference ONE canonical realpath. DAEMON §6.2 line 926 currently spells it `.cc-pinned/node_modules/@anthropic-ai/claude-code/bin/claude.exe` — the `.exe` suffix on a Mach-O arm64 binary is almost certainly a stale Windows-ism; the real launcher on this box is the platform package binary `.cc-pinned/node_modules/@anthropic-ai/claude-code-darwin-arm64/claude` (Mach-O arm64, v2.1.152). **OWED back-edit:** reconcile DAEMON §6.2 line 926 to the resolved realpath. This doc, the §2.3 profile, and §7 reference that single path and do not re-spell it. The realpath is load-bearing: §2.4 canonicalization means a wrong/symlinked binary path either fails the spawn or silently read-denies the 214 MB binary under the jail.

## Decisions (LOCKED 2026-06-05 — user evaluation)

- **Mechanism = Option A:** `sandbox-exec` (seatbelt) write+read-jail as the v1 DEFAULT (sandbox-exec confirmed present on this box), with the `securityd` mach-deny as the keychain floor. **Helper-UID is a config TOGGLE** — off by default; the configurable hardening for higher-stakes work, or forced on if commissioning gate 1 shows the CC binary needs `securityd` to boot. The VM tier stays reserved (`escalate_to_vm`, not built in v1).
- **OAuth token:** relocated OUT of the writable `CLAUDE_CONFIG_DIR`.
- **Default read posture:** cross-project read-deny ON by default for L2–L5.
- **Empirical validation deferred to build:** the 7 §8.1 commissioning gates (does CC boot under the seatbelt? does the mach-deny break its auth? do real installs land? …) are checked **when the spawn-chokepoint increment is built** — the seatbelt is literally the pane's launch command. The design is locked now; if the CC binary surprises us at build, the profile is adjusted then.

---

## 0. The constraints this design is built to (LOCKED, do not re-litigate)

These were evaluated and locked by the user on 2026-06-05. The design serves them; it does not reopen them.

1. **Run environment:** the user's **primary dev machine TODAY** (their files, `~/.ssh`, keychain, other projects all present → real confinement needed now). Moving to a **dedicated machine soon** → the design MUST be configurable to **relax** there.
2. **Default + per-process configurable:** ship a sane **default** profile, tunable at the start of each build/process. A policy with knobs, not one fixed setting. Not too tight (must not cripple agents), not too lenient.
3. **The jail is about FILESYSTEM WRITES + SECRET READS, not capability.** Agents keep web/search, full tools, and the ability to run code/tests/install deps. Network egress is **deferred** (accepted risk on a trusted box) — recorded, not built.
4. **Permission posture:** skip-permissions **inside** the jail (spawned CC auto-approves its own tool calls; containment bounds the blast radius). NOT `allowedTools`-restricted in v1. Revisitable.
5. **HARD mac-native constraint:** the pinned CC is a mac-native Mach-O binary run interactively in tmux. **A Linux Docker/OCI container is OFF THE TABLE** — it would require a different, non-pinned Linux CC and break H40. Containment MUST be mac-native: restricted helper OS user, `sandbox-exec`/seatbelt profile, a macOS VM, or a combination. Evaluate THESE.

---

## 1. Threat model + trust boundary

The corpus until now lacked an adversarial framing. This section supplies it.

### 1.1 Trust boundary

**TRUSTED (the control plane):**

- The **user**.
- The **harness code** (`harnessd/` and its daemon, the single-writer executor).
- The **ledgers** (the node state, the lease/owner-token records).
- The **role docs** (`operational/L{1-5}/role.md`) and the **read-only design docs** (`design/*.md`).

**UNTRUSTED-BY-DEFAULT (the data plane):**

- An **agent's actions beyond its own node workspace** — sibling nodes, parent/cousin nodes, the L1 portfolio tree, `harnessd/`, the design docs, the user's `~` and other projects.
- **Anything an agent reads during a build** — scraped pages, dependency source, test fixtures, tool output. A build can ingest attacker-influenced bytes through search/web/installs, which are intentionally open.

The agent's **own node workspace** and **below** is the only region it is trusted to mutate.

### 1.2 Adversary

The adversary is **a spawned agent that has gone off-policy**, by any of three routes that are operationally indistinguishable from the daemon's point of view:

- **Buggy** — a loop, a bad path join, a `rm -rf` with a wrong base.
- **Prompt-injected** — content read during the build (a scraped page, a malicious README, a poisoned dependency) steers the agent to act against the user.
- **`cd`'d-away** — the agent legitimately changes working directory and then writes/read-globs relative to the wrong root.

The adversary has, by design (constraint 4), **auto-approved tool calls** and the **full tool set** including Bash, web, and dep-install. It can run arbitrary code and compiled binaries. We do **not** rely on the agent's judgment or on `allowedTools` to bound it. **The containment is the structural bound.**

### 1.3 What the jail must structurally prevent

A spawned agent (buggy / injected / cd'd-away) MUST NOT be able to:

- **Write** outside its own node workspace: sibling/parent/cousin nodes, the L1 portfolio tree, `harnessd/` and the ledgers, the design docs, the user's home or other projects.
- **Read** the user's secrets: `~/.ssh` key material, the keychain, the OAuth token file itself, the credential stores under `~/.config`/`~/` (gh, gcloud, docker, npm, kube, netrc, git-credentials, shell histories), `.env`/secret-pattern files in sibling and other projects, inherited secret env vars.

> **Two guarantees here are MEASURED, not asserted — and one was a hole the first draft shipped.** The default profile in §2.3 now delivers all of the above (verified holes from the escape-path review are closed: the keychain is closed by a mach-service deny **and** the helper-UID kernel wall, not by the file-read deny which the review proved irrelevant; the broad credential set is denied, not just four home dirs; and `.env`/secret-pattern files outside the workspace are denied by a glob). Two caveats are bounded explicitly rather than over-claimed: **(a)** the keychain file-read deny alone does NOT protect the keychain (the `security` CLI reads via the `securityd` MACH service, not file IO — see §2.3 / §3.3); **(b)** same-UID seatbelt does NOT hide other same-UID processes' argv/env from this agent (`ps eww`, leaked `--token=…` on another pane's command line) — that residual is closed only by the `HELPER-UID` knob (§2.5, §3.3 residual-exposure note).

### 1.4 What MUST stay allowed (or role resolution / work breaks)

- **Reads** of: the agent's own subtree; same-level siblings' **published contracts**; its **parent** node (the F34 read graph, WORKSPACE-SCHEMA lines 63-72).
- **Reads** of the `--system-prompt-file` **role doc** at `operational/L{1-5}/role.md` (DAEMON §6.2 line 930, §7 line 1055).
- **Reads** of the read-only harness **design docs** under `design/*.md` (brief.md is pointer-not-payload; upstream intent is pulled on demand, WORKSPACE-SCHEMA line 217).
- **Reads** of the clean config dir `CLAUDE_CONFIG_DIR=.cc-pinned/config` and the pinned binary under `.cc-pinned/node_modules/...` — **EXCEPT** the single token file (§3).
- **Writes** to the agent's own node subtree and the per-session `CLAUDE_CODE_TMPDIR` (SCALE §6).
- **Writes** to `CLAUDE_CONFIG_DIR` and (pending the §8.1 boot smoke-test) `~/.claude` — **CC writes its own lock/state/history there during a long-lived session; the jail must allow these or it bricks the interactive boot before any agent work happens** (§2.3 write-allow; the token-file read-deny is layered on top so a writable config still can't read the credential). This was a hole the first draft's §2.3 profile left open and §8.1 already predicted.
- **Writes** to the **redirected per-tool dependency caches** (npm/pip/go/cargo/nuget/yarn), pointed INTO the workspace by env vars set at the chokepoint (§2.3 tool-cache redirection). **Without this, a JS/Go/Rust/.NET build hard-fails on its VERY FIRST `npm install` / `go mod` / `cargo` fetch** (VERIFIED: those write per-user caches at `~/.npm`, `~/go/pkg/mod`, `~/.cargo` outside the workspace and abort with `EPERM`/`Operation not permitted` under a workspace-only write-jail; pip is the lucky exception that degrades to cache-disabled). Constraint 3 requires install/build to work, so this is first-class, not an afterthought.
- **Network**: search/web/dep-installs (constraint 3; §5).

> **Two reads the default DENIES, named so they're a known limitation not a surprise** (the secret-deny dirs are mixed secret/non-secret): denying all of `~/.ssh` blocks `known_hosts`, so **SSH-based dep fetches (`git+ssh`, `go get` over SSH, `pip install git+ssh://…`) break by default** — use HTTPS registries/deps, or flip to the narrowed-key-material deny in §2.3 (option b) to leave `known_hosts`/`config` readable; denying all of `~/.aws` blocks `~/.aws/config` (region/profile, non-secret) so SDK calls in tests that read the default profile break. Both are named decisions in §2.3, not silent breaks.

L1 and optimizer-L1 hold read-only whole-portfolio god-views (WORKSPACE-SCHEMA lines 54-59). They **mutate nothing**, so the write-deny applies to them too — the god-view is a read capability, never a write or kill capability.

### 1.5 Threat-model correction — the "0700 home already protects secrets" premise is FALSE on this box

The cluster prompt notes "Unix 0700 home dirs already block cross-user secret reads." **On this machine that premise is only partly true and must be enforced, not assumed:**

| Path | Actual perms (VERIFIED) | Consequence |
|---|---|---|
| `~peeta` (`/Users/peeta`) | `drwxr-x---` **(0750, group staff)** | A helper user **in group staff** could traverse and read any group-readable file. NOT 0700. |
| `/Users/peeta/Documents` | `drwx------` **(0700)** | Blocks a different non-staff UID from traversing into the harness tree at all. |
| `~/.ssh` | `drwx------` **(0700)** | SSH keys protected from a different UID by ownership alone. ✅ |
| `~/Library/Keychains/*` | `0600` | Keychain DB protected from a different UID by ownership alone. ✅ |
| harness repo root | `drwxr-xr-x` **(0755, world-readable)** | A helper user could read `harnessd/` + `design/` + `.cc-pinned/config/.oauth_token` unless tightened. |

**Net:** `~/.ssh` and the keychain DB are the only secrets the cross-UID (helper-user) wall already covers by default — **by file ownership, which matters because the keychain's secret-access path is `securityd` (mach), not file IO** (§2.3): a same-UID seatbelt's file-read deny does NOT cover the keychain, so for the keychain specifically the helper-UID wall is structurally stronger. The 0700-home claim is a **prerequisite to enforce** (a helper-user fork must `chmod 700 ~`, tighten the 0755 repo root, and protect the token file), **not a property to assume**. This shapes the mechanism fork in §2: the recommended default is the same-UID seatbelt jail (it does not depend on any of these perms being right for the FILE-path secrets), **but the keychain forces either a `(deny mach-lookup …)` clause that may break CC's boot (§8.1 gate 1) or falling back to HELPER-UID as the keychain floor** — the one place same-UID seatbelt cannot reach.

---

## 2. The write-jail — mechanism (FORK — for user review) + the configurable profile

### 2.1 Mechanism evaluation (the three mac-native candidates)

**Candidate A — `sandbox-exec` / seatbelt `.sb` profile (RECOMMENDED DEFAULT).**

A per-spawn seatbelt profile, templated from the node's one-spine address, wrapping the CC invocation at the spawn chokepoint.

- ✅ **Confines the entire process tree with zero per-child work** (VERIFIED): a nested bash, a `python3` subprocess, **and a compiled Mach-O `/bin/cp`** were all blocked from writing outside the work tree. Seatbelt policy is inherited across fork/exec, so CC's Bash tool, its node children, installed deps, and spawned test processes are all confined by **one** wrapper. This is the decisive property for an interactive CC that shells out freely.
- ✅ **Per-node-precise write-root** for free — the allowed-write subpath is the node's physical `L{n}/` path, computed from `node_address` exactly as WORKSPACE-SCHEMA line 74's path-scoping already is.
- ✅ **Stateless** — no machine-state mutation, no user creation, no `chmod` surgery. Same UID, so the pinned binary, role docs, and OAuth-token env injection "just work."
- ✅ **Network stays open for free** — the profile touches only `file-read*`/`file-write*`, never `network*` (VERIFIED).
- ⚠️ **`sandbox-exec` is officially DEPRECATED** in its own man page (~since 2017) but ships and runs on 26.4, root-owned `0755`, and is the substrate Apple's own app sandbox and Codex CLI use today. "Deprecated" = no public support promise, not "removed." **Recorded as an accepted-with-trigger risk (§8), not a v1 blocker.**
- ⚠️ **Same-UID secret-read hiding hits the realpath gotcha** (§2.4) — must canonicalize paths or the deny silently leaks.

**Candidate B — restricted helper OS user.**

Spawn the agent as a separate, unprivileged UID; rely on the kernel's cross-UID ownership wall for secret reads.

- ✅ **Stronger, kernel-level cross-UID isolation** for the user's own `~/.ssh`, keychain, and other projects — needs no path canonicalization, no symlink fragility.
- ❌ **Blocked by the verified perms wall** (§1.5): `/Users/peeta` is 0750 and `/Users/peeta/Documents` is **0700**, so a different non-staff UID **cannot even traverse into the harness tree** to reach the 214 MB pinned binary or the role docs. Fixing this means **relocating the harness outside the home dir** or adding ACLs/group membership along the entire path — materially invasive.
- ❌ **Coarse** — one helper user serves all nodes, so every node can write every other node's workspace *as that user* unless combined with seatbelt or per-node POSIX ACLs. Per-node helper users give true isolation but add user-management overhead at spawn/teardown.
- ❌ **One-time privileged setup** — `sysadminctl`/`dscl` are root-only. Plus `chmod 700 ~`, tighten the 0755 repo root, protect the token file. A real prerequisite, not a per-spawn cost — but a setup cost the default should not require.

**Candidate C — macOS VM.**

A full VM as the isolation boundary.

- ✅ Strongest isolation; the machine boundary *is* the jail.
- ❌ **Overkill for v1** on the primary machine. Reserved as the **escalation tier** (§2.5, the `ESCALATE-TO-VM` knob) for builds that ingest untrusted external input where a seatbelt-policy bug is unacceptable. On the coming dedicated machine the VM is unnecessary — the machine itself is the boundary and the knobs relax instead.

### 2.2 FORK — for user review

> **FORK: write-jail mechanism. RECOMMENDATION: Candidate A (seatbelt `sandbox-exec`) as the v1 default, with the helper-user (Candidate B) carved as an *optional* belt-and-suspenders read-floor toggle, and the VM (Candidate C) reserved as the `ESCALATE-TO-VM` knob target — not built in v1.**
>
> **Why A over B for the default:** the live tests are decisive. Seatbelt confines the whole process tree (including compiled binaries and installed deps) with zero per-child work and **zero host-permission surgery**; the helper-user path is blocked by the verified 0750/0700 walls and would force relocating the harness or rewriting ACLs. Seatbelt keeps the same UID, so the pinned binary, role docs, and OAuth env injection need no cross-user readability setup, no `launchctl asuser` / `sudo -u` plumbing, no tmux-server-ownership juggling. The seatbelt reproduces the helper-user's home-secret read-wall via explicit `(deny file-read* …)` clauses, at far lower setup cost — **for FILE-path secrets.**
>
> **The real tradeoff to weigh (why this is a genuine fork, not a foregone conclusion) — and the escape-path review SHARPENED it:**
> - Seatbelt-only is **lightest** but carries (a) the **deprecation risk** (§8), (b) the **same-UID realpath fragility** for secret-read denies (§2.4) — a mis-canonicalized path silently leaks a secret, and (c) **two things the seatbelt structurally cannot do that the helper-UID does for free:** the **keychain** (the `security` CLI reads via the `securityd` MACH service, not file IO, so a file-read deny is useless — the seatbelt needs a `(deny mach-lookup …)` that MAY break CC's own boot, §8.1 gate 1; the helper-UID covers the keychain by file ownership unconditionally), and **same-UID argv/process-table visibility** (a sibling agent's `--token=…` is visible via `ps eww`; only a separate UID hides it).
> - Helper-user **eliminates the realpath fragility AND covers the keychain AND closes cross-process argv** (all by kernel ownership, no profile) but is **invasive to stand up** on this box and **coarse** (one UID for all nodes) unless layered with seatbelt anyway.
> - The honest middle is **A as default, B available as a hardening toggle** (the `HELPER-UID` knob, §2.5) when a build wants the kernel read-wall in addition to the seatbelt write-jail. On the dedicated machine, both can relax.
>
> **Decision owner:** the user. Recommendation stands at **A-default, B-optional-toggle, C-as-escalation-knob** — BUT note the keychain caveat: if §8.1 gate 1 shows the pinned CC needs `securityd` to authenticate at boot, the global mach-deny can't ship and **`HELPER-UID` becomes the correct keychain floor by default**, not the seatbelt. If the user prefers the kernel read-wall from day one anyway (it also closes the keychain + argv gaps cleanly), flip `HELPER-UID` on by default and pay the one-time setup (`chmod 700 ~`, relocate-or-ACL the harness, create the UID).

### 2.3 The DEFAULT seatbelt profile (the sane middle — "writes jailed to workspace+caches+config, secrets + cross-project source unreadable, role/design docs + system libs readable")

The WRITE jail below was **VERIFIED strong on macOS 26.4** (writes inside the work tree succeed; writes to `$HOME` fail `Operation not permitted`, file never created; nested-`sandbox-exec`, `osascript do shell script`, LaunchAgent-plist, `launchctl submit`, `crontab`, and symlink-out-of-workspace all blocked — see §8.1 regression checklist). The READ side of the **first draft was wrong** and has been rebuilt: the escape-path review proved the old deny-named-set-behind-`(allow default)` structure left the keychain, `~/.claude.json`, `~/.config/gh`, `~/.zsh_history`, `~/.codex`, `~/.gemini`, and every sibling `.env` readable — and, with §5 open egress, exfiltratable. The default now (a) closes the keychain via a **mach-service deny** because the file-read deny is irrelevant to the `securityd` access path, (b) inverts the home-tree read posture to **deny-then-allow** so a NEW credential file added next month is denied by default, and (c) denies cross-project source to match the WORKSPACE-SCHEMA read graph.

> **§2.6 renders this template from the RESOLVED `containment_profile` block (§2.5a), not from `node_address` alone.** Every `<…>` is a substituted, realpath-canonicalized (§2.4) parameter; `extra_read_denies` / `extra_write_roots` / the L1-god-view read-open override come from the resolved block. The template below is the DEFAULT column for an L2–L5 node on the primary machine.

```scheme
(version 1)
(allow default)                          ; network + system-lib + /etc reads open by default

;; --- WRITE JAIL (verified strong; deny-all-then-allow-list) ---
(deny file-write*)
(allow file-write*
  (subpath "<WORKROOT>")                 ; node's physical L{n}/ workspace, realpath-canonicalized
  (subpath "<TMPDIR>")                   ; per-session CLAUDE_CODE_TMPDIR, realpath-canonicalized
  (subpath "<CONFIG>")                   ; CLAUDE_CONFIG_DIR — CC's own lock/state writes (token relocated OUT per §3.2 option a; else add a write+read deny on the token literal)
  (subpath "<HOME>/.claude")             ; pending §8.1 boot test: CC session logs/history (drop if boot proves it unused)
  (literal "/dev/null") (literal "/dev/stdout") (literal "/dev/stderr")
  (regex #"^/dev/tty"))
;; Dep-cache writes are kept INSIDE <WORKROOT> by env redirection (below), so no extra write-root needed.

;; --- KEYCHAIN: mach-service deny (the file-read deny does NOT protect it — securityd is a mach service) ---
(deny mach-lookup
  (global-name "com.apple.SecurityServer")
  (global-name "com.apple.securityd"))   ; GATED on §8.1 gate 1: if CC itself needs securityd to boot,
                                         ; the HELPER-UID kernel wall becomes the keychain floor instead (§3.3)

;; --- READ DENY: secrets (broad named set — covers the credential stores the review found readable) ---
;; NOTE: this named set + the pattern-globs below + <READ_DENY_ROOT> are the v1 default. The STRONGEST
;; form is a full inversion — (deny file-read* (subpath "<HOME>")) then allow-list {harness repo, role/
;; design docs, <CONFIG>-minus-token} — so a NEW ~/.something-token next month is denied by default.
;; The inversion is the `invert_home_reads` knob (§2.5a); v1 default ships the broad named set
;; because a blanket $HOME read-deny risks blocking unforeseen legit reads (e.g. ~/.gitconfig, ~/.cache).
(deny file-read*
  ;; home-tree credential stores (well beyond the old four dirs):
  (subpath "<HOME>/.ssh")               ; NOTE: blocks known_hosts → see option (b) narrowed-key deny below
  (subpath "<HOME>/.aws")               ; NOTE: blocks ~/.aws/config (non-secret) too — named limitation (§1.4)
  (subpath "<HOME>/.gnupg")
  (subpath "<HOME>/Library/Keychains")
  (subpath "<HOME>/.config/gh") (subpath "<HOME>/.config/gcloud")
  (subpath "<HOME>/.kube") (subpath "<HOME>/.docker")
  (subpath "<HOME>/.codex") (subpath "<HOME>/.gemini")
  (literal "<HOME>/.netrc") (literal "<HOME>/.npmrc") (literal "<HOME>/.pypirc")
  (literal "<HOME>/.git-credentials") (literal "<HOME>/.claude.json")
  (literal "<HOME>/.claude/.credentials.json")
  (literal "<HOME>/.zsh_history") (literal "<HOME>/.bash_history")
  (literal "<CONFIG>/.oauth_token")     ; single-file deny — see §3 (relocate preferred)
  ;; <EXTRA_READ_DENIES> — list-valued knob (§2.5a) renders additional secret paths here
  )

;; --- READ DENY: cross-project source, matching the WORKSPACE-SCHEMA read graph for L2–L5 ---
;; Deny-read everything outside the node's allowed read-set; the read-set is the SAME pure-function-of-address
;; the F34 visibility graph computes. Rendered per §2.6 as the complement of {own subtree, sibling published
;; contracts, parent chain, role/design docs, <CONFIG> minus token}. (L1/optimizer-L1 god-view: this whole
;; block is omitted — explicit read-everything exception, §2.5b.)
(deny file-read* (subpath "<READ_DENY_ROOT>"))   ; cousins / other projects / other-subtrees, per address

;; --- READ DENY: secret-pattern files anywhere (the sibling-.env guarantee, §1.3) ---
(deny file-read*
  (regex #"/\.env($|\.)")               ; **/.env, **/.env.*
  (regex #"/(credentials|secrets)[^/]*$")
  (regex #"\.pem$"))
;; ...then re-allow the agent's OWN workspace secret-pattern files (seatbelt = last-match-wins, so this
;; un-denies the agent's own .env without un-denying siblings'). This is what scopes the deny to
;; "outside WORKROOT" — WITHOUT it the agent cannot read its own .env/.pem and a real build breaks.
(allow file-read* (subpath "<WORKROOT>"))
```

**Tool-cache redirection (set at the chokepoint BEFORE launch — part of the default, not an afterthought).** So per-user package caches land INSIDE the jail instead of hard-failing:

```
NPM_CONFIG_CACHE=$WORKROOT/.cache/npm     PIP_CACHE_DIR=$WORKROOT/.cache/pip
GOMODCACHE=$WORKROOT/.cache/go            GOCACHE=$WORKROOT/.cache/gobuild
CARGO_HOME=$WORKROOT/.cargo               YARN_CACHE_FOLDER=$WORKROOT/.cache/yarn
NUGET_PACKAGES=$WORKROOT/.nuget
```

VERIFIED: `npm install --cache $WORKROOT/.npmcache` and `PIP_CACHE_DIR=$WORKROOT/…` both succeed RC=0 under the identical jail; the unredirected `npm install`/`go mod`/`cargo` all hard-fail. **Trade-off:** per-node caches lose cross-node sharing (slower cold installs) — acceptable for v1; a shared read-only cache mount is a later optimization.

- **Keychain (mach):** the `(deny mach-lookup …)` is the real keychain control. **VERIFIED** the old file-read deny was bypassable: under it, `security dump-keychain` enumerated 54 login-keychain items and `find-internet-password`/`find-generic-password` ran exit 0. The mach-deny is **gated on §8.1 gate 1** — if the pinned CC needs `securityd` for its own OAuth/keychain auth at boot, the mach-deny can't ship globally and the **HELPER-UID kernel wall (which covers the keychain by file ownership) becomes the keychain floor**, not the seatbelt.
- **SSH read — pick per knob (named decision, not a silent break):** the default denies all of `~/.ssh` (option a, accepted v1 break of `git+ssh` dep fetches; use HTTPS deps). If SSH-based fetch is a real need, swap the `~/.ssh` subpath deny for the narrowed key-material deny (option b): `(deny file-read* (regex #"^<HOME>/\.ssh/(id_|.*_key|identity)"))`, leaving `known_hosts`/`config` readable.
- **Network:** intentionally **no `(deny network*)`** clause — search/web/installs keep working (constraint 3; §5).
- **Reads otherwise OPEN** — role docs (`operational/L{1-5}/role.md`), design docs (`design/*.md`), the rest of `.cc-pinned/config`, the pinned binary, `/etc`, system libs all readable so role resolution and read-only harness docs work (VERIFIED: denied-secret read failed *while* allowed-workspace + role-doc reads succeeded under the same profile). The cross-project read-deny is the complement that closes the §5 exfil surface to the agent's own readable set.
- **`<WORKROOT>`** = the node's own subtree only (`project-{name}/L3/{area}/L4/{workstream}/L5/{task}/`, or the coordinator's owned subtree). Siblings/parent/cousins/L1-tree/`harnessd/`/`design/`/`~` are all write-DENY by virtue of the global `(deny file-write*)`.

### 2.4 HARD implementation requirement — realpath canonicalization (the #1 silent-hole risk)

> **Seatbelt matches the RESOLVED REAL PATH, not the symlink path. VERIFIED both directions:**
> - A `(deny file-read* (subpath "/tmp/secretdir"))` rule **silently failed** — the secret leaked, exit 0 — because `/tmp` is a symlink to `/private/tmp`. The same rule against the realpath `/private/tmp/secretdir` correctly denied it (exit 1).
> - Symmetrically, an `(allow file-write*)` rule written with a `/tmp` logical path **silently over-denied** a legitimate workspace write.

**Consequence (build requirement):** the spawn chokepoint MUST canonicalize **every** path it templates into the profile — `<WORKROOT>`, `<TMPDIR>`, every secret-deny path — with `realpath` / `pwd -P` **before** substitution. The traps are `/tmp` (→ `/private/tmp`) and `/var` (→ `/private/var`) used as build scratch. Node workspaces under `~/...` are typically not symlinked, so the workspace-allow is usually fine — but the rule is **canonicalize unconditionally**, because a single un-canonicalized secret path is a silent leak. This is the single most important detail for getting the profile right.

### 2.5 The configurable profile — the input surface (the knobs are WIRED, not just asserted)

The first draft asserted configurability but never gave the knobs an input: §2.6 derived the whole profile from `node_address` alone, so changing a knob meant editing the template — a code change, violating constraint 2 ("tunable at the start of each build/process"). Fixed below: a config-time block the chokepoint reads to RESOLVE the profile, plus an explicit two-layer scope (machine baseline vs per-spawn override) with a precedence rule.

#### 2.5a The `containment_profile` config block (the named input the chokepoint resolves)

This rides the **same config-time surface the E31/E32 model-pin already uses** (DAEMON §6.2 STEP 2 reads `level_config`; model+runtime is config-time per E31, DAEMON line 962). Two layers:

**MACHINE PROFILE** — set ONCE per host at install (`primary` | `dedicated`). Supplies the baseline / floor. The RELAX delta lives here only.

```
machine_profile: primary            # or: dedicated
machine_floor:                      # the denies a per-spawn override may NOT remove (primary box)
  secret_read_denies: [<the §2.3 base secret set>]
  cross_project_read_deny: true
  network_egress: open              # v1 open; see §5
```

**PER-SPAWN `containment_profile`** — set by the parent/L1 at the chokepoint, carried in `level_config`. Resolved into the rendered `.sb`:

```
containment_profile:
  write_roots:        [<extra paths beyond WORKROOT+TMPDIR+CONFIG>]   # additive only
  extra_read_denies:  [<additional secret paths, e.g. a project-specific token file>]   # additive only
  helper_uid:         false      # true → add the kernel cross-UID read-wall (one-time setup)
  deny_network:       false      # true → add (deny network*) + outbound allowlist (§5)
  escalate_to_vm:     false      # RESERVED/inert in v1 (no VM tier) — see fallback below
  tighten_reads:      false      # true → full cross-project read-jail even on a dedicated box
  invert_home_reads:  false      # true → deny ALL of $HOME then allow-list (new credential files denied by default, §2.3)
```

**Resolution order (stated, so §2.5/§2.6 no longer contradict):**
`machine baseline (primary|dedicated) → per-spawn override → rendered .sb`. **Absent fields fall to the DEFAULT column** (§2.5c). §2.6 renders the template FROM this resolved block, not from `node_address` alone.

#### 2.5b Precedence — override can TIGHTEN, never RELAX below the machine floor (monotonic)

TIGHTEN (per-spawn, this-build lifetime: "this build ingests untrusted input") and RELAX (host-global, machine lifetime: "the dedicated box is trusted") are **different scopes** and the first draft collapsed them.

- **RELAX lives ONLY in the machine profile** (`machine_profile: dedicated` strips the home-secret + cross-project denies for EVERY spawn on the box). The operator sets it once at install.
- **A per-spawn `containment_profile` can only ADD denies / narrow roots — never remove a machine-floor deny.** Rule: `resolved_denies = machine_floor.denies ∪ override.extra_denies`; `override` cannot subtract from `machine_floor`. This closes the safety hole where a per-build setting could silently strip the machine's secret-denies.
- **Conflict resolution (per-spawn TIGHTEN on a RELAXED machine):** the per-spawn TIGHTEN wins *upward* (more denies) — it re-adds cross-project/secret denies for that one node even on a dedicated box. It can never win *downward*.
- **god-view (L1 / optimizer-L1, §2.5b-exception):** the read-everything exception is set by node ROLE at the address layer (L1 is god-view per WORKSPACE-SCHEMA lines 54-59), NOT by a per-spawn flag — so an injected non-L1 node cannot grant itself god-view.

#### 2.5c The knob table (default / tighten / relax) — now backed by §2.5a fields

| Knob (field) | DEFAULT (primary box) | TIGHTEN (per-spawn override, higher-stakes / untrusted input) | RELAX (machine_profile: dedicated) |
|---|---|---|---|
| **`write_roots`** | WORKROOT + `CLAUDE_CODE_TMPDIR` + `CONFIG` (+ redirected caches) | drop `CONFIG`/scratch to WORKROOT-only | add a shared output dir, or (dedicated) drop to `(allow file-write*)` |
| **`secret_read_denies` + `extra_read_denies`** | the §2.3 broad secret set; **`extra_read_denies` adds project-specific secrets without a code change** | also keep on the dedicated box | drop the home-secret denies (machine is the boundary) |
| **`cross_project_read_deny` / `tighten_reads`** | **ON by default** (matches WORKSPACE-SCHEMA read graph) | stays on | OFF on dedicated box unless `tighten_reads` re-adds it per-spawn |
| **`deny_network`** | off (open, §5) | **on** → `(deny network*)` + outbound allowlist | off |
| **`helper_uid`** | off (seatbelt-only) | on (add kernel cross-UID read-wall — pay one-time setup) | off |
| **`escalate_to_vm`** | off (RESERVED/inert in v1) | flag set, but **no VM tier exists in v1** → fallback below | off (VM unnecessary) |

**`escalate_to_vm` is a RESERVED/inert knob in v1** (matching the §8 ledger: the VM tier is NOT BUILT). Its named trigger is "a build ingests untrusted external input on the primary machine." **v1 fallback when the flag is set:** the chokepoint does NOT silently provide no extra containment — instead it applies the **maximal seatbelt TIGHTEN** (WORKROOT-only writes + full cross-project read-deny + `(deny network*)` + `helper_uid: on`) and journals the residual risk in `containment_posture`. The flag becomes live when Candidate C is built.

The default is "not too tight, not too lenient": all writes jailed to the node + scratch + its own config/caches, the broad secret set AND cross-project source unreadable (matching the architecture's own read graph), network + tools open. Tightening adds egress control + the kernel UID wall + (eventually) the VM; relaxing happens at the MACHINE layer on the trusted dedicated box.

### 2.6 Profile is a TEMPLATE rendered per-spawn from the one-spine address

The profile is **not a hand-curated permissions file**. The chokepoint renders it from TWO inputs — the one-spine address (for the path-derived roots) AND the resolved `containment_profile` block (§2.5a, for the knob values):

1. **Resolve** the `containment_profile`: `machine baseline → per-spawn override → resolved block` (§2.5a/§2.5b). Absent fields fall to the DEFAULT column.
2. **Realpath-canonicalize** the node workspace → `<WORKROOT>` and every templated path (§2.4).
3. Substitute (via `sandbox -D` params, VERIFIED to work) `<WORKROOT>`, `<TMPDIR>`, `<HOME>`, `<CONFIG>`, plus the resolved knob values: `<EXTRA_READ_DENIES>` from `extra_read_denies`, the extra `write_roots`, the conditional `(deny mach-lookup …)` / `(deny network*)` clauses.
4. Derive `<READ_DENY_ROOT>` (cross-project) and the secret base set from the **same path-scoping** the F34 visibility graph already computes (WORKSPACE-SCHEMA line 74 + the read table lines 63-72): the read/write roots are a pure function of the one-spine address. So the **path-derived** roots come from the address and the **policy knobs** come from the resolved config block — neither is a hand-edited permissions file, and the two together have no drift.

This is the concrete upgrade of WORKSPACE-SCHEMA line 74's "filesystem-level ACLs are an available hardening" into the **stated enforcement mechanism** — now matching the read table (lines 63-72), not just the write-scoping, for L2–L5 nodes.

### 2.7 The L5 / Codex leg — do NOT double-wrap

The L5 runtime (DAEMON §6.3) is `codex-cli 0.128.0`, which **ships its own Apple-seatbelt sandbox natively** (its `workspace-write` mode *is* a seatbelt policy). The current shell alias is `codex --dangerously-bypass-approvals-and-sandbox` — i.e. the native containment is currently **disabled**.

- **Fix:** for harness-spawned Codex, **drop the bypass flag** and use Codex's native seatbelt confined to the node workspace. Do **not** wrap it in a second external `sandbox-exec`.
- Same containment *philosophy* (write-jail to the node workspace), runtime-native *mechanism*.
- This is the **Codex-adapter security fill** owed by the L4+L5 Codex audit (DAEMON §6.3 is currently underspecified for containment). Flagged here so it isn't dropped.

---

## 3. Secret protection

### 3.1 The OAuth token — where it lives, how it reaches the agent

- **How it reaches the agent (clean path):** env-injected. The daemon's isolation env (DAEMON §6.2 lines 936-937) reads the token via a **token-file / `_FILE_DESCRIPTOR`** (`$(cat …)`), exporting it as `CLAUDE_CODE_OAUTH_TOKEN`, so **the literal credential never lands in the pane or the transcript**. The launcher comment is explicit: "export `CLAUDE_CODE_OAUTH_TOKEN` in the environment before calling this (don't bake it in)."
- **The on-disk tension (load-bearing, VERIFIED):** a `0600` copy of the token **exists on disk** at `.cc-pinned/config/.oauth_token`, and that file sits **inside** `CLAUDE_CONFIG_DIR` — the very directory the agent must read for clean-config boot. So "the token lives outside the jail's read scope" is **NOT true as laid out today**: the env-injected path is clean, but the on-disk file is reachable if the read scope includes the whole config dir.

### 3.2 Resolution (pick one; both are in-scope for the secret-protection fill)

> **Interaction with the now-WRITABLE config dir (§2.3):** because the §2.3 profile must make `CLAUDE_CONFIG_DIR` **writable** (CC writes its own lock/state there or the boot bricks), a token left inside a writable config dir could be read OR rewritten by the agent. So **option (a) relocate is now the preferred default** — moving the token OUT of the writable config dir is the clean separation. If (b) is used, the single-file read-deny must hold even though the surrounding dir is writable (the agent can write config but the literal token path stays read-denied AND ideally write-denied — add `(deny file-write* (literal "<CONFIG>/.oauth_token"))` if the file remains in place).

- **(a) Relocate** `.oauth_token` **OUT of `CLAUDE_CONFIG_DIR`** to a path above the jail's read+write root (cleanest — the agent reads/writes `config/` but the token isn't in it), **or**
- **(b) Single-file read-deny** `(deny file-read* (literal "<CONFIG>/.oauth_token"))` (+ the write-deny above) while allowing the rest of `config/` — seatbelt subpath/literal deny supports this (VERIFIED the deny-specific-file-while-allowing-siblings pattern works), and so does a helper-UID ACL. This is the clause already shown in §2.3.

> **Open question gating (b) → must be verified in H40 before relying on disk-deny:** does the pinned CC consume the token from the **env var alone** at spawn, or does it **re-read `config/.oauth_token` from disk** during the session? If it re-reads from disk, an env-only injection won't suffice and the file cannot simply be removed — a read-deny would break auth. **Empirical check belongs in the H40 vanilla-boot test.** Until then, prefer **(a) relocate** as the safer default (the binary's documented path is the env var).

### 3.3 The scrubbed spawn env — no inherited secret env vars

> **Correction (wiring honesty):** DAEMON §6.2 lines 935-938 specify a **named isolation-env set** (`CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_OAUTH_TOKEN` via token-file, two disable flags) — it does **NOT** contain an `env -i` clean-slate clear. A grep of DAEMON for `env -i` returns zero hits. So the clean-slate scrub this section relies on is a **SECURITY-OWNED ADDITION**, not a pre-existing seat being merely wired. This matters: if the chokepoint sets only the named vars ON TOP OF the daemon's inherited environment (which on the primary box carries the user's shell secrets), inherited API keys DO leak into the agent. The "no inherited secret env vars" guarantee rests on `env -i` being actively added.

- **SECURITY UPGRADES DAEMON §6.2's named isolation-env set to an `env -i` clean-slate rebuild + named allowlist.** **VERIFIED:** under `env -i` a `FAKE_SECRET` came back empty, so the rebuilt env carries **only** the needed vars (`CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CODE_TMPDIR`, the cache-redirection vars from §2.3, the disable-autoupdate/nonessential-traffic flags) — no inherited API keys, other-project secrets, or stray credentials. **OWED back-edit:** add `env -i` explicitly to DAEMON §6.2's isolation-env line, or the chokepoint owner will implement the named-set-only version and the scrub silently won't happen. Owning increment: the **spawn-chokepoint adapter** (same as the token read-deny).
- **`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`** appears in the binary strings (PINNED-CC.md) but its behavior is **NOT verified** — name it and set it so the token var is **not re-inherited by CC's own child processes** (Bash-run tools, dep installers) beyond the binary itself. **Commissioning gate owed (§8.1 gate 5):** empirically confirm it removes `CLAUDE_CODE_OAUTH_TOKEN` from a child `Bash` process (have the agent run `env | grep OAUTH` and assert empty). **If the flag is a no-op or misnamed on 2.1.152, every `Bash(curl …)` inherits the token and can exfiltrate it over the open network (§5)** — in that case the token-in-child-env path is an **accepted risk listed in §8 with its own trigger**, not silently assumed closed.

**Net secret-protection story:** token is **env-injected, not readable-from-disk-by-the-agent** (relocate or single-file deny); the inheritable env is **scrubbed clean** (`env -i` clean-slate, SECURITY-owned; subprocess-scrub flag pending §8.1 gate 5); role docs + read-only harness docs **stay readable** (verified compatible with deny-specific-secrets). `~/.ssh` key material covered by the §2.3 read-deny; **the keychain is covered by the §2.3 mach-service deny (NOT the file-read deny, which the escape-path review proved irrelevant) and, when `HELPER-UID` is on, by kernel file-ownership.**

> **Residual same-UID exposure (accepted-with-trigger, §8):** a same-UID seatbelt does NOT isolate the process-table/argv view. `env -i` scrubs the CHILD's OWN env but gives zero protection against this agent READING another same-UID process's secret-bearing argv (e.g. a tool invoked `--token=…` on a sibling agent's pane, visible via `ps eww`) or the user's other processes. A live `ps eww` scan returned no full-env hits this run (macOS gates full-env visibility cross-process), but secret-bearing **argv** remains same-UID-visible. This is exactly the gap the **`HELPER-UID` (per-node UID) knob** closes and the same-UID seatbelt structurally cannot — framed as accepted-with-trigger, not implicitly covered by `env -i`.

> **DEFER-with-trigger — full env-scrub beyond the jail:** scrubbing *every* potentially-sensitive var from the whole process environment beyond the token + the named set is **deferred**. Trigger to revisit: a measured leak of a non-OAuth secret into an agent process, or the move to handling untrusted external input. v1 ships `env -i` + the OAuth-only injection + the subprocess-scrub flag; it does not attempt an exhaustive env allowlist.

---

## 4. Permission posture — a named decision checked at spawn

### 4.1 The posture

- **Auth:** OAuth-token (subscription) via the env injection above.
- **Role:** `--system-prompt-file <operational/L{n}/role.md>` (H40-blessed primary). This replaces base block 2, keeps the 57-char identity line, and keeps the **default 24-tool SWE set** incl. search/web/Bash/Edit/Write. **VERIFIED interactive + OAuth-compatible by H40.**
- **Permissions:** **skip-permissions inside the jail** — the permission-bypass mode flag (the `--dangerously-skip-permissions` / `bypassPermissions` mode) so the unattended session auto-approves its own tool calls.
- **Tools:** **full default set incl. search**. NOT `allowedTools`-restricted in v1.
- **Containment, not capability, bounds the blast radius.** Auto-approval is safe **only because the seatbelt jail is the structural bound.** If the jail is ever disabled (the relax knob on the dedicated box), the auto-approve posture must be **re-evaluated together with it**.

### 4.2 `--bare` is REJECTED (do not "simplify" toward it)

H40 explicitly ruled out `--bare` (H40-FINDINGS §3/TL;DR rank 4): it strips to a 3-tool set `[Bash, Edit, Read]` **and** reads auth strictly from `ANTHROPIC_API_KEY`, **never OAuth/keychain**. It breaks both the OAuth-only subscription-token spawn and the full-tools-incl-search requirement. **Skip-permissions must be implemented WITHOUT `--bare`.** Recorded so a future maintainer doesn't regress toward it.

### 4.3 Posture is asserted + journaled at spawn (mirror the OAuth/model checks)

The corpus already trace-checks spawn-time invariants (TRANSPORTS §5.2: every child's `model_used == configured` else an L1 spawn-failure escalation must exist; the E32 model-pin check in DAEMON §6.3). SECURITY.md mirrors this: at the DAEMON §6.1/§6.2 chokepoint, **assert and journal a named "containment posture" record** alongside the OAuth-only assertion:

```
containment_posture := {
  sandbox_profile_id/hash : <hash of the rendered .sb>,
  machine_profile         : primary | dedicated,            # the resolved baseline (§2.5a)
  skip_permissions        : on,
  tools                   : full-incl-search,
  network                 : open-v1 | egress-denied,         # deny_network knob
  write_root              : <node-workspace realpath>,
  write_roots_extra       : [<resolved extra paths>],
  secret_read_scope       : injected-env-only (token file denied/relocated),
  cross_project_read_deny : on | off,                        # default on for L2–L5 (§2.5c)
  extra_read_denies       : [<resolved per-build secret paths>],
  keychain_floor          : mach-deny | helper-uid | NONE,   # NONE flags an open keychain (§8.1 gate 1)
  subprocess_token_scrub  : verified | UNVERIFIED | failed-accepted-risk,   # §8.1 gate 5
  helper_uid              : off | on,
  escalate_to_vm          : off | on (reserved-v1: applies maximal-tighten fallback, §2.5c)
}
```

This makes the posture **auditable the same way OAuth-only is, and revisitable** (constraint 4: skip-permissions and full-tools are modifiable later). The `keychain_floor` and `subprocess_token_scrub` fields make the two review-surfaced holes **journaled and greppable** — a `keychain_floor: NONE` or `subprocess_token_scrub: failed-accepted-risk` is an auditable accepted-risk, not a silent gap.

> **Open item (spawn-chokepoint owner):** the **exact** permission-bypass flag spelling for the pinned 2.1.152 binary was not re-verified in H40 (H40 confirmed `--system-prompt-file`, `--append`, `--bare`, `--agents`). Confirm the precise flag / `settings.json` permission-mode value against `--help` and confirm it **composes with `--system-prompt-file` + OAuth**, the same way H40 confirmed the others.

---

## 5. Network / search posture — OPEN in v1, egress-control DEFERRED-with-trigger

- **v1 posture: OPEN.** The write-jail + secret-deny profile leaves **network egress fully open** — VERIFIED: with no `(deny network*)` clause, search/web/dep-installs all keep working under the jail with zero extra config. This is required by constraint 3 (agents keep web/search/installs).
- **DEFERRED-with-trigger.** Egress-control is a **single profile delta, no architecture change**: add `(deny network*)` + an allowlist of `(allow network-outbound (remote ip "…"))` entries. It is **not built in v1**.
- **Re-arm triggers (named):**
  - A build that **ingests untrusted external input** (scraped / attacker-controlled data) — pair with `ESCALATE-TO-VM` or the TIGHTEN read-deny knob.
  - Any future run on a **shared / hostile network**.
  - **NOTE:** moving to the dedicated machine is **NOT** a trigger to add egress control — that move **relaxes** (constraint 1). The dedicated box is *more* trusted, not less.
- **Accepted-risk record (honest about the exposure):** with open egress and full Bash/installs, a **prompt-injected-but-jailed** agent can exfiltrate **anything it CAN read** over the open network. The §2.3 read-jail now shrinks "what it CAN read" to the agent's **own readable set per the WORKSPACE-SCHEMA graph** — its own node, sibling published contracts, parent chain, role/design docs — and DENIES cross-project source, the broad secret set, and `.env`-pattern files by default. So the residual exfil surface is the agent's *legitimately-readable* content, not the whole disk. The jail bounds *writes*, *secret reads*, and *cross-project reads*; it does **not** bound exfiltration of the agent's own readable content. This is the accepted risk on a trusted box. Owner: the user. **Note:** if §8.1 gate 5 shows the OAuth token survives into `Bash` children, the token itself joins the exfil surface — tracked as its own accepted-with-trigger row in §8.

---

## 6. Fleet HALT — the human kill-switch (independent of L1 and the watchdog)

A single human-operated freeze/kill of the whole fleet, **independent of L1's judgment and of the watchdog's evidence gates.** It is the "third human-initiated authority" — it rides cluster ③'s human-control authority directly and needs **no evidence**; it just sets the flag the readers obey. **It is a thin operation over EXISTING seats — no new mechanism.**

### 6.1 Level 1 — FREEZE (the recommended panic button, reversible, non-destructive)

**HALT = set `paused_at` at the ROOT one-spine prefix, via the single-writer executor** (TRANSPORTS §5.3 pause-subtree primitive; the flag is DAEMON §3.2's `paused_at`).

Because the root is an ancestor of every node, the prefix check denies the whole fleet at **two already-seated enforcing readers**:

- **DAEMON §6.1 STEP 0** (lines 877-881): the chokepoint refuses to launch any child whose node-or-ancestor has `paused_at != null`. → **instantly freezes all new spawns** (and `--resume`/necro, which share the chokepoint, line 996).
- **WATCHDOG §3.4 step 0:** the recovery loop **skips prod/respawn/FAILED** for a paused node. → the watchdog stops "helpfully" respawning anything.

This is **independent of the watchdog's evidence/grace gates by design**, because the pause-gate is checked **FIRST** and short-circuits them. And it's a **non-destructive freeze** — WATCHDOG §3.4 step 0 + TRANSPORTS §5.3 make `paused_at` a "held quiet, intentional, not a stall" state; the watchdog must **not** mark a paused idle node FAILED. Freeze the whole fleet instantly and reversibly, then decide — without killing in-flight work or corrupting the ledger.

> **CRITICAL SCOPE — FREEZE is a spawn/respawn QUIESCING control, NOT an in-flight stop.** `paused_at` is obeyed by exactly two readers: the spawn chokepoint (refuses NEW spawns / `--resume` / necro) and the watchdog (skips respawn). **An agent ALREADY running in its tmux pane keeps executing tool calls, keeps writing to its workspace, and — with open egress (§5) — keeps exfiltrating; the freeze does nothing to it.** So FREEZE alone does NOT bound the blast radius of an actively-misbehaving RUNNING agent: it stops the fleet from GROWING and from self-healing, then you decide. To halt live action you must escalate to Level 2 (§6.2).
>
> **In-flight pause (the live-agent counterpart, if a non-destructive stop of a RUNNING agent is wanted):** `SIGSTOP` the pane's process group via the executor (reversible with `SIGCONT`) — this freezes a live agent's execution without killing it or desyncing the ledger, as the non-destructive complement to `paused_at`. Like the kill, it routes through the executor, never raw tmux. **v1:** `SIGSTOP`-live-pause is named here as the correct mechanism but is **gated to the same TRANSPORTS §5.3 control-surface increment** as the freeze; until built, the only in-flight stop is the destructive Level-2 CAS kill.

### 6.2 Level 2 — KILL (destructive override)

If freeze is insufficient: **CAS-guarded executor `transition` fan-out**, leaf-first, presenting `expected_owner_token` + `expected_generation` (DAEMON §4.1). This is the **same CAS that is the double-kill interlock** (TRANSPORTS §7.2 / WATCHDOG §5.4) — a second killer's stale token aborts. Only **L1 may force-reap at depth** (the emergency override, destructive, requires explicit confirmation, agent-lifecycle §135); the god-view layer is read-only and **cannot kill**.

### 6.3 The invariant

**A fleet HALT NEVER touches tmux directly.** Both freeze and kill route through the **single-writer executor**, so the ledger stays consistent. A raw `tmux kill` desyncs the ledger and is **explicitly forbidden**. The freeze is one executor op (instant, no per-node race); the kill is a CAS-fenced fan-out through the one serialization domain.

> The HALT is specified here as a **data-layer executor op addressable by root prefix**. The button rendering / GUI is deferred to the later GUI pass (TRANSPORTS §5.1/§5.3 specify data, not pixels).

---

## 7. Wiring + build-increment ownership

Each control names exactly where it attaches and which build increment owns it, so none stays homeless (the V1/Decision-A complaint that flagged this doc).

| # | Control | Attaches at | Owning build increment | Wiring note |
|---|---|---|---|---|
| **1** | Threat model + trust boundary | (design) | This doc | The adversarial framing the corpus lacked; consumed by every control below. |
| **2** | **Write-jail** (seatbelt `.sb` template + realpath canonicalization + per-node WORKROOT) | **DAEMON §6.2 in-role boot — the detached tmux PANE LAUNCH COMMAND.** The seatbelt prefix is part of the pane's launch command-line at session-create: `sandbox-exec -f <profile>.sb <env-i + binary + flags>` **IS** the detached pane's command (§7.1). Applied **after** the §6.1 CAS claim (STEP 1) + cluster-④ admission seat clears, at the §6.2 actor-open the §6.1 pseudocode calls "STEP 4". | The **spawn-chokepoint adapter** increment | Profile params resolved from the `containment_profile` block (§2.5a) AND derived from `node_address` via the same path-scoping as **WORKSPACE-SCHEMA lines 63-74** → upgrades its "available hardening" to the stated mechanism, now matching the READ table too. Same jail re-applied on resume/necro (they share the chokepoint). NOTE: "STEP 4" is a label in §6.1's pseudocode, not a heading in §6.2 — cite "§6.2 pane launch command". |
| **2b** | Sibling/parent/cousin deny-reads + secret set derivation | Same chokepoint | **Same as visibility-graph derivation** (WORKSPACE-SCHEMA path-scoping increment) | Pure function of the one-spine address; no separate permissions file. |
| **2c** | **L5/Codex** native-seatbelt fill (drop `--dangerously-bypass-…`) | DAEMON §6.3 Codex adapter | The **owed L4+L5 Codex audit** | Runtime-native containment, workspace = node dir. Do not double-wrap. |
| **3** | **Secret protection** (token relocate-or-single-file-deny + `env -i` clean-slate + keychain mach-deny + `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`) | DAEMON §6.2 isolation env | The **spawn-chokepoint adapter** increment | **NOT merely wiring an existing seat:** DAEMON §6.2 specifies a named isolation-env set with NO `env -i` (grep=0) — SECURITY UPGRADES it to an `env -i` clean-slate rebuild (SECURITY-owned addition; OWED back-edit to DAEMON §6.2, §3.3). Adds the token read-deny/relocate and the keychain **mach-service** deny (file-read deny proven irrelevant, §2.3). Disk-deny gated on the §8.1 token re-read check; subprocess-scrub gated on §8.1 gate 5. |
| **4** | **Permission posture** (skip-perms-in-jail, full tools, journaled record) | DAEMON §6.1/§6.2; asserted like the E32 model-pin check in §6.3 | The **spawn-chokepoint adapter** increment | Named, journaled `containment_posture` record (§4.3); mirrors TRANSPORTS §5.2 `model_used` trace-checker. `--bare` rejected. |
| **5** | **Network/search posture** (OPEN v1; egress-control deferred) | The seatbelt profile (omission of `(deny network*)`) | **No build** in v1 — deferred. Re-arm = profile delta in the chokepoint increment when triggered | Accepted-risk record (§5); triggers = untrusted external input / hostile network. Dedicated-machine move is NOT a trigger. |
| **6** | **Fleet HALT** (root `paused_at` freeze + CAS kill + named `SIGSTOP` live-pause) | **DAEMON §6.1 STEP 0** (paused prefix-check) + the **single-writer kill path**; verb from **TRANSPORTS §5.3** human-control; third authority per **WATCHDOG §3.4 step 0** | The **TRANSPORTS §5.3 control-surface** increment | Root-prefix freeze + CAS human-kill fan-out (mostly existing seats). **FREEZE is spawn/respawn quiescing only — it does NOT stop a RUNNING agent** (§6.1); live stop = Level-2 CAS kill, or the named `SIGSTOP`-via-executor in-flight pause (same increment, gated). GUI deferred to the GUI pass. |
| **7** | **Per-session resource envelope** (RAM/FD rlimits) | Same spawn wrapper as the seatbelt (co-located, orthogonal control) | The **SCALE §6 commissioning-run** increment | `ulimit`/`setrlimit` in the spawn wrapper; whitelist the per-session `CLAUDE_CODE_TMPDIR` as the 2nd write-root so CC scratch works. **Mechanism stated; values come from the first pressure-up run** (unmeasured today). |

### 7.1 tmux-server-ownership wiring note (the concrete seam)

`sandbox-exec` wraps the **CC command inside the pane**, NOT the shared tmux server. The concrete seam: the seatbelt prefix is part of the **pane's launch command-line at session-create** — `tmux new-session -d -s harness:<addr> 'sandbox-exec -f <profile>.sb env -i <allowlist> <binary> <flags>'`. The whole `sandbox-exec … env -i … claude …` string IS the detached pane's command. It is NOT applied via `send-keys` after attach (which would leave a pre-jail window and risk a send-keys race). So one global tmux server still manages all panes while **each agent process is independently jailed** from the instant it launches, and `env -i` isolates that pane's env. The realpath-canonicalized binary path (header / §2.3) is the one inside this command.

---

## 8. Deferred items + accepted-with-trigger risks (the discipline ledger)

Minimal-but-effective, NOT gold-plated. What's deferred, and the trigger to revisit:

| Item | Status | Trigger to revisit | Owner |
|---|---|---|---|
| **Network egress control** | DEFERRED (accepted risk on trusted box) | Untrusted external input / shared-hostile network. NOT the dedicated-machine move. | User |
| **Full env-scrub beyond the jail** | DEFERRED | A measured non-OAuth secret leak into an agent, or untrusted-input handling | Spawn-chokepoint owner |
| **`sandbox-exec` deprecation** | ACCEPTED-WITH-TRIGGER (functional on 26.4; Apple/Codex depend on it) | A macOS bump that breaks the `.sb` grammar or removes the binary → escalate to the VM tier (Candidate C) or App-Sandbox entitlements | Spawn-chokepoint owner |
| **macOS VM tier** | NOT BUILT (reserved as `ESCALATE-TO-VM` knob target) | Untrusted external input on the primary machine; or `sandbox-exec` removal | User |
| **Helper-UID read-floor** | OPTIONAL TOGGLE (off by default) | A build wants the kernel cross-UID wall in addition to seatbelt; OR §8.1 gate 1 shows CC needs `securityd` (then HELPER-UID becomes the keychain floor) | User |
| **Cross-PROJECT read confidentiality** | **ON BY DEFAULT** for L2–L5 (matches WORKSPACE-SCHEMA read graph) | RELAX is the dedicated-machine machine_profile; `tighten_reads` re-adds it per-spawn on a relaxed box | Per-build / operator |
| **Token in CC child-process env** | ACCEPTED-WITH-TRIGGER **only if §8.1 gate 5 shows `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` is a no-op** | Gate 5 fails (token survives into `Bash` children) → token exfiltratable over §5 open egress | Spawn-chokepoint owner |
| **Cross-process argv/env visibility (same-UID)** | ACCEPTED-WITH-TRIGGER (seatbelt is same-UID) | Closed only by `HELPER-UID`; revisit when secret-bearing argv on a sibling pane is a real exposure | User |
| **Keychain via `securityd` mach path** | CLOSED by mach-deny OR HELPER-UID (NOT the file-read deny) | §8.1 gate 1 forces the choice; if CC needs securityd, HELPER-UID is the floor | Spawn-chokepoint owner |
| **Per-session RAM/FD ceiling VALUES** | MECHANISM stated, values unmeasured | First SCALE §6 commissioning pressure-up run | SCALE owner |

### 8.1 Commissioning checks owed before relying on the jail (the H40-adjacent gates)

The seatbelt mechanism is verified for bash/python/cp/network in isolation, but the **214 MB interactive CC binary was not yet booted under the profile.** Before v1 relies on the jail, run (analogous to WATCHDOG §8's empirical commissioning gates):

1. **CC-boots-under-seatbelt:** does the pinned CC run a long-lived tmux session under `sandbox-exec` with the §2.3 profile? The profile already adds the `(subpath "<CONFIG>")` + `(subpath "<HOME>/.claude")` write-allows this gate predicts CC needs — **confirm they suffice** and that the `(deny mach-lookup com.apple.SecurityServer/securityd)` keychain clause does NOT break CC's own boot. **Decision fork inside this gate:** if CC needs `securityd` to authenticate at boot, the global mach-deny CANNOT ship — fall back to `HELPER-UID` as the keychain floor (kernel file-ownership covers the keychain DB) and DROP the mach-deny from the seatbelt. Also confirm no other `(allow mach-lookup …)` is needed (updater self-check etc.).
2. **Inherited-confinement check:** run a real build and confirm a child `Bash(npm install)` is write-jailed too (the inheritance property, verified for cp/python/bash, re-confirmed for CC's actual subprocess spawning).
3. **Real dep-install lands under the jail (the "not too tight" gate):** with the §2.3 cache-redirection env set, confirm a real `npm install`, `pip install`, `go mod download`, and `cargo fetch` all SUCCEED (RC=0) inside the jail — they hard-fail without redirection. This is the bar constraint 2 sets ("must not cripple agents").
4. **Token-consumption check (§3.2):** does CC read the token from the env var alone, or re-read `config/.oauth_token` from disk? Decides relocate-vs-deny.
5. **Subprocess env-scrub check (§3.3):** have the jailed agent run `env | grep OAUTH` inside a `Bash` tool call and assert empty — i.e. confirm `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` actually removes `CLAUDE_CODE_OAUTH_TOKEN` from CC's child processes on 2.1.152. **If it does NOT,** the token-in-child-env exfil path is OPEN under §5 egress → record as an accepted risk in §8 with its own trigger (do not assume closed).
6. **Keychain mach-deny holds (§2.3):** under the shipped profile, confirm `security dump-keychain` / `find-internet-password` are BLOCKED (the file-read deny alone left them exit-0; the mach-deny or the HELPER-UID wall must close them).
7. **Helper-UID + OAuth check** (only if that knob is turned on): confirm the pinned CC + env-injected OAuth works as a different UID with a writable `CLAUDE_CONFIG_DIR` and readable role/harness docs.

**Write-jail regression checklist (these VERIFIED-HELD on the box — a future profile edit must not silently re-open them).** The write jail is genuinely strong; lock it with a regression assertion so e.g. adding a broad `(allow mach-lookup)` for keychain doesn't accidentally re-enable launchd job submission:

- nested `sandbox-exec` with a permissive profile → blocked (`sandbox_apply: Operation not permitted`)
- `osascript do shell script` → inherits the sandbox, stays jailed
- LaunchAgent plist write → blocked; `launchctl submit` → no effect
- `crontab` install → blocked
- symlink-out-of-workspace write → blocked (seatbelt resolves the write target's realpath, §2.4)
- logical `/tmp/X` deny LEAKS while `/private/tmp/X` realpath deny BLOCKS → the §2.4 canonicalize-everything rule is load-bearing

---

## 9. Summary

- **Threat model:** trusted = user + harness + ledgers + role/design docs; untrusted = an agent's actions beyond its own node + anything it reads. Adversary = a buggy / prompt-injected / cd'd-away agent with auto-approved full tools. Containment, not judgment, is the bound. **The "0700-home already protects secrets" premise is FALSE on this box (home is 0750, repo root 0755) — a prerequisite to enforce, not assume.**
- **Write-jail (FORK — recommendation A):** a per-spawn `sandbox-exec` seatbelt profile, rendered from the one-spine address AND the resolved `containment_profile` block, as the **detached tmux pane's launch command** at DAEMON §6.2 in-role boot. Confines the whole process tree (verified incl. compiled binaries; write-escapes nested-sandbox/osascript/launchd/cron/symlink all verified blocked) with zero per-child work and zero host-permission surgery. Helper-UID offered as an optional read-floor toggle (and the keychain/argv floor if §8.1 gate 1 forces it); VM reserved as the escalation knob. **Realpath-canonicalize every templated path** (the #1 silent-hole). Default profile = writes jailed to node + scratch + own config + **redirected dep-caches** (so npm/go/cargo installs work); the **broad** secret set AND **cross-project source** unreadable (matching the WORKSPACE-SCHEMA read graph); keychain closed by a **mach-service deny** (not the irrelevant file-read deny); everything else (system libs, network, tools) open. Knobs WIRED via the config block: `write_roots` / `secret_read_denies`+`extra_read_denies` / `cross_project_read_deny` / `deny_network` / `helper_uid` / `escalate_to_vm` (reserved).
- **Secrets:** token env-injected (never on the pane/transcript); the on-disk `config/.oauth_token` **must be relocated or single-file-denied** (it currently sits inside the readable config dir); **`env -i` is a SECURITY-OWNED clean-slate addition** (DAEMON §6.2 has the named set but NO `env -i` — owed back-edit); subprocess-scrub flag is **unverified** (§8.1 gate 5) and its failure is a named accepted risk; **the keychain is closed by the mach-service deny / helper-UID, NOT the file-read deny which the review proved bypassable**; role/design reads stay open.
- **Permission posture:** OAuth + `--system-prompt-file` role + skip-permissions + full tools incl. search, journaled as a named `containment_posture` record. `--bare` rejected.
- **Network:** OPEN in v1; egress-control deferred-with-trigger (one profile delta). Exfil surface narrowed by the cross-project read-jail to the agent's own readable set.
- **Fleet HALT:** root `paused_at` freeze (reversible, two existing readers obey) + CAS human-kill fan-out, all through the single-writer — never raw tmux. Independent of L1 and the watchdog. **FREEZE is spawn/respawn quiescing only; a RUNNING agent needs the Level-2 kill or the named `SIGSTOP` live-pause.**

**Forks for user review:**
1. **Write-jail mechanism (§2.2)** — RECOMMEND seatbelt-as-default, helper-UID-as-optional-toggle, VM-as-escalation-knob. Real tradeoff sharpened by the escape-path review: seatbelt's deprecation + same-UID realpath fragility + **its structural inability to cover the keychain (mach path) and same-UID argv** vs helper-user's invasive-but-kernel-strong read-wall that covers all three. User decides whether `HELPER-UID` is on from day one; **§8.1 gate 1 may force it as the keychain floor regardless** (if CC needs `securityd` to boot, the global mach-deny can't ship).
2. **OAuth token on disk (§3.2)** — relocate the file out of `CLAUDE_CONFIG_DIR` (safer default) **vs** single-file read-deny. Gated on the §8.1 check of whether CC re-reads the token from disk.

**What wires where (the one-liner):** every control attaches at the **DAEMON §6.1/§6.2 spawn chokepoint** (write-jail = the §6.2 detached-pane launch command `sandbox-exec -f … env -i … <binary>`; secret-scrub + posture-assertion ride the isolation env — `env -i` itself is a SECURITY-owned upgrade to DAEMON §6.2, not an inherited seat) **except** the fleet-HALT, which rides **TRANSPORTS §5.3** (root `paused_at` + CAS kill + named `SIGSTOP`) read by **DAEMON §6.1 STEP 0** and **WATCHDOG §3.4 step 0**, and the **resource envelope**, which co-locates in the spawn wrapper but is owned by **SCALE §6**. The write-jail + read-jail are the concrete upgrade of **WORKSPACE-SCHEMA lines 63-74** (read table + line-74 hardening).
