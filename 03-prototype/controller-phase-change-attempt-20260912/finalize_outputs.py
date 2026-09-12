from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_phase_change_attempt as impl


def read_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def numeric(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    for row in rows:
        for key in keys:
            if row.get(key) in (None, ""):
                row[key] = None
                continue
            try:
                row[key] = float(row[key])
            except ValueError:
                pass
    return rows


rows = numeric(read_csv(HERE / "原始结果.csv"), (
    "nr", "nz", "dt_s", "duration_s", "final_max_C", "final_mean_C", "reported_event_time_s",
    "interpolated_event_time_s", "candidate_temperature_range_C", "max_linear_relative_residual",
    "normalized_moisture_balance_error", "latent_integral_J_est", "latent_peak_power_W", "proxy_scale",
    "L_v_J_per_kg", "latent_product_Lv_scale", "water_balance_max_abs_kg_s", "proxy_boundary_loss_max_kg_s",
    "water_trace_count", "max_physical_heat_balance_relative", "max_physical_heat_balance_residual_J"))
traces = numeric(read_csv(HERE / "latent-source-trace.csv"), (
    "time_s", "latent_power_W", "proxy_scale", "L_v_J_per_kg", "raw_boundary_loss_rate_kg_s",
    "proxy_boundary_loss_rate_kg_s", "j_w_outer_max_kg_m2_s", "gamma_raw_integral_kg_s",
    "gamma_proxy_integral_kg_s", "total_water_kg", "bound_water_kg", "liquid_water_kg",
    "phase_split_residual_kg", "free_flux_factor"))
water_audit = read_csv(HERE / "water-audit.csv")
heat_audit = read_csv(HERE / "heat-audit.csv")
failures = [r for r in rows if r.get("status") == "FAIL"]
comparisons = impl.comparison_rows(rows)
component_comparisons = impl.component_split_rows(rows)
component_validation = impl.component_validations()
refinement = impl.refinement_rows(rows)
ident_rows, ident_obj = impl.identifiability(traces)
validations = impl.validations(rows, comparisons, ident_rows, failures)

impl.write_csv(HERE / "候选配对比较.csv", comparisons)
impl.write_csv(HERE / "component-split-comparison.csv", component_comparisons)
impl.write_csv(HERE / "space-time-refinement.csv", refinement)
impl.write_csv(HERE / "identifiability.csv", ident_rows)
impl.write_json(HERE / "identifiability.json", ident_obj)
impl.write_csv(HERE / "validation-register.csv", validations)
impl.write_csv(HERE / "component-validation-register.csv", component_validation)
(HERE / "候选方案对比.md").write_text(
    impl.report(rows, comparisons, ident_rows, validations, failures, component_comparisons, component_validation),
    encoding="utf-8",
)

manifest_path = HERE / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["status"] = "BLOCKED"
manifest["finalized_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
outputs = []
for path in sorted(HERE.rglob("*")):
    if path.is_file() and path.name not in {"handoff.json", "manifest.json"} and "__pycache__" not in path.parts:
        outputs.append({"path": impl.rel(path), "sha256": impl.sha256(path), "bytes": path.stat().st_size})
manifest["outputs"] = outputs
impl.write_json(manifest_path, manifest)

handoff_path = HERE / "handoff.json"
handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
handoff["status"] = "BLOCKED"
handoff["outputs"] = outputs + [{"path": impl.rel(manifest_path), "sha256": impl.sha256(manifest_path)}]
handoff["validation_register"] = [{"id": x["id"], "status": x["status"]} for x in validations] + [
    {"id": x["id"], "status": x["status"]} for x in component_validation
]
handoff["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
impl.write_json(handoff_path, handoff)
print(json.dumps({"status": "BLOCKED", "rows": len(rows), "failures": len(failures),
                  "comparison_rows": len(comparisons), "component_rows": len(component_comparisons),
                  "refinement_rows": len(refinement), "outputs": len(outputs)}, ensure_ascii=False))
