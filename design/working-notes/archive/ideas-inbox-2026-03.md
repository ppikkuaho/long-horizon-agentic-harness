# Ideas Inbox: AI Agent Architecture Relevance (March 2026)

Architecture-relevant ideas captured from personal notes, March 2026. Item numbers are
stable and cited from ROADMAP.md and PROPOSAL-deferred-ideas-consolidation.md.

---

## RELEVANT TO AI AGENT ARCHITECTURE DESIGN (14 items)

### 1. L1-L4 Agent Hierarchy: Escalation, Leadership, and Problem Solving
- **Summary:** Detailed notes on how an L1-L4 multi-agent hierarchy should handle escalation. When a lower-level agent (associate) hits a block, the manager should not just say "try harder" but: (a) interrogate the associate's process, (b) consider parallel approaches, (c) consult lateral experts (Codex, Gemini), (d) offer different tools, (e) correct the associate's approach. Each level needs leadership skills for managing subagents, prompt writing/design skills, knowledge of typical AI failure modes, and structured problem-solving methodologies packaged as validated skills.
- **Category:** RELEVANT -- directly about agent hierarchy design, delegation patterns, escalation protocols, and leadership skills for AI managers

### 2. L1 Pre-Work Research Team + User-Level Audit Process
- **Summary:** L1 needs its own pre-work/pre-spec research team that operates before engagement. Also proposes a user-level audit process for early system runs: a readable trace showing "L1 kicks off to L2, L2 breaks the problem, delegates to L3s, L3s delegate to L4s, L4s get stuck, ask L3, L3 does problem work, sends it back, L4s work, escalated back to L3, escalated to L2, L2 corrects course/direction." Essentially a behavioral trace of the multi-agent system.
- **Category:** RELEVANT -- directly about agent hierarchy orchestration, observability/audit patterns, and pre-work research phases in multi-agent systems

### 3. Discussive L1 Branch + "What Does a Good Answer Look Like" System
- **Summary:** Two ideas: (1) A separate system that evaluates answer quality -- given a technical question, what areas/topics does a good answer need to cover conceptually? (2) A separate L1 branch that is discussive (for problem work), using a branching discussion with an L1 copy subagent. This keeps the main context window clean and avoids earlier context influencing later questions.
- **Category:** RELEVANT -- about answer quality evaluation systems, context management via branching subagents, and keeping context windows clean through architectural patterns

### 4. Multi-Account Orchestration for LLM Providers
- **Summary:** Infrastructure need: route work across multiple provider accounts with usage-limit-aware switching (both LLM-driven and deterministic), and handle the coupling between the logged-in account and MCP/integration state so that switching accounts does not break tool integrations.
- **Category:** RELEVANT -- about infrastructure for multi-agent systems: account orchestration, account management for tool integrations

### 5. Manus Backend Lead: Single CLI Tool > Function Calling for Agents
- **Summary:** Extremely detailed post (from r/LocalLLaMA) from a former Manus backend lead arguing that a single `run(command="...")` tool with Unix-style commands outperforms a catalog of typed function calls. Key insights: (a) Unix text streams and LLM tokens share the same interface model; (b) CLI is the densest tool-use pattern in LLM training data; (c) pipe composition replaces multiple tool calls; (d) progressive `--help` discovery beats stuffing documentation into system prompts; (e) error messages should include "what to do instead" guidance; (f) two-layer architecture separating Unix execution (Layer 1) from LLM presentation (Layer 2); (g) never drop stderr; (h) overflow mode with truncation + file reference for large outputs.
- **Links:** https://www.reddit.com/r/LocalLLaMA/comments/1rrisqn/ | https://github.com/epiral/pinix | https://github.com/epiral/agent-clip
- **Category:** RELEVANT -- directly about agent tool interface design, Unix-inspired agent architecture, progressive discovery patterns, two-layer execution/presentation architecture

### 6. Effective Harnesses for Long-Running Agents (Anthropic Engineering)
- **Summary:** Anthropic's engineering blog post on building harnesses for agents that work across multiple context windows. Key patterns: (a) initializer agent sets up environment + progress tracking; (b) coding agent works on one feature at a time with incremental progress; (c) feature list in JSON with status tracking; (d) git commits + progress files for session recovery; (e) startup protocol: check working directory, read progress, select next task; (f) browser automation for end-to-end testing.
- **Links:** https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- **Link content:** Detailed guide on two-part architecture (initializer + coding agent), feature lists, progress tracking, testing tools, and startup protocols for multi-session agents.
- **Category:** RELEVANT -- directly about long-running agent architecture, session management, progress tracking, and harness design

### 7. Get Physics Done (GDP) -- Agentic Research Loops
- **Summary:** Open-source AI research copilot for physics. Transforms research questions into structured workflows across four phases: formulation, planning, execution, verification. Installs into Claude Code, Gemini CLI, Codex, and OpenCode as an MCP server with ~61 commands.
- **Links:** https://github.com/psi-oss/get-physics-done
- **Link content:** An MCP-based agentic research system with phased execution, task dependency management, wave-based parallelization, research memory (notation/verification consistency across 18 physics fields), artifact generation, and rigorous validation (dimensional analysis, limiting-case checks).
- **Category:** RELEVANT -- exemplar of domain-specific agentic system design with phased workflows, parallelization patterns, and MCP integration

### 8. Treat All AI Context Like a Unix File (Research Paper)
- **Summary:** Paper/discussion about treating all AI context like Unix files -- applying Unix filesystem metaphors to AI context management.
- **Links:** https://www.reddit.com/r/AgentsOfAI/comments/1rjhvc7/new_paper_treat_all_ai_context_like_a_unix_file/
- **Link content:** Could not fetch (Reddit blocked), but title indicates a paper proposing Unix file abstractions for managing AI agent context.
- **Category:** RELEVANT -- about context/workspace management patterns for AI agents, Unix-inspired architecture

### 9. Verification/Comparison Agent -- Separate Verifier Pattern
- **Summary:** Proposes a formal verification agent/bot pattern: when asking AI to create or iterate on output, use a separate verifier agent (not the executor) that compares ground truth with output, describes differences, and may not even pass judgment -- just reports differences. For visual/uneven tasks, use multiple verification passes.
- **Category:** RELEVANT -- about verification/quality patterns in multi-agent systems, separation of executor and verifier roles

### 10. Atomic Skills + Skill/Prompt Builder
- **Summary:** Codify specific atomic functions (verification, etc.) as skills. Have workflows invoke individual skills. Would work for front-end design etc. Need to build a skill/prompt builder and explain the thinking to Claude.
- **Category:** RELEVANT -- about composable skill architecture for agents, workflow design with atomic skill primitives

### 11. ReAct vs Plan-and-Execute: Architecture Behind Modern AI Agents
- **Summary:** Newsletter from "What's AI" (Louis-Francois Bouchard / Towards AI). Covers two key agent architecture patterns: ReAct (loops through thought-action-observation, good for uncertain tasks) and Plan-and-Execute (structured roadmap upfront, efficient for predictable workflows). Advanced Deep Research systems combine both. Key insight: building strong agents is about choosing the right level of structure for the uncertainty level.
- **Category:** RELEVANT -- directly about agent reasoning architectures, ReAct vs Plan-and-Execute patterns, autonomy vs workflow control

### 12. Small Accurate Transformers for Atomic Tasks
- **Summary:** Capability density is compressing fast -- the AdderBoard competition for smallest transformer with 99%+ accuracy on 10-digit addition hit 36 parameters. Implication: small specialized models could handle atomic agent tasks extremely efficiently.
- **Category:** RELEVANT -- about using small specialized models for atomic tasks within agent architectures

### 13. Agent UI/UX: "Chat Box is a Terrible Interface for AI Agents"
- **Summary:** Reddit post from r/AI_Agents arguing that single chat windows are nightmares for managing agents. Problems: lack of state visibility, context pollution, poor monitoring of background tasks. Proposes "Workspace" or "Dashboard" UI with clean separation between conversation, tools, and agent state/memory. Noted as potential UI/UX direction.
- **Category:** RELEVANT -- about workspace/dashboard design for multi-agent systems, agent state visibility, monitoring patterns

### 14. Backend Layer for Claude Code Agents -- 6 Backend Primitives
- **Summary:** A backend layer providing 6 primitives that let Claude Code agents manage backend operations end-to-end.
- **Links:** https://www.reddit.com/r/ClaudeAI/comments/1rtddzb/
- **Category:** RELEVANT -- about backend infrastructure primitives for agentic systems

---

## POTENTIALLY RELEVANT (7 items)

### 15. Anthropic Claude Certified Architect -- Foundations Study Guide
- **Summary:** The Claude Certified Architect Foundations Certification Exam Guide from Anthropic.
- **Category:** POTENTIALLY RELEVANT -- covers Claude architecture knowledge that may inform agent design patterns

### 16. Claude Code Best Practice Hits GitHub Trending (15,000 stars)
- **Links:** https://www.reddit.com/r/ClaudeAI/comments/1rsyfdz/
- **Category:** POTENTIALLY RELEVANT -- best practices for Claude Code usage could inform agent development patterns

### 17. Claude Code Builds Entire Games from Single Prompt
- **Links:** https://www.reddit.com/r/ClaudeAI/comments/1rrzlw2/
- **Category:** POTENTIALLY RELEVANT -- demonstrates autonomous agent capability in game development with visual QA loop

### 18. Karpathy Auto-ML Research Repo
- **Links:** https://www.reddit.com/r/AgentsOfAI/comments/1ro490o/karpathy_just_opensourced_autoresearch_one_gpu/
- **Category:** POTENTIALLY RELEVANT -- automated ML research could inform autonomous research agent design

### 19. Arc AGI Solve Harness + Iterative Self-Improvement
- **Summary:** An ARC-AGI solve harness with iterative self-improvement capabilities.
- **Links:** https://x.com/noemon_ai/status/2029970173248049243
- **Category:** POTENTIALLY RELEVANT -- iterative self-improvement patterns for AI agents

### 20. B2B SaaS Growth Playbooks as a Claude Skill
- **Links:** https://www.reddit.com/r/ClaudeAI/comments/1rsgn90/
- **Category:** POTENTIALLY RELEVANT -- demonstrates skill packaging pattern for domain expertise

### 21. iPhone MCP Server
- **Links:** https://www.reddit.com/r/ClaudeAI/comments/1riryys/
- **Category:** POTENTIALLY RELEVANT -- MCP server for mobile device control, relevant to agent tool ecosystem
