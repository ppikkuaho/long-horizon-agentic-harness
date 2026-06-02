# Code Review Dimensions Research

Researched 2026-03-17. Sources: Google eng-practices, Microsoft Engineering Fundamentals Playbook, OWASP Secure Code Review Guide, GitHub staff engineer blog, Stack Overflow, academic systematic reviews, specialized concurrency checklists, production readiness frameworks.

---

## 1. Identified Dimensions

### 1.1 Correctness / Functionality

**What it checks:** Does the code do what it's supposed to do? Does it handle edge cases? Are there off-by-one errors, null pointer risks, incorrect boolean logic, wrong return values?

**When it matters:** Always. This is the universal baseline.

**Expertise needed:** Domain knowledge of what the code is supposed to do. Understanding of the feature/bug being addressed.

**Independence:** Fully independent dimension. The most fundamental lens.

---

### 1.2 Design / Architecture

**What it checks:** Do the abstractions make sense? Is the code in the right place in the system? Does it follow established architectural patterns? Are responsibilities properly separated? Is coupling appropriate? Does the change fit within the larger system's design direction?

**When it matters:** Always, but especially for new features, new abstractions, refactors, and anything touching core infrastructure. Less critical for small bug fixes within existing patterns.

**Expertise needed:** System-level understanding. Familiarity with the codebase's architecture, established patterns, and design philosophy. Senior/staff-level judgment.

**Independence:** Genuinely independent from correctness. Code can be correct but architecturally wrong (e.g., putting business logic in the controller layer). Partially overlaps with complexity -- bad design often manifests as complexity -- but design is about *where things go* and *how they relate*, while complexity is about *how hard things are to understand*.

---

### 1.3 Complexity / Readability / Maintainability

**What it checks:** Can another developer understand this code quickly? Are there unnecessary abstractions or over-engineering? Is the code "too clever"? Are names clear and descriptive? Is the control flow straightforward? Would the next person who touches this code be able to modify it safely?

Google's framing: "Too complex" = "can't be understood quickly by code readers" or "developers are likely to introduce bugs when they try to modify it."

**When it matters:** Always. This is the dimension that pays dividends over years.

**Expertise needed:** General engineering experience. Ability to read code as a "fresh pair of eyes." No deep domain expertise needed -- in fact, *not* being the expert is useful here, since it tests whether the code communicates on its own.

**Independence:** Partially overlaps with design (bad design causes complexity) but is distinct. Code can have good architecture yet be locally hard to read (dense expressions, poor variable names, unnecessarily compact logic). Also partially overlaps with style but is deeper -- style is about formatting conventions, complexity is about cognitive load.

**Sub-dimensions:**
- **Naming quality** -- variables, functions, classes communicate what they are/do
- **Comment quality** -- comments explain "why" not "what"; no misleading stale comments
- **Code structure** -- single responsibility, appropriate function length, logical organization

---

### 1.4 Testing

**What it checks:** Are there tests? Are they the right kind (unit/integration/e2e)? Do they actually test meaningful behavior or just achieve coverage? Would they catch regressions? Are test assertions specific enough? Are edge cases covered? Are tests themselves readable and maintainable?

**When it matters:** Always for code changes. The type and depth of testing expected varies by risk level and team norms.

**Expertise needed:** Testing methodology knowledge. Understanding of what kinds of tests are appropriate for the change. Ability to think about "what could break."

**Independence:** Genuinely independent. Code can be correct, well-designed, and readable but have no tests (or bad tests). Testing quality doesn't subsume any other dimension.

---

### 1.5 Security

**What it checks:** OWASP categories provide the comprehensive breakdown:

- **Input validation** -- injection prevention (SQL, XSS, command injection), allowlist vs blocklist, output encoding
- **Authentication & session management** -- password hashing, token security, session invalidation, MFA
- **Authorization** -- access control enforcement (server-side), IDOR prevention, privilege escalation, default-deny
- **Cryptography** -- proper algorithms, key management, random number generation
- **Sensitive data handling** -- no secrets in logs/URLs/error messages, encryption at rest/transit
- **Dependency security** -- known vulnerabilities in third-party libraries

**When it matters:** Always at a baseline level (no obvious injection, no leaked secrets). Deep security review matters for: auth flows, payment processing, data handling, API boundaries, anything exposed to untrusted input.

**Expertise needed:** Security-specific knowledge. Many security issues are invisible to general-purpose reviewers. The OWASP Top 10 provides a minimum knowledge baseline, but deep security review requires specialized training.

**Independence:** Genuinely independent. Code can be correct, well-designed, readable, and well-tested but have a critical security vulnerability. Security thinking is a distinct mental model.

---

### 1.6 Performance

**What it checks:** Algorithm efficiency (time/space complexity), unnecessary allocations, N+1 query problems, cache misses, inefficient data structures, unneeded work in hot paths, payload sizes, network round trips.

**When it matters:** Situational. Critical for: hot paths, database queries, API endpoints serving high traffic, data processing pipelines, mobile/frontend rendering. Less critical for: admin tools, one-off scripts, rarely-executed code paths.

**Expertise needed:** Performance profiling intuition. Understanding of the runtime environment (database query plans, memory models, network latency). Knowledge of what's "hot" in the system.

**Independence:** Genuinely independent. Code can be correct, secure, and readable but have O(n^2) behavior where O(n) was possible. Sometimes trades off against readability.

---

### 1.7 Concurrency / Thread Safety

**What it checks:** Race conditions, deadlocks, data races on shared mutable state, proper synchronization, atomic operations used correctly, thread-safe lazy initialization, proper locking granularity, documentation of thread-safety guarantees.

Specialized checklists exist (e.g., code-review-checklists/java-concurrency on GitHub) covering:
- Every lazily initialized field checked for thread safety
- Shared state not leaked outside critical sections
- Multiple related variables updated atomically (snapshot pattern)
- Field access protection verified even for primitives (memory visibility)

**When it matters:** Whenever code touches shared mutable state, concurrent operations, parallel processing, async patterns. Not relevant for purely single-threaded code.

**Expertise needed:** Deep concurrency knowledge. This is one of the hardest dimensions to review well -- concurrency bugs are subtle, intermittent, and often invisible in code review without specialized thinking.

**Independence:** Genuinely independent. Code can be correct in a single-threaded context but broken under concurrency. This is a specialized form of correctness, but the mental model is so different that it warrants its own dimension.

---

### 1.8 Error Handling / Resilience

**What it checks:** Are errors handled explicitly rather than swallowed? Do error messages provide useful context without leaking sensitive info? Are resources cleaned up on failure (try-finally, defer, RAII)? Is there appropriate retry logic? Circuit breakers? Graceful degradation? Timeout handling? Are failure modes documented?

**When it matters:** Always at a baseline level (no swallowed exceptions). Deep resilience review matters for: distributed systems, network calls, database operations, critical business flows.

**Expertise needed:** Experience with production systems. Understanding of how systems fail in the real world. SRE/reliability engineering perspective.

**Independence:** Partially overlaps with correctness (error handling is part of "correct behavior") but distinct in practice. A reviewer focused on "does the happy path work?" won't catch missing error handling. The resilience lens specifically asks "what happens when things go wrong?"

---

### 1.9 API Design / Interface Contracts

**What it checks:** Is the API surface clean and minimal? Are parameter types appropriate? Is naming consistent with existing APIs? Are return types/error codes well-defined? Is backward compatibility maintained? Are breaking changes properly versioned? Is the API documented? Is it ergonomic for callers?

Includes:
- REST/GraphQL compliance (proper HTTP methods, status codes)
- Request/response payload design
- Versioning strategy
- SDK/client impact of changes

**When it matters:** Whenever code defines or modifies a public interface -- API endpoints, library interfaces, module boundaries, shared contracts between services. Less relevant for internal implementation details.

**Expertise needed:** API design sense. Understanding of the consumers of the interface. Backward compatibility awareness.

**Independence:** Genuinely independent. Code can be internally well-structured but expose a confusing or brittle API. The "inside-out" vs "outside-in" thinking is different.

---

### 1.10 Data Model / Schema

**What it checks:** Is the data model normalized appropriately? Are schema migrations safe (backward-compatible, reversible)? Will the migration work on large tables without locking? Are indexes appropriate? Are column types and constraints correct? Is data integrity maintained? Are there cascade/orphan risks?

**When it matters:** Whenever the change touches database schemas, data models, storage formats, or serialization. Schema changes are high-risk because they're hard to roll back.

**Expertise needed:** Database expertise. Understanding of migration strategies, locking behavior, data integrity constraints.

**Independence:** Genuinely independent. Code logic can be correct while the underlying schema change is dangerous (e.g., adding a non-nullable column without a default to a large table).

---

### 1.11 Operational Readiness / Observability

**What it checks:** Is there adequate logging for debugging production issues? Are metrics emitted for key operations (latency, error rate, throughput -- the "Four Golden Signals")? Is distributed tracing supported? Are alerts configured with actionable thresholds? Are feature flags in place for safe rollout? Is there a rollback plan?

**When it matters:** For any change that will run in production. Critical for: new services, new endpoints, major feature launches, infrastructure changes. Less critical for: test-only changes, documentation updates.

**Expertise needed:** SRE/DevOps perspective. Understanding of production debugging workflows. Knowledge of the monitoring stack.

**Independence:** Genuinely independent. Code can be correct, well-designed, and secure but completely opaque in production. This is the "day 2 operations" lens that many reviews miss entirely.

---

### 1.12 Style / Conventions

**What it checks:** Formatting, indentation, import ordering, bracket placement, line length. Adherence to language-specific style guides and team conventions.

**When it matters:** Always, but should be mostly automated (linters, formatters). Human review of style is low-value if tooling handles it.

**Expertise needed:** Knowledge of the team's style guide. Minimal specialized expertise.

**Independence:** Independent but low-value as a distinct review dimension. Subsumable by automated tooling in most codebases. Google lists it as a dimension but notes it should be mostly handled by style guides and automated checks.

---

### 1.13 Documentation

**What it checks:** Are READMEs updated? Is API documentation current? Are inline docs (docstrings, JSDoc) present for public interfaces? Are architecture decision records (ADRs) created for significant decisions? Is the changelog updated?

**When it matters:** Whenever the change affects how users/developers interact with the system. New features, API changes, configuration changes, behavioral changes.

**Expertise needed:** Understanding of who the documentation audience is (end users? other developers? ops team?).

**Independence:** Somewhat independent. Could be considered part of "completeness" rather than a distinct lens. Google treats it as a separate dimension. In practice, it's easily forgotten unless explicitly checked.

---

### 1.14 Accessibility (a11y)

**What it checks:** WCAG compliance, semantic HTML, ARIA attributes, keyboard navigation, screen reader compatibility, color contrast, focus management, alt text for images.

**When it matters:** For any user-facing UI code. Legal requirement in many jurisdictions. Critical for public-facing products.

**Expertise needed:** Accessibility standards knowledge. Screen reader testing experience. Understanding of assistive technologies.

**Independence:** Genuinely independent. Code can be functionally correct and well-designed but completely inaccessible. Requires a distinct mental model.

---

### 1.15 Internationalization (i18n) / Localization

**What it checks:** Are strings externalized for translation? RTL layout support? Date/time/number formatting using locale-aware APIs? No hardcoded language assumptions? Text expansion accounted for in UI? Unicode handling correct?

**When it matters:** For any product serving multiple locales. Should be considered from the start -- retrofitting i18n is expensive.

**Expertise needed:** i18n best practices. Understanding of locale-specific issues (RTL, CJK text, pluralization rules).

**Independence:** Genuinely independent. Code can work perfectly in English but break in Arabic or Chinese. Distinct from accessibility though sometimes related.

---

### 1.16 Compliance / Regulatory

**What it checks:** GDPR data handling (consent, right to deletion, data minimization), HIPAA requirements, PCI-DSS for payment data, data residency requirements, audit logging, privacy impact. License compatibility of dependencies.

**When it matters:** Situational. Critical when handling personal data, health data, financial data, or operating in regulated industries. Many teams don't consider this a code review dimension at all until they get burned.

**Expertise needed:** Knowledge of applicable regulations. Legal/compliance team involvement for significant changes.

**Independence:** Genuinely independent. Code can be technically excellent but violate GDPR by logging PII without consent.

---

### 1.17 Dependency / Supply Chain

**What it checks:** Are new dependencies justified? Are they well-maintained? Do they have known vulnerabilities? Is the license compatible? Is the dependency pinned to a specific version? Is the transitive dependency tree acceptable? Could a lighter alternative work?

**When it matters:** Whenever new dependencies are added. Also relevant for dependency version upgrades.

**Expertise needed:** Understanding of the ecosystem's dependency landscape. Awareness of supply chain attack vectors.

**Independence:** Partially overlaps with security (vulnerability scanning) but is broader -- includes license risk, maintenance risk, and bloat concerns.

---

## 2. Dimension Independence Analysis

### Genuinely Independent Dimensions (distinct mental models)

1. **Correctness** -- "does it work?"
2. **Design/Architecture** -- "is it in the right place?"
3. **Testing** -- "will we know if it breaks?"
4. **Security** -- "can it be exploited?"
5. **Performance** -- "is it fast enough?"
6. **Concurrency** -- "is it safe under parallelism?"
7. **Operational Readiness** -- "can we run it in production?"
8. **API Design** -- "is the contract good for consumers?"
9. **Accessibility** -- "can everyone use it?"

### Semi-Independent (distinct but frequently overlap)

10. **Complexity/Readability** -- overlaps with design but operates at a different scale (local vs structural)
11. **Error Handling/Resilience** -- overlaps with correctness but requires a distinct "what goes wrong?" mindset
12. **Data Model/Schema** -- overlaps with design but has unique risks (migration safety, locking)
13. **i18n** -- overlaps with accessibility but targets a different user need
14. **Compliance** -- overlaps with security but adds legal/regulatory concerns

### Subsumable / Low-Independence

15. **Style** -- mostly automatable; not a distinct review lens for humans
16. **Documentation** -- important but more of a completeness check than a distinct analytical lens
17. **Dependencies** -- partially covered by security review; the non-security aspects (licensing, bloat) are a lightweight check

---

## 3. Existing Frameworks and Presets

### 3.1 Google's "What to Look For" (9 dimensions)

Google's eng-practices guide lists: Design, Functionality, Complexity, Tests, Naming, Comments, Style, Documentation, and Context (evaluating the change in the broader system). This is the most widely cited industry framework.

Notably flat -- no tiers or presets. Every review is expected to cover all dimensions.

### 3.2 Microsoft Engineering Fundamentals (2-pass approach)

Microsoft's reviewer guidance suggests two passes:
1. **Design pass** -- PR overview, user-facing changes, component interactions, architectural patterns
2. **Code quality pass** -- complexity, naming/readability, error handling, functionality (race conditions, performance, security), style, tests

This is closer to a tiered approach -- the design pass acts as a quick filter before the detailed pass.

### 3.3 OWASP Secure Code Review (security-specific framework)

Organized by threat category: input validation, authentication, authorization, cryptography, business logic, configuration, monitoring. Uses both code pattern analysis and data flow analysis as review techniques.

Not a general review framework -- specifically for the security dimension, but deeply structured within that dimension.

### 3.4 Stack Overflow's "Good Reviews Better" (3 tiers by scope)

Informal but useful framing:
- Scope correctness (is this the right change?)
- Code correctness (is the implementation right?)
- Polish (naming, style, minor improvements)

### 3.5 Tiered Approaches (observed in practice)

From multiple sources, a common pattern emerges in practice:

**Tier 1: Quick/Lightweight Review** (for small, low-risk changes)
- Correctness (does it work?)
- Readability (can I understand it?)
- Tests (are there any?)
- Style (linter passing?)

**Tier 2: Standard Review** (for typical feature work)
- All of Tier 1, plus:
- Design (does it fit the architecture?)
- Error handling
- Performance (obvious issues)
- Documentation (if user-facing)

**Tier 3: Deep Review** (for critical/high-risk changes)
- All of Tier 2, plus:
- Security (threat modeling)
- Concurrency (if applicable)
- Data model safety (if schema changes)
- Operational readiness (logging, monitoring, rollback)
- API compatibility (if public interfaces change)
- Compliance (if personal data involved)

**Tier 4: Specialist Review** (routed to specific expertise)
- Security review by security team
- Accessibility review by a11y specialist
- Performance review with profiling data
- Database review by DBA

### 3.6 Meta's Metrics-Driven Approach

Meta doesn't publish a dimension framework but uses metrics to manage review quality:
- **Eyeball Time** -- guardrail metric to prevent rubber-stamp reviews
- **Time In Review** -- total elapsed time (optimized for speed)
- Small diff sizes enforced to make thorough review practical

### 3.7 DORA Metrics (process-level, not per-review)

Used by senior engineers to evaluate the review process itself:
- Lead time for changes
- First response time
- Rework cycles
- Change failure rate

---

## 4. Key Insights

### What senior engineers actually do (vs what checklists say)

From the GitHub staff engineer blog and other practitioner sources:

1. **Skim first for intent and scope** -- understand what the change is trying to do before evaluating how
2. **Distinguish blockers from preferences** -- critical bugs vs style preferences vs "I would have done it differently"
3. **Check the "what could go wrong" path** -- error handling, edge cases, failure modes
4. **Evaluate in context of the whole system** -- not just "is this function correct?" but "does this change make the system better?"
5. **Ask questions rather than dictate** -- "Have you considered X?" rather than "Change this to X"

### Dimensions most commonly missed in practice

Based on the research, these dimensions are mentioned in frameworks but frequently skipped in real reviews:
- **Operational readiness** (logging, monitoring, alerting)
- **Data model safety** (migration risks)
- **Accessibility**
- **i18n**
- **Compliance/regulatory**
- **Concurrency** (unless the reviewer has specific expertise)

### The automation boundary

Dimensions that should be automated (not human-reviewed):
- Style/formatting (linters, formatters)
- Known vulnerability scanning (Dependabot, Snyk)
- Basic code smells (static analysis)
- Test coverage metrics (coverage tools)
- Type safety (type checkers)

Human review should focus on dimensions that require judgment, context, or adversarial thinking.

---

## 5. Sources

- [Google Engineering Practices - What to Look For](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- [Microsoft Engineering Fundamentals - Reviewer Guidance](https://microsoft.github.io/code-with-engineering-playbook/code-reviews/process-guidance/reviewer-guidance/)
- [OWASP Secure Code Review Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html)
- [GitHub Staff Engineer - How to Review Code Effectively](https://github.blog/developer-skills/github/how-to-review-code-effectively-a-github-staff-engineers-philosophy/)
- [Stack Overflow - How to Make Good Code Reviews Better](https://stackoverflow.blog/2019/09/30/how-to-make-good-code-reviews-better/)
- [Senior Engineer's Guide to Code Reviews (DEV)](https://dev.to/middleware/the-senior-engineers-guide-to-the-code-reviews-1p3b)
- [DX - Code Review Checklist](https://getdx.com/blog/code-review-checklist/)
- [Java Concurrency Code Review Checklist](https://github.com/code-review-checklists/java-concurrency)
- [Go Concurrency Code Review](https://go.dev/wiki/CodeReviewConcurrency)
- [Meta - Improving Code Review Time](https://engineering.fb.com/2022/11/16/culture/meta-code-review-time-improving/)
- [Systematic Literature Review and Taxonomy of Modern Code Review (arXiv)](https://arxiv.org/abs/2103.08777)
- [Cortex - Production Readiness Checklist](https://www.cortex.io/post/how-to-create-a-great-production-readiness-checklist)
