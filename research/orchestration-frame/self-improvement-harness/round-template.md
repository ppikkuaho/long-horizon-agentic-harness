# Round Template

Create one `brief.md` per round using this shape.

```md
# Iteration <NN> Brief

Objective:
- <what this round is trying to improve>

Task class:
- <research|coding|debugging|design|ops|writing|other>

Relevant topology:
- <what surfaces must be mapped or validated for this task class>

Quality benchmark:
- <what "professional-quality" means for this task class under the active constraints>

Path-lock risk:
- <how this round could get trapped in the wrong basin>

Required perturbation if triggered:
- <which anti-rigidity operator should be used if the path proves too narrow>

Target artifacts:
- <path 1>
- <path 2>

Why this round exists:
- <what prior reviewer findings or structural gaps justify it>

Carry-forward required changes:
- <required change 1>
- <required change 2>

Required success for this round:
- <condition 1>
- <condition 2>

Must not regress:
- <constraint 1>
- <constraint 2>

Required reviewer evidence:
- <what reviewers must explicitly comment on>

Verification surfaces:
- <tests, sources, comparisons, runtime checks, review surfaces, or other validators that matter this round>

Out of scope:
- <what not to change this round>

Role packets:
- Builder reads: <file list>
- Reviewer 1 reads: <file list>
- Reviewer 2 reads: <file list>
```
