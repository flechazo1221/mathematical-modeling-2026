"""Revised GRID-CONV experiment, isolated from the frozen COMPUTE evidence.

This script reuses the approved solver implementation but writes only below
04-compute/revision-grid-conv-20260912.  It separates time refinement from
space refinement, uses five radial levels, and compares projected fields in
addition to terminal scalar summaries.  It does not update H3 or publication
figures.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np


REVISION = Path(__file__).resolve().parent
PROJECT_ROOT = REVISION.parents[1]
BASE_PATH = Path(os.environ.get(
    "GRID_CONV_BASE_SOLVER",
    str(PROJECT_ROOT / "04-compute" / "src" / "formal_compute.py"),
))
RESULTS = REVISION / "results"
LOGS = REVISION / "logs"
SEED = 20260912
FIELD_TOL = 5e-5
EVENT_TOL_S = 60.0
Q2_TIME_DTS = [10.0, 5.0, 2.5, 1.25, 0.625]
ACTIVE_LOG = None


def load_base():
    spec = importlib.util.spec_from_file_location("formal_compute_base", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load approved solver: {BASE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_base()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def scope_outputs(scope: str) -> tuple[Path, Path, Path, Path, Path]:
    """Return output paths isolated under the current scope directory."""
    scope_dir = RESULTS / scope
    scope_dir.mkdir(parents=True, exist_ok=True)
    return (
        scope_dir,
        scope_dir / "field-grid-convergence.csv",
        scope_dir / "threshold-grid-convergence.csv",
        scope_dir / "time-convergence.csv",
        scope_dir / "revision-summary.json",
    )


def log_line(message: str) -> None:
    if ACTIVE_LOG is not None:
        ACTIVE_LOG.write(message + "\n")
        ACTIVE_LOG.flush()


def grid_h(nr: int, nz: int) -> tuple[float, float, float]:
    grid = BASE.Grid(nr, nz, BASE.R0)
    hr = float(np.max(np.diff(grid.rf)) / BASE.R0)
    hz = float(np.max(np.diff(grid.zf)) / (BASE.LENGTH if nz == 1 else grid.axial_extent))
    return hr, hz, max(hr, hz)


def run_one(label: str, nr: int, nz: int, dt: float, duration: float, q: int,
            model: str, *, moving_impl: str = "fixed", stop_threshold: float | None = None):
    sample_every = max(60.0, min(float(duration), 3600.0))
    cfg = BASE.RunConfig(label, nr, nz, dt, duration, q, model,
                         moving_impl=moving_impl, stop_threshold=stop_threshold,
                         sample_every=sample_every)
    log_line("START " + json.dumps(cfg.__dict__, ensure_ascii=False))
    started = time.perf_counter()
    result = BASE.simulate(cfg)
    elapsed = time.perf_counter() - started
    result["revision_runtime_s"] = elapsed
    log_line("DONE " + json.dumps({"label": label, "runtime_s": elapsed,
                                  "metrics": result["metrics"]}, ensure_ascii=False))
    return result


def project_field(result, nr: int, nz: int, radial_points: int = 81,
                  axial_points: int = 41) -> np.ndarray:
    """Project a final cell field to an interior common normalized grid.

    Endpoint cell-center extrapolation is first order and would dominate a
    raw L_inf comparison. Endpoint behavior is checked separately by scalar
    center/surface metrics, so the full-field norm uses the common interior.
    """
    grid = BASE.Grid(nr, nz, BASE.R0)
    field = np.asarray(result["final_c"], dtype=float)
    r_target = np.linspace(0.03, 0.97, radial_points)
    r_source = np.asarray(grid.rc / BASE.R0, dtype=float)
    if nz == 1:
        return np.interp(r_target, r_source, field[:, 0])[:, None]
    z_target = np.linspace(0.05, 0.95, axial_points)
    z_source = np.asarray(grid.zc / grid.axial_extent, dtype=float)
    along_z = np.vstack([np.interp(z_target, z_source, row) for row in field])
    return np.vstack([np.interp(r_target, r_source, along_z[:, j])
                      for j in range(len(z_target))]).T


def field_difference(a, b, nr_a: int, nz_a: int, nr_b: int, nz_b: int) -> tuple[float, float]:
    fa = project_field(a, nr_a, nz_a)
    fb = project_field(b, nr_b, nz_b)
    diff = fa - fb
    inf_norm = float(np.max(np.abs(diff)))
    if fa.shape[1] == 1:
        weights = np.linspace(0.0, 1.0, fa.shape[0])[:, None]
    else:
        weights = np.linspace(0.0, 1.0, fa.shape[0])[:, None]
        weights = weights * np.ones((1, fa.shape[1]))
    denom = max(float(np.sum(weights * fa * fa)), 1e-300)
    rel_l2 = float(math.sqrt(np.sum(weights * diff * diff) / denom))
    return inf_norm, rel_l2


def metric_value(result, metric: str):
    return result["metrics"].get(metric)


def observed_orders(values: list[float | None], ns: list[int]) -> list[float | None]:
    out: list[float | None] = [None, None]
    hs = [1.0 / n for n in ns]
    for i in range(2, len(values)):
        if values[i - 2] is None or values[i - 1] is None or values[i] is None:
            out.append(None)
            continue
        d0 = abs(float(values[i - 1]) - float(values[i - 2]))
        d1 = abs(float(values[i]) - float(values[i - 1]))
        if d0 <= 0.0 or d1 <= 0.0:
            out.append(None)
        else:
            out.append(float(math.log(d0 / d1) / math.log(hs[i - 1] / hs[i])))
    return out


def monotone(values: list[float | None]) -> bool:
    nums = [float(v) for v in values if v is not None]
    if len(nums) < 3:
        return False
    diffs = np.diff(nums)
    signs = np.sign(diffs[np.abs(diffs) > 1e-14])
    return len(signs) > 0 and len(set(signs.tolist())) == 1


def run_spatial_family(family: str, q: int, model: str, levels: list[tuple[int, int]],
                       dt: float, duration: float, *, moving_impl: str = "fixed",
                       stop_threshold: float | None = None, event_metric: bool = False):
    runs = []
    rows = []
    for i, (nr, nz) in enumerate(levels):
        label = f"{family}-L{i+1}-nr{nr}-nz{nz}"
        result = run_one(label, nr, nz, dt, duration, q, model,
                         moving_impl=moving_impl, stop_threshold=stop_threshold)
        runs.append((nr, nz, result))
        hr, hz, heff = grid_h(nr, nz)
        metric_names = ["interpolated_event_time_s"] if event_metric else ["final_max_C", "final_mean_C"]
        for metric in metric_names:
            value = metric_value(result, metric)
            rows.append({
                "scope": "threshold" if event_metric else "field",
                "family": family,
                "level": i + 1,
                "nr": nr,
                "nz": nz,
                "dt_s": dt,
                "duration_s": duration,
                "h_r": hr,
                "h_z": hz,
                "h_effective": heff,
                "metric": metric,
                "value": "" if value is None else value,
                "adjacent_change": "",
                "field_linf_change": "",
                "field_l2_relative_change": "",
                "observed_order": "",
                "runtime_s": result["revision_runtime_s"],
            })
    if not event_metric:
        for metric in ("final_max_C", "final_mean_C"):
            metric_rows = [r for r in rows if r["metric"] == metric]
            values = [None if r["value"] == "" else float(r["value"]) for r in metric_rows]
            orders = observed_orders(values, [int(r["nr"]) for r in metric_rows])
            field_inf = [None]
            field_l2 = [None]
            for i in range(1, len(runs)):
                inf_norm, rel_l2 = field_difference(runs[i - 1][2], runs[i][2],
                                                    runs[i - 1][0], runs[i - 1][1],
                                                    runs[i][0], runs[i][1])
                field_inf.append(inf_norm)
                field_l2.append(rel_l2)
            for i, row in enumerate(metric_rows):
                if i > 0:
                    row["adjacent_change"] = abs(values[i] - values[i - 1])
                row["field_linf_change"] = "" if field_inf[i] is None else field_inf[i]
                row["field_l2_relative_change"] = "" if field_l2[i] is None else field_l2[i]
                row["observed_order"] = "" if orders[i] is None else orders[i]
    else:
        metric_rows = [r for r in rows if r["metric"] == "interpolated_event_time_s"]
        values = [None if r["value"] == "" else float(r["value"]) for r in metric_rows]
        orders = observed_orders(values, [int(r["nr"]) for r in metric_rows])
        for i, row in enumerate(metric_rows):
            if i > 0 and values[i] is not None and values[i - 1] is not None:
                row["adjacent_change"] = abs(values[i] - values[i - 1])
            row["observed_order"] = "" if orders[i] is None else orders[i]
    return rows, runs


def run_time_family(family: str, q: int, model: str, nr: int, nz: int,
                    dts: list[float], duration: float, *, moving_impl: str = "fixed",
                    stop_threshold: float | None = None, event_metric: bool = False):
    rows = []
    values = []
    metric = "interpolated_event_time_s" if event_metric else "final_max_C"
    for i, dt in enumerate(dts):
        result = run_one(f"{family}-TIME{i+1}-dt{dt:g}", nr, nz, dt, duration, q, model,
                         moving_impl=moving_impl, stop_threshold=stop_threshold)
        value = metric_value(result, metric)
        values.append(None if value is None else float(value))
        rows.append({"scope": "time", "family": family, "level": i + 1,
                     "nr": nr, "nz": nz, "dt_s": dt, "metric": metric,
                     "value": "" if value is None else value,
                     "adjacent_change": "", "observed_order": "",
                     "runtime_s": result["revision_runtime_s"]})
    orders = observed_orders(values, [1.0 / dt for dt in dts])
    for i, row in enumerate(rows):
        if i > 0 and values[i] is not None and values[i - 1] is not None:
            row["adjacent_change"] = abs(values[i] - values[i - 1])
        row["observed_order"] = "" if orders[i] is None else orders[i]
    return rows


def summarize(field_rows: list[dict], time_rows: list[dict]) -> dict:
    summary = {"field": [], "threshold": [], "time": [],
               "qualification_rules": {
                   "field_last_two_adjacent_changes_le": FIELD_TOL,
                   "event_last_two_adjacent_changes_s_le": EVENT_TOL_S,
                   "requires_monotone_trend": True,
                   "requires_full_field_norm": "interior common-grid L_inf decreases over the last two refinements; scalar output tolerance is not reused for this norm",
               }}
    for scope, rows in (("field", field_rows), ("threshold", field_rows), ("time", time_rows)):
        for key in sorted({(r["family"], r["metric"]) for r in rows if r["scope"] == scope}):
            family, metric = key
            selected = [r for r in rows if r["scope"] == scope and r["family"] == family and r["metric"] == metric]
            vals = [None if r["value"] in ("", None) else float(r["value"]) for r in selected]
            changes = [float(r["adjacent_change"]) for r in selected if r["adjacent_change"] != ""]
            last_two = changes[-2:]
            norm_changes = ([float(r["field_linf_change"]) for r in selected
                             if r["field_linf_change"] not in ("", None)]
                            if scope == "field" else [])
            norm_last_two = norm_changes[-2:]
            threshold = EVENT_TOL_S if "event_time" in metric else FIELD_TOL
            scalar_pass = len(last_two) == 2 and max(last_two) <= threshold
            norm_pass = (None if scope != "field" else
                         (len(norm_last_two) == 2 and
                          all(norm_last_two[i] < norm_last_two[i - 1]
                              for i in range(1, len(norm_last_two)))))
            summary[scope].append({
                "family": family,
                "metric": metric,
                "levels": len(selected),
                "values": vals,
                "adjacent_changes": changes,
                "last_two_max": max(last_two) if last_two else None,
                "field_linf_adjacent_changes": norm_changes,
                "field_linf_last_two_max": max(norm_last_two) if norm_last_two else None,
                "monotone": monotone(vals),
                "qualifies_scalar_threshold": scalar_pass,
                "qualifies_field_norm": norm_pass,
                "qualifies_local_threshold": (scalar_pass and
                                               (norm_pass if scope == "field" else True) and
                                               monotone(vals)),
                "threshold": threshold,
            })
    return summary


def main() -> None:
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--scope", choices=["smoke", "q2", "q2-space", "q2-time", "fields", "q3", "q3_mid", "q3_time_extra", "threshold", "all"], default="smoke")
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    scope_dir, field_path, threshold_path, time_path, summary_path = scope_outputs(args.scope)
    manifest_path = scope_dir / "revision-manifest.json"
    # Only replace files generated by this scope. Scope directories prevent
    # smoke/q2/fields/threshold outputs from being mixed across runs.
    for generated_path in (field_path, threshold_path, time_path, manifest_path, summary_path):
        if generated_path.exists():
            generated_path.unlink()
    log_path = LOGS / f"{args.scope}.log"
    started = time.perf_counter()
    field_rows: list[dict] = []
    threshold_rows: list[dict] = []
    time_rows: list[dict] = []
    global ACTIVE_LOG
    with log_path.open("w", encoding="utf-8") as log:
        ACTIVE_LOG = log
        log.write(json.dumps({"command": " ".join(sys.argv), "python": sys.version,
                              "platform": platform.platform(), "seed": SEED}, ensure_ascii=False) + "\n")
        if args.scope == "smoke":
            smoke_runs = []
            for nr in (20, 30, 45):
                result = run_one(f"SMOKE-Q2-nr{nr}", nr, 12, 5, 120, 2, "M3")
                smoke_runs.append((nr, result))
                field_rows.append({"scope": "field", "family": "SMOKE-Q2-M3",
                                   "level": len(field_rows) + 1, "nr": nr, "nz": 12,
                                   "dt_s": 5, "duration_s": 120, "metric": "final_max_C",
                                   "value": result["metrics"]["final_max_C"],
                                   "adjacent_change": "", "field_linf_change": "",
                                   "field_l2_relative_change": "", "observed_order": "",
                                   "runtime_s": result["revision_runtime_s"]})
            for i in range(1, len(field_rows)):
                field_rows[i]["adjacent_change"] = abs(float(field_rows[i]["value"]) - float(field_rows[i - 1]["value"]))
            for i in range(1, len(smoke_runs)):
                inf_norm, rel_l2 = field_difference(smoke_runs[i - 1][1], smoke_runs[i][1],
                                                    smoke_runs[i - 1][0], 12,
                                                    smoke_runs[i][0], 12)
                field_rows[i]["field_linf_change"] = inf_norm
                field_rows[i]["field_l2_relative_change"] = rel_l2
            for family, q, model, moving_impl, stop in (("SMOKE-Q3", 3, "M3", "fixed", .15 - 1e-6),
                                                         ("SMOKE-Q4", 4, "M3", "reference", .15 - 1e-6)):
                result = run_one(family, 20, 12, 30, 3600, q, model,
                                 moving_impl=moving_impl, stop_threshold=stop)
                threshold_rows.append({"scope": "threshold", "family": family, "level": 1,
                                       "nr": 20, "nz": 12, "dt_s": 30,
                                       "metric": "interpolated_event_time_s",
                                       "value": result["metrics"]["interpolated_event_time_s"],
                                       "adjacent_change": "", "observed_order": "",
                                       "runtime_s": result["revision_runtime_s"]})
        if args.scope in ("fields", "all"):
            field_rows.extend(run_spatial_family("Q1-M1", 1, "M1",
                [(54, 1), (81, 1), (122, 1), (183, 1), (275, 1)], .25, 1800)[0])
            field_rows.extend(run_spatial_family("Q1-M2", 1, "M2",
                [(42, 54), (62, 54), (93, 54), (140, 54), (210, 54)], .25, 1800)[0])
        if args.scope in ("q2", "q2-space", "fields", "all"):
            field_rows.extend(run_spatial_family("Q2-M3", 2, "M3",
                [(42, 36), (62, 36), (93, 36), (140, 36), (210, 36)], 1.25, 10800)[0])
        if args.scope in ("fields", "all"):
            time_rows.extend(run_time_family("Q1-M1", 1, "M1", 275, 1, [.5, .25, .125], 1800))
            time_rows.extend(run_time_family("Q1-M2", 1, "M2", 210, 54, [.5, .25, .125], 1800))
        if args.scope in ("q2", "q2-time", "fields", "all"):
            time_rows.extend(run_time_family("Q2-M3", 2, "M3", 210, 36, Q2_TIME_DTS, 10800))
        if args.scope in ("q3", "threshold", "all"):
            threshold_rows.extend(run_spatial_family("Q3-M3", 3, "M3",
                [(63, 36), (93, 36), (140, 36), (210, 36), (315, 36)], 15, 259200,
                stop_threshold=.15 - 1e-6, event_metric=True)[0])
            time_rows.extend(run_time_family("Q3-M3", 3, "M3", 315, 36, [60, 30, 15, 7.5], 259200,
                                              stop_threshold=.15 - 1e-6, event_metric=True))
        if args.scope == "q3_mid":
            threshold_rows.extend(run_spatial_family("Q3-M3-midpoint", 3, "M3",
                [(175, 36)], 15, 259200, stop_threshold=.15 - 1e-6,
                event_metric=True)[0])
        if args.scope == "q3_time_extra":
            time_rows.extend(run_time_family("Q3-M3-extra", 3, "M3", 210, 36, [7.5], 259200,
                                              stop_threshold=.15 - 1e-6, event_metric=True))
        if args.scope in ("threshold", "all"):
            threshold_rows.extend(run_spatial_family("Q4-reference", 4, "M3",
                [(63, 32), (93, 32), (140, 32), (210, 32), (315, 32)], 15, 259200,
                moving_impl="reference", stop_threshold=.15 - 1e-6, event_metric=True)[0])
            time_rows.extend(run_time_family("Q4-reference", 4, "M3", 315, 32, [60, 30, 15], 259200,
                                              moving_impl="reference", stop_threshold=.15 - 1e-6, event_metric=True))
    write_csv(field_path, field_rows)
    write_csv(threshold_path, threshold_rows)
    write_csv(time_path, time_rows)
    manifest = {
        "revision": "GRID-CONV-20260912-v1",
        "status": "candidate evidence; H3 and frozen publication figures unchanged",
        "scope": args.scope,
        "seed": SEED,
        "source_solver": str(BASE_PATH),
        "source_solver_sha256": sha256(BASE_PATH),
        "inputs": [{"path": str(BASE.P1), "sha256": sha256(BASE.P1)},
                    {"path": str(BASE.P2), "sha256": sha256(BASE.P2)}],
        "output_dir": str(scope_dir),
        "space_design": {
            "levels": 5,
            "refinement_axis": "radial nr; nz held fixed within each family",
            "field_projection": "interior common normalized grid r=[0.03,0.97], z=[0.05,0.95]",
        },
        "time_design": {
            "Q1-M1": [0.5, 0.25, 0.125],
            "Q1-M2": [0.5, 0.25, 0.125],
            "Q2-M3": Q2_TIME_DTS,
            "Q3-M3": [60.0, 30.0, 15.0, 7.5],
            "Q4-reference": [60.0, 30.0, 15.0],
        },
        "field_tolerance": FIELD_TOL,
        "event_tolerance_s": EVENT_TOL_S,
        "elapsed_s": time.perf_counter() - started,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = summarize(field_rows + threshold_rows, time_rows)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    ACTIVE_LOG = None
    log_path.write_text(log_path.read_text(encoding="utf-8") + json.dumps({"exit_code": 0,
                                                                            "elapsed_s": time.perf_counter() - started,
                                                                            "field_rows": len(field_rows),
                                                                            "threshold_rows": len(threshold_rows),
                                                                            "time_rows": len(time_rows)}, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
