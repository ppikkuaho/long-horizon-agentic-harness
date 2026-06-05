# Fork Decisions — build phase (present to user at finished build)

> **Rule (user directive, 2026-06-05):** for a fork encountered during the build, unless it
> **diverges from the spec**: exercise best judgment for the most spec-faithful resolution,
> **note the decision here** (+ a RESOLVED marker in the owning doc), and **proceed — do not
> block**. Present this accumulated list to the user when the build is finished. Stop ONLY on an
> actual blocker (a genuine spec ambiguity/divergence, a test that can't go green, a missing
> dependency). This log is the "present at end" artifact.

| # | Fork | Decision | Rationale | Where recorded |
|---|---|---|---|---|
| FORK-CRC | WAL torn/corrupt-record detection (Increment 2) | **crc32 backstop** — `build_wal_record` always emits `crc32(payload)`; `load_wal` treats a crc mismatch as torn alongside the length-prefix mismatch. No `len` field in the json. | The design recommendation; closes the silently-split-record gap the length-prefix alone misses; done-test (e) requires it. (User delegated "you decide" 2026-06-05.) | IMPL-PLAN FORK-CRC RESOLVED marker; built Increment 2 |
| FORK-SEQ | global monotonic `seq` allocation (Increment 2) | **derive from WAL** — `next_seq()` = last WAL `seq` + 1 on load; the WAL is the single source of truth; no authoritative persisted counter. | The design recommendation; no separate counter that can desync from the WAL on a crash. (User delegated "you decide" 2026-06-05.) | IMPL-PLAN FORK-SEQ RESOLVED marker; built Increment 2 |
