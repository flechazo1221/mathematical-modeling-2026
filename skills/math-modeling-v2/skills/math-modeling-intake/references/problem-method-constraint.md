# Problem, Method, and Constraint Intake

Use this reference to turn the selected problem into an auditable H1 definition. The goal is not to recognize method names from keywords; it is to establish what must be answered, what evidence exists, and which method families remain feasible.

## 1. Four inventories

### Known information

Classify every known item and retain its source location:

- **Files:** statements, attachments, tables, figures, dictionaries, templates, and official rules.
- **Fields:** variable meaning, type, unit, range, missing value convention, index, grouping, and time or spatial semantics.
- **Rules:** scoring rules, submission limits, definitions, deadlines, and prohibited operations.
- **Background facts:** stated domain facts. Separate facts supplied by the problem, facts verified from authoritative sources, and assumptions introduced by the team.

Do not treat an inferred definition or common-sense belief as a supplied fact.

### Requested questions

First determine the exact number of questions. Split compound sentences when they require different outputs or validation, but preserve the original numbering as a parent identifier.

For every subquestion record:

- problem keyword and action: describe, explain, estimate, predict, evaluate, classify, cluster, optimize, simulate, compare, or test;
- target object and decision user;
- required output, granularity, unit, horizon, uncertainty expression, and success criterion;
- links to other subquestions: **consistent/shared definition**, **difference/comparison**, **dependency/input**, or **trade-off/conflict**.

If the number or boundary of subquestions is ambiguous, provide alternative decompositions and put the choice into H1 instead of silently selecting one.

### Constraints

Maintain a constraint register with `id`, category, source, natural-language statement, formal expression or executable check, scope, hardness, affected questions, and status.

- **Explicit:** budget caps, capacity, required integer or binary variables, mandated methods or formats.
- **Data:** small samples, missing labels, imbalance, limited history, sampling bias, or insufficient resolution.
- **Practical/domain:** nonnegative demand, proportions in `[0,1]`, mutually exclusive states, service or policy bounds.
- **Temporal:** end time not earlier than start time, causal ordering, forecast origin, no future-information leakage. Prediction without predictors or historical signal is an identifiability gap, not permission to invent data.
- **Physical:** conservation of mass, energy, or flow; dimensional and unit consistency; geometric or network feasibility.

Distinguish hard constraints that invalidate a solution from soft preferences that may be penalized. If two constraints conflict, expose the conflict and affected outputs in H1.

### Deliverables

List every required paper component and submission artifact concretely: which question it answers, required content, format, page or file limit, evidence source, and acceptance check. Do not use vague entries such as “complete analysis.”

## 2. Task type and method-family screening

Assign task types from the required output and validation target, not from isolated wording. A subquestion may have one primary and one justified secondary type.

| Task type | Candidate method families | Initial suitability checks |
| --- | --- | --- |
| Data analysis | descriptive statistics, correlation, regression, factor analysis | Is the goal description, association, explanation, or dimension reduction? Are scale, sample size, and assumptions adequate? |
| Prediction | regression, time series, machine learning | Is there a defined target, prediction horizon, usable predictors, historical coverage, and leakage-safe validation? |
| Comprehensive evaluation | weighting, TOPSIS, AHP, fuzzy evaluation | Are criteria directional and comparable? Are weights evidence-based? Is ranking stability testable? |
| Classification | logistic regression, decision trees, ensembles | Are labels defined and sufficiently represented? Are probability calibration, imbalance, and error costs addressed? |
| Clustering | k-means, hierarchical clustering, DBSCAN | Is an unsupervised grouping actually requested? Are distance, scaling, cluster shape, noise, and stability defensible? |
| Optimization | linear, integer, multi-objective optimization | Are decision variables, objective functions, hard constraints, feasible sets, and trade-off rules explicit? |
| Mechanism or simulation | differential equations, conservation models, Monte Carlo | Is a mechanism or uncertainty propagation needed? Can parameters and initial/boundary conditions be identified? |

These are families, not an exhaustive algorithm catalog. Do not recommend a complex family merely because it appears in the table.

For each subquestion:

1. State the primary task type and why the requested output implies it.
2. Define the simplest credible baseline.
3. Compare only plausible families using data needs, assumptions, constraint compatibility, interpretability, computation, validation, and failure conditions.
4. Give a provisional recommendation with evidence and confidence.
5. Record rejected families and the decisive reason, such as no labels, insufficient time depth, non-spherical clusters, nonlinear physics, or an infeasible integer requirement.
6. Pass unresolved alternatives to H1 and detailed model construction to `math-modeling-design`.

## 3. Required matrix

`问题方法约束矩阵.md` must contain one row per numbered subquestion with at least:

| Question | Keywords | Output contract | Relationship | Primary / secondary type | Baseline | Provisional family | Data basis | Binding constraints | Validation | Rejected families and reasons | Unknowns / H1 decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Run these completeness checks before reporting `PASS`:

- every question maps to at least one mandatory deliverable;
- every mandatory deliverable maps back to a question or an official submission rule;
- every hard constraint has a formal or executable check, or is explicitly marked unformalized;
- every provisional family has a data basis, baseline, validation path, and failure condition;
- cross-question definitions, units, time horizons, and shared variables are consistent;
- no prediction uses information unavailable at its forecast origin;
- no causal claim is implied by correlation-only evidence.
