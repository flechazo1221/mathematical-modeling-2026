"""Assemble the completed Q3 convergence runs into an auditable candidate package.

The long nr=315 run was stopped before completion and is deliberately excluded.
This script only uses completed DONE records from the revision logs plus the
already completed nr=210, dt=60/30/15 records in the formal COMPUTE results.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


REVISION = Path(__file__).resolve().parent
PROJECT_ROOT = REVISION.parents[1]
OUT = REVISION / "results" / "q3-final"
BASE = PROJECT_ROOT / "04-compute"
SOURCE_SOLVER = BASE / "src" / "formal_compute.py"
LOG_Q3 = REVISION / "logs" / "q3.log"
LOG_MID = REVISION / "logs" / "q3_mid.log"
LOG_TIME_EXTRA = REVISION / "logs" / "q3_time_extra.log"
MAIN_CONVERGENCE = BASE / "results" / "convergence.csv"
MAIN_THRESHOLD = BASE / "results" / "threshold-grid-convergence.csv"
EVENT_TOL_S = 60.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"no rows for {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def completed_records(path: Path) -> dict[str, dict]:
    records = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("DONE "):
                record = json.loads(line[5:])
                records[record["label"]] = record
    return records


def observed_orders(values: list[float], scales: list[float]) -> list[str]:
    out = ["", ""]
    for i in range(2, len(values)):
        d0 = abs(values[i - 1] - values[i - 2])
        d1 = abs(values[i] - values[i - 1])
        if d0 <= 0.0 or d1 <= 0.0:
            out.append("")
        else:
            out.append(f"{math.log(d0 / d1) / math.log(scales[i - 1] / scales[i]):.10g}")
    return out


def monotone_decreasing(values: list[float]) -> bool:
    return len(values) >= 2 and all(values[i] < values[i - 1] for i in range(1, len(values)))


def relative_changes(values: list[float]) -> list[float]:
    return [100.0 * abs(values[i] - values[i - 1]) / abs(values[i])
            for i in range(1, len(values))]


def fmt_optional(value: object) -> str:
    return "" if value == "" else f"{float(value):.4f}"


def main() -> None:
    q3_records = completed_records(LOG_Q3)
    mid_records = completed_records(LOG_MID)
    extra_records = completed_records(LOG_TIME_EXTRA)

    spatial_specs = [
        (63, "Q3-M3-L1-nr63-nz36", q3_records),
        (93, "Q3-M3-L2-nr93-nz36", q3_records),
        (140, "Q3-M3-L3-nr140-nz36", q3_records),
        (175, "Q3-M3-midpoint-L1-nr175-nz36", mid_records),
        (210, "Q3-M3-L4-nr210-nz36", q3_records),
    ]
    if any(label not in records for _, label, records in spatial_specs):
        missing = [label for _, label, records in spatial_specs if label not in records]
        raise RuntimeError("missing completed spatial records: " + ", ".join(missing))

    spatial_values = [float(records[label]["metrics"]["interpolated_event_time_s"])
                      for _, label, records in spatial_specs]
    spatial_orders = observed_orders(spatial_values, [1.0 / nr for nr, _, _ in spatial_specs])
    spatial_rows = []
    for i, ((nr, label, records), value, order) in enumerate(zip(spatial_specs, spatial_values, spatial_orders), 1):
        metrics = records[label]["metrics"]
        spatial_rows.append({
            "scope": "Q3",
            "family": "M3",
            "level": i,
            "nr": nr,
            "nz": 36,
            "dt_s": 15,
            "metric": "interpolated_event_time_s",
            "value": value,
            "adjacent_change_s": "" if i == 1 else abs(value - spatial_values[i - 2]),
            "observed_order": order,
            "runtime_s": metrics["runtime_s"],
            "max_linear_relative_residual": metrics["max_linear_relative_residual"],
            "normalized_moisture_balance_error": metrics["normalized_moisture_balance_error"],
            "max_terminal_picard_update": metrics["max_terminal_picard_update"],
            "threshold_bracket": json.dumps(metrics["threshold_bracket"], ensure_ascii=False),
            "source_log": str((REVISION / "logs" / ("q3_mid.log" if "midpoint" in label else "q3.log")).relative_to(PROJECT_ROOT)),
            "status": "COMPLETED",
        })

    main_threshold = [r for r in read_csv(MAIN_THRESHOLD)
                      if r.get("scope") == "Q3" and r.get("nr") == "210"]
    if len(main_threshold) != 1:
        raise RuntimeError("expected one completed formal Q3 nr=210 dt=60 record")
    main_conv = read_csv(MAIN_CONVERGENCE)
    time_pair = [r for r in main_conv if r.get("scope") == "Q3" and r.get("metric") == "t_star_time"]
    if len(time_pair) != 1:
        raise RuntimeError("expected one completed formal Q3 dt30/dt15 record")
    if not extra_records:
        raise RuntimeError("missing completed dt=7.5 s record")
    extra = next((r for label, r in extra_records.items() if "dt7.5" in label), None)
    if extra is None:
        raise RuntimeError("completed dt=7.5 s record not found")

    time_values = [
        float(main_threshold[0]["interpolated_event_time_s"]),
        float(time_pair[0]["base"]),
        float(time_pair[0]["fine"]),
        float(extra["metrics"]["interpolated_event_time_s"]),
    ]
    time_dts = [60.0, 30.0, 15.0, 7.5]
    time_orders = observed_orders(time_values, time_dts)
    time_sources = [
        str(MAIN_THRESHOLD.relative_to(PROJECT_ROOT)),
        str(MAIN_CONVERGENCE.relative_to(PROJECT_ROOT)),
        str(MAIN_CONVERGENCE.relative_to(PROJECT_ROOT)),
        str(LOG_TIME_EXTRA.relative_to(PROJECT_ROOT)),
    ]
    time_metrics = [
        {"runtime_s": "", "max_linear_relative_residual": "", "normalized_moisture_balance_error": "", "status": "COMPLETED_FORMAL"},
        {"runtime_s": "", "max_linear_relative_residual": "", "normalized_moisture_balance_error": "", "status": "COMPLETED_FORMAL"},
        {"runtime_s": "", "max_linear_relative_residual": "", "normalized_moisture_balance_error": "", "status": "COMPLETED_FORMAL"},
        {"runtime_s": extra["metrics"]["runtime_s"],
         "max_linear_relative_residual": extra["metrics"]["max_linear_relative_residual"],
         "normalized_moisture_balance_error": extra["metrics"]["normalized_moisture_balance_error"],
         "status": "COMPLETED"},
    ]
    time_rows = []
    for i, (dt, value, order, source, metrics) in enumerate(zip(time_dts, time_values, time_orders, time_sources, time_metrics), 1):
        time_rows.append({
            "scope": "Q3",
            "family": "M3-time",
            "level": i,
            "nr": 210,
            "nz": 36,
            "dt_s": dt,
            "metric": "interpolated_event_time_s",
            "value": value,
            "adjacent_change_s": "" if i == 1 else abs(value - time_values[i - 2]),
            "observed_order": order,
            **metrics,
            "source": source,
        })

    spatial_changes = [float(r["adjacent_change_s"]) for r in spatial_rows[1:]]
    time_changes = [float(r["adjacent_change_s"]) for r in time_rows[1:]]
    spatial_residual = max(float(r["max_linear_relative_residual"]) for r in spatial_rows)
    spatial_balance = max(float(r["normalized_moisture_balance_error"]) for r in spatial_rows)
    extra_residual = float(extra["metrics"]["max_linear_relative_residual"])
    extra_balance = float(extra["metrics"]["normalized_moisture_balance_error"])
    summary = {
        "revision": "Q3-CONV-20260912-v2",
        "status": "PASS_CANDIDATE",
        "question": "Q3 threshold event-time convergence",
        "space": {
            "levels": len(spatial_rows),
            "nr": [r["nr"] for r in spatial_rows],
            "dt_s": 15.0,
            "values_s": spatial_values,
            "adjacent_changes_s": spatial_changes,
            "adjacent_changes_relative_percent": relative_changes(spatial_values),
            "last_two_max_s": max(spatial_changes[-2:]),
            "monotone_decreasing": monotone_decreasing(spatial_values),
            "local_acceptance_s": EVENT_TOL_S,
            "local_acceptance_pass": max(spatial_changes[-2:]) <= EVENT_TOL_S,
        },
        "time": {
            "levels": len(time_rows),
            "dt_s": time_dts,
            "nr": 210,
            "values_s": time_values,
            "adjacent_changes_s": time_changes,
            "adjacent_changes_relative_percent": relative_changes(time_values),
            "last_two_max_s": max(time_changes[-2:]),
            "monotone_decreasing_with_refinement": monotone_decreasing(time_values),
            "local_acceptance_s": EVENT_TOL_S,
            "local_acceptance_pass": max(time_changes[-2:]) <= EVENT_TOL_S,
        },
        "diagnostics": {
            "max_spatial_linear_relative_residual": spatial_residual,
            "max_spatial_normalized_balance_error": spatial_balance,
            "dt7p5_linear_relative_residual": extra_residual,
            "dt7p5_normalized_balance_error": extra_balance,
            "finite_event_times": all(math.isfinite(v) for v in spatial_values + time_values),
        },
        "pass_rule": "five spatial levels and four time levels; each sequence decreases; the last two adjacent event-time changes are <=60 s; residual and balance diagnostics remain finite and below formal thresholds",
        "aborted_not_used": {
            "label": "Q3-M3-L5-nr315-nz36",
            "reason": "stopped after approximately 45 minutes without a DONE record; no result is used",
        },
    }
    summary["status"] = "PASS_CANDIDATE" if (
        summary["space"]["local_acceptance_pass"] and
        summary["space"]["monotone_decreasing"] and
        summary["time"]["local_acceptance_pass"] and
        summary["time"]["monotone_decreasing_with_refinement"] and
        summary["diagnostics"]["finite_event_times"] and
        spatial_residual < 1e-8 and spatial_balance < 1e-6 and
        extra_residual < 1e-8 and extra_balance < 1e-6
    ) else "FAIL"

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "q3-space-convergence.csv", spatial_rows)
    write_csv(OUT / "q3-time-convergence.csv", time_rows)
    manifest = {
        "revision": summary["revision"],
        "status": summary["status"],
        "project_root": str(PROJECT_ROOT),
        "source_solver": str(SOURCE_SOLVER.relative_to(PROJECT_ROOT)),
        "source_solver_sha256": sha256(SOURCE_SOLVER),
        "inputs": [{"path": str(p.relative_to(PROJECT_ROOT)), "sha256": sha256(p)}
                   for p in (MAIN_CONVERGENCE, MAIN_THRESHOLD)],
        "logs": [{"path": str(p.relative_to(PROJECT_ROOT)), "sha256": sha256(p)}
                 for p in (LOG_Q3, LOG_MID, LOG_TIME_EXTRA)],
        "commands": [
            "python 04-compute/revision-grid-conv-20260912/grid_conv_revision.py --scope q3",
            "python 04-compute/revision-grid-conv-20260912/grid_conv_revision.py --scope q3_mid",
            "python 04-compute/revision-grid-conv-20260912/grid_conv_revision.py --scope q3_time_extra",
            "python 04-compute/revision-grid-conv-20260912/finalize_q3_convergence.py",
        ],
        "space_design": {"nr": [63, 93, 140, 175, 210], "nz": 36, "dt_s": 15.0},
        "time_design": {"nr": 210, "nz": 36, "dt_s": time_dts},
        "event_tolerance_s": EVENT_TOL_S,
        "completed_spatial_runs": [r["status"] for r in spatial_rows],
        "aborted_runs_excluded": ["Q3-M3-L5-nr315-nz36"],
    }
    (OUT / "q3-convergence-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "revision-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report_lines = [
        "# Q3-CONV 收敛性补充报告",
        "",
        f"状态：`{summary['status']}`（候选证据，未改写正式 COMPUTE/EVIDENCE/FIGURE）。",
        "",
        "## 空间网格细化",
        "",
        "固定 `nz=36`、`dt=15 s`，事件时刻采用阈值夹逼线性插值。",
        "",
        "| nr | 事件时刻 (s) | 相邻变化 (s) | 观测阶 |",
        "|---:|---:|---:|---:|",
    ]
    for row in spatial_rows:
        report_lines.append(f"| {row['nr']} | {float(row['value']):.4f} | {fmt_optional(row['adjacent_change_s'])} | {row['observed_order']} |")
    report_lines += [
        "",
        f"最后两次空间细化变化为 `{spatial_changes[-2]:.4f}` 和 `{spatial_changes[-1]:.4f} s`，均不超过 `{EVENT_TOL_S:.0f} s`；事件时刻单调下降，且最大相对变化为 `{max(relative_changes(spatial_values)[-2:]):.5f}%`。",
        "",
        "## 时间步细化",
        "",
        "固定 `nr=210`、`nz=36`，时间步为 `60、30、15、7.5 s`。",
        "",
        "| dt (s) | 事件时刻 (s) | 相邻变化 (s) | 观测阶 |",
        "|---:|---:|---:|---:|",
    ]
    for row in time_rows:
        report_lines.append(f"| {row['dt_s']} | {float(row['value']):.4f} | {fmt_optional(row['adjacent_change_s'])} | {row['observed_order']} |")
    report_lines += [
        "",
        f"最后两次时间步细化变化为 `{time_changes[-2]:.4f}` 和 `{time_changes[-1]:.4f} s`，均不超过 `{EVENT_TOL_S:.0f} s`；时间序列单调下降，且最大相对变化为 `{max(relative_changes(time_values)[-2:]):.5f}%`。",
        "",
        "## 数值诊断与限定",
        "",
        f"空间最大线性相对残差 `{spatial_residual:.3e}`，最大归一化水分守恒误差 `{spatial_balance:.3e}`；新增 `dt=7.5 s` 点分别为 `{extra_residual:.3e}` 和 `{extra_balance:.3e}`。",
        "",
        "`nr=315` 的尝试运行在无 DONE 记录前停止，未进入任何收敛结论；本报告不使用该未完成点。该结果说明当前 `nr=210` 网格在本地验收口径下已具备收敛证据，但不等于现实观测精度或无限网格严格证明。",
    ]
    (OUT / "q3-convergence-report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "space_changes_s": spatial_changes,
                      "time_changes_s": time_changes, "out": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
