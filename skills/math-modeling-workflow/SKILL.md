---
name: math-modeling-workflow
description: Orchestrates a mathematical-modeling project as separate Codex tasks with file-based handoffs, human decision gates, reproducibility checks, and final audit. Use when the user asks to run the complete staged workflow and explicitly allows creating independent tasks.
---

# Mathematical Modeling Workflow

This Skill is the control plane. It does not analyze the problem, implement models, draw publication figures, or write the paper.

## Roots and authority

- `SUITE_ROOT`: two directories above this file; read-only.
- `PROJECT_ROOT`: the user project directory.
- Only the controller writes `PROJECT_ROOT/.workflow/`.
- Only the team approves files in `PROJECT_ROOT/decisions/`.
- Read `../../shared/references/workflow-contract.md`, `human-decisions.md`, `ai-disclosure.md`, and `quality-principles.md` before orchestration.

## Start condition

Create independent Codex tasks only when the user explicitly requests the staged workflow and authorizes new tasks. Otherwise explain the required authorization and do not simulate separate conversations.

Initialize once:

```powershell
py -3 "<SUITE_ROOT>/scripts/init_v2_project.py" --project-root "<PROJECT_ROOT>" --contest "<CONTEST>" --year <YEAR>
```

## State machine

Run in this order:

```text
SELECTION → H0 → INTAKE → H1 → DESIGN → PROTOTYPE → H2 → COMPUTE → EVIDENCE
       → H3 → FIGURE → optional C1 → PAPER → AUDIT → H4 → COMPLETE
```

For every AI stage:

1. Validate the previous handoff and required team decision.
2. Create a new task, not a fork and not a continuation of an earlier stage task.
3. Use the same local `PROJECT_ROOT` when available; give the task one stage Skill, allowed inputs, one write directory, required outputs, and a stop condition.
4. Record its task ID in `.workflow/threads.json`.
5. Wait for completion or attention, then validate files and SHA-256 values.
6. Record the task's actual purpose, affected files, model/tool identity when available, and pending or completed human review in `.workflow/ai-usage-log.json`.
7. Update `.workflow/state.json` only after validation.

For `SELECTION`, give the new task every candidate problem and attachment, the fixed rubric, the competition time budget, and the `00-selection/` write boundary. For `INTAKE`, pass only the candidate approved at H0 and its associated attachments; a numeric ranking is not approval.

For `PAPER` (the `07-paper/` delivery stage), do not create the task until DESIGN, COMPUTE, EVIDENCE, and FIGURE have validated `PASS` handoffs and H3 has approved the claims. The new task prompt must name the target contest and year, required output formats, approved paper type or types when known, and require `math-modeling-paper` to apply both its hard writing gate and the bundled `references/paper-template-2026/INTEGRATION.md` routing contract. Explicitly instruct it to organize the paper by each subproblem's approved route, use only executed and confirmed results, auto-bind upstream tables/figures/metrics, explain rather than list results, preserve quantitative validation details, analyze limitations/sensitivity/scope, run formula-code-result-figure-text consistency checks, and polish only after those checks pass. Do not pass the adjacent source repository as a runtime dependency.

Use `scripts/workflow_control.py` for authorization, task registration, stage completion, gate advancement, and status reads. Do not edit state or task records ad hoc. The task-creation tool itself remains a Codex capability; this script records and validates its result.

```powershell
py -3 "<SUITE_ROOT>/scripts/workflow_control.py" --project-root "<PROJECT_ROOT>" authorize-tasks --value yes
py -3 "<SUITE_ROOT>/scripts/workflow_control.py" --project-root "<PROJECT_ROOT>" start-stage --stage SELECTION --thread-id "<THREAD_ID>" --host-id "<HOST_ID>"
py -3 "<SUITE_ROOT>/scripts/workflow_control.py" --project-root "<PROJECT_ROOT>" record-ai-use --stage SELECTION --tool-or-model "Codex task (configured model)" --purpose "候选赛题评估与H0材料准备" --affected-file "00-selection/选题评分.json" --human-review "等待H0团队选题"
py -3 "<SUITE_ROOT>/scripts/workflow_control.py" --project-root "<PROJECT_ROOT>" finish-stage --stage SELECTION
py -3 "<SUITE_ROOT>/scripts/workflow_control.py" --project-root "<PROJECT_ROOT>" advance-gate --gate H0
```

## Human gates

At H0, H1, H2, H3, and H4 set `status` to `WAITING_FOR_TEAM`, report the choice package, and end the turn. H0 selects the problem after the fixed weighted comparison; the controller and selection task must not choose on the team's behalf. Do not create the next task until the corresponding decision file satisfies `shared/schemas/decision.schema.json` and contains a real team approval.

The controller must never write `TEAM_APPROVED` or `TEAM_APPROVED_FOR_SUBMISSION`. It may validate a decision or record an explicit decision supplied by named team members, but may not infer consent.

## Failure routing

- Problem definition or assumptions: reopen H1 or rerun DESIGN.
- Candidate-problem evidence or viability: rerun SELECTION and reopen H0.
- Model route or metric: reopen H2.
- Implementation or numerical evidence: rerun COMPUTE.
- Claim mapping: rerun EVIDENCE or reopen H3.
- Publication figure: rerun FIGURE.
- Writing or document construction: rerun PAPER.

Create a fresh repair task with the audit findings and frozen decisions. Do not use a generic repair task that can override team choices.

## Completion

Run:

```powershell
py -3 "<SUITE_ROOT>/scripts/validate_v2_workspace.py" --project-root "<PROJECT_ROOT>" --require-complete
```

Only report complete when validation succeeds and H4 is `TEAM_APPROVED_FOR_SUBMISSION`. Generated work remains draft material until the team reviews and adapts it under the competition's current rules.
