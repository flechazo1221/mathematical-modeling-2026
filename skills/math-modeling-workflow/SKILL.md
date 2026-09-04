---
name: math-modeling-workflow
description: Orchestrates and continuously supervises a mathematical-modeling project as separate Codex tasks with file-based handoffs, human decision gates, reproducibility checks, deviation stops, and final audit. Use when the user asks to run the complete staged workflow and explicitly allows creating independent tasks.
---

# Mathematical Modeling Workflow

This Skill is the control plane. It does not analyze the problem, implement models, draw publication figures, or write the paper.

## Roots and authority

- `SUITE_ROOT`: two directories above this file; read-only.
- `PROJECT_ROOT`: the user project directory.
- Only the controller writes `PROJECT_ROOT/.workflow/`.
- Only the team approves files in `PROJECT_ROOT/decisions/`.
- Read `../../shared/references/workflow-contract.md`, `human-decisions.md`, `ai-disclosure.md`, and `quality-principles.md` before orchestration.
- Read and apply `../process-agent-supervisor/SKILL.md` for every AI stage from dispatch through validated handoff. The controller is the supervisor; the stage task must not supervise or clear itself.

## Start condition

Create independent Codex tasks only when the user explicitly requests the staged workflow and authorizes new tasks. Otherwise explain the required authorization and do not simulate separate conversations.

Initialize once:

```powershell
py -3 "<SUITE_ROOT>/scripts/init_v2_project.py" --project-root "<PROJECT_ROOT>" --contest "<CONTEST>" --year <YEAR>
```

## State machine

Run in this order:

```text
SELECTION → H0 → INTAKE → H1 → WAITING_FOR_LITERATURE → LITERATURE
       → DESIGN → PROTOTYPE → H2 → COMPUTE → EVIDENCE → H3
       → FIGURE → optional C1 → PAPER → AUDIT → H4 → COMPLETE
```

For every AI stage:

1. Validate the previous handoff and required team decision.
2. Build the supervision baseline from the stage objective, allowed inputs, one write directory, required outputs, frozen team decisions, prohibitions, acceptance conditions, and next gate. If these conflict or are materially incomplete, do not dispatch; report `SUPERVISION: BLOCKED`.
3. Create a new task, not a fork and not a continuation of an earlier stage task.
4. Use the same local `PROJECT_ROOT` when available; give the task one stage Skill plus the complete baseline and an explicit instruction to stop and report before acting against it.
5. Record its task ID in `.workflow/threads.json`.
6. Monitor the running task with the available task wait/status mechanism. At each meaningful progress event, compare its declared plan, actions, tool output, and changed artifacts with the baseline. Inspect primary evidence when needed; do not accept the task's summary as sole proof of alignment.
7. Classify the observation as `ALIGNED`, `NEEDS_CLARIFICATION`, `DEVIATED`, or `BLOCKED` according to `process-agent-supervisor`. Stay quiet for `ALIGNED`; for `NEEDS_CLARIFICATION`, permit only reversible work while seeking a brief explanation.
8. On `DEVIATED`, interrupt the task immediately, do not start repair work, do not finish the stage or advance any downstream gate, and preserve all artifacts. Report the baseline conflict and concrete evidence using the supervisor report format, then wait for an explicit team recovery decision.
9. On normal completion, validate the handoff, files, SHA-256 values, and the final artifacts against the same baseline. A task claiming completion does not pass supervision or stage validation by itself.
10. Record the task's actual purpose, affected files, model/tool identity when available, and pending or completed human review in `.workflow/ai-usage-log.json`.
11. Update `.workflow/state.json` only after both supervision and ordinary stage validation pass.

## Continuous AI supervision

Supervision is mandatory for `SELECTION`, `INTAKE`, `DESIGN`, `PROTOTYPE`, `COMPUTE`, `EVIDENCE`, `FIGURE`, `PAPER`, and `AUDIT`. It starts before task dispatch and ends only at a validated handoff, an immediate deviation stop, or a user-requested termination.

The controller must enforce these workflow-wide invariants:

- no stage changes the selected problem, approved interpretation, model route, metrics, claims, or submission decision without the corresponding human gate;
- no task reads unapproved stage inputs or writes outside its assigned directory;
- no downstream stage consumes an unvalidated, `FAIL`, `BLOCKED`, or supervision-stopped handoff;
- no numerical, visual, or written claim is treated as approved merely because an agent produced it;
- no supervision verdict replaces reproducibility checks, domain validation, independent audit, or human approval.

Do not create a separate supervisor task unless the user explicitly asks for one. The controller retains supervision responsibility and must remain able to interrupt each stage task. If the platform cannot expose progress or interrupt a task, issue a clear stop instruction, quarantine its output from downstream use, report the limitation, and wait for the team.

For `SELECTION`, give the new task every candidate problem and attachment, the fixed rubric, the competition time budget, and the `00-selection/` write boundary. For `INTAKE`, pass only the candidate approved at H0 and its associated attachments; a numeric ranking is not approval.

After H1 is approved, advance the gate and stop at `WAITING_FOR_LITERATURE`. Tell the user to place relevant papers or reports in `PROJECT_ROOT/literature/input/`; they may use `$math-modeling-literature` for optional search and open-access download assistance. Do not create the LITERATURE task in the same turn as H1 approval. Resume only after the user returns and at least one supported literature file exists.

For `LITERATURE`, create a fresh task using only `$math-modeling-literature-reading`. Give it the approved H1 decision, original problem context, `literature/input/` as read-only user material, and `02-literature/` as its sole write directory. Require `文献阅读结果.md`, `文献清单.json`, and a `PASS` handoff. Do not start DESIGN until that handoff and all declared hashes validate.

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

At H0, H1, H2, H3, and H4 set `status` to `WAITING_FOR_TEAM`, report the choice package, and end the turn. H0 selects the problem after the fixed weighted comparison; the controller and selection task must not choose on the team's behalf. Do not create the next task until the corresponding decision file satisfies `shared/schemas/decision.schema.json` and contains a real team approval. H1 approval leads to a separate `WAITING_FOR_LITERATURE` checkpoint; this is an input pause, not another approval gate.

The controller must never write `TEAM_APPROVED` or `TEAM_APPROVED_FOR_SUBMISSION`. It may validate a decision or record an explicit decision supplied by named team members, but may not infer consent.

Continue supervision at human gates by checking that no AI task attempts to answer the team's question, rewrite the options to force a choice, or proceed while the gate is unresolved. A pending human decision is expected workflow state, not agent deviation; crossing it without approval is deviation.

## Failure routing

- Problem definition or assumptions: reopen H1 or rerun DESIGN.
- Missing, unreadable, or irrelevant user literature: remain at `WAITING_FOR_LITERATURE` or rerun LITERATURE after the user changes the source set.
- Literature-reading error or unsupported synthesis: rerun LITERATURE; do not patch the DESIGN output to hide the upstream defect.
- Candidate-problem evidence or viability: rerun SELECTION and reopen H0.
- Model route or metric: reopen H2.
- Implementation or numerical evidence: rerun COMPUTE.
- Claim mapping: rerun EVIDENCE or reopen H3.
- Publication figure: rerun FIGURE.
- Writing or document construction: rerun PAPER.

Create a fresh repair task with the audit findings and frozen decisions. Do not use a generic repair task that can override team choices.

A supervision stop precedes failure routing. Preserve the stopped task's artifacts, present recovery options, and wait for the team to choose whether to discard, inspect, or use them as read-only diagnostic evidence. Only then create a fresh, supervised repair task within the selected route.

## Completion

Run:

```powershell
py -3 "<SUITE_ROOT>/scripts/validate_v2_workspace.py" --project-root "<PROJECT_ROOT>" --require-complete
```

Only report complete when validation succeeds and H4 is `TEAM_APPROVED_FOR_SUBMISSION`. Generated work remains draft material until the team reviews and adapts it under the competition's current rules.
