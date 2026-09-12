from __future__ import annotations

import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[1]
SEED = 20260912


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def rhs(state: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Dimensionless phase-change toy; diagnostic only, not material calibration."""
    liquid, vapor, temp = state
    a_v, k_evap, latent, eq_scale = np.exp(p)
    # Deliberately omit temperature feedback in this structural baseline.
    # If c_v,eq(T, S_l) is later supplied, latent heat can affect C indirectly
    # through T; that conditional case is not identified by the current data.
    v_eq = 0.10 + eq_scale * 0.30
    gamma = k_evap * (v_eq - vapor)
    return np.array(
        [
            -0.12 * liquid - gamma,
            gamma - a_v * vapor,
            0.42 * (0.78 - temp) - latent * gamma,
        ],
        dtype=float,
    )


def integrate(p: np.ndarray, n: int = 1201, t_end: float = 8.0) -> tuple[np.ndarray, np.ndarray]:
    times = np.linspace(0.0, t_end, n)
    states = np.empty((n, 3), dtype=float)
    states[0] = [0.82, 0.06, 0.20]
    for i in range(n - 1):
        dt = times[i + 1] - times[i]
        x = states[i]
        k1 = rhs(x, p)
        k2 = rhs(x + 0.5 * dt * k1, p)
        k3 = rhs(x + 0.5 * dt * k2, p)
        k4 = rhs(x + dt * k3, p)
        states[i + 1] = x + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
    return times, states


def observations(p: np.ndarray, mode: str) -> np.ndarray:
    _, x = integrate(p)
    total = x[:, 0] + x[:, 1]
    if mode == "C_only":
        return total
    if mode == "C_T":
        return np.column_stack([total, x[:, 2]]).ravel()
    if mode == "C_T_vapor":
        return np.column_stack([total, x[:, 2], x[:, 1]]).ravel()
    raise ValueError(mode)


def jacobian(p: np.ndarray, mode: str) -> np.ndarray:
    cols = []
    for j in range(len(p)):
        step = 1e-5
        plus = p.copy()
        minus = p.copy()
        plus[j] += step
        minus[j] -= step
        cols.append((observations(plus, mode) - observations(minus, mode)) / (2 * step))
    return np.column_stack(cols)


def identifiability_rows() -> list[dict[str, object]]:
    p = np.log(np.array([0.35, 0.80, 0.60, 1.0], dtype=float))
    rows: list[dict[str, object]] = []
    for mode in ["C_only", "C_T", "C_T_vapor"]:
        J = jacobian(p, mode)
        norms = np.linalg.norm(J, axis=0)
        scaled = J / np.maximum(norms, 1e-15)
        singular = np.linalg.svd(scaled, compute_uv=False)
        rank = int(np.sum(singular > 1e-8))
        cond = float(singular[0] / singular[-1]) if rank == len(p) else math.inf
        rows.append(
            {
                "observation_set": mode,
                "parameters": "a_v,k_evap,L_v,eq_scale",
                "n_observations": int(J.shape[0]),
                "rank_at_tol_1e-8": rank,
                "condition_number_scaled": cond,
                "singular_values": ";".join(f"{v:.6e}" for v in singular),
                "decision": "NON_IDENTIFIABLE" if rank < len(p) or cond > 1e8 else "DIAGNOSTIC_ONLY",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    keys = list(rows[0])
    lines = [",".join(keys)]
    for row in rows:
        vals = []
        for key in keys:
            value = row[key]
            text = str(value).replace('"', '""')
            vals.append(f'"{text}"')
        lines.append(",".join(vals))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def source_audit() -> list[dict[str, object]]:
    rels = [
        "decisions/H1-problem.json",
        "decisions/H2-model.json",
        "decisions/H3-claims.json",
        "02-design/handoff.json",
        "02-design/H2-优化审计与方向.md",
        "02-design/contracts/model-q23-fixed.json",
        "02-design/contracts/model-q4-m1-reference.json",
        "02-design/contracts/model-q4-m2-moving-fv.json",
        "02-design/supplemental-extensions/model-cfd.json",
        "02-design/supplemental-extensions/扩展模型设计.md",
        "02-design/supplemental-extensions/统一比较合同.json",
        "02-literature/文献阅读结果.md",
        "04-compute/results/key-metrics.json",
        "04-compute/results/validation-register.csv",
        "input/A题/附件/附件1.xlsx",
        "input/A题/附件/附件2.xlsx",
    ]
    records = []
    for rel in rels:
        path = PROJECT / rel
        records.append({"path": rel, "exists": path.exists(), "sha256": sha256(path) if path.exists() else None})
    return records


def report(ident_rows: list[dict[str, object]], sens_rows: list[dict[str, object]]) -> str:
    first = ident_rows[0]
    second = ident_rows[1]
    third = ident_rows[2]
    sens_lines = "\n".join(
        f"| {r['factor']} | {r['relative_change']} | {r['delta_C_final']:.6g} | {r['delta_T_final']:.6g} |"
        for r in sens_rows
    )
    return f"""# 潜热—液汽—结合水候选原型研究报告

状态：**BLOCKED / unsupported for high-fidelity promotion**。本目录是 `03-prototype/controller-phase-change-20260912/` 的独立候选证据，不修改 M1–M4、COMPUTE、EVIDENCE、FIGURE 或 PAPER。

## 1. 结论先行

当前附件只能支持外界温度/水分边界历程和收缩半径；没有液相/汽相/结合水分辨观测、内部温湿剖面、孔隙率、渗透率、毛细曲线、相对渗透率、蒸汽有效扩散率、相变速率或本题材料的潜热测量。因此：

- “显式加入相变量”在守恒结构上**可写出**，但在本题数据上**不可识别、不可验证**；
- `L_v` 与 `Gamma` 不能用当前单场 `C,T` 或边界数据分开识别；
- 已有 `D(C,T)` 是等效迁移项，若再并列加入 `j_l` 与 `j_v` 而不重标定，会重复计数；
- 现有低成本 toy 只验证了退化方向，不能提供材料参数或现实精度证据。

## 2. 与冻结主模型的重复计数风险

当前 Q2–Q4 使用单一总含水率 `C` 和状态相关有效系数 `D(C,T)`。`D` 已经把可观测尺度上的多种迁移阻力 lump 成一个系数。直接添加液相毛细通量、汽相扩散通量和 `Gamma` 会有四类风险：

1. `D(C,T)` 与 `j_l+j_v` 同时承担总水分迁移，导致传输路径加和两次；只有将 `D` 替换成相分辨通量的导出量或重新反演，才可比较。
2. 冻结的 `h_m(C_s-C_∞)` 已规定总边界水通量；再单独给液/汽表面蒸发通量，若没有相分配规则，会重复计数或破坏总量守恒。
3. 冻结的 `rho(C), cp(C), k(C)` 是有效物性；相变量加入后，若仍保留原有效储热项并再加液/汽显热，可能重复计入热容。
4. Q4 已用观测 `R(t)` 和固体连续性处理收缩；再用 `phi(S_l)`、渗透率和体积变化自由更新几何，会把观测边界和新孔隙闭合混在一起，必须先选定唯一的几何/密度语义。

总水量必须以 `m_w = rho_d C = m_l+m_v(+m_b)` 的体积库存解释，不能把无密度的 `C` 直接当作质量积分。

## 3. 最小一致候选结构

以总湿体积为控制体，令 `S_l` 为液相饱和度，`c_v` 为气相孔隙水蒸气密度（kg/m^3 气相），`b` 为结合水干基含量（kg/kg 干固体，可选），`phi` 为孔隙率，`Gamma_lv` 为液—汽相变质量源（kg/m^3/s）：

\\[
 m_l=\\phi rho_l S_l,\\quad m_v=\\phi(1-S_l)c_v,\\quad m_b=rho_d b.
\\]

最小两相质量闭合为

\\[
 \\partial_t m_l+\\nabla\\cdot j_l=-Gamma_lv,\\qquad
 \\partial_t m_v+\\nabla\\cdot j_v=+Gamma_lv.
\\]

例如可写 `j_l=-rho_l K k_rl(S_l)/mu_l grad p_c(S_l)`，`j_v=-phi(1-S_l)D_v,eff grad c_v`，以及 `Gamma_lv=k_evap(c_v,eq(T,S_l)-c_v)`；这只是结构候选，当前没有许可把其中参数数值化。

若显式加入结合水，至少要增加

\\[
 \\partial_t m_b+\\nabla\\cdot j_b=-Gamma_b,
\\]

并在液/汽方程右端加入 `Gamma_b` 的分配项；`Gamma_b`、`b_eq(T,RH)` 或 `D_b` 必须由结合水实验识别。三式相加后必须得到 `\\partial_t(m_l+m_v+m_b)+\\nabla\\cdot(j_l+j_v+j_b)=0`。

在不考虑相流显热输运的最低阶能量式中，令 `C_h` 是一次且仅一次定义的体积热容：

\\[
 C_h\\partial_t T=\\nabla\\cdot(k_eff\\nabla T)-L_v Gamma_lv-Q_b.
\\]

`-L_v Gamma_lv` 的单位是 W/m^3；`L_v` 只有在 `Gamma_lv` 的质量基准明确为 kg/m^3/s 时才能使用 J/kg。若表面发生汽化，还需在边界能量通量中明确 `L_v J_v,out`；同一汽化事件不能同时作为体内 `Gamma_lv` 和表面潜热再次计入。

总水分边界应先固定总通量口径，例如当前干基模型的候选写法

\\[
 J_w^out=rho_d h_m(C_s-C_\\infty),\\qquad
 n\\cdot(j_l+j_v+j_b)=J_w^out,
\\]

并另外规定 `J_l,out+J_v,out(+J_b,out)=J_w^out`。只有总通量观测时，液/汽边界分配不可识别；若使用蒸汽 Robin 边界，还必须提供 `c_v,∞`、界面平衡和相应传质系数。

## 4. 来源和数据需求审计

| 量/关系 | 当前真实来源 | 结论 |
|---|---|---|
| `T_∞(t), C_∞(t)` | 附件 1，241 点、60 s 间隔 | 有，但只是环境边界 |
| `R(t)` | 附件 2，145 点、1800 s 间隔 | 有，且主路线已使用 |
| `rho_d`, `D(C,T)`, `h`, `h_m`, `k`, `cp` | H1/H2 冻结的题设/经验口径 | 只支持当前等效路线，不自动拆成相参数 |
| `phi`, `K`, `p_c(S_l)`, `k_rl`, `D_v,eff` | 附件与 H1/H2 均无 | 缺失；文献只能给结构，不能跨材料移植数值 |
| `Gamma_lv`, `k_evap`, `c_v,eq` | 无相分辨实验/汽相浓度序列 | 缺失且相互混淆 |
| `L_v` | 需明确材料/温度/压力口径；当前项目无本题实测来源 | 不能以通用常数替代“本题可验证参数” |
| 结合水 `b`, `b_eq`, `Gamma_b` | 无吸附/解吸或结合水实验 | 缺失 |
| `T(r,t), C(r,t), c_v(r,t), S_l(r,t)` | 附件 3 是输出模板，不是独立内部观测 | 无验证数据 |

P07 只支持热—蒸汽—液态水耦合的结构及“总失重不保证内部场”的验证警告；P10/P15 支持多尺度/结合水机制会增加参数负担。已有文献交接明确禁止把跨材料参数直接迁移。

## 5. 符号、量纲和低成本识别证据

本实验采用无量纲 toy ODE，仅测试观测结构，不模拟药材，也不拟合附件。参数为正的无量纲 `a_v,k_evap,L_v,eq_scale`，观测集分别为总含水量 `C_total`、`(C_total,T)` 和 `(C_total,T,c_v)`。`Gamma` 只以 `k_evap(c_eq-c_v)` 的结构出现。

| 观测集 | Jacobian 秩（4 参数） | 缩放条件数 | 判断 |
|---|---:|---:|---|
| `C_total` | {first['rank_at_tol_1e-8']} | {first['condition_number_scaled']} | `L_v` 不进入水分守恒观测，结构性不可识别 |
| `C_total,T` | {second['rank_at_tol_1e-8']} | {second['condition_number_scaled']:.3e} | 即使有整体温度，也只可作 toy 诊断；不等于本题可识别 |
| `C_total,T,c_v` | {third['rank_at_tol_1e-8']} | {third['condition_number_scaled']:.3e} | 增加汽相观测后才有机会区分相变和汽相损失，但仍需独立材料参数/重复工况 |

单因素 toy 扰动（仍为无量纲，不可回填主模型）如下：

| 因子 | 相对变化 | `Delta C_final` | `Delta T_final` |
|---|---:|---:|---:|
{sens_lines}

解释边界：toy 中潜热只通过能量方程影响温度，若没有内部温度观测，它对 `C_total` 没有独立信号；即便有温度，`L_v`、`k_evap` 与平衡关系会形成强相关。已有项目的附件只有环境温度和含水边界，不能通过该 toy 反向创造可识别性。

## 6. 支持结论与拒绝标准

| 项目 | 当前判定 |
|---|---|
| 守恒方程可写性 | 支持：两相/三池结构可定义，且总库存可相加 |
| 当前数据闭合 | 不支持：相变量、边界分配、参数和内部观测缺失 |
| `L_v`/`Gamma` 分开识别 | 不支持 |
| 仅以现有 `C,T` 单场结果验证相机制 | 不支持；会把等效项与新机制混淆 |
| 是否进入主模型 | 拒绝/回退到冻结 M3/M4 |

任一项出现以下情形，候选直接拒绝：

1. 单相极限不能在合并离散误差内回归冻结 M3/M4；
2. `m_l+m_v(+m_b)` 与边界积分不闭合，细化后残差不降或超过预注册 `1e-5`；
3. `L_v`、`k_evap`、平衡关系或相边界分配的 profile interval 触及边界，或 Jacobian 条件数大于 `1e8`；
4. 仅靠调 `D(C,T)`、`h_m` 或潜热项解释同一段总含水曲线，无法用独立 `c_v/S_l/b/T(r,t)` 证伪；
5. 把总失重/总含水率拟合改善写成相机制验证，或把跨材料文献参数直接移植；
6. Q4 同时自由更新 `R(t)`、`phi` 和固体密度，导致几何/库存语义不唯一。

## 7. 进入 H2 前的最小补充数据

优先级最低但足以解除当前 BLOCKED 的组合是：

1. 同一批次、同一工况的样品质量/总含水率、中心—表面温度剖面和至少一个内部时序点；
2. 独立汽相证据：孔隙/表面水蒸气浓度或 RH，最好有 `c_v(r,t)`；
3. 相分辨水量：低场 NMR、DSC/TGA 或等效方法分离自由/液态与结合水，并重复至少 3 个工况；
4. `phi(C,T)`、干基密度 `rho_d` 和收缩/体积同步测量，避免 `phi` 与 `rho_d` 共线；
5. 渗透率/毛细压力/相对渗透率或允许固定的独立材料测量；至少得到 `K|p_c'|` 的尺度，而不是分别自由拟合；
6. 本材料、本工况下的相变动力学 `k_evap` 和平衡关系 `c_v,eq(T,S_l)`，并用阶段变化覆盖恒速与降速期；
7. 若保留潜热：温度相关 `L_v(T,p)` 的来源和表面/体内汽化位置；能量计量必须与质量通量同步。

在这些数据到位前，最小成本方案是只做无量纲结构审计、单相极限回归和合成数据上的 profile-identifiability 试验；不要把 toy 或现有缩减 CFD 的示例参数并入主模型。
"""


def main() -> None:
    started = time.perf_counter()
    np.random.seed(SEED)
    ident_rows = identifiability_rows()
    write_csv(OUT / "identifiability.csv", ident_rows)

    base = np.log(np.array([0.35, 0.80, 0.60, 1.0], dtype=float))
    factors = [("a_v", 1.20, 0), ("k_evap", 1.20, 1), ("L_v", 1.20, 2), ("eq_scale", 1.20, 3)]
    _, x0 = integrate(base)
    c0 = x0[-1, 0] + x0[-1, 1]
    t0 = x0[-1, 2]
    sens_rows = []
    for name, multiplier, idx in factors:
        p = base.copy()
        p[idx] += math.log(multiplier)
        _, x = integrate(p)
        sens_rows.append(
            {
                "factor": name,
                "relative_change": f"x{multiplier:.2f}",
                "delta_C_final": float(x[-1, 0] + x[-1, 1] - c0),
                "delta_T_final": float(x[-1, 2] - t0),
            }
        )
    write_csv(OUT / "sensitivity.csv", sens_rows)

    checks = {
        "state_units": {"m_l": "kg/m3_bulk", "m_v": "kg/m3_bulk", "m_b": "kg/m3_bulk", "Gamma": "kg/m3/s"},
        "flux_units": {"j_l": "kg/m2/s", "j_v": "kg/m2/s", "J_boundary": "kg/m2/s"},
        "energy_units": {"C_h_dTdt": "W/m3", "div_k_grad_T": "W/m3", "Lv_Gamma": "W/m3"},
        "dimensionless_toy_warning": "toy parameters are not material values and must not enter M1-M4",
    }
    dump(OUT / "symbolic_checks.json", checks)
    dump(OUT / "toy_results.json", {"seed": SEED, "identifiability": ident_rows, "sensitivity": sens_rows, "claim_limit": "dimensionless structural diagnostic only"})

    audit = source_audit()
    dump(OUT / "source-audit.json", audit)
    report_text = report(ident_rows, sens_rows)
    (OUT / "候选方案对比.md").write_text(report_text, encoding="utf-8")
    (OUT / "H2-选择包.md").write_text(
        "# H2 选择包（候选扩展，不推进团队闸门）\n\n"
        "结论：**BLOCKED / unsupported**。守恒结构可定义，但当前附件没有相分辨状态、内部场或材料参数，不能支持潜热—液汽—结合水扩展进入主模型。\n\n"
        "- 保留：符号守恒结构、量纲检查、无量纲识别诊断、拒绝标准和补充数据清单。\n"
        "- 回退：冻结 M3/M4；不得并入 `D(C,T)`、`h_m` 或 H3 图表。\n"
        "- 已进行的优化与后续优化方向：已实施了总库存相加、单相/观测集识别诊断和潜热边界重复计数审计；未实施真实多相求解、参数拟合或高分辨率事件比较。后续仅在补齐相分辨实验后做 profile-identifiability、单相极限回归和守恒/能量闭合。\n\n"
        "详细证据见 `候选方案对比.md`、`identifiability.csv`、`sensitivity.csv` 和 `source-audit.json`。",
        encoding="utf-8",
    )

    command = f'"{sys.executable}" -B 03-prototype/controller-phase-change-20260912/run_controller_phase_change.py'
    manifest = {
        "schema_version": "1.0",
        "status": "BLOCKED",
        "scope": "independent latent-heat / liquid-vapor / bound-water candidate probe",
        "seed": SEED,
        "command": command,
        "runtime_s": time.perf_counter() - started,
        "environment": {"python": sys.version, "executable": sys.executable, "platform": platform.platform(), "numpy": np.__version__},
        "inputs": audit,
        "outputs": [],
        "claims": ["symbolic and dimensional structure is internally consistent", "current task data do not identify phase-resolved extension", "toy evidence is diagnostic only"],
        "unknowns": ["no phase-resolved observations", "no material-specific Lv/Gamma/equilibrium/porosity/permeability source", "no independent internal T/C profiles"],
        "warnings": ["do not promote to M1-M4", "do not treat toy parameters as physical values", "do not infer reality from reduced CFD examples"],
    }
    (OUT / "run.log").write_text(
        f"status=BLOCKED\nseed={SEED}\ncommand={command}\nruntime_s={manifest['runtime_s']:.6f}\n"
        f"C_only_rank={ident_rows[0]['rank_at_tol_1e-8']}\nC_T_rank={ident_rows[1]['rank_at_tol_1e-8']}\nC_T_vapor_rank={ident_rows[2]['rank_at_tol_1e-8']}\n",
        encoding="utf-8",
    )
    output_files = [p for p in sorted(OUT.rglob("*")) if p.is_file() and p.name not in {"复现清单.json", "handoff.json"}]
    manifest["outputs"] = [{"path": p.relative_to(PROJECT).as_posix(), "sha256": sha256(p)} for p in output_files]
    dump(OUT / "复现清单.json", manifest)
    handoff = {
        "schema_version": "1.0",
        "stage": "PROTOTYPE",
        "status": "BLOCKED",
        "scope": "controller-phase-change candidate only; primary route unchanged",
        "inputs": audit,
        "outputs": manifest["outputs"] + [{"path": (OUT / "复现清单.json").relative_to(PROJECT).as_posix(), "sha256": sha256(OUT / "复现清单.json")}],
        "frozen_decisions": [x for x in audit if x["path"] in {"decisions/H1-problem.json", "decisions/H2-model.json", "decisions/H3-claims.json"}],
        "assumptions": ["the toy is dimensionless and not a calibration", "M1-M4 and all upstream folders are read-only"],
        "unknowns": manifest["unknowns"],
        "claims": manifest["claims"],
        "warnings": manifest["warnings"],
        "required_next_actions": ["obtain phase-resolved internal data and material-specific closure before any H2 reconsideration", "keep M1-M4 unchanged"],
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    dump(OUT / "handoff.json", handoff)
    print(json.dumps({"status": "BLOCKED", "identifiability": ident_rows, "runtime_s": manifest["runtime_s"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
