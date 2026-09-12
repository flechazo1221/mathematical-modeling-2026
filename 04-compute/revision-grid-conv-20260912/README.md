# GRID-CONV revision 20260912

This is an isolated COMPUTE-stage revision. It reuses the frozen H2 solver but does not overwrite `04-compute/results`, `05-evidence`, `06-figure`, or `decisions`.

The revision adds five radial levels, independent time refinement at the finest spatial level, interior common-grid field norms, observed-order estimates, and pre-registered local acceptance thresholds. Each scope writes to its own `results/<scope>/` directory and has its own log, manifest, and summary, so a smoke run cannot be mistaken for the focused Q2 run. It is candidate evidence only until the team reviews the results and the affected COMPUTE/EVIDENCE handoff is regenerated.

Run from the project root:

```powershell
& 'C:\Users\Linza\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  '04-compute/revision-grid-conv-20260912/grid_conv_revision.py' --scope smoke
```

Available scopes are `smoke`, `q2`, `q2-space`, `q2-time`, `fields`, `q3`, `q3_mid`, `q3_time_extra`, `threshold`, and `all`. `q2-space` runs only the five-level Q2 spatial refinement; `q2-time` runs only Q2 time refinement with the added `dt=0.625` level. `q3` is the focused Q3 convergence run with five spatial levels and four time-step levels; `q3_mid` and `q3_time_extra` are the recoverable single-run supplements used by the completed candidate package. The long threshold scope remains separate because Q3/Q4 runs are much more expensive. Outputs are under `results/<scope>/`; logs are under `logs/<scope>.log`.

## Completed Q3 candidate package

The completed Q3 package is assembled at `results/q3-final/` by `finalize_q3_convergence.py`. It uses five completed spatial levels `nr=63,93,140,175,210` at fixed `dt=15 s`, and four completed time levels `dt=60,30,15,7.5 s` at fixed `nr=210`. The attempted `nr=315` run was stopped before a `DONE` record and is explicitly excluded from the package. The final summary is a candidate COMPUTE result only; formal `04-compute/results`, downstream EVIDENCE, and FIGURE artifacts are unchanged.
