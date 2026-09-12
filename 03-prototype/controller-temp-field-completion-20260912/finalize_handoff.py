"""Finalize small post-run summaries and a schema-compatible handoff.

The expensive solver run is complete.  This read-only postprocessor adds
explicit energy-refinement and Q2 sensitivity summaries, refreshes the human
reports, and removes non-schema metadata from handoff.json.  It writes only
inside this completion directory.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_csv(name: str):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(name: str, rows: list[dict]):
    path = OUT / name
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fnum(value, digits=4):
    if value is None or value == "":
        return "NA"
    return f"{float(value):.{digits}f}"


def energy_refinement():
    rows = read_csv("energy-audit-summary.csv")
    raw = read_csv("energy-audit.csv")
    out = []
    for impl in ("prescribed-T-baseline", "internal-temperature"):
        for q in ("Q2", "Q3", "Q4"):
            for ladder in ("spatial", "time", "joint"):
                levels = ["L", "M", "H"] if ladder != "joint" else ["L", "H"]
                vals = []
                for level in levels:
                    source_ladder, source_level = ladder, level
                    if ladder == "joint" and level == "M":
                        source_ladder, source_level = "spatial", "M"
                    summary = next((x for x in rows if x["implementation"] == impl and x["question"] == q and
                                    x["family"] == source_ladder and x["level"] == source_level), None)
                    selected = [x for x in raw if x["implementation"] == impl and x["question"] == q and
                                x["family"] == source_ladder and x["level"] == source_level]
                    if summary is None:
                        continue
                    if selected and "linear_solver_relative_residual_last" in selected[0]:
                        linear = max((float(x["linear_solver_relative_residual_last"]) for x in selected), default=None)
                    else:
                        # Backward-compatible refresh for the first run of
                        # this directory: original-results.csv already stores
                        # the source solver's matrix residual per case.
                        original = read_csv("原始结果.csv")
                        matching = [x for x in original if x.get("implementation") == impl and x.get("question") == q and
                                    x.get("family") == source_ladder and x.get("level") == source_level]
                        linear = max((float(x["max_linear_relative_residual"]) for x in matching
                                      if x.get("max_linear_relative_residual") not in (None, "")), default=None)
                    vals.append((level, summary.get("max_relative_residual"), linear, summary.get("cumulative_residual_J")))
                for i, (level, physical, linear, cumulative) in enumerate(vals):
                    previous = vals[i - 1] if i else None
                    delta = None if previous is None or physical in (None, "") or previous[1] in (None, "") else abs(float(physical) - float(previous[1]))
                    if impl == "prescribed-T-baseline":
                        status = "NOT_APPLICABLE"
                    elif physical in (None, ""):
                        status = "BLOCKED"
                    elif previous is None:
                        status = "REFERENCE"
                    else:
                        status = "DECREASES" if float(physical) <= float(previous[1]) else "INCREASES"
                    out.append({"implementation": impl, "question": q, "ladder": ladder, "level": level,
                                "physical_max_relative_residual": physical, "linear_max_relative_residual": linear,
                                "cumulative_residual_J": cumulative, "adjacent_physical_change": delta,
                                "refinement_status": status})
    write_csv("energy-refinement.csv", out)
    return out


def sensitivity_summary():
    raw = read_csv("parameter-sensitivity.csv")
    out = []
    for q in ("Q2", "Q3", "Q4"):
        for parameter in ("h", "hm", "rho", "cp", "k"):
            selected = [x for x in raw if x["question"] == q and x["parameter"] == parameter]
            base = next((x for x in raw if x["question"] == q and x["parameter"] == "base"), {})
            low = next((x for x in selected if x["level"] == "low"), {})
            high = next((x for x in selected if x["level"] == "high"), {})
            metric = "final_max_C" if q == "Q2" else "t_star_s"
            lo, mid, hi = low.get(metric), base.get(metric), high.get(metric)
            span = None if lo in (None, "") or hi in (None, "") else abs(float(hi) - float(lo))
            out.append({"question": q, "parameter": parameter, "metric": metric,
                        "low": lo, "base": mid, "high": hi, "low_high_span": span,
                        "source_status": "audit envelope; not identified"})
    write_csv("parameter-sensitivity-summary.csv", out)
    return out


def refresh_reports(energy_rows, sensitivity_rows):
    # Add a compact, explicit energy conclusion to the existing report.
    energy = """# 移动域能量库存审计\n\n## 审计口径\n\n候选热方程按 `ΔE_sensible = Q_boundary + Q_latent + R` 审计。`E_sensible=∫rho cp (T-T0)dV`，内部导热通量在相邻控制体中成对抵消但保留绝对通量规模；`Q_boundary` 是侧面/端面 Robin 热通量积分；`Q_latent=0` 是本轮明确省略的项，不是由数据识别出的零潜热；`R` 是显热库存变化减去边界热量和潜热项的残差。\n\n## 结果\n\n|问题|实现|梯子|显热残差最大相对值|线性收支残差最大相对值|相邻细化趋势|判断|\n|---|---|---|---:|---:|---|---|\n"""
    for row in energy_rows:
        energy += f"|{row['question']}|{row['implementation']}|{row['ladder']}-{row['level']}|{fnum(row.get('physical_max_relative_residual'),4)}|{fnum(row.get('linear_max_relative_residual'),6)}|{row.get('refinement_status')}|"
        if row["implementation"] == "prescribed-T-baseline":
            energy += "NOT_APPLICABLE|\n"
        elif row.get("physical_max_relative_residual") in (None, ""):
            energy += "BLOCKED|\n"
        else:
            energy += ("INCONCLUSIVE: 物理显热库存未闭合|\n" if row.get("refinement_status") in ("INCREASES", "DECREASES", "REFERENCE") else "BLOCKED|\n")
    energy += """\n## 关键结论\n\n- 线性离散方程的单步 `linear_max_relative_residual` 接近求解器尺度，说明线性系统本身能复核。\n- 但将 Picard 更新后的 `rho*cp` 与温度共同形成物理显热库存后，Q2/Q3 的最大相对库存残差约为 1.90–1.98，Q4 约为 1.53–1.99；这些量级远大于线性收支残差，且随细化并未稳定降到报告容差。\n- 因此当前候选只能证明“求解器产生了内部温度场”，不能证明当前无潜热、可变热容口径已经完成能量闭合。Q4 移动域还额外承担几何变化项，正式升级必须补上可审计的几何/焓/边界通量合同。\n- 基线没有温度 PDE；其能量审计为 `NOT_APPLICABLE`，不能把强制赋值温度当作热能守恒证据。\n\n逐步数据在 `energy-audit.csv`，三层趋势在 `energy-refinement.csv`；每个核心算例的明细在 `model-internal-temperature/.../energy-groups.csv`。\n"""
    (OUT / "移动域能量审计.md").write_text(energy, encoding="utf-8")

    # Replace the sensitivity report with Q2 field effects plus Q3/Q4 event effects.
    sens = """# 参数区间敏感性结果\n\n本轮在 8×8 诊断网格、预设时间步上，对 `h`、`hm`、`rho`、`cp`、`k` 做 0.8/1.0/1.2 单因素扰动。该区间是围绕已批准公式或冻结边界值的审计包络，不是识别置信区间。\n\n## Q2 三小时场量\n\n|参数|低值 final max C|基准 final max C|高值 final max C|低-高跨度|\n|---|---:|---:|---:|---:|\n"""
    for row in sensitivity_rows:
        if row["question"] == "Q2":
            sens += f"|{row['parameter']}|{fnum(row.get('low'),7)}|{fnum(row.get('base'),7)}|{fnum(row.get('high'),7)}|{fnum(row.get('low_high_span'),7)}|\n"
    sens += """\n## Q3/Q4 首次事件\n\n|问题|参数|低值事件(s)|基准事件(s)|高值事件(s)|跨度(s)|\n|---|---|---:|---:|---:|---:|\n"""
    for row in sensitivity_rows:
        if row["question"] in ("Q3", "Q4"):
            sens += f"|{row['question']}|{row['parameter']}|{fnum(row.get('low'),1)}|{fnum(row.get('base'),1)}|{fnum(row.get('high'),1)}|{fnum(row.get('low_high_span'),1)}|\n"
    sens += """\n## 来源与识别边界\n\n- `rho/cp/k` 的基线公式来自批准合同；P05 仅提供不同材料的密度类比，`cp/k` 没有本题材料独立来源，故均标为不可识别。\n- `h/hm` 的批准值来自 H1；P06/P08 的值对应不同材料、几何或驱动力定义，只用于说明量纲/量级风险，不能直接迁移。\n- 敏感性结果支持风险排序，不支持反演出唯一物性；不能用同一含水率结果同时拟合 `rho/cp/k/h/hm`。完整来源表见 `parameter-sources.md`。\n"""
    (OUT / "参数区间敏感性.md").write_text(sens, encoding="utf-8")

    # Insert the measured energy result into the decision package while keeping
    # the team-choice block and all three options unchanged.
    h2_path = OUT / "H2-选择包.md"
    h2 = h2_path.read_text(encoding="utf-8")
    marker = "## 五、最小补测方案"
    addition = """## 五、按本轮实际审计结果的门槛判断\n\n- 三层空间和三层时间的事件误差都仍是数百至数千秒；例如候选 Q3 空间 H 相对 M 仍约 3087 s，时间 H 相对 M 仍约 472 s，候选 Q4 分别约 1235 s 和 355 s，均未达到 60 s 报告门槛。\n- Q2/Q3/Q4 的显热库存残差没有形成随细化下降到零的证据；线性求解残差小不等于含可变 `rho*cp` 的物理能量闭合。\n- 因此本轮的三种结果是：**支持升级为“数值内部温度状态”候选；正式主路线证据不足需补测；无来源潜热/完整热湿升级不支持。**\n\n"""
    if marker in h2 and "## 五、按本轮实际审计结果的门槛判断" not in h2:
        h2 = h2.replace(marker, addition + marker)
    h2 = h2.replace("## 五、最小补测方案", "## 六、最小补测方案")
    h2 = h2.replace("## 六、已进行的优化与后续优化方向", "## 七、已进行的优化与后续优化方向")
    h2 = h2.replace("## 七、交接文件", "## 八、交接文件")
    h2_path.write_text(h2, encoding="utf-8")

    # Add the explicit summary file to the comparison report without changing
    # its original numerical table.
    comp_path = OUT / "候选方案对比.md"
    comp = comp_path.read_text(encoding="utf-8")
    marker = "## 5. 运行与失败记录"
    addition = """## 5. 能量审计结论\n\n本轮将“线性方程收支”与“显热库存收支”分开。候选的线性系统残差接近求解器尺度，但显热库存残差在 Q2/Q3/Q4 均未随细化稳定降到容差；Q4 还存在移动几何项。基线因没有温度 PDE，能量审计为不适用。这个结果阻止把内部温度候选直接升级为正式热湿主路线，但不否定其作为数值状态候选的运行证据。\n\n"""
    if marker in comp and "## 5. 能量审计结论" not in comp and "## 5.1 能量审计结论" not in comp:
        comp = comp.replace(marker, addition + marker)
    comp = comp.replace("## 5.1 能量审计结论", "## 5. 能量审计结论")
    comp = comp.replace("## 5. 运行与失败记录", "## 6. 运行与失败记录")
    comp_path.write_text(comp, encoding="utf-8")


def valid_handoff():
    old = json.loads((OUT / "handoff.json").read_text(encoding="utf-8"))
    files = []
    for p in sorted(OUT.rglob("*")):
        if not p.is_file() or p.name in {"handoff.json", "manifest.json"}:
            continue
        if "__pycache__" in p.parts or p.suffix.lower() in {".pyc", ".pyo"}:
            continue
        files.append({"path": rel(p), "sha256": sha256(p)})
    input_items = [{"path": x["path"], "sha256": x["sha256"]} for x in old.get("inputs", [])]
    frozen = [{"path": x["path"], "sha256": x["sha256"]} for x in old.get("frozen_decisions", [])]
    handoff = {
        "schema_version": "1.0",
        "stage": "PROTOTYPE",
        "status": "PASS",
        "inputs": input_items,
        "outputs": files,
        "frozen_decisions": frozen,
        "assumptions": old.get("assumptions", []),
        "unknowns": old.get("unknowns", []),
        "claims": old.get("claims", []),
        "evidence": [
            "原始结果.csv and paired-comparison.csv contain 48 core paired runs; space/time/joint CSVs separate the refinement controls.",
            "energy-audit.csv and energy-refinement.csv separate linear solve residuals from physical sensible-inventory residuals.",
            "parameter-source-register.csv and parameter-sensitivity.csv record source status and bounded perturbations for rho, cp, k, h and hm.",
            "validation-register.csv records PASS, INCONCLUSIVE and BLOCKED gates without converting missing internal observations into validation.",
        ],
        "warnings": old.get("warnings", []),
        "required_next_actions": old.get("required_next_actions", []),
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    (OUT / "handoff.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {"inputs": old.get("inputs", []), "outputs": files, "handoff_sha256": sha256(OUT / "handoff.json")}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    energy_rows = energy_refinement()
    sensitivity_rows = sensitivity_summary()
    refresh_reports(energy_rows, sensitivity_rows)
    valid_handoff()
    print(json.dumps({"status": "PASS", "energy_refinement_rows": len(energy_rows),
                      "sensitivity_summary_rows": len(sensitivity_rows), "handoff": str(OUT / "handoff.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
