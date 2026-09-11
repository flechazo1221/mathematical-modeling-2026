"""Create reproducibility/evidence manifests and schema-shaped COMPUTE handoff."""
from __future__ import annotations
import hashlib,json,platform,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy,openpyxl,PIL

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/"04-compute"
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def item(rel): return {"path":rel.as_posix(),"sha256":digest(ROOT/rel)}
def stable_output(p):
 return p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"

inputs=[Path("decisions/H2-model.json"),Path("decisions/H1-problem.json"),Path("03-prototype/handoff.json"),
        Path("02-design/候选模型方案.md"),Path("02-design/H2-优化审计与方向.md"),Path("02-design/验证计划.json")]
inputs += sorted(Path("02-design/contracts").glob("*.json"))
inputs += sorted(p for p in Path("input/A题/附件").rglob("*") if p.is_file())
files=sorted([p for p in OUT.rglob("*") if stable_output(p) and p.name not in {"复现清单.json","证据索引.json","handoff.json"}])
manifest={"schema_version":"1.0","stage":"COMPUTE","seed":20260911,
 "environment":{"python":sys.version,"platform":platform.platform(),"numpy":numpy.__version__,"openpyxl":openpyxl.__version__,"Pillow":PIL.__version__},
 "inputs":[item(p) for p in inputs],
 "commands":[
  f'"{sys.executable}" 04-compute/src/formal_compute.py --mode p1',
  f'"{sys.executable}" 04-compute/src/formal_compute.py --mode full',
  f'"{sys.executable}" 04-compute/src/formal_compute.py --mode extended',
  f'"{sys.executable}" 04-compute/src/finalize_compute.py'],
 "numerical_contract":{"method":"cell-centered conservative axisymmetric FV on two-sided locally refined radial grids; backward-Euler coefficient Picard; preconditioned CG","picard_absolute_update_tolerance":1e-7,"threshold":"max(C)<0.15-1e-6","event_time":"linear interpolation inside the first-crossing bracket, then conservative ceiling to 60 s for reporting","report_resolution_s":60,"radius":"shape-preserving PCHIP","terminal_window_base_s":3600},
 "outputs":[{"path":p.relative_to(ROOT).as_posix(),"sha256":digest(p)} for p in files]}
(OUT/"复现清单.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

metrics=json.loads((OUT/"results/key-metrics.json").read_text(encoding="utf-8"))
with (OUT/"results/validation-register.csv").open(encoding="utf-8-sig") as f:
 import csv
 validation_rows=list(csv.DictReader(f))
stage_status="PASS" if all(r["status"]=="PASS" for r in validation_rows) else "FAIL"
evidence={"schema_version":"1.0","stage":"COMPUTE","status":stage_status,
 "claims":[
  {"id":"C-Q1","claim":"M1 baseline and M2 2-D backbone were run under common boundary/physics conventions; dimensional effect and fixed-time-step radial convergence are separately recorded.","evidence":["04-compute/results/q1-samples.csv","04-compute/results/field-grid-convergence.csv","04-compute/results/convergence.csv"]},
  {"id":"C-Q2","claim":"M3 state-law route was run for 3 h; M2 constant-law and M4 temperature-field cases are comparators, not observational-fit improvements.","evidence":["04-compute/results/q2-samples.csv","04-compute/results/key-metrics.json"]},
  {"id":"C-Q3","claim":"The first full-domain moisture-threshold crossing was spatially stabilized, bracketed, interpolated, and checked at 30 s and 15 s time steps.","evidence":["04-compute/results/q3-threshold-trajectory.csv","04-compute/results/threshold-grid-convergence.csv","04-compute/results/convergence.csv"]},
  {"id":"C-Q4","claim":"Moving-radius reference and moving-FV paths, radial/event convergence, geometry/dry-solid conservation, interpolation sensitivity and Jacobian ablation were executed.","evidence":["04-compute/results/q4-threshold-trajectory.csv","04-compute/results/threshold-grid-convergence.csv","04-compute/results/validation-register.csv","04-compute/results/sensitivity.csv"]},
  {"id":"C-ROBUST","claim":"Boundary, empirical-law, terminal-window and radius-interpolation pressure tests are reported without claiming causal or observational validation. Formerly 72 h-censored cases were continued to their first threshold crossing.","evidence":["04-compute/results/sensitivity.csv","04-compute/results/sensitivity-extended.csv"]}],
 "key_values":metrics,"validation_status":stage_status,"failed_validations":[r for r in validation_rows if r["status"]!="PASS"],"diagnostic_figures":["04-compute/diagnostic-figures/diagnostic-threshold.png","04-compute/diagnostic-figures/diagnostic-convergence.png","04-compute/diagnostic-figures/diagnostic-sensitivity.png"]}
(OUT/"证据索引.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")

all_outputs=sorted([p for p in OUT.rglob("*") if stable_output(p) and p.name!="handoff.json"])
handoff={"schema_version":"1.0","stage":"COMPUTE","status":stage_status,"inputs":[item(p) for p in inputs],
 "outputs":[{"path":p.relative_to(ROOT).as_posix(),"sha256":digest(p)} for p in all_outputs],
 "frozen_decisions":[item(Path("decisions/H1-problem.json")),item(Path("decisions/H2-model.json"))],
 "assumptions":["M4 is limited to the problem-identifiable temperature-dependent coefficient coupling and is used only as an ablation.","The 4 h terminal environment uses the frozen one-hour mean base case and bounded 0.5/2 h window tests.","For extended threshold runs after 72 h, the chamber continues at the approved terminal-window values and Q4 radius is held at the final observed attachment-2 radius.","Moving material cells use affine radial motion and dry-solid density continuity; no unsupported latent-heat source is introduced."],
 "unknowns":["No internal experimental observations are available, so numerical differences among M2/M3/M4 are not fit improvements.","Problem-supplied empirical laws are treated as conditional simulation laws, not universal material properties."],
 "claims":["All numerical values in the COMPUTE evidence were generated by recorded commands.","The approved M1-M4 compatibility route, baseline, threshold and moving-domain validation commands were executed without changing upstream files.","Diagnostic figures are model-checking aids only and are not publication figures."],
 "evidence":["04-compute/证据索引.json maps claims to source tables.","04-compute/results/validation-register.csv records V01-V12 outcomes.","04-compute/复现清单.json records hashes, environment, parameters and commands."],
 "warnings":["Model contrasts must not be described as empirical accuracy gains.","Sensitivity ranges are conditional on preregistered bounded scenarios and do not exhaust structural uncertainty.","The Q2 V02 margin is narrow (4.00114e-5 versus 5e-5), so downstream consumers must retain the recorded finest-grid values and must not recompute on the old coarse grid."],
 "required_next_actions":(["For V02, increase radial resolution or adopt a demonstrably higher-order conservative radial discretization until the four-decimal field tolerance passes.","For V06, refine the time step and locally bracket the Q3/Q4 threshold until the reported 60 s event time is unchanged; otherwise ask the team whether to reopen H2 validation tolerances.","Do not start EVIDENCE, publication figures or paper writing while COMPUTE is FAIL."] if stage_status=="FAIL" else ["Independently verify this handoff schema and every declared SHA-256 before starting EVIDENCE.","Stop here; do not create publication figures or paper text in this task."]),
 "completed_at":datetime.now(timezone.utc).astimezone().isoformat()}
(OUT/"handoff.json").write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"status":stage_status,"outputs":len(all_outputs),"handoff_sha256":digest(OUT/"handoff.json"),"key_metrics":metrics},ensure_ascii=False,indent=2))
