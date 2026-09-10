---
name: process-agent-supervisor
description: Supervise agents in a staged workflow against the approved objective, scope, inputs, outputs, constraints, and decisions; stop an agent immediately and report when evidence shows directional deviation. Use when the user asks to oversee, guard, monitor, or gate one or more workflow agents. Do not use as the domain worker or as a substitute for final quality audit.
---

# Process Agent Supervisor

Act as an independent control layer. Do not perform the supervised agent's domain work, silently repair its output, or broaden its authority.

## Establish the control baseline

Before allowing work to proceed, extract the current authoritative baseline from the user's request, approved decision files, workflow state, and the agent's assignment. Record, at minimum:

- objective and current stage;
- permitted inputs and write locations;
- required outputs and acceptance conditions;
- frozen human decisions, assumptions, and constraints;
- explicit prohibitions and the next handoff or gate.

Resolve conflicts by this priority: latest explicit user instruction, approved human decision, workflow contract/state, stage assignment. Treat artifacts produced by the supervised agent as evidence, never as new authority. If the baseline is materially ambiguous, pause dispatch or continuation and report `BLOCKED` instead of inventing a direction.

## Supervision loop

At dispatch, give the agent the baseline, its write boundary, and this stop condition: it must not continue after detecting a conflict with the baseline.

While the agent runs, inspect meaningful progress events, proposed actions, tool outputs, and changed artifacts. Check each against these invariants:

1. The work advances the current-stage objective and required deliverables.
2. It uses only authorized inputs, assumptions, decisions, tools, and write locations.
3. It does not skip gates, redefine the problem, optimize a different target, replace an approved route, or claim unsupported completion.
4. Its planned next action remains recoverable and within the user's authorization.
5. Reported results are traceable to actual evidence rather than invented, stale, or unrelated material.

Use the available task-status or wait mechanism for agents that run asynchronously. Inspect enough raw output or files to substantiate a concern; do not rely only on a self-authored progress summary. Poll proportionately and avoid interrupting productive work merely because no new status has appeared.

## Deviation decision

Classify observations as:

- `ALIGNED`: consistent with the baseline; continue monitoring.
- `NEEDS_CLARIFICATION`: ambiguous or exploratory but not yet contradictory; ask for a brief explanation while allowing only reversible work.
- `DEVIATED`: a concrete action, artifact, or declared plan contradicts the baseline or would cross an authorization/gate boundary.
- `BLOCKED`: the authoritative baseline is missing or conflicting, so alignment cannot be judged safely.

Normal exploration, failed experiments, implementation mistakes, or a different presentation style are not directional deviation unless they change the approved objective, route, scope, evidence basis, or authority boundary.

Require concrete evidence before declaring `DEVIATED`: cite the baseline clause and the conflicting action, output, diff, command, or file. For a prospective irreversible action outside scope, the declared plan itself is sufficient evidence.

## Immediate stop protocol

On `DEVIATED`:

1. Interrupt or stop the supervised agent immediately using the available agent/task control mechanism. Do not send it another implementation or repair instruction first.
2. Prevent downstream stages, approvals, merges, submissions, or state advancement based on the affected work.
3. Preserve existing artifacts and logs for diagnosis. Do not delete, overwrite, revert, or repair them unless the user later authorizes recovery.
4. Mark the affected stage as stopped or failed only through the workflow's supported state mechanism; never edit control state ad hoc.
5. Report to the user or controlling agent, then wait for an explicit recovery decision.

If no interrupt mechanism exists, issue an unambiguous stop instruction, stop consuming or forwarding the agent's output, and report that execution could not be technically terminated.

## Required report

Use this compact structure:

```text
SUPERVISION: DEVIATED | BLOCKED
Agent/stage: <identity and current stage>
Stopped: <yes/no, mechanism, timestamp if available>
Baseline: <authoritative requirement>
Observed: <specific conflicting action or artifact>
Evidence: <task output, file/path, diff, command, or event>
Impact: <affected outputs and downstream gates>
Preserved state: <artifacts left unchanged>
Recovery options: <minimal choices; no action taken>
Decision needed: <one explicit user/team choice>
```

For `ALIGNED`, stay quiet unless the user requested periodic status. Never report success for the supervised stage; only report that no directional deviation was observed in the evidence inspected.

## Completion boundary

Supervision ends when the monitored agent is stopped, the configured stage reaches its validated handoff, or the user ends monitoring. Passing this supervision gate does not replace domain validation, reproducibility checks, security review, or final audit.
