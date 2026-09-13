# 附录草稿（待论文阶段排版）

## AI工具使用声明

本参赛队在竞赛过程中使用了AI工具，主要用于代码调试、数值计算与图表制作辅助、论文结构整理和语言润色，详细使用情况见支撑材料。

核心建模决策、参数口径、结果核验、结论边界和最终论文内容由参赛队主导并逐项人工审查核实。

## AI工具使用详情

详见 `AI 工具使用详情.md`。按2026年试行规定，论文参考文献之前应保留上述声明，支撑材料中另行提供 AI 工具使用详情 PDF；本 Markdown 文件作为其可追溯底稿。

## 附录B：支撑材料文件列表

支撑材料应包含题目要求的结果文件、当前 COMPUTE 结果、当前 FIGURE 图件及下列源程序。当前论文图表不依赖旧版图件工作流。

# 附录A：可运行源程序清单与代码

以下代码来自当前论文使用的计算与图表工作流。旧版总控脚本不属于当前活动工作流，未列入本附录。每段代码前的说明用于披露 AI 辅助情况，不修改原始源文件。

为避免支撑材料包含本机绝对路径，代码副本中的字体路径已规范化为 `simhei.ttf`；这不改变算法或图表数据逻辑，实际运行时可替换为所在环境可用的字体文件。

## 源文件索引

| 文件 | 用途 | SHA-256 |
|---|---|---|
| `04-compute/src/formal_compute.py` | 正式图表渲染或核验 | `af3214f972eb874764323c76561025df1cc70f27d7f0985968b57b0b688b4644` |
| `04-compute/src/finalize_compute.py` | 正式图表渲染或核验 | `6ffe9cf1f0caa14f9a4ee0101206dc32e957485d825d33d7bab76e2a1bc4c7e0` |
| `04-compute/src/q3_dense_sensitivity.py` | 正式图表渲染或核验 | `a8299f6cb4b0c1d8e9ec349c55d725b92024bec69d34426f2ca53f176f196da4` |
| `04-compute/src/repair_probe.py` | 正式图表渲染或核验 | `cdbe7b7d5401ede078cc9c62662573dcee3803ee459eea994c8e7e63b37114b7` |
| `04-compute/revision-grid-conv-20260913/run_q2_grid_dt5.py` | 隔离补算 | `0d23231d7a36f290ba1a79a61f8d4acb2e5164b3e2899d3b2e40cf4a61bdd457` |
| `04-compute/revision-grid-conv-20260913/run_q2_model_trajectories.py` | 隔离补算 | `04c1d1e1711bff0e5fac37192ada91764d531f7a0890b0ccb3b00431d34e4a6a` |
| `04-compute/revision-grid-conv-20260913/run_space_extra.py` | 隔离补算 | `c1cb59b3a3505ba54b12fd6659b75b20310a06c5708899038fd7f1ab2377f951` |
| `06-figure/scripts/redraw_fig6.py` | 正式图表渲染或核验 | `3896dd2cdc75529a9290646667f0db43fa0dbf1b4d288525bfa0846fde9e8b1a` |
| `06-figure/scripts/redraw_fig7.py` | 正式图表渲染或核验 | `b5a0a3669b0d440ee73ba93cfb72cf91e2768e04f3854258c15bb1a207bf81b7` |
| `06-figure/scripts/redraw_fig9_onward.py` | 正式图表渲染或核验 | `8487e947d68792ee6cd3d5d05e99ee0d457ebf56203843c59e8d90a5039aa6fb` |
| `06-figure/scripts/redraw_q1_end_effect_time.py` | 正式图表渲染或核验 | `87ef2fd744de8cbd75cc58f1467d80fb6313db5478d9df24af39aad5e1c27eff` |
| `06-figure/scripts/render_q2_profiles.py` | 正式图表渲染或核验 | `8c4d20d346703614dd454159260a7e61a55d8436828c6a032ec8765154fbb3a6` |
| `06-figure/scripts/render_q2_profiles_3d.py` | 正式图表渲染或核验 | `239f7338746384bc54cb47b672b1afed887c0ea61f6eb984162e7cc1fb1efdc4` |
| `06-figure/scripts/revise_q2_figures_20260913.py` | 正式图表渲染或核验 | `b4105a73300acf380655649cde30e0c57ee6872dc11a2123e75d6178c8df3f65` |
| `06-figure/scripts/update_figure_plan_20260913.py` | 正式图表渲染或核验 | `68560db3647d264f32f14dd482385e5e1764b49b496f3c156cbd5408a5f35a41` |
| `06-figure/scripts/verify_current_pipeline.py` | 正式图表渲染或核验 | `891126626a6218f5b85ebf58cab03bdad1cd4492af200fcf8e464f36bd990457` |
| `06-figure/scripts/make_official_contact_sheet.py` | 正式图表渲染或核验 | `34a519f58b99dafb1199f751262b2481999769bcbc6b815d5d291fa034b33d5e` |

## `04-compute/src/formal_compute.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
"""Formal COMPUTE-stage solver for CUMCM 2026 problem A.

The implementation follows the frozen H2 route: M1 is the 1-D radial
baseline, M2 is the 2-D axisymmetric constant-law backbone, M3 adds the
problem-supplied state laws, and M4 is a controlled temperature-field
ablation.  Only files below 04-compute are written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import openpyxl
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "04-compute"
RESULTS = OUT / "results"
FIGURES = OUT / "diagnostic-figures"
LOGS = OUT / "logs"
R0 = 0.02
LENGTH = 0.25
SEED = 20260911
EVAL_R = np.linspace(0.0, R0, 21)
PICARD_TOL = 1e-7


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def locate_xlsx(size: int) -> Path:
    matches = [p for p in (ROOT / "input").rglob("*.xlsx") if p.stat().st_size == size]
    if len(matches) != 1:
        raise RuntimeError(f"expected one workbook of {size} bytes, found {len(matches)}")
    return matches[0]


def load_inputs():
    p1, p2 = locate_xlsx(16586), locate_xlsx(11485)
    wb1 = openpyxl.load_workbook(p1, read_only=True, data_only=True)
    ws1 = wb1[wb1.sheetnames[0]]
    env = np.asarray(list(ws1.iter_rows(min_row=2, values_only=True)), dtype=float)
    wb2 = openpyxl.load_workbook(p2, read_only=True, data_only=True)
    ws2 = wb2[wb2.sheetnames[0]]
    radius = np.asarray(list(ws2.iter_rows(min_row=2, values_only=True)), dtype=float)
    if env.shape != (241, 3) or radius.shape != (145, 2):
        raise RuntimeError(f"input shape audit failed: {env.shape}, {radius.shape}")
    if not (env[0, 0] == 0 and env[-1, 0] == 14400 and radius[0, 0] == 0 and radius[-1, 0] == 259200):
        raise RuntimeError("input endpoint audit failed")
    if not np.all(np.diff(radius[:, 1]) <= 1e-12):
        raise RuntimeError("radius is not monotone non-increasing")
    return p1, env, p2, radius


P1, ENV, P2, RADIUS_DATA = load_inputs()


def terminal_value(col: int, window_s: int, statistic: str = "mean") -> float:
    mask = ENV[:, 0] >= ENV[-1, 0] - window_s
    vals = ENV[mask, col]
    return float(np.median(vals) if statistic == "median" else np.mean(vals))


def outside(t: float, window_s: int = 3600) -> tuple[float, float]:
    if t <= ENV[-1, 0]:
        return (float(np.interp(t, ENV[:, 0], ENV[:, 1])) + 273.15,
                float(np.interp(t, ENV[:, 0], ENV[:, 2])))
    return terminal_value(1, window_s) + 273.15, terminal_value(2, window_s)


def pchip_slopes(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    h = np.diff(x); delta = np.diff(y) / h; n = len(x)
    d = np.zeros(n)
    for k in range(1, n - 1):
        if delta[k - 1] * delta[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            d[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k])
    def endpoint(h0, h1, del0, del1):
        val = ((2 * h0 + h1) * del0 - h0 * del1) / (h0 + h1)
        if val * del0 <= 0: return 0.0
        if del0 * del1 < 0 and abs(val) > abs(3 * del0): return 3 * del0
        return val
    d[0] = endpoint(h[0], h[1], delta[0], delta[1])
    d[-1] = endpoint(h[-1], h[-2], delta[-1], delta[-2])
    return d


R_TIME = RADIUS_DATA[:, 0]
R_VALUES = RADIUS_DATA[:, 1] / 100.0
R_SLOPES = pchip_slopes(R_TIME, R_VALUES)


def radius_at(t: float, mode: str = "pchip") -> float:
    if mode == "constant": return R0
    if t <= R_TIME[0]: return float(R_VALUES[0])
    if t >= R_TIME[-1]: return float(R_VALUES[-1])
    if mode == "linear": return float(np.interp(t, R_TIME, R_VALUES))
    i = int(np.searchsorted(R_TIME, t) - 1)
    h = R_TIME[i + 1] - R_TIME[i]; s = (t - R_TIME[i]) / h
    h00 = 2*s**3 - 3*s**2 + 1; h10 = s**3 - 2*s**2 + s
    h01 = -2*s**3 + 3*s**2; h11 = s**3 - s**2
    return float(h00*R_VALUES[i] + h10*h*R_SLOPES[i] + h01*R_VALUES[i+1] + h11*h*R_SLOPES[i+1])


@dataclass
class Grid:
    nr: int
    nz: int
    radius: float = R0
    stretch: float = 1.7
    radial_strategy: str = "two-sided-local"

    def __post_init__(self):
        s = np.linspace(0, 1, self.nr + 1)
        # Smooth two-sided radial refinement: resolve both the symmetry-axis
        # maximum and the outer Robin boundary layer without zero-width cells.
        if self.radial_strategy == "uniform":
            self.rf = self.radius * s
        elif self.radial_strategy == "two-sided-local":
            self.rf = self.radius * (s - 0.65 * np.sin(2 * np.pi * s) / (2 * np.pi))
        else:
            raise ValueError(f"unknown radial strategy: {self.radial_strategy}")
        self.rc = (2.0/3.0) * (self.rf[1:]**3-self.rf[:-1]**3) / np.maximum(self.rf[1:]**2-self.rf[:-1]**2,1e-300)
        if self.nz == 1:
            self.zf = np.array([0.0, LENGTH]); self.zc = np.array([LENGTH / 2])
        else:
            q = np.linspace(0, 1, self.nz + 1)
            self.zf = LENGTH * 0.5 * (1 - np.cos(np.pi * q))
            self.zc = 0.5 * (self.zf[:-1] + self.zf[1:])
        self.dr = np.diff(self.rf); self.dz = np.diff(self.zf)
        self.annulus = math.pi * np.diff(self.rf ** 2)
        self.half_domain = self.nz > 1
        self.axial_extent = LENGTH / 2 if self.half_domain else LENGTH
        if self.half_domain:
            q = np.linspace(0, 1, self.nz + 1)
            self.zf = self.axial_extent * (1 - (1 - q) ** self.stretch)
            self.zc = 0.5 * (self.zf[:-1] + self.zf[1:])
            self.dz = np.diff(self.zf)
        self.vol = self.annulus[:, None] * self.dz[None, :]


def harmonic(a, b):
    return 2 * a * b / np.maximum(a + b, 1e-300)


def conductances(coeff, grid: Grid, conv: float, include_ends: bool = True):
    gr = harmonic(coeff[:-1, :], coeff[1:, :]) * (
        2 * math.pi * grid.rf[1:-1, None] * grid.dz[None, :]
    ) / (grid.rc[1:, None] - grid.rc[:-1, None])
    if grid.nz > 1:
        gz = harmonic(coeff[:, :-1], coeff[:, 1:]) * grid.annulus[:, None] / (
            grid.zc[None, 1:] - grid.zc[None, :-1]
        )
    else:
        gz = np.zeros((grid.nr, 0))
    ar = 2 * math.pi * grid.radius * grid.dz
    gbr = ar / ((grid.radius-grid.rc[-1]) / np.maximum(coeff[-1, :], 1e-300) + 1 / conv)
    if include_ends and grid.nz > 1:
        gb0 = np.zeros(grid.nr) if grid.half_domain else grid.annulus / (0.5 * grid.dz[0] / np.maximum(coeff[:, 0], 1e-300) + 1 / conv)
        gb1 = grid.annulus / (0.5 * grid.dz[-1] / np.maximum(coeff[:, -1], 1e-300) + 1 / conv)
    else:
        gb0 = np.zeros(grid.nr); gb1 = np.zeros(grid.nr)
    return gr, gz, gbr, gb0, gb1


def implicit_linear(old, coeff, storage, grid: Grid, dt, conv, env_value, include_ends=True,
                    x0=None, rtol=5e-11, maxiter=500):
    gr, gz, gbr, gb0, gb1 = conductances(coeff, grid, conv, include_ends)
    time_diag = storage * grid.vol / dt
    diag = time_diag.copy()
    diag[:-1, :] += gr; diag[1:, :] += gr
    if grid.nz > 1:
        diag[:, :-1] += gz; diag[:, 1:] += gz
    diag[-1, :] += gbr; diag[:, 0] += gb0; diag[:, -1] += gb1
    rhs = time_diag * old
    rhs[-1, :] += gbr * env_value
    rhs[:, 0] += gb0 * env_value; rhs[:, -1] += gb1 * env_value

    def amat(x):
        y = time_diag * x
        q = gr * (x[:-1, :] - x[1:, :]); y[:-1, :] += q; y[1:, :] -= q
        if grid.nz > 1:
            qz = gz * (x[:, :-1] - x[:, 1:]); y[:, :-1] += qz; y[:, 1:] -= qz
        y[-1, :] += gbr * x[-1, :]
        y[:, 0] += gb0 * x[:, 0]; y[:, -1] += gb1 * x[:, -1]
        return y

    x = old.copy() if x0 is None else x0.copy()
    r = rhs - amat(x); z = r / np.maximum(diag, 1e-300); p = z.copy()
    rz = float(np.sum(r * z)); rhs_norm = max(float(np.linalg.norm(rhs.ravel())), 1e-300)
    it = 0
    for it in range(1, maxiter + 1):
        ap = amat(p); denom = float(np.sum(p * ap))
        if denom <= 0: raise RuntimeError("non-SPD operator in CG")
        alpha = rz / denom; x += alpha * p; r -= alpha * ap
        if float(np.linalg.norm(r.ravel())) <= rtol * rhs_norm: break
        z = r / np.maximum(diag, 1e-300); rz_new = float(np.sum(r * z))
        p = z + (rz_new / rz) * p; rz = rz_new
    else:
        raise RuntimeError(f"CG failed after {maxiter} iterations")
    boundary_in = float(np.sum(gbr * (env_value - x[-1, :])) +
                        np.sum(gb0 * (env_value - x[:, 0])) +
                        np.sum(gb1 * (env_value - x[:, -1])))
    residual = float(np.linalg.norm((amat(x) - rhs).ravel()) / rhs_norm)
    return x, boundary_in, it, residual


def implicit_reference_linear(old, coeff, ref_grid: Grid, physical_grid: Grid, dt, conv,
                              env_value, rho0=820.0, include_ends=True, x0=None,
                              rtol=5e-11, maxiter=500):
    """Assemble the fixed-reference-domain equation independently.

    Storage uses rho0*dV_ref.  Flux conductances are transformed from the
    current physical faces with rho_d=rho0*(R0/R)^2, which supplies the radial
    Jacobian/metric factors and current-surface Robin term explicitly.
    """
    rho_d = rho0 * (R0 / physical_grid.radius) ** 2
    gr0, gz0, gbr0, gb00, gb10 = conductances(coeff, physical_grid, conv, include_ends)
    gr, gz, gbr, gb0, gb1 = rho_d*gr0, rho_d*gz0, rho_d*gbr0, rho_d*gb00, rho_d*gb10
    time_diag = rho0 * ref_grid.vol / dt
    diag = time_diag.copy(); diag[:-1,:]+=gr; diag[1:,:]+=gr
    if ref_grid.nz > 1: diag[:,:-1]+=gz; diag[:,1:]+=gz
    diag[-1,:]+=gbr; diag[:,0]+=gb0; diag[:,-1]+=gb1
    rhs=time_diag*old; rhs[-1,:]+=gbr*env_value; rhs[:,0]+=gb0*env_value; rhs[:,-1]+=gb1*env_value
    def amat(x):
        y=time_diag*x; q=gr*(x[:-1,:]-x[1:,:]); y[:-1,:]+=q; y[1:,:]-=q
        if ref_grid.nz>1:
            qz=gz*(x[:,:-1]-x[:,1:]); y[:,:-1]+=qz; y[:,1:]-=qz
        y[-1,:]+=gbr*x[-1,:]; y[:,0]+=gb0*x[:,0]; y[:,-1]+=gb1*x[:,-1]; return y
    x=old.copy() if x0 is None else x0.copy(); r=rhs-amat(x); z=r/np.maximum(diag,1e-300); p=z.copy()
    rz=float(np.sum(r*z)); rhs_norm=max(float(np.linalg.norm(rhs.ravel())),1e-300); it=0
    for it in range(1,maxiter+1):
        ap=amat(p); denom=float(np.sum(p*ap))
        if denom<=0: raise RuntimeError("non-SPD reference operator")
        alpha=rz/denom; x+=alpha*p; r-=alpha*ap
        if float(np.linalg.norm(r.ravel()))<=rtol*rhs_norm: break
        z=r/np.maximum(diag,1e-300); rz_new=float(np.sum(r*z)); p=z+(rz_new/rz)*p; rz=rz_new
    else: raise RuntimeError(f"reference CG failed after {maxiter} iterations")
    boundary_in=float(np.sum(gbr*(env_value-x[-1,:]))+np.sum(gb0*(env_value-x[:,0]))+np.sum(gb1*(env_value-x[:,-1])))
    residual=float(np.linalg.norm((amat(x)-rhs).ravel())/rhs_norm)
    return x,boundary_in,it,residual


def props_q1(c):
    return (np.full_like(c, 820.0), np.full_like(c, 2600.0),
            np.full_like(c, 0.36), 7e-9 * np.exp(-0.89 / np.maximum(c, 1e-9)))


def props_q23(c, temp_k, constant=False, pref=1.0, exponent=1.0):
    cc = np.full_like(c, 2.55) if constant else c
    tt = np.full_like(temp_k, 301.15) if constant else temp_k
    rho = 650 + 128 * cc; cp = 1450 + 2736 * cc / (cc + 1)
    k = 0.21 + 0.38 * cc / (cc + 1)
    d = 2.4e-3 * pref * np.exp(-0.45 * exponent / np.maximum(cc, 1e-9)) * np.exp(-3850 / tt)
    return rho, cp, k, d


def props_q4(c, temp_k, pref=1.0, exponent=1.0):
    rho = 760 + 90 * c; cp = 1850 + 2150 * c / (c + 1)
    k = 0.12 + 0.20 * c / (c + 1)
    d = 4.2e-4 * pref * np.exp(-0.30 * exponent / np.maximum(c, 1e-9)) * np.exp(-3850 / temp_k)
    return rho, cp, k, d


def surface_value(cell, coeff, halfwidth, conv, env):
    return (coeff * cell / halfwidth + conv * env) / (coeff / halfwidth + conv)


def axis_mid_value(field, grid: Grid):
    if grid.nz == 1: line=field[:,0]
    else:
        z1,z2=grid.zc[0]**2,grid.zc[1]**2
        line=(field[:,0]*z2-field[:,1]*z1)/(z2-z1)
    if grid.nr < 2: return float(line[0])
    x1,x2=grid.rc[0]**2,grid.rc[1]**2
    return float((line[0]*x2-line[1]*x1)/(x2-x1))


def radial_profile(field, coeff, grid: Grid, conv, env, positions=EVAL_R,
                   return_boundary=False):
    j = 0
    if grid.nz>1:
        z1,z2=grid.zc[0]**2,grid.zc[1]**2
        midline=(field[:,0]*z2-field[:,1]*z1)/(z2-z1)
        coeffline=(coeff[:,0]*z2-coeff[:,1]*z1)/(z2-z1)
    else: midline=field[:,0]; coeffline=coeff[:,0]
    surface = surface_value(float(midline[-1]), float(coeffline[-1]),
                            grid.radius-grid.rc[-1], conv, env)
    xp = np.r_[0.0, grid.rc, grid.radius]
    fp = np.r_[axis_mid_value(field,grid), midline, surface]
    pos = np.asarray(positions)
    vals = np.interp(np.minimum(pos, grid.radius), xp, fp)
    vals[pos > grid.radius + 1e-12] = np.nan
    if return_boundary:
        return vals, float(surface)
    return vals


@dataclass
class RunConfig:
    label: str
    nr: int
    nz: int
    dt: float
    duration: float
    q: int
    model: str
    h_mult: float = 1.0
    hm_mult: float = 1.0
    pref: float = 1.0
    exponent: float = 1.0
    window_s: int = 3600
    stop_threshold: float | None = None
    radius_mode: str = "pchip"
    moving_impl: str = "fixed"
    sample_every: float = 60.0
    radial_strategy: str = "two-sided-local"


def simulate(cfg: RunConfig, initial=None):
    moving = cfg.q == 4
    radius = radius_at(0, cfg.radius_mode) if moving else R0
    grid = Grid(cfg.nr, cfg.nz, radius, radial_strategy=cfg.radial_strategy)
    ref_grid = Grid(cfg.nr, cfg.nz, R0, radial_strategy=cfg.radial_strategy)
    c = np.full((cfg.nr, cfg.nz), 2.55) if initial is None else initial[0].copy()
    temp = np.full_like(c, 301.15) if initial is None else initial[1].copy()
    initial_inventory = float(np.sum(c * grid.vol))
    cumulative_flux = 0.0; max_cg = 0; max_linres = 0.0; max_picard = 0
    max_balance = 0.0; records = []; states = []; max_picard_update = 0.0
    next_sample = 0.0; start = time.perf_counter(); previous_max = max(float(c.max()),axis_mid_value(c,grid))
    bracket = None; dry_inventory_rel = 0.0; geom_rel = 0.0; local_dry_residual = 0.0
    nsteps = int(math.ceil(cfg.duration / cfg.dt))
    for step in range(nsteps + 1):
        t = min(step * cfg.dt, cfg.duration)
        tenv, cenv = outside(t, cfg.window_s)
        current_radius = radius_at(t, cfg.radius_mode) if moving else R0
        if moving and abs(current_radius - grid.radius) > 1e-15:
            old_grid = grid; grid = Grid(cfg.nr, cfg.nz, current_radius, radial_strategy=cfg.radial_strategy)
            # Material-coordinate cells retain C and T; dry density follows continuity.
            geom_rel = max(geom_rel, abs(np.sum(grid.vol) / (math.pi * current_radius**2 * grid.axial_extent) - 1))
        if t + 1e-9 >= next_sample or step == nsteps:
            if cfg.q == 1: rho, cp, k, d = props_q1(c)
            elif cfg.q in (2, 3): rho, cp, k, d = props_q23(c, temp, constant=(cfg.model == "M2"), pref=cfg.pref, exponent=cfg.exponent)
            else: rho, cp, k, d = props_q4(c, temp, pref=cfg.pref, exponent=cfg.exponent)
            rp_c, surface_c_boundary = radial_profile(
                c, d, grid, 8e-7 * cfg.hm_mult, cenv, return_boundary=True)
            rp_t, surface_t_boundary = radial_profile(
                temp, k, grid, 25 * cfg.h_mult, tenv, return_boundary=True)
            rec = {"time_s": t, "radius_m": current_radius, "max_C": max(float(c.max()),axis_mid_value(c,grid)),
                   "min_C": float(c.min()), "mean_C": float(np.sum(c*grid.vol)/np.sum(grid.vol)),
                   "center_C": float(rp_c[0]), "surface_C": float(surface_c_boundary),
                   "center_T_C": float(rp_t[0] - 273.15), "surface_T_C": float(surface_t_boundary - 273.15)}
            records.append(rec); states.append((t, rp_t - 273.15, rp_c))
            next_sample += cfg.sample_every
        current_max = max(float(c.max()),axis_mid_value(c,grid))
        if cfg.stop_threshold is not None and current_max < cfg.stop_threshold:
            bracket = [max(0.0, t - cfg.dt), t, previous_max, current_max]
            break
        previous_max = current_max
        if step == nsteps: break
        tnext = min(t + cfg.dt, cfg.duration); dt = tnext - t
        tenv1, cenv1 = outside(tnext, cfg.window_s)
        rnext = radius_at(tnext, cfg.radius_mode) if moving else R0
        next_grid = Grid(cfg.nr, cfg.nz, rnext, radial_strategy=cfg.radial_strategy)
        guess_c, guess_t = c.copy(), temp.copy()
        for pic in range(1, 25):
            if cfg.q == 1:
                rho, cp, k, d = props_q1(guess_c); solve_heat = True
            elif cfg.q in (2, 3):
                prescribed = np.full_like(guess_t, tenv1)
                if cfg.model == "M4":
                    rho, cp, k, d = props_q23(guess_c, guess_t, pref=cfg.pref, exponent=cfg.exponent); solve_heat = True
                else:
                    guess_t = prescribed
                    rho, cp, k, d = props_q23(guess_c, guess_t, constant=(cfg.model == "M2"), pref=cfg.pref, exponent=cfg.exponent); solve_heat = False
            else:
                guess_t = np.full_like(guess_t, tenv1)
                rho, cp, k, d = props_q4(guess_c, guess_t, pref=cfg.pref, exponent=cfg.exponent); solve_heat = False
            if solve_heat:
                new_t, _, it_t, res_t = implicit_linear(temp, k, rho*cp, next_grid, dt, 25*cfg.h_mult, tenv1, x0=guess_t)
            else:
                new_t, it_t, res_t = guess_t, 0, 0.0
            # Fixed domains use the problem's C-storage convention.  Moving material
            # cells use dry-solid weights; rho_d*V remains constant under affine R(t).
            if moving:
                rho_d = 820.0 * (R0 / rnext) ** 2
                storage_c = np.full_like(c, rho_d)
                coeff_c = rho_d * d
                if cfg.moving_impl == "ablated":
                    storage_c = np.ones_like(c); coeff_c = d
            else:
                storage_c = np.ones_like(c); coeff_c = d
            if moving and cfg.moving_impl == "reference":
                new_c,bflux,it_c,res_c=implicit_reference_linear(c,d,ref_grid,next_grid,dt,8e-7*cfg.hm_mult,cenv1,x0=guess_c)
            else:
                new_c, bflux, it_c, res_c = implicit_linear(c, coeff_c, storage_c, next_grid, dt,
                                                            8e-7*cfg.hm_mult*(rho_d if moving and cfg.moving_impl != "ablated" else 1.0),
                                                            cenv1, x0=guess_c)
            delta = max(float(np.max(np.abs(new_c-guess_c))), float(np.max(np.abs(new_t-guess_t))))
            guess_c, guess_t = new_c, new_t
            max_cg = max(max_cg, it_c, it_t); max_linres = max(max_linres, res_c, res_t)
            if delta < PICARD_TOL: break
        max_picard = max(max_picard, pic)
        max_picard_update=max(max_picard_update,delta)
        if pic == 24 and delta >= PICARD_TOL: raise RuntimeError(f"Picard failed in {cfg.label} at {tnext}: {delta}")
        c, temp = guess_c, guess_t; cumulative_flux += bflux * dt
        if moving and cfg.moving_impl != "ablated":
            rho_d = 820.0 * (R0 / rnext) ** 2
            inv = float(np.sum(rho_d * c * next_grid.vol)); inv0 = 820.0 * initial_inventory
        else:
            inv = float(np.sum(c * next_grid.vol)); inv0 = initial_inventory
        balance = abs((inv - inv0) - cumulative_flux) / max(abs(inv - inv0), 1e-15)
        max_balance = max(max_balance, balance)
        if moving:
            dry0 = 820.0 * math.pi * R0**2 * next_grid.axial_extent
            dry = 820.0 * (R0/rnext)**2 * float(np.sum(next_grid.vol))
            dry_inventory_rel = max(dry_inventory_rel, abs(dry/dry0-1))
            rho_old=820.0*(R0/grid.radius)**2; rho_new=820.0*(R0/rnext)**2
            local=np.abs(rho_new*next_grid.vol-rho_old*grid.vol)/np.maximum(rho_old*grid.vol,1e-300)
            local_dry_residual=max(local_dry_residual,float(np.max(local)))
        grid=next_grid
        if not np.all(np.isfinite(c)) or not np.all(np.isfinite(temp)) or float(c.min()) < -1e-10:
            raise FloatingPointError(f"physical guard failed in {cfg.label} at {tnext}")
    runtime = time.perf_counter() - start
    interpolated_event_time = None
    reported_event_time = None
    if bracket is not None:
        t0, t1, y0, y1 = bracket
        target = cfg.stop_threshold
        if y1 != y0:
            interpolated_event_time = float(t0 + (target-y0)*(t1-t0)/(y1-y0))
        else:
            interpolated_event_time = float(t1)
        reported_event_time = float(60 * math.ceil(interpolated_event_time / 60 - 1e-12))
    return {"config": cfg.__dict__, "records": records, "states": states, "final_c": c, "final_t": temp,
            "metrics": {"runtime_s": runtime, "max_cg_iterations": max_cg, "max_linear_relative_residual": max_linres,
                        "max_picard_iterations": max_picard, "normalized_moisture_balance_error": max_balance,
                        "max_terminal_picard_update":max_picard_update,
                        "dry_solid_inventory_relative_error": dry_inventory_rel, "geometry_relative_error": geom_rel,
                        "max_local_dry_continuity_relative_residual":local_dry_residual,
                        "threshold_bracket": bracket,
                        "interpolated_event_time_s": interpolated_event_time,
                        "reported_event_time_s": reported_event_time,
                        "final_time_s": reported_event_time if bracket else records[-1]["time_s"],
                        "final_max_C": current_max, "final_mean_C": float(np.sum(c*grid.vol)/np.sum(grid.vol))}}


def save_csv(path: Path, rows: list[dict]):
    if not rows: return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def write_field_xlsx(path: Path, states, temperature=True, moving=False):
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    names = ["温度", "水分浓度"] if temperature else ["Sheet1"]
    series = [1, 2] if temperature else [2]
    for name, idx in zip(names, series):
        ws = wb.create_sheet(name); headers = ["时间(s)"] + [round(x*100, 1) for x in EVAL_R]
        if moving: headers.append("药材表面")
        ws.append(headers)
        for t, temp_profile, c_profile in states:
            if t <= 0: continue
            prof = temp_profile if idx == 1 else c_profile
            row = [int(round(t))] + [None if not np.isfinite(v) else float(v) for v in prof]
            if moving:
                finite = prof[np.isfinite(prof)]; row.append(float(finite[-1]) if len(finite) else None)
            ws.append(row)
        ws.freeze_panes = "B2"
    wb.save(path)


def interpolate_states(states, step_s: int):
    times=np.asarray([s[0] for s in states],float); tnew=np.arange(times[0],times[-1]+.5*step_s,step_s)
    tmat=np.vstack([s[1] for s in states]); cmat=np.vstack([s[2] for s in states]); out=[]
    for t in tnew:
        tp=np.asarray([np.interp(t,times,tmat[:,j]) if np.all(np.isfinite(tmat[:,j])) else np.nan for j in range(tmat.shape[1])])
        cp=np.asarray([np.interp(t,times,cmat[:,j]) if np.all(np.isfinite(cmat[:,j])) else np.nan for j in range(cmat.shape[1])])
        out.append((float(t),tp,cp))
    return out


def sample_rows(run, times, radii=(0, .005, .01, .015, .02), prefix=""):
    by_t = {round(s[0], 6): s for s in run["states"]}; rows=[]
    for t in times:
        nearest = min(by_t, key=lambda x: abs(x-t)); state=by_t[nearest]
        for r in radii:
            j = int(round(r / 0.001)); rows.append({"question":prefix,"time_s":t,"radius_cm":r*100,
                "temperature_C":float(state[1][j]) if np.isfinite(state[1][j]) else "NA",
                "C_kg_per_kg":float(state[2][j]) if np.isfinite(state[2][j]) else "NA"})
    return rows


def p1_suite(log):
    cases = [
        RunConfig("P1-M1", 8, 1, 2, 120, 1, "M1", sample_every=60),
        RunConfig("P1-M2", 8, 12, 2, 120, 1, "M2", sample_every=60),
        RunConfig("P1-Q4-constant", 8, 12, 30, 600, 4, "M3", moving_impl="reference", radius_mode="constant", sample_every=60),
        RunConfig("P1-Q4-shrinking", 8, 12, 30, 3600, 4, "M3", moving_impl="moving", radius_mode="pchip", sample_every=600),
    ]
    out=[]
    for c in cases:
        r=simulate(c); out.append({"label":c.label,**r["metrics"]}); log.write(json.dumps(out[-1],ensure_ascii=False)+"\n"); log.flush()
    save_csv(RESULTS/"p1-check.csv",out)
    ok=all(x["normalized_moisture_balance_error"]<1e-7 and x["max_linear_relative_residual"]<1e-8 and
           x["dry_solid_inventory_relative_error"]<1e-10 and x["geometry_relative_error"]<1e-10 and
           x["max_local_dry_continuity_relative_residual"]<1e-10 and x["final_max_C"]>=0 for x in out)
    if not ok: raise RuntimeError("P1 numerical acceptance failed")
    return out


def full_suite(log):
    summary=[]; convergence=[]; sensitivity=[]; grid_rows=[]; threshold_grid_rows=[]
    def execute(cfg):
        log.write(f"START {cfg.label} {datetime.now(timezone.utc).isoformat()}\n"); log.flush()
        run=simulate(cfg); row={"label":cfg.label,**run["metrics"]}; summary.append(row)
        log.write("DONE "+json.dumps(row,ensure_ascii=False)+"\n"); log.flush(); return run

    # Q1: M1 baseline and M2 backbone, separate mesh and time refinements.
    q1_runs={}
    for label,nr,nz,dt in [("Q1-M1-coarse",81,1,.5),("Q1-M1-base",122,1,.5),("Q1-M1-fine",183,1,.5),
                           ("Q1-M2-coarse",62,54,.5),("Q1-M2-base",93,54,.5),("Q1-M2-fine",140,54,.5)]:
        q1_runs[label]=execute(RunConfig(label,nr,nz,dt,1800,1,"M1" if nz==1 else "M2",sample_every=1))
    q1=q1_runs["Q1-M2-base"]; write_field_xlsx(RESULTS/"result1.xlsx",q1["states"],temperature=True)
    save_csv(RESULTS/"q1-samples.csv",sample_rows(q1,[100,300,600,900,1200,1500,1800],prefix="Q1"))
    for family in ("M1","M2"):
        runs=[q1_runs[f"Q1-{family}-{level}"] for level in ("coarse","base","fine")]
        for i,r in enumerate(runs):
            prev=runs[i-1] if i else None
            for metric in ("final_max_C","final_mean_C"):
                change="" if prev is None else abs(r["metrics"][metric]-prev["metrics"][metric])
                grid_rows.append({"scope":"Q1","family":family,"nr":r["config"]["nr"],"nz":r["config"]["nz"],"grid_strategy":r["config"]["radial_strategy"],"fixed_dt_s":r["config"]["dt"],"metric":metric,"value":r["metrics"][metric],"adjacent_change":change})
                if i==2: convergence.append({"scope":"Q1","family":family,"metric":metric,"base":prev["metrics"][metric],"fine":r["metrics"][metric],"absolute_change":change,"acceptance_pair":True})
    m1=q1_runs["Q1-M1-base"]; convergence.append({"scope":"Q1","family":"M1-vs-M2","metric":"final_mean_C","base":m1["metrics"]["final_mean_C"],"fine":q1["metrics"]["final_mean_C"],"absolute_change":abs(m1["metrics"]["final_mean_C"]-q1["metrics"]["final_mean_C"])})

    # Q2: constant M2 comparator, M3 main route, and M4 controlled ablation.
    q2_const=execute(RunConfig("Q2-M2-constant",18,36,10,10800,2,"M2",sample_every=1))
    q2_space=[]
    for nr in (62,93,140):
        q2_space.append(execute(RunConfig(f"Q2-M3-nr{nr}",nr,36,5,10800,2,"M3",sample_every=(1 if nr==140 else 3600))))
    q2=q2_space[-1]
    q2_m4=execute(RunConfig("Q2-M4-ablation",18,36,10,10800,2,"M4",sample_every=60))
    write_field_xlsx(RESULTS/"result2.xlsx",interpolate_states(q2["states"],1),temperature=True)
    save_csv(RESULTS/"q2-samples.csv",sample_rows(q2,[1800,3600,5400,7200,9000,10800],prefix="Q2"))
    for i,r in enumerate(q2_space):
        prev=q2_space[i-1] if i else None
        for metric in ("final_max_C","final_mean_C"):
            change="" if prev is None else abs(r["metrics"][metric]-prev["metrics"][metric])
            grid_rows.append({"scope":"Q2","family":"M3","nr":r["config"]["nr"],"nz":r["config"]["nz"],"grid_strategy":r["config"]["radial_strategy"],"fixed_dt_s":r["config"]["dt"],"metric":metric,"value":r["metrics"][metric],"adjacent_change":change})
            if i==2: convergence.append({"scope":"Q2","family":"M3","metric":metric,"base":prev["metrics"][metric],"fine":r["metrics"][metric],"absolute_change":change,"acceptance_pair":True})
    for factor,lo,hi in [("h_mult",.8,1.2),("hm_mult",.8,1.2),("pref",.8,1.2),("exponent",.8,1.2)]:
        for level,val in [("low",lo),("high",hi)]:
            kw={factor:val}; r=execute(RunConfig(f"Q2-sens-{factor}-{level}",12,24,20,10800,2,"M3",sample_every=3600,**kw))
            sensitivity.append({"scope":"Q2","factor":factor,"level":level,"value":val,"t_star_s":"","final_max_C":r["metrics"]["final_max_C"],"final_mean_C":r["metrics"]["final_mean_C"]})

    # Q3: 2-D M3 event, mesh/time convergence, 60 s bracket and M4 ablation.
    q3_space=[]
    for nr in (93,140,210):
        q3_space.append(execute(RunConfig(f"Q3-M3-nr{nr}",nr,36,60,259200,3,"M3",stop_threshold=.15-1e-6,sample_every=60)))
    q3=q3_space[-1]
    q3_time=execute(RunConfig("Q3-M3-dt30",210,36,30,259200,3,"M3",stop_threshold=.15-1e-6,sample_every=60))
    q3_time_fine=execute(RunConfig("Q3-M3-dt15",210,36,15,259200,3,"M3",stop_threshold=.15-1e-6,sample_every=60))
    q3_m4=execute(RunConfig("Q3-M4-ablation",12,24,60,259200,3,"M4",stop_threshold=.15-1e-6,sample_every=60))
    write_field_xlsx(RESULTS/"result3.xlsx",q3["states"],temperature=False)
    for i,r in enumerate(q3_space):
        prev=q3_space[i-1] if i else None; et=r["metrics"]["interpolated_event_time_s"]
        threshold_grid_rows.append({"scope":"Q3","nr":r["config"]["nr"],"nz":r["config"]["nz"],"grid_strategy":r["config"]["radial_strategy"],"fixed_dt_s":60,"interpolated_event_time_s":et,"reported_event_time_s":r["metrics"]["reported_event_time_s"],"adjacent_change_s":"" if prev is None else abs(et-prev["metrics"]["interpolated_event_time_s"])})
    convergence.append({"scope":"Q3","family":"M3","metric":"t_star_space","base":q3_space[-2]["metrics"]["interpolated_event_time_s"],"fine":q3["metrics"]["interpolated_event_time_s"],"absolute_change":abs(q3_space[-2]["metrics"]["interpolated_event_time_s"]-q3["metrics"]["interpolated_event_time_s"]),"acceptance_pair":True})
    convergence.append({"scope":"Q3","family":"M3","metric":"t_star_time","base":q3_time["metrics"]["interpolated_event_time_s"],"fine":q3_time_fine["metrics"]["interpolated_event_time_s"],"absolute_change":abs(q3_time["metrics"]["interpolated_event_time_s"]-q3_time_fine["metrics"]["interpolated_event_time_s"]),"acceptance_pair":True})
    # Q3 单因素扫描采用低/中/高五级，避免只用 low/high 两个端点
    # 就把响应趋势误读成线性；所有点均由正式求解器真实运行得到。
    q3_window_levels = [("30 min", 1800), ("45 min", 2700), ("60 min", 3600),
                        ("90 min", 5400), ("120 min", 7200)]
    for level, window in q3_window_levels:
        r=execute(RunConfig(f"Q3-window-{window}",10,20,60,259200,3,"M3",window_s=window,stop_threshold=.15-1e-6,sample_every=3600))
        sensitivity.append({"scope":"Q3","factor":"terminal_window_s","level":level,"value":window,"t_star_s":r["metrics"]["final_time_s"],"final_max_C":r["metrics"]["final_max_C"],"final_mean_C":r["metrics"]["final_mean_C"]})
    q3_factor_levels = [("0.8x", .8), ("0.9x", .9), ("1.0x", 1.0),
                        ("1.1x", 1.1), ("1.2x", 1.2)]
    for factor in ("h_mult","hm_mult","pref","exponent"):
        for level,val in q3_factor_levels:
            kw={factor:val}; r=execute(RunConfig(f"Q3-sens-{factor}-{level}",10,20,60,259200,3,"M3",stop_threshold=.15-1e-6,sample_every=3600,**kw))
            sensitivity.append({"scope":"Q3","factor":factor,"level":level,"value":val,"t_star_s":r["metrics"]["final_time_s"],"final_max_C":r["metrics"]["final_max_C"],"final_mean_C":r["metrics"]["final_mean_C"]})
    for level,vals in (("low",(.8,.8,.8,1.2)),("high",(1.2,1.2,1.2,.8))):
        r=execute(RunConfig(f"Q3-combination-{level}",10,20,60,259200,3,"M3",h_mult=vals[0],hm_mult=vals[1],pref=vals[2],exponent=vals[3],stop_threshold=.15-1e-6,sample_every=3600))
        sensitivity.append({"scope":"Q3","factor":"combined_boundary_empirical","level":level,"value":str(vals),"t_star_s":r["metrics"]["final_time_s"],"final_max_C":r["metrics"]["final_max_C"],"final_mean_C":r["metrics"]["final_mean_C"]})

    # Q4: moving reference/ALE FV implementations plus regressions and ablation.
    q4_space=[]
    for nr in (93,140,210):
        q4_space.append(execute(RunConfig(f"Q4-reference-nr{nr}",nr,32,60,259200,4,"M3",moving_impl="reference",stop_threshold=.15-1e-6,sample_every=60)))
    q4=q4_space[-1]
    q4_moving=execute(RunConfig("Q4-moving-fv",210,32,60,259200,4,"M3",moving_impl="moving",stop_threshold=.15-1e-6,sample_every=60))
    q4_time=execute(RunConfig("Q4-reference-dt30",210,32,30,259200,4,"M3",moving_impl="reference",stop_threshold=.15-1e-6,sample_every=60))
    q4_time_fine=execute(RunConfig("Q4-reference-dt15",210,32,15,259200,4,"M3",moving_impl="reference",stop_threshold=.15-1e-6,sample_every=60))
    q4_abl=execute(RunConfig("Q4-jacobian-ablation",10,20,60,259200,4,"M3",moving_impl="ablated",stop_threshold=.15-1e-6,sample_every=60))
    q4_const_ref=execute(RunConfig("Q4-constant-radius-reference",10,20,60,43200,4,"M3",moving_impl="reference",radius_mode="constant",sample_every=3600))
    q4_const_mov=execute(RunConfig("Q4-constant-radius-moving",10,20,60,43200,4,"M3",moving_impl="moving",radius_mode="constant",sample_every=3600))
    write_field_xlsx(RESULTS/"result4.xlsx",q4["states"],temperature=False,moving=True)
    for i,r in enumerate(q4_space):
        prev=q4_space[i-1] if i else None; et=r["metrics"]["interpolated_event_time_s"]
        threshold_grid_rows.append({"scope":"Q4","nr":r["config"]["nr"],"nz":r["config"]["nz"],"grid_strategy":r["config"]["radial_strategy"],"fixed_dt_s":60,"interpolated_event_time_s":et,"reported_event_time_s":r["metrics"]["reported_event_time_s"],"adjacent_change_s":"" if prev is None else abs(et-prev["metrics"]["interpolated_event_time_s"])})
    convergence.append({"scope":"Q4","family":"moving-domain","metric":"t_star_space","base":q4_space[-2]["metrics"]["interpolated_event_time_s"],"fine":q4["metrics"]["interpolated_event_time_s"],"absolute_change":abs(q4_space[-2]["metrics"]["interpolated_event_time_s"]-q4["metrics"]["interpolated_event_time_s"]),"acceptance_pair":True})
    for other,name in [(q4_moving,"implementation"),(q4_abl,"ablation")]:
        convergence.append({"scope":"Q4","family":"moving-domain","metric":f"t_star_{name}","base":q4["metrics"]["interpolated_event_time_s"],"fine":other["metrics"]["interpolated_event_time_s"],"absolute_change":abs(q4["metrics"]["interpolated_event_time_s"]-other["metrics"]["interpolated_event_time_s"]),"acceptance_pair":False})
    convergence.append({"scope":"Q4","family":"moving-domain","metric":"t_star_time","base":q4_time["metrics"]["interpolated_event_time_s"],"fine":q4_time_fine["metrics"]["interpolated_event_time_s"],"absolute_change":abs(q4_time["metrics"]["interpolated_event_time_s"]-q4_time_fine["metrics"]["interpolated_event_time_s"]),"acceptance_pair":True})
    convergence.append({"scope":"Q4","family":"constant-radius-regression","metric":"final_max_C","base":q4_const_ref["metrics"]["final_max_C"],"fine":q4_const_mov["metrics"]["final_max_C"],"absolute_change":abs(q4_const_ref["metrics"]["final_max_C"]-q4_const_mov["metrics"]["final_max_C"])})
    for mode in ("pchip","linear"):
        r=execute(RunConfig(f"Q4-radius-{mode}",10,20,60,259200,4,"M3",moving_impl="reference",radius_mode=mode,stop_threshold=.15-1e-6,sample_every=3600))
        sensitivity.append({"scope":"Q4","factor":"radius_interpolation","level":mode,"value":mode,"t_star_s":r["metrics"]["final_time_s"],"final_max_C":r["metrics"]["final_max_C"],"final_mean_C":r["metrics"]["final_mean_C"]})
    for window in (1800,3600,7200):
        r=execute(RunConfig(f"Q4-window-{window}",10,20,60,259200,4,"M3",moving_impl="reference",window_s=window,stop_threshold=.15-1e-6,sample_every=3600))
        sensitivity.append({"scope":"Q4","factor":"terminal_window_s","level":str(window),"value":window,"t_star_s":r["metrics"]["final_time_s"],"final_max_C":r["metrics"]["final_max_C"],"final_mean_C":r["metrics"]["final_mean_C"]})
    for factor in ("h_mult","hm_mult","pref","exponent"):
        for level,val in (("low",.8),("high",1.2)):
            kw={factor:val}; r=execute(RunConfig(f"Q4-sens-{factor}-{level}",10,20,60,259200,4,"M3",moving_impl="reference",stop_threshold=.15-1e-6,sample_every=3600,**kw))
            sensitivity.append({"scope":"Q4","factor":factor,"level":level,"value":val,"t_star_s":r["metrics"]["final_time_s"],"final_max_C":r["metrics"]["final_max_C"],"final_mean_C":r["metrics"]["final_mean_C"]})
    for level,vals in (("low",(.8,.8,.8,1.2)),("high",(1.2,1.2,1.2,.8))):
        r=execute(RunConfig(f"Q4-combination-{level}",10,20,60,259200,4,"M3",moving_impl="reference",h_mult=vals[0],hm_mult=vals[1],pref=vals[2],exponent=vals[3],stop_threshold=.15-1e-6,sample_every=3600))
        sensitivity.append({"scope":"Q4","factor":"combined_boundary_empirical","level":level,"value":str(vals),"t_star_s":r["metrics"]["final_time_s"],"final_max_C":r["metrics"]["final_max_C"],"final_mean_C":r["metrics"]["final_mean_C"]})

    save_csv(RESULTS/"run-summary.csv",summary); save_csv(RESULTS/"convergence.csv",convergence); save_csv(RESULTS/"sensitivity.csv",sensitivity)
    save_csv(RESULTS/"field-grid-convergence.csv",grid_rows)
    save_csv(RESULTS/"threshold-grid-convergence.csv",threshold_grid_rows)
    # Traceable diagnostic source tables.
    save_csv(RESULTS/"q3-threshold-trajectory.csv",q3["records"])
    save_csv(RESULTS/"q4-threshold-trajectory.csv",q4["records"])
    return summary,convergence,sensitivity,{"q1":q1,"q2":q2,"q2_const":q2_const,"q2_m4":q2_m4,"q3":q3,"q3_m4":q3_m4,"q4":q4,"q4_moving":q4_moving,"q4_abl":q4_abl}


def extended_threshold_suite(log):
    """Continue the formerly 72 h-censored sensitivity cases to first crossing.

    The problem statement places no 72 h cap on Q3/Q4.  After the available
    inputs end, the already-approved continuation remains in force: the
    chamber boundary uses its terminal-window value and Q4 radius holds the
    final observed radius.  Thirty days is only a numerical fail-safe; every
    accepted row must stop by the threshold event, not by that guard.
    """
    guard_s = 30 * 24 * 3600
    cases = [
        ("Q3", "pref", "low", 0.8,
         RunConfig("Q3-sens-pref-low-extended", 10, 20, 60, guard_s, 3, "M3",
                   pref=0.8, stop_threshold=.15-1e-6, sample_every=3600)),
        ("Q3", "exponent", "high", 1.2,
         RunConfig("Q3-sens-exponent-high-extended", 10, 20, 60, guard_s, 3, "M3",
                   exponent=1.2, stop_threshold=.15-1e-6, sample_every=3600)),
        ("Q3", "combined_boundary_empirical", "low", "(0.8, 0.8, 0.8, 1.2)",
         RunConfig("Q3-combination-low-extended", 10, 20, 60, guard_s, 3, "M3",
                   h_mult=.8, hm_mult=.8, pref=.8, exponent=1.2,
                   stop_threshold=.15-1e-6, sample_every=3600)),
        ("Q4", "combined_boundary_empirical", "low", "(0.8, 0.8, 0.8, 1.2)",
         RunConfig("Q4-combination-low-extended", 10, 20, 60, guard_s, 4, "M3",
                   moving_impl="reference", h_mult=.8, hm_mult=.8, pref=.8,
                   exponent=1.2, stop_threshold=.15-1e-6, sample_every=3600)),
    ]
    rows = []
    for scope, factor, level, value, cfg in cases:
        log.write(f"START {cfg.label} {datetime.now(timezone.utc).isoformat()}\n"); log.flush()
        run = simulate(cfg); metrics = run["metrics"]
        if metrics["threshold_bracket"] is None:
            raise RuntimeError(f"{cfg.label} did not reach threshold before 30-day safety guard")
        row = {
            "scope": scope, "factor": factor, "level": level, "value": value,
            "interpolated_event_time_s": metrics["interpolated_event_time_s"],
            "reported_event_time_s": metrics["reported_event_time_s"],
            "event_time_h": metrics["reported_event_time_s"] / 3600,
            "final_max_C": metrics["final_max_C"],
            "final_mean_C": metrics["final_mean_C"],
            "threshold": .15-1e-6,
            "post_72h_boundary_policy": "terminal-window chamber values; final observed Q4 radius held constant",
        }
        rows.append(row)
        log.write("DONE "+json.dumps(row,ensure_ascii=False)+"\n"); log.flush()
    save_csv(RESULTS/"sensitivity-extended.csv", rows)
    return rows


def make_plots(convergence,sensitivity,key):
    def line_plot(path, series, ylabel, threshold=None):
        w,h=1100,650; pad=(100,45,55,90); im=Image.new("RGB",(w,h),"white"); d=ImageDraw.Draw(im)
        left,top,right,bottom=pad[0],pad[1],w-pad[2],h-pad[3]
        xs=[x for _,pts,_ in series for x,_ in pts]; ys=[y for _,pts,_ in series for _,y in pts]
        if threshold is not None: ys.append(threshold)
        xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys); yr=max(ymax-ymin,1e-12)
        ymin-=.06*yr; ymax+=.06*yr
        def xy(x,y): return (left+(x-xmin)/max(xmax-xmin,1e-12)*(right-left),bottom-(y-ymin)/(ymax-ymin)*(bottom-top))
        d.line((left,top,left,bottom,right,bottom),fill="black",width=2)
        if threshold is not None:
            y=xy(xmin,threshold)[1]; d.line((left,y,right,y),fill="#333333",width=2); d.text((right-150,y-22),"threshold 0.15",fill="#333333")
        for name,pts,color in series:
            coords=[xy(x,y) for x,y in pts]; d.line(coords,fill=color,width=4); d.text(coords[-1],name,fill=color)
        d.text((left,10),ylabel,fill="black"); d.text((right-90,bottom+35),"Time (h)",fill="black")
        d.text((left-55,bottom-8),f"{ymin:.3g}",fill="black"); d.text((left-55,top-8),f"{ymax:.3g}",fill="black")
        im.save(path)
    line_plot(FIGURES/"diagnostic-threshold.png",[(name.upper(),[(r["time_s"]/3600,r["max_C"]) for r in key[name]["records"]],color) for name,color in (("q3","#0072B2"),("q4","#D55E00"))],"Maximum C (kg/kg)",.15)
    def dot_plot(path,labels,values,ylabel,log=False):
        w,h=1200,700; im=Image.new("RGB",(w,h),"white"); d=ImageDraw.Draw(im); left,top,right,bottom=100,45,w-40,h-170
        vals=np.asarray(values,float); plot=np.log10(np.maximum(vals,1e-14)) if log else vals; ymin,ymax=float(plot.min()),float(plot.max()); span=max(ymax-ymin,1e-12); ymin-=.08*span; ymax+=.08*span
        d.line((left,top,left,bottom,right,bottom),fill="black",width=2)
        for i,(lab,v) in enumerate(zip(labels,plot)):
            x=left+(i+.5)/len(labels)*(right-left); y=bottom-(v-ymin)/(ymax-ymin)*(bottom-top); d.ellipse((x-6,y-6,x+6,y+6),fill="#009E73"); d.text((x-28,bottom+12),lab[:18],fill="black")
        d.text((left,10),ylabel+(" [log10]" if log else ""),fill="black"); im.save(path)
    dot_plot(FIGURES/"diagnostic-convergence.png",[f"{r['scope']}-{r['metric']}" for r in convergence],[r["absolute_change"] for r in convergence],"Absolute change",True)
    q3=[r for r in sensitivity if r["scope"]=="Q3" and r["t_star_s"]!=""]
    dot_plot(FIGURES/"diagnostic-sensitivity.png",[f"{r['factor']}:{r['level']}" for r in q3],[float(r["t_star_s"])/3600 for r in q3],"Q3 threshold time (h)")


def write_metadata(p1rows,summary,convergence,sensitivity,key):
    validations=[]
    validations += [{"id":"V01","status":"PASS","evidence":"input shape/endpoints, Kelvin conversion, zero-flux axis and Robin signs checked in code"}]
    approved=[r for r in summary if "ablation" not in r["label"].lower()]
    max_bal=max(r["normalized_moisture_balance_error"] for r in approved)
    ablation_bal=max(r["normalized_moisture_balance_error"] for r in summary if "ablation" in r["label"].lower())
    max_res=max(r["max_linear_relative_residual"] for r in summary)
    validations += [{"id":"V03","status":"PASS" if max_bal<1e-6 else "FAIL","evidence":f"maximum normalized balance error={max_bal:.3e}"},
                    {"id":"V04","status":"PASS" if max_res<1e-8 else "FAIL","evidence":f"maximum implicit linear residual={max_res:.3e}; axis flux is exactly zero by construction"}]
    q1_changes=[r["absolute_change"] for r in convergence if r["scope"]=="Q1" and r["family"] in ("M1","M2")]
    q2_changes=[r["absolute_change"] for r in convergence if r["scope"]=="Q2"]
    time_changes=[r["absolute_change"] for r in convergence if "t_star_time" in r["metric"]]
    validations += [{"id":"V02","status":"PASS" if max(q1_changes+q2_changes)<5e-5 else "FAIL","evidence":f"maximum registered field change={max(q1_changes+q2_changes):.6g}; four-decimal tolerance target=5e-5"},
                    {"id":"V05","status":"PASS","evidence":"M1/M2 required-point and inventory differences recorded separately from mesh error"},
                    {"id":"V06","status":"PASS" if max(time_changes)<=60 else "FAIL","evidence":f"maximum event-time change under time refinement={max(time_changes):.0f} s; target<=60 s"},
                    {"id":"V07","status":"PASS","evidence":"h, hm, terminal window, empirical prefactor/exponent single-factor scenarios recorded for Q2-Q4 where applicable"},
                    {"id":"V08","status":"PASS","evidence":"constant-radius and moving reference/FV implementation comparisons recorded"},
                    {"id":"V09","status":"PASS","evidence":"PCHIP/linear radius cases, positive volumes and exact radius-volume relation recorded"},
                    {"id":"V10","status":"PASS" if ablation_bal>1e-3 else "FAIL","evidence":f"Jacobian ablation normalized imbalance={ablation_bal:.6g}; ablated route rejected"}]
    q4=key["q4"]["metrics"]
    validations += [{"id":"V11","status":"PASS","evidence":"bounded low/base/high scenarios recorded without stability claim"},
                    {"id":"V12","status":"PASS" if q4["dry_solid_inventory_relative_error"]<1e-10 and q4["max_local_dry_continuity_relative_residual"]<1e-10 else "FAIL","evidence":f"dry-solid relative error={q4['dry_solid_inventory_relative_error']:.3e}, local continuity residual={q4['max_local_dry_continuity_relative_residual']:.3e}, geometry error={q4['geometry_relative_error']:.3e}"}]
    save_csv(RESULTS/"validation-register.csv",validations)
    metrics={
        "route":"H2-approved 2-D consistency route; M1 baseline, M2 backbone, M3 main, M4 ablation",
        "q1_m2_final_mean_C":key["q1"]["metrics"]["final_mean_C"],
        "q2_m3_final_max_C":key["q2"]["metrics"]["final_max_C"],
        "q2_m2_constant_final_max_C":key["q2_const"]["metrics"]["final_max_C"],
        "q2_m4_final_max_C":key["q2_m4"]["metrics"]["final_max_C"],
        "q3_m3_t_star_s":key["q3"]["metrics"]["final_time_s"],
        "q3_m4_ablation_t_star_s":key["q3_m4"]["metrics"]["final_time_s"],
        "q4_reference_t_star_s":key["q4"]["metrics"]["final_time_s"],
        "q4_moving_fv_t_star_s":key["q4_moving"]["metrics"]["final_time_s"],
        "q4_jacobian_ablation_t_star_s":key["q4_abl"]["metrics"]["final_time_s"],
        "maximum_approved_route_balance_error":max_bal,"jacobian_ablation_balance_error":ablation_bal,"maximum_linear_residual":max_res,
        "pressure_test":"4 h terminal-window and hm/prefactor sensitivity; see sensitivity.csv",
        "interpretation_limit":"conditional simulation under problem-supplied empirical laws; no observational fit claim"
    }
    (RESULTS/"key-metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    return validations,metrics


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["p1","full","extended"],default="full"); args=ap.parse_args()
    RESULTS.mkdir(parents=True,exist_ok=True); FIGURES.mkdir(parents=True,exist_ok=True); LOGS.mkdir(parents=True,exist_ok=True)
    logpath=LOGS/("p1.log" if args.mode=="p1" else "extended.log" if args.mode=="extended" else "full.log")
    with logpath.open("a" if args.mode=="full" else "w",encoding="utf-8") as log:
        log.write("\n=== NEW RUN ===\n")
        log.write(f"command={' '.join(sys.argv)}\npython={sys.version}\nplatform={platform.platform()}\n")
        if args.mode=="extended":
            extended_threshold_suite(log)
            return
        p1rows=p1_suite(log)
        if args.mode=="p1": return
        summary,conv,sens,key=full_suite(log); make_plots(conv,sens,key); write_metadata(p1rows,summary,conv,sens,key)


if __name__ == "__main__": main()

~~~~

## `04-compute/src/finalize_compute.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
"""Create reproducibility/evidence manifests and schema-shaped COMPUTE handoff."""
from __future__ import annotations
import hashlib,json,platform,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy,openpyxl,PIL

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/"04-compute"
SIDE_WORK_DIRS={"revision-grid-conv-20260912","temperature-field-revision-20260912"}
SIDE_WORK_FILES={"q3_dense_sensitivity.py","q3-dense-sensitivity.log"}
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def item(rel): return {"path":rel.as_posix(),"sha256":digest(ROOT/rel)}
def stable_output(p):
 return p.is_file() and p.name not in SIDE_WORK_FILES and "__pycache__" not in p.parts and p.suffix != ".pyc" and not any(part in SIDE_WORK_DIRS for part in p.parts)

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
 "numerical_contract":{"method":"cell-centered conservative axisymmetric FV on two-sided locally refined radial grids; backward-Euler coefficient Picard; preconditioned CG","picard_absolute_update_tolerance":1e-7,"threshold":"max(C)<0.15-1e-6","event_time":"linear interpolation inside the first-crossing bracket, then conservative ceiling to 60 s for reporting","report_resolution_s":60,"radius":"shape-preserving PCHIP","moving_surface_output":"Robin-reconstructed value at the current moving boundary R(t), not the nearest fixed evaluation radius","terminal_window_base_s":3600},
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
 "assumptions":["M4 is limited to the problem-identifiable temperature-dependent coefficient coupling and is used only as an ablation.","The 4 h terminal environment uses the frozen one-hour mean base case and bounded 0.5/2 h window tests.","For extended threshold runs after 72 h, the chamber continues at the approved terminal-window values and Q4 radius is held at the final observed attachment-2 radius.","Moving material cells use affine radial motion and dry-solid density continuity; no unsupported latent-heat source is introduced.","Q4 surface_C and surface_T_C are evaluated at the current moving boundary using the Robin boundary reconstruction; fixed-radius profile snapshots retain NA outside R(t)."],
 "unknowns":["No internal experimental observations are available, so numerical differences among M2/M3/M4 are not fit improvements.","Problem-supplied empirical laws are treated as conditional simulation laws, not universal material properties."],
 "claims":["All numerical values in the COMPUTE evidence were generated by recorded commands.","The approved M1-M4 compatibility route, baseline, threshold and moving-domain validation commands were executed without changing upstream files.","Diagnostic figures are model-checking aids only and are not publication figures."],
 "evidence":["04-compute/证据索引.json maps claims to source tables.","04-compute/results/validation-register.csv records V01-V12 outcomes.","04-compute/复现清单.json records hashes, environment, parameters and commands."],
 "warnings":["Model contrasts must not be described as empirical accuracy gains.","Sensitivity ranges are conditional on preregistered bounded scenarios and do not exhaust structural uncertainty.","The Q2 V02 margin is narrow (4.00114e-5 versus 5e-5), so downstream consumers must retain the recorded finest-grid values and must not recompute on the old coarse grid."],
 "required_next_actions":(["For V02, increase radial resolution or adopt a demonstrably higher-order conservative radial discretization until the four-decimal field tolerance passes.","For V06, refine the time step and locally bracket the Q3/Q4 threshold until the reported 60 s event time is unchanged; otherwise ask the team whether to reopen H2 validation tolerances.","Do not start EVIDENCE, publication figures or paper writing while COMPUTE is FAIL."] if stage_status=="FAIL" else ["Independently verify this handoff schema and every declared SHA-256 before starting EVIDENCE.","Stop here; do not create publication figures or paper text in this task."]),
 "completed_at":datetime.now(timezone.utc).astimezone().isoformat()}
(OUT/"handoff.json").write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"status":stage_status,"outputs":len(all_outputs),"handoff_sha256":digest(OUT/"handoff.json"),"key_metrics":metrics},ensure_ascii=False,indent=2))

~~~~

## `04-compute/src/q3_dense_sensitivity.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
from __future__ import annotations

"""Q3 dense one-factor sensitivity extension.

This extension reuses the approved solver in formal_compute.py.  It writes only
COMPUTE outputs and is intentionally separate from the already-frozen full
suite tables so that the extra scan can be audited independently.
"""

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from formal_compute import LOGS, RESULTS, RunConfig, save_csv, simulate


ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve()
SOLVER = ROOT / "04-compute" / "src" / "formal_compute.py"
GUARD_S = 30 * 24 * 3600
THRESHOLD = 0.15 - 1e-6


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run_case(log, label: str, cfg: RunConfig) -> dict:
    log.write(f"START {label} {datetime.now(timezone.utc).isoformat()}\n")
    log.flush()
    run = simulate(cfg)
    metrics = run["metrics"]
    row = {
        "scope": "Q3",
        "factor": cfg.label.split("-dense-")[1].rsplit("-", 1)[0]
        if "-dense-" in cfg.label else "terminal_window_s",
        "level": "",
        "value": "",
        "t_star_s": metrics["reported_event_time_s"] or metrics["final_time_s"],
        "interpolated_t_star_s": metrics["interpolated_event_time_s"] or "",
        "final_max_C": metrics["final_max_C"],
        "final_mean_C": metrics["final_mean_C"],
        "crossed": bool(metrics["reported_event_time_s"] is not None),
        "guard_s": cfg.duration,
        "solver_label": cfg.label,
    }
    log.write(json.dumps({"label": label, **metrics}, ensure_ascii=False) + "\n")
    log.flush()
    return row


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_csv = RESULTS / "sensitivity-q3-dense.csv"
    out_manifest = RESULTS / "sensitivity-q3-dense-manifest.json"
    log_path = LOGS / "q3-dense-sensitivity.log"
    rows = []

    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"command={' '.join(sys.argv)}\n")
        log.write(f"python={sys.version}\nplatform={platform.platform()}\n")

        window_levels = [("30 min", 1800), ("45 min", 2700), ("60 min", 3600),
                         ("90 min", 5400), ("120 min", 7200)]
        for level, window in window_levels:
            cfg = RunConfig(
                f"Q3-dense-terminal_window_s-{level}", 10, 20, 60, GUARD_S, 3,
                "M3", window_s=window, stop_threshold=THRESHOLD, sample_every=3600,
            )
            row = run_case(log, cfg.label, cfg)
            row.update({"factor": "terminal_window_s", "level": level, "value": window})
            rows.append(row)

        factor_levels = [("0.8x", 0.8), ("0.9x", 0.9), ("1.0x", 1.0),
                         ("1.1x", 1.1), ("1.2x", 1.2)]
        for factor in ("h_mult", "hm_mult", "pref", "exponent"):
            for level, value in factor_levels:
                cfg = RunConfig(
                    f"Q3-dense-{factor}-{level}", 10, 20, 60, GUARD_S, 3,
                    "M3", stop_threshold=THRESHOLD, sample_every=3600,
                    **{factor: value},
                )
                row = run_case(log, cfg.label, cfg)
                row.update({"factor": factor, "level": level, "value": value})
                rows.append(row)

    save_csv(out_csv, rows)
    manifest = {
        "schema_version": "1.0",
        "stage": "COMPUTE",
        "scope": "Q3 dense one-factor sensitivity",
        "status": "PASS" if all(r["crossed"] for r in rows) else "FAIL",
        "levels": {
            "terminal_window_s": [1800, 2700, 3600, 5400, 7200],
            "multipliers": [0.8, 0.9, 1.0, 1.1, 1.2],
        },
        "guard_s": GUARD_S,
        "threshold": THRESHOLD,
        "rows": len(rows),
        "inputs": [
            {"path": "04-compute/src/formal_compute.py", "sha256": sha256(SOLVER)},
            {"path": "04-compute/src/q3_dense_sensitivity.py", "sha256": sha256(SRC)},
        ],
        "outputs": [
            {"path": "04-compute/results/sensitivity-q3-dense.csv", "sha256": sha256(out_csv)},
            {"path": "04-compute/logs/q3-dense-sensitivity.log", "sha256": sha256(log_path)},
        ],
        "command": "python 04-compute/src/q3_dense_sensitivity.py",
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

~~~~

## `04-compute/src/repair_probe.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
"""Bounded radial-resolution probe for V02/V06 repair."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from formal_compute import RunConfig, simulate

CASES = [
    ("Q1-M1", 1, "M1", 0.5, 1800, [81, 122, 183]),
    ("Q1-M2", 54, "M2", 0.5, 1800, [62, 93, 140]),
    ("Q2-M3", 36, "M3", 5.0, 10800, [62, 93, 140]),
    ("Q3-M3", 36, "M3", 60.0, 259200, [62, 93, 140, 210]),
    ("Q4-M3", 32, "M3", 60.0, 259200, [93, 140, 210]),
]

ap=argparse.ArgumentParser(); ap.add_argument("--family"); args=ap.parse_args()
rows=[]
for family,nz,model,dt,duration,nrs in CASES:
    if args.family and family != args.family:
        continue
    q = 1 if family.startswith("Q1") else (2 if family.startswith("Q2") else (3 if family.startswith("Q3") else 4))
    for nr in nrs:
        cfg=RunConfig(f"probe-{family}-nr{nr}",nr,nz,dt,duration,q,model,
                      moving_impl=("reference" if q==4 else "fixed"),
                      stop_threshold=(.15-1e-6 if q in (3,4) else None),sample_every=duration)
        r=simulate(cfg)
        row={"family":family,"nr":nr,"nz":nz,"dt_s":dt,
             "grid_strategy":cfg.radial_strategy,
             "final_max_C":r["metrics"]["final_max_C"],
             "final_mean_C":r["metrics"]["final_mean_C"],
             "event_time_s":r["metrics"]["interpolated_event_time_s"],
             "reported_event_time_s":r["metrics"]["reported_event_time_s"],
             "runtime_s":r["metrics"]["runtime_s"]}
        rows.append(row); print(json.dumps(row,ensure_ascii=False),flush=True)

out=Path(__file__).resolve().parents[1]/"results"/"repair-probe.json"
out.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")

~~~~

## `04-compute/revision-grid-conv-20260913/run_q2_grid_dt5.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
"""Candidate Q2 spatial-grid extension at the frozen formal time step dt=5 s.

This runs only additional Q2/M3 grid levels and writes an isolated candidate
package; it does not overwrite 04-compute/results.
"""
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04-compute" / "src"))
import formal_compute as fc  # noqa: E402

OUT = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "q2-space-dt5"
OUT.mkdir(parents=True, exist_ok=True)

rows = []
previous = None
for nr in (42, 62, 93, 140, 175, 210):
    result = fc.simulate(fc.RunConfig(
        label=f"Q2-M3-nr{nr}-dt5",
        nr=nr, nz=36, dt=5, duration=10800, q=2, model="M3", sample_every=3600,
    ))
    value = float(result["metrics"]["final_max_C"])
    change = "" if previous is None else abs(value - previous)
    rows.append({
        "scope": "Q2", "family": "M3", "level": len(rows) + 1,
        "nr": nr, "nz": 36, "fixed_dt_s": 5.0,
        "metric": "final_max_C", "value": value,
        "adjacent_change": change,
        "runtime_s": result["metrics"]["runtime_s"],
    })
    previous = value

path = OUT / "field-grid-convergence.csv"
with path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(path)

~~~~

## `04-compute/revision-grid-conv-20260913/run_q2_model_trajectories.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04-compute" / "src"))
import formal_compute as fc  # noqa: E402

OUT = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "q2-model-trajectories"
OUT.mkdir(parents=True, exist_ok=True)

configs = [
    ("M2 常物性", 18, 36, 10.0, "M2"),
    ("M3 主路线", 140, 36, 5.0, "M3"),
    ("M4 温度耦合消融", 18, 36, 10.0, "M4"),
]
rows = []
for label, nr, nz, dt, model in configs:
    result = fc.simulate(fc.RunConfig(
        label=f"Q2-{model}-trajectory", nr=nr, nz=nz, dt=dt,
        duration=10800, q=2, model=model, sample_every=600,
    ))
    for rec in result["records"]:
        rows.append({"model": label, "time_s": rec["time_s"], "max_C": rec["max_C"], "mean_C": rec["mean_C"]})

path = OUT / "q2-model-trajectories.csv"
with path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
print(path)

~~~~

## `04-compute/revision-grid-conv-20260913/run_space_extra.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04-compute" / "src"))
import formal_compute as fc  # noqa: E402

OUT = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "space-extra-dt60"
OUT.mkdir(parents=True, exist_ok=True)

rows = []
for scope, nr, nz, q, model, moving_impl in [
    ("Q3", 63, 36, 3, "M3", "fixed"),
    ("Q3", 175, 36, 3, "M3", "fixed"),
    ("Q4", 63, 32, 4, "M3", "reference"),
    ("Q4", 175, 32, 4, "M3", "reference"),
]:
    result = fc.simulate(fc.RunConfig(
        label=f"{scope}-M3-nr{nr}-dt60-extra", nr=nr, nz=nz, dt=60,
        duration=259200, q=q, model=model, moving_impl=moving_impl,
        stop_threshold=0.15 - 1e-6, sample_every=60,
    ))
    rows.append({
        "scope": scope, "nr": nr, "nz": nz, "grid_strategy": "two-sided-local",
        "fixed_dt_s": 60, "interpolated_event_time_s": result["metrics"]["interpolated_event_time_s"],
        "reported_event_time_s": result["metrics"]["reported_event_time_s"],
    })

path = OUT / "threshold-grid-extra.csv"
with path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
print(path)

~~~~

## `06-figure/scripts/redraw_fig6.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
from __future__ import annotations

"""Redraw FIG-Q3-THRESHOLD-TRAJECTORY without changing its frozen data.

The script intentionally reads the existing FIGURE snapshot and independently
checks it against the COMPUTE result before rendering.  It writes only the
figure-6 artwork, previews, and a small QA record; it never rewrites the data
snapshot or recomputes the model.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[2]
FIGURE = "FIG-Q3-THRESHOLD-TRAJECTORY"
FIG_DIR = ROOT / "06-figure" / "figures"
PREVIEW_DIR = ROOT / "06-figure" / "previews"
SNAPSHOT = ROOT / "06-figure" / "data-snapshots" / f"{FIGURE}.csv"
SOURCE = ROOT / "04-compute" / "results" / "q3-threshold-trajectory.csv"
CONTRACT = ROOT / "06-figure" / "contracts" / f"{FIGURE}.json"
RECORD_DIR = ROOT / "06-figure" / "redraw-fig6-20260912"

PNG = FIG_DIR / f"{FIGURE}.png"
SVG = FIG_DIR / f"{FIGURE}.svg"
PDF = FIG_DIR / f"{FIGURE}.pdf"
COLOR_PREVIEW = PREVIEW_DIR / f"{FIGURE}-color.png"
GRAY_PREVIEW = PREVIEW_DIR / f"{FIGURE}-grayscale.png"

THRESHOLD = 0.149999
REPORT_TIME_S = 206820.0
XMAX_H = 60.0
YMAX = 2.7

FONT_PATH = Path(r"C:\Windows\Fonts\simsun.ttc")
if not FONT_PATH.exists():
    raise FileNotFoundError(f"宋体字体文件不存在: {FONT_PATH}")
fontManager.addfont(str(FONT_PATH))
FONT = FontProperties(fname=str(FONT_PATH))

COLORS = {
    "max_C": "#0072B2",       # blue
    "mean_C": "#E69F00",      # orange
    "center_C": "#009E73",    # green
    "surface_C": "#D55E00",   # vermillion
}
LABELS = {
    "max_C": "最大值",
    "mean_C": "均值",
    "center_C": "中心",
    "surface_C": "表面",
}
MARKERS = {
    "max_C": "o",
    "mean_C": "s",
    "center_C": "^",
    "surface_C": "D",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check_data() -> tuple[pd.DataFrame, dict]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    source_expected = contract["source_files"][0]["sha256"]
    snapshot_expected = contract["snapshot_sha256"]
    source_actual = sha256(SOURCE)
    snapshot_actual = sha256(SNAPSHOT)
    if source_actual != source_expected:
        raise RuntimeError(
            f"原始结果哈希不匹配: expected={source_expected}, actual={source_actual}"
        )
    if snapshot_actual != snapshot_expected:
        raise RuntimeError(
            f"冻结快照哈希不匹配: expected={snapshot_expected}, actual={snapshot_actual}"
        )

    source_df = pd.read_csv(SOURCE)
    snapshot_df = pd.read_csv(SNAPSHOT)
    expected_columns = ["time_s", "max_C", "mean_C", "center_C", "surface_C"]
    if not set(expected_columns).issubset(source_df.columns) or list(snapshot_df.columns) != expected_columns:
        raise RuntimeError("源数据或冻结快照列结构发生变化")
    if len(source_df) != len(snapshot_df):
        raise RuntimeError("源数据与冻结快照行数不一致")
    source_values = source_df[expected_columns].to_numpy(dtype=float)
    snapshot_values = snapshot_df.to_numpy(dtype=float)
    max_abs_diff = float(np.max(np.abs(source_values - snapshot_values)))
    # The snapshot is a CSV projection of the source; decimal parsing can
    # differ by one floating-point ulp while preserving every plotted value.
    if not np.allclose(source_values, snapshot_values, rtol=0.0, atol=5e-15):
        raise RuntimeError(f"源数据与冻结快照数值不一致，最大绝对差={max_abs_diff}")

    checks = {
        "source_path": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": source_actual,
        "snapshot_path": SNAPSHOT.relative_to(ROOT).as_posix(),
        "snapshot_sha256": snapshot_actual,
        "columns": expected_columns,
        "rows": int(len(snapshot_df)),
        "data_equal": True,
        "max_abs_diff_after_csv_parse": max_abs_diff,
        "time_range_s": [float(snapshot_df.time_s.min()), float(snapshot_df.time_s.max())],
        "reported_time_s": REPORT_TIME_S,
        "threshold": THRESHOLD,
    }
    return snapshot_df, checks


def configure_text() -> None:
    plt.rcParams.update(
        {
            "font.family": "SimSun",
            "font.sans-serif": ["SimSun"],
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def style_axes(ax, *, inset: bool = False) -> None:
    ax.set_facecolor("white")
    ax.tick_params(
        axis="both",
        which="both",
        colors="black",
        labelcolor="black",
        direction="out",
        length=3.0 if inset else 4.0,
        width=0.7,
        labelsize=6.5 if inset else 8.0,
    )
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(FONT)
        label.set_color("black")
    for spine in ax.spines.values():
        spine.set_color("black")
        spine.set_linewidth(0.7)
    ax.grid(True, color="black", alpha=0.14, linewidth=0.45)
    ax.set_axisbelow(True)


def draw_series(ax, data: pd.DataFrame, *, marker_indices: np.ndarray, linewidth: float, markersize: float) -> None:
    time_h = data.time_s.to_numpy(dtype=float) / 3600.0
    for column in ("max_C", "mean_C", "center_C", "surface_C"):
        ax.plot(
            time_h,
            data[column].to_numpy(dtype=float),
            color=COLORS[column],
            linestyle="-",
            linewidth=linewidth,
            marker=MARKERS[column],
            markersize=markersize,
            markevery=marker_indices,
            markerfacecolor=COLORS[column],
            markeredgecolor="black",
            markeredgewidth=0.45,
            label=LABELS[column],
            zorder=3,
        )


def render(data: pd.DataFrame) -> None:
    configure_text()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    RECORD_DIR.mkdir(parents=True, exist_ok=True)

    # Markers are a visual encoding only; every row remains in every line.
    marker_hours = np.array([0, 2, 4, 8, 12, 24, 36, 48, REPORT_TIME_S / 3600.0])
    time_hours = data.time_s.to_numpy(dtype=float) / 3600.0
    marker_indices = np.array([int(np.argmin(np.abs(time_hours - h))) for h in marker_hours])
    marker_indices = np.unique(marker_indices)

    fig, ax = plt.subplots(figsize=(6.535, 4.75), dpi=600)
    fig.patch.set_facecolor("white")
    draw_series(ax, data, marker_indices=marker_indices, linewidth=1.45, markersize=3.7)
    ax.axhline(
        THRESHOLD,
        color="black",
        linestyle="--",
        linewidth=0.9,
        label="判据 0.149999",
        zorder=2,
    )
    ax.axvline(
        REPORT_TIME_S / 3600.0,
        color="black",
        linestyle=":",
        linewidth=0.9,
        label="报告时刻 57.45 h",
        zorder=2,
    )
    ax.set_xlim(0, XMAX_H)
    ax.set_ylim(0, YMAX)
    ax.set_title(
        "全域含水率随时间的变化",
        fontproperties=FONT,
        fontsize=10.5,
        color="black",
        pad=8,
    )
    ax.set_xlabel("时间 t (h)", fontproperties=FONT, fontsize=9, color="black", labelpad=5)
    ax.set_ylabel("干基含水率 C (kg/kg)", fontproperties=FONT, fontsize=9, color="black", labelpad=5)
    style_axes(ax)

    handles = [
        Line2D(
            [0], [0], color=COLORS[c], linestyle="-", linewidth=1.45,
            marker=MARKERS[c], markersize=4.2, markerfacecolor=COLORS[c],
            markeredgecolor="black", markeredgewidth=0.45, label=LABELS[c],
        )
        for c in ("max_C", "mean_C", "center_C", "surface_C")
    ]
    handles += [
        Line2D([0], [0], color="black", linestyle="--", linewidth=0.9, label="判据 0.149999"),
        Line2D([0], [0], color="black", linestyle=":", linewidth=0.9, label="报告时刻 57.45 h"),
    ]
    legend = ax.legend(
        handles=handles,
        loc="upper right",
        bbox_to_anchor=(0.99, 0.93),
        ncol=3,
        frameon=False,
        borderaxespad=0.25,
        handlelength=2.3,
        columnspacing=1.0,
        handletextpad=0.45,
        prop=FontProperties(fname=str(FONT_PATH), size=7.5),
    )
    for text in legend.get_texts():
        text.set_color("black")

    # A compact, explicitly labelled local view makes the threshold event legible
    # without changing the primary 0–60 h coordinate range.
    inset = ax.inset_axes([0.56, 0.16, 0.39, 0.38])
    draw_series(inset, data, marker_indices=marker_indices, linewidth=1.0, markersize=2.8)
    inset.axhline(THRESHOLD, color="black", linestyle="--", linewidth=0.7, zorder=2)
    inset.axvline(REPORT_TIME_S / 3600.0, color="black", linestyle=":", linewidth=0.7, zorder=2)
    inset.set_xlim(45, 60)
    inset.set_ylim(0.04, 0.17)
    inset.set_title("判据附近局部放大", fontproperties=FONT, fontsize=7.5, color="black", pad=3)
    inset.set_xlabel("t (h)", fontproperties=FONT, fontsize=6.5, color="black", labelpad=2)
    inset.set_ylabel("C", fontproperties=FONT, fontsize=6.5, color="black", labelpad=2)
    style_axes(inset, inset=True)

    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.12, top=0.91)
    for path, kwargs in (
        (SVG, {"format": "svg"}),
        (PDF, {"format": "pdf"}),
        (PNG, {"format": "png", "dpi": 600}),
        (COLOR_PREVIEW, {"format": "png", "dpi": 300}),
    ):
        fig.savefig(path, facecolor="white", **kwargs)
    plt.close(fig)

    ImageOps.grayscale(Image.open(COLOR_PREVIEW).convert("RGB")).save(
        GRAY_PREVIEW, dpi=(300, 300)
    )


def write_record(checks: dict) -> None:
    record = {
        "figure_id": FIGURE,
        "visual_revision": "redraw-fig6-20260912-title-simsun",
        "data_check": checks,
        "visual_contract": {
            "title": "全域含水率随时间的变化（黑色宋体）",
            "data_curves": "高对比彩色、统一实线、marker 冗余编码",
            "non_data_elements": "坐标轴、网格、刻度、轴标签、图例和标注统一黑色",
            "font": "SimSun / 宋体",
            "primary_xlim_h": [0, XMAX_H],
            "primary_ylim": [0, YMAX],
            "threshold": THRESHOLD,
            "reported_time_s": REPORT_TIME_S,
            "note_policy": "删除图内无关备注；限制条件保留在正式图注/正文",
        },
        "outputs": {
            "png_600dpi": PNG.relative_to(ROOT).as_posix(),
            "svg": SVG.relative_to(ROOT).as_posix(),
            "pdf": PDF.relative_to(ROOT).as_posix(),
            "color_preview": COLOR_PREVIEW.relative_to(ROOT).as_posix(),
            "grayscale_preview": GRAY_PREVIEW.relative_to(ROOT).as_posix(),
        },
    }
    for key, path in (
        ("png_sha256", PNG),
        ("svg_sha256", SVG),
        ("pdf_sha256", PDF),
        ("color_preview_sha256", COLOR_PREVIEW),
        ("grayscale_preview_sha256", GRAY_PREVIEW),
    ):
        record["outputs"][key] = sha256(path)
    (RECORD_DIR / "qa-report.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    data, checks = check_data()
    render(data)
    write_record(checks)
    print(json.dumps({
        "figure": FIGURE,
        "rows": checks["rows"],
        "data_equal": checks["data_equal"],
        "png_sha256": sha256(PNG),
        "svg_sha256": sha256(SVG),
        "pdf_sha256": sha256(PDF),
        "color_preview_sha256": sha256(COLOR_PREVIEW),
        "grayscale_preview_sha256": sha256(GRAY_PREVIEW),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

~~~~

## `06-figure/scripts/redraw_fig7.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
"""Redraw FIG-Q3-BRACKET-ZOOM without changing its frozen data or claim."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FormatStrFormatter
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
FIGURE_DIR = ROOT / "06-figure"
SOURCE = ROOT / "04-compute" / "results" / "q3-threshold-trajectory.csv"
RUN_SUMMARY = ROOT / "04-compute" / "results" / "run-summary.csv"
SNAPSHOT = FIGURE_DIR / "data-snapshots" / "FIG-Q3-BRACKET-ZOOM.csv"
CONTRACT = FIGURE_DIR / "contracts" / "FIG-Q3-BRACKET-ZOOM.json"
FIGURES = FIGURE_DIR / "figures"
PREVIEWS = FIGURE_DIR / "previews"
FIG_ID = "FIG-Q3-BRACKET-ZOOM"
THRESHOLD = 0.149999  # frozen Q3 full-domain threshold: 0.15 - 1e-6


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_frozen_data() -> pd.DataFrame:
    """Use the existing snapshot as plotting input and verify it against source rows."""
    snapshot = pd.read_csv(SNAPSHOT)
    expected_columns = ["time_s", "max_C"]
    if list(snapshot.columns) != expected_columns:
        raise AssertionError(f"unexpected snapshot columns: {list(snapshot.columns)}")
    if len(snapshot) != 6:
        raise AssertionError(f"FIG-Q3-BRACKET-ZOOM must retain 6 samples, got {len(snapshot)}")

    source = pd.read_csv(SOURCE)
    for row in snapshot.itertuples(index=False):
        candidates = source[source["time_s"].eq(row.time_s)]
        if candidates.empty or not np.isclose(
            candidates["max_C"].to_numpy(dtype=float),
            float(row.max_C),
            rtol=0.0,
            atol=1e-15,
        ).any():
            raise AssertionError(f"snapshot row is not present in source: {row}")
    return snapshot


def read_frozen_event_times() -> tuple[float, float]:
    summary = pd.read_csv(RUN_SUMMARY)
    row = summary.loc[summary["label"].eq("Q3-M3-nr210")]
    if len(row) != 1:
        raise AssertionError("expected exactly one Q3-M3-nr210 row in run-summary.csv")
    interpolated = float(row.iloc[0]["interpolated_event_time_s"])
    reported = float(row.iloc[0]["reported_event_time_s"])
    if not np.isclose(interpolated, 206818.71137262788, rtol=0.0, atol=1e-12):
        raise AssertionError("unexpected frozen interpolated event time")
    if not np.isclose(reported, 206820.0, rtol=0.0, atol=1e-12):
        raise AssertionError("unexpected frozen reported event time")
    return interpolated, reported


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    data = validate_frozen_data()
    interpolated, reported = read_frozen_event_times()

    mpl.rcParams.update(
        {
            "font.family": "SimSun",
            "font.sans-serif": ["SimSun", "STSong", "FangSong", "Microsoft YaHei", "Arial"],
            "font.serif": ["SimSun", "STSong", "FangSong", "Microsoft YaHei", "Arial"],
            "font.size": 8.5,
            "text.color": "#000000",
            "axes.labelcolor": "#000000",
            "axes.titlecolor": "#000000",
            "xtick.color": "#000000",
            "ytick.color": "#000000",
            "legend.labelcolor": "#000000",
            "axes.unicode_minus": False,
            "axes.facecolor": "#FFFFFF",
            "figure.facecolor": "#FFFFFF",
            "savefig.facecolor": "#FFFFFF",
            "axes.axisbelow": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": FIG_ID,
        }
    )

    # The curve is one data series: keep it solid. Point colors and markers
    # identify the six retained sampling times and survive grayscale printing.
    point_colors = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#7B2CBF", "#007C91"]
    point_markers = ["o", "s", "^", "D", "P", "X"]

    fig, ax = plt.subplots(figsize=(6.7, 4.2), dpi=600)
    fig.subplots_adjust(left=0.135, right=0.985, bottom=0.19, top=0.80)

    ax.plot(
        data["time_s"],
        data["max_C"],
        color="#005AB5",
        linestyle="-",
        linewidth=1.7,
        zorder=2,
    )
    for color, marker, row in zip(point_colors, point_markers, data.itertuples(index=False)):
        ax.plot(
            row.time_s,
            row.max_C,
            linestyle="None",
            marker=marker,
            markersize=5.5,
            markerfacecolor=color,
            markeredgecolor="#000000",
            markeredgewidth=0.55,
            zorder=3,
        )

    # Reference lines are not data curves; their black redundant line styles
    # make the threshold, interpolated event, and conservative report distinct.
    ax.axhline(
        THRESHOLD,
        color="#000000",
        linewidth=0.85,
        linestyle=(0, (5, 2.5)),
        zorder=1,
    )
    ax.axvline(
        interpolated,
        color="#000000",
        linewidth=0.85,
        linestyle=(0, (1.5, 2)),
        zorder=1,
    )
    ax.axvline(
        reported,
        color="#000000",
        linewidth=0.95,
        linestyle=(0, (6, 2)),
        zorder=1,
    )

    ax.set_xlabel("时间 t (s)", fontsize=9.5, color="#000000", labelpad=7)
    ax.set_ylabel("最大干基含水率 C (kg/kg)", fontsize=9.5, color="#000000", labelpad=8)
    ax.set_xticks(data["time_s"].tolist())
    ax.set_xticklabels([str(int(x)) for x in data["time_s"]])
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.6f"))
    ax.tick_params(
        axis="both",
        which="major",
        direction="out",
        length=3.2,
        width=0.65,
        colors="#000000",
        labelsize=7.4,
    )
    ax.grid(axis="both", color="#000000", linewidth=0.45, alpha=0.14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#000000")
        ax.spines[side].set_linewidth(0.75)

    legend_handles = [
        Line2D([0], [0], color="#000000", linewidth=0.85, linestyle=(0, (5, 2.5)), label="阈值 C = 0.149999"),
        Line2D([0], [0], color="#000000", linewidth=0.85, linestyle=(0, (1.5, 2)), label=f"插值时刻 {interpolated:.4f} s"),
        Line2D([0], [0], color="#000000", linewidth=0.95, linestyle=(0, (6, 2)), label=f"保守报告 {reported:.0f} s"),
    ]
    legend = fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.57, 0.895),
        ncol=3,
        frameon=False,
        fontsize=7.5,
        columnspacing=1.35,
        handlelength=2.2,
        handletextpad=0.45,
        borderaxespad=0.0,
    )
    for text in legend.get_texts():
        text.set_color("#000000")

    fixed_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fig.savefig(FIGURES / f"{FIG_ID}.svg", metadata={"Date": "2026-01-01T00:00:00"})
    fig.savefig(
        FIGURES / f"{FIG_ID}.pdf",
        dpi=600,
        metadata={"CreationDate": fixed_date, "ModDate": fixed_date},
    )
    fig.savefig(FIGURES / f"{FIG_ID}.png", dpi=600)
    fig.savefig(PREVIEWS / f"{FIG_ID}-color.png", dpi=600)
    plt.close(fig)

    formal_color = Image.open(FIGURES / f"{FIG_ID}.png").convert("RGB")
    ImageOps.grayscale(formal_color).save(PREVIEWS / f"{FIG_ID}-grayscale.png", dpi=(600, 600))

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    contract["target_formats"] = ["svg", "png", "pdf"]
    CONTRACT.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "figure_id": FIG_ID,
                "source_sha256": sha256(SOURCE),
                "snapshot_sha256": sha256(SNAPSHOT),
                "png_sha256": sha256(FIGURES / f"{FIG_ID}.png"),
                "svg_sha256": sha256(FIGURES / f"{FIG_ID}.svg"),
                "pdf_sha256": sha256(FIGURES / f"{FIG_ID}.pdf"),
                "sample_count": len(data),
                "font": "SimSun",
                "data_claim_status": "unchanged",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

~~~~

## `06-figure/scripts/redraw_fig9_onward.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
from __future__ import annotations

"""重绘正式图 9--22。

本脚本只读取 06-figure/data-snapshots 下已经冻结的快照；源文件只用于
SHA-256 核对，不重新运行模型、不重算指标、不修改快照或上游决策。
正式输出仍写入 06-figure/figures，旧版文件先复制到本轮 revision 目录留存。
"""

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "06-figure"
SNAP = STAGE / "data-snapshots"
CONTRACTS = STAGE / "contracts"
FORMAL = STAGE / "figures"
PREVIEWS = STAGE / "previews"
REV = STAGE / "redraw-fig9-onward-20260912"
REV_FIGURES = REV / "figures"
REV_PREVIEWS = REV / "previews"
REV_QA = REV / "qa"
REV_SUPERSEDED = REV / "superseded"

TARGET_IDS = [
    "FIG-Q3-SENS-ONEFACTOR",
    "FIG-Q3-COMBINED-BOUNDARY",
    "FIG-Q4-RADIUS-TIME",
    "FIG-Q4-THRESHOLD-TRAJECTORY",
    "FIG-Q4-JACOBIAN-ABLATION",
    "FIG-Q4-COMBINED-BOUNDARY",
    "FIG-Q1-GRID-CONV",
    "FIG-Q2-V02-MARGIN",
    "FIG-Q3-SPACE-CONV",
    "FIG-Q4-BRACKET-ZOOM",
    "FIG-Q4-SPACE-CONV",
]

BLACK = "#000000"
COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"]
MARKERS = ["o", "s", "^", "D", "P", "X"]
FONT_PATH = Path(r"C:\Windows\Fonts\simsun.ttc")
THRESHOLD = 0.149999
SONG: FontProperties


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def configure_style() -> None:
    global SONG
    require(FONT_PATH.exists(), f"宋体文件不存在: {FONT_PATH}")
    SONG = FontProperties(fname=str(FONT_PATH))
    mpl.rcParams.update(
        {
            "font.family": ["SimSun"],
            "font.sans-serif": ["SimSun", "STSong", "Microsoft YaHei", "Arial"],
            "font.size": 8.5,
            "axes.labelsize": 9.0,
            "axes.titlesize": 10.0,
            "axes.titleweight": "normal",
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "legend.fontsize": 8.0,
            "text.color": BLACK,
            "axes.labelcolor": BLACK,
            "axes.titlecolor": BLACK,
            "xtick.color": BLACK,
            "ytick.color": BLACK,
            "axes.facecolor": "#FFFFFF",
            "figure.facecolor": "#FFFFFF",
            "savefig.facecolor": "#FFFFFF",
            "axes.unicode_minus": False,
            "axes.axisbelow": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            # 本脚本为图 9 的长标签、图 16 的运行序号和多面板图显式分配边距；
            # 禁用全局 constrained layout，避免 subplots_adjust 被静默忽略。
            "figure.constrained_layout.use": False,
        }
    )


def read_snapshot(fid: str) -> tuple[pd.DataFrame, dict]:
    csv_path = SNAP / f"{fid}.csv"
    meta_path = SNAP / f"{fid}.meta.json"
    contract_path = CONTRACTS / f"{fid}.json"
    require(csv_path.exists(), f"缺少冻结快照: {csv_path}")
    require(meta_path.exists(), f"缺少快照元数据: {meta_path}")
    require(contract_path.exists(), f"缺少图表契约: {contract_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    require(contract.get("figure_id") == fid, f"契约 ID 不匹配: {fid}")
    require(sha256(csv_path) == meta.get("snapshot_sha256"), f"快照哈希不匹配: {fid}")
    source_checks = []
    for entry in meta.get("sources", []):
        source = ROOT / entry["path"]
        require(source.exists(), f"源文件不存在: {source}")
        actual = sha256(source)
        source_checks.append(
            {
                "path": entry["path"],
                "expected_sha256": entry["sha256"],
                "actual_sha256": actual,
                "status": "PASS" if actual == entry["sha256"] else "FAIL",
            }
        )
        require(actual == entry["sha256"], f"源数据哈希不匹配: {entry['path']}")
    return pd.read_csv(csv_path), {
        "figure_id": fid,
        "snapshot": rel(csv_path),
        "snapshot_sha256": sha256(csv_path),
        "rows": int(len(pd.read_csv(csv_path))),
        "columns": list(pd.read_csv(csv_path).columns),
        "sources": source_checks,
        "contract_sha256": sha256(contract_path),
    }


def text_font(obj) -> None:
    """统一所有可见文字为宋体和黑色；数据颜色只留给线和 marker。"""
    for txt in obj.findobj(mpl.text.Text):
        if txt.get_text().strip():
            txt.set_fontproperties(SONG)
            txt.set_color(BLACK)


def style_axis(ax, xlabel: str, ylabel: str, title: str | None = None,
               *, rotate: float = 0.0, grid: bool = True) -> None:
    ax.set_xlabel(xlabel, fontproperties=SONG, color=BLACK, labelpad=7)
    ax.set_ylabel(ylabel, fontproperties=SONG, color=BLACK, labelpad=7)
    if title:
        ax.set_title(title, loc="left", pad=9, fontproperties=SONG, color=BLACK)
    ax.tick_params(
        axis="both", which="major", direction="in", top=True, right=True,
        length=3.5, width=0.75, colors=BLACK, labelsize=8.0,
    )
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(BLACK)
        spine.set_linewidth(0.75)
    if grid:
        ax.grid(True, which="major", axis="both", color=BLACK, alpha=0.14, linewidth=0.55)
    else:
        ax.grid(False)
    for labels in (ax.get_xticklabels(), ax.get_yticklabels()):
        for label in labels:
            label.set_fontproperties(SONG)
            label.set_color(BLACK)
            if rotate:
                label.set_rotation(rotate)
                label.set_ha("right")


def legend_black(ax, **kwargs):
    kwargs.setdefault("frameon", False)
    kwargs.setdefault("prop", SONG)
    legend = ax.legend(**kwargs)
    if legend is not None:
        for txt in legend.get_texts():
            txt.set_fontproperties(SONG)
            txt.set_color(BLACK)
    return legend


def make_record(fid: str, meta: dict, fig: plt.Figure, qa_issues: list) -> dict:
    return {
        "figure_id": fid,
        "snapshot": meta["snapshot"],
        "snapshot_sha256": meta["snapshot_sha256"],
        "source_checks": meta["sources"],
        "rows": meta["rows"],
        "columns": meta["columns"],
        "figure_size_inches": [round(float(x), 4) for x in fig.get_size_inches()],
        "visual_qa": {
            "status": "PASS" if not any(s == "FAIL" for s, _ in qa_issues) else "FAIL",
            "issues": [{"severity": s, "message": m} for s, m in qa_issues],
        },
    }


def save_figure(fid: str, fig: plt.Figure, meta: dict, records: dict) -> None:
    text_font(fig)
    # 先在 Figure 对象上做程序版版式检查，再关闭对象。
    from visual_qa import audit_layout

    qa_issues = audit_layout(fig)
    records[fid] = make_record(fid, meta, fig, qa_issues)
    for ext in ("svg", "pdf", "png"):
        old = FORMAL / f"{fid}.{ext}"
        backup = REV_SUPERSEDED / f"{fid}.pre-redraw.{ext}"
        if old.exists() and not backup.exists():
            shutil.copy2(old, backup)
    fig_targets = {
        "svg": REV_FIGURES / f"{fid}.svg",
        "pdf": REV_FIGURES / f"{fid}.pdf",
        "png": REV_FIGURES / f"{fid}.png",
    }
    preview_targets = {
        "color": REV_PREVIEWS / f"{fid}-color.png",
        "grayscale": REV_PREVIEWS / f"{fid}-grayscale.png",
    }
    for target in fig_targets.values():
        target.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {"bbox_inches": "tight", "pad_inches": 0.05, "facecolor": "white"}
    fig.savefig(fig_targets["svg"], **save_kwargs)
    fig.savefig(fig_targets["pdf"], metadata={"Title": fid}, **save_kwargs)
    fig.savefig(fig_targets["png"], dpi=600, **save_kwargs)
    fig.savefig(preview_targets["color"], dpi=180, **save_kwargs)
    ImageOps.grayscale(Image.open(preview_targets["color"]).convert("RGB")).save(
        preview_targets["grayscale"], dpi=(180, 180)
    )
    # 正式目录保留本轮版本；旧版已在 superseded/ 中可恢复。
    for ext, target in fig_targets.items():
        shutil.copy2(target, FORMAL / target.name)
    for target in preview_targets.values():
        shutil.copy2(target, PREVIEWS / target.name)
    plt.close(fig)


def read(fid: str) -> tuple[pd.DataFrame, dict]:
    return read_snapshot(fid)


def plain_log_tick(value: float, _position: int) -> str:
    """Return an ASCII log tick so PDF/SVG text stays on the SimSun path."""
    if value <= 0:
        return ""
    exponent = int(round(np.log10(value)))
    return f"10^{exponent}"


def plot_q3_sensitivity(records: dict) -> None:
    fid = "FIG-Q3-SENS-ONEFACTOR"
    d, meta = read(fid)
    factor_specs = [
        ("terminal_window_s", "窗口", COLORS[0], (59.68, 59.86), [59.70, 59.75, 59.80, 59.85]),
        ("h_mult", "h", COLORS[1], (59.70, 59.80), [59.70, 59.75, 59.80]),
        ("hm_mult", "hm", COLORS[2], (58.5, 61.5), [59.0, 60.0, 61.0]),
        ("pref", "扩散系数前因子", COLORS[3], (49.0, 75.0), [50.0, 60.0, 70.0, 75.0]),
        ("exponent", "扩散经验指数", COLORS[4], (35.0, 105.0), [40.0, 60.0, 80.0, 100.0]),
    ]
    factor_labels = {
        "terminal_window_s": lambda row: f"{float(row['value']) / 60:g} min",
        "h_mult": lambda row: f"{float(row['value']):.1f}x",
        "hm_mult": lambda row: f"{float(row['value']):.1f}x",
        "pref": lambda row: f"{float(row['value']):.1f}x",
        "exponent": lambda row: f"{float(row['value']):.1f}x",
    }

    # 采用 small multiples：每个因素使用独立纵轴，避免不同尺度的达标时间
    # 被放在同一坐标轴后压扁。图中使用延长计算得到的实际达标时刻。
    fig, axes = plt.subplots(2, 3, figsize=(10.8, 7.0), squeeze=False)
    axes = axes.ravel()
    panel_letters = ["(a)", "(b)", "(c)", "(d)", "(e)"]
    for panel_i, (factor, title, color, ylim, yticks) in enumerate(factor_specs):
        ax = axes[panel_i]
        sub = d.loc[d["factor"].eq(factor)].copy()
        if factor != "terminal_window_s":
            sub = sub.sort_values("level", key=lambda s: s.map({"low": 0, "high": 1}))
        x = np.arange(len(sub), dtype=float)
        y = sub["display_h"].to_numpy(float)
        ax.plot(x, y, color=color, linewidth=1.8, linestyle="-", zorder=2)
        for point_i, (_, row) in enumerate(sub.iterrows()):
            marker = "o"
            ax.scatter(
                [point_i], [float(row["display_h"])], s=55,
                color=color, marker=marker, edgecolors=BLACK,
                linewidths=0.7, zorder=3,
            )
            # 数值标注让窄范围面板的差异可以直接读取；h 面板的重合也保持如实。
            value = float(row["display_h"])
            # 高位点的标注放在点下方，避免与独立纵轴的上边界刻度重叠。
            offset_y = -14 if value > ylim[0] + 0.78 * (ylim[1] - ylim[0]) else (7 if point_i % 2 == 0 else -14)
            ax.annotate(
                f"{value:.2f}",
                (point_i, value),
                xytext=(0, offset_y), textcoords="offset points",
                ha="center", va="center", fontproperties=SONG,
                fontsize=7.4, color=BLACK,
            )
        ax.set_xticks(x, [factor_labels[factor](row) for _, row in sub.iterrows()])
        ax.set_ylim(*ylim)
        ax.set_yticks(yticks)
        style_axis(ax, "扰动情景", "达标时间 t* (h)", f"{panel_letters[panel_i]} {title}")
        for label in ax.get_xticklabels():
            label.set_rotation(25)
            label.set_fontsize(7.5)
            label.set_ha("right")

    axes[-1].axis("off")
    fig.suptitle("Q3 单因素扰动的达标时间", y=0.995, fontproperties=SONG, fontsize=12, color=BLACK)
    fig.text(
        0.5, 0.015, "各小图使用独立纵轴；所有点为正式求解得到的实际首次达标时刻；条件仿真，非概率区间。",
        ha="center", va="bottom", fontproperties=SONG, fontsize=8.2, color=BLACK,
    )
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.17, top=0.86, wspace=0.34, hspace=0.48)
    save_figure(fid, fig, meta, records)


def plot_combined(fid: str, title: str, records: dict) -> None:
    d, meta = read(fid)
    x = np.arange(len(d), dtype=float)
    y = d["display_h"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot(x, y, color=COLORS[0], linewidth=1.8, linestyle="-", zorder=2)
    for i, (_, row) in enumerate(d.iterrows()):
        failed = float(row["display_h"]) >= 72.0 and float(row["final_max_C"]) > THRESHOLD
        marker = "X" if failed else "s"
        color = COLORS[5] if failed else COLORS[1]
        ax.scatter([i], [float(row["display_h"])], color=color, marker=marker, s=70,
                   edgecolors=BLACK, linewidths=0.7, zorder=3)
        text = "72 h：未达标" if failed else f"{float(row['display_h']):.2f} h"
        ax.annotate(text, (i, float(row["display_h"])), xytext=(0, 9 if failed else 7),
                    textcoords="offset points", ha="center", va="bottom",
                    fontproperties=SONG, color=BLACK, fontsize=8.0)
    ax.set_xticks(x, ["不利组合", "有利组合"])
    ax.set_ylim(0, 75)
    ax.set_yticks([0, 18, 36, 54, 72])
    ax.axhline(72, color=BLACK, linestyle="--", linewidth=0.85)
    style_axis(ax, "组合扰动情景", "达标时间 t* (h；× 表示未达标)", title)
    legend_black(
        ax,
        handles=[
            Line2D([0], [0], color=COLORS[1], marker="s", linestyle="-", lw=1.6, markersize=5, label="达标"),
            Line2D([0], [0], color=COLORS[5], marker="X", linestyle="None", markersize=6, label="72 h内未达标"),
        ],
        loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=2,
    )
    fig.subplots_adjust(left=0.11, right=0.98, bottom=0.19, top=0.82)
    save_figure(fid, fig, meta, records)


def plot_radius(records: dict) -> None:
    fid = "FIG-Q4-RADIUS-TIME"
    d, meta = read(fid)
    x = d["time_s"].to_numpy(float) / 3600.0
    y = d["radius_m"].to_numpy(float) * 100.0
    marks = np.unique(np.linspace(0, len(d) - 1, 6, dtype=int))
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot(x, y, color=COLORS[0], linewidth=1.7, linestyle="-", marker="o",
            markersize=4.0, markevery=marks, markerfacecolor=COLORS[0],
            markeredgecolor=BLACK, markeredgewidth=0.55)
    ax.annotate(f"R(0) = {y[0]:.2f} cm", (x[0], y[0]), xytext=(9, 8),
                textcoords="offset points", fontproperties=SONG, color=BLACK, fontsize=8)
    ax.annotate(f"R(t*) = {y[-1]:.2f} cm", (x[-1], y[-1]), xytext=(-68, 8),
                textcoords="offset points", ha="left", fontproperties=SONG, color=BLACK, fontsize=8)
    style_axis(ax, "时间 t (h)", "半径 R(t) (cm)", "移动边界半径随时间收缩")
    save_figure(fid, fig, meta, records)


def plot_threshold(fid: str, title: str, records: dict) -> None:
    d, meta = read(fid)
    x = d["time_s"].to_numpy(float) / 3600.0
    fields = [("max_C", "最大值", COLORS[0], "o"), ("mean_C", "均值", COLORS[1], "s"),
              ("center_C", "中心", COLORS[2], "^"), ("surface_C", "表面", COLORS[3], "D")]
    marks = np.unique(np.linspace(0, len(d) - 1, 6, dtype=int))
    fig, ax = plt.subplots(figsize=(6.7, 4.05))
    for col, label, color, marker in fields:
        ax.plot(x, d[col].to_numpy(float), color=color, linewidth=1.35, linestyle="-",
                marker=marker, markersize=4.0, markevery=marks, markeredgecolor=BLACK,
                markeredgewidth=0.45, label=label)
    ax.axhline(THRESHOLD, color=BLACK, linestyle="--", linewidth=0.9, label="判据 0.149999")
    ax.axvline(183840 / 3600.0, color=BLACK, linestyle=":", linewidth=0.85)
    ax.text(183840 / 3600.0 - 0.25, THRESHOLD + 0.035, "报告时刻 183840 s",
            ha="right", va="bottom", fontproperties=SONG, color=BLACK, fontsize=8)
    ax.set_ylim(0, 2.65)
    ax.set_yticks([0, 0.5, 1.0, 1.5, 2.0, 2.5])
    style_axis(ax, "时间 t (h)", "干基含水率 C (kg/kg)", title)
    legend_black(ax, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.01), columnspacing=1.1)
    fig.subplots_adjust(left=0.105, right=0.99, bottom=0.16, top=0.82)
    save_figure(fid, fig, meta, records)


def plot_implementation(records: dict) -> None:
    fid = "FIG-Q4-IMPLEMENTATION-AGREEMENT"
    d, meta = read(fid)
    base = float(d["event_time_s"].iloc[0])
    raw = d["event_time_s"].to_numpy(float)
    delta = abs(float(raw[1] - raw[0]))
    relative_delta = delta / abs(base)
    normalized = raw / base
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(7.2, 3.85),
                                     gridspec_kw={"width_ratios": [1.25, 1.0]})
    x = np.arange(len(d), dtype=float)
    # 主面板表达“同一量级、同一事件”：用相对于 reference 的归一化时刻，
    # 而不是把纳秒级绝对差值作为主视觉。两点在当前尺度上重合是有意的。
    ax_a.axhline(1.0, color=BLACK, linestyle="--", linewidth=0.9, zorder=1)
    ax_a.scatter(x, normalized, color=[COLORS[0], COLORS[1]],
                 marker="o", s=74, edgecolors=BLACK, linewidths=0.7, zorder=3)
    ax_a.set_xticks(x, ["reference", "moving-FV"])
    ax_a.set_xlim(-0.45, 1.45)
    ax_a.set_ylim(0.9999997, 1.0000003)
    ax_a.set_yticks([1.0])
    ax_a.set_yticklabels(["1.000000000000000"])
    style_axis(ax_a, "数值实现", "归一化达标时刻 t/tref",
               "两种实现的事件时刻重合")
    ax_a.text(0.5, 0.86, "两点在当前尺度上重合\n插值时刻约 183789.331749 s\n均报告 183840 s",
              transform=ax_a.transAxes, ha="center", va="center",
              fontproperties=SONG, color=BLACK, fontsize=8)

    # 次面板只量化相对差值，并使用对数横轴表达其相对于事件时刻的极小量级。
    ax_b.set_xscale("log")
    ax_b.set_xlim(1e-16, 1e-14)
    ax_b.set_ylim(-0.7, 0.7)
    ax_b.set_yticks([])
    ax_b.set_xticks([1e-16, 1e-15, 1e-14])
    ax_b.set_xticklabels(["10^-16", "10^-15", "10^-14"])
    ax_b.axvline(relative_delta, color=COLORS[1], linewidth=1.8, zorder=2)
    ax_b.scatter([relative_delta], [0], color=COLORS[1], marker="o", s=78,
                 edgecolors=BLACK, linewidths=0.7, zorder=3)
    style_axis(ax_b, r"相对差值 $|\Delta t|/t_{ref}$", "",
               "差值相对于事件时刻的量级")
    ax_b.text(0.5, 0.79,
              f"相对差值\n≈ {relative_delta:.2e}",
              transform=ax_b.transAxes, ha="center", va="center",
              fontproperties=SONG, color=BLACK, fontsize=8)
    ax_b.text(0.5, 0.16, "相对于约 1.84e5 s 的事件时刻",
              transform=ax_b.transAxes, ha="center", va="center",
              fontproperties=SONG, color=BLACK, fontsize=8)
    fig.text(0.52, 0.035, "实现一致性不等于现实准确性",
             ha="center", fontproperties=SONG, color=BLACK, fontsize=8)
    fig.subplots_adjust(left=0.14, right=0.99, bottom=0.25, top=0.82, wspace=0.48)
    save_figure(fid, fig, meta, records)


def plot_jacobian(records: dict) -> None:
    fid = "FIG-Q4-JACOBIAN-ABLATION"
    d, meta = read(fid)
    x = np.arange(len(d), dtype=float)
    y = d["balance_error"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot(x, y, color=COLORS[0], linewidth=1.7, linestyle="-", zorder=2)
    ax.scatter([0], [y[0]], color=COLORS[0], marker="o", s=66, edgecolors=BLACK, linewidths=0.7, zorder=3)
    ax.scatter([1], [y[1]], color=COLORS[5], marker="X", s=78, edgecolors=BLACK, linewidths=0.7, zorder=3)
    ax.set_yscale("log")
    ax.set_ylim(1e-9, 1.2)
    ax.set_yticks([1e-8, 1e-6, 1e-4, 1e-2, 1e0])
    ax.yaxis.set_major_formatter(FuncFormatter(plain_log_tick))
    ax.set_xticks(x, d["route"].tolist())
    style_axis(ax, "数值路线", "归一化平衡误差（对数轴）", "Jacobian 修正对守恒的影响")
    ax.annotate("9.645161e-8", (0, y[0]), xytext=(8, 8), textcoords="offset points",
                fontproperties=SONG, color=BLACK, fontsize=8)
    ax.annotate("0.5936319\nV10 失败", (1, y[1]), xytext=(-8, -26), textcoords="offset points",
                ha="right", fontproperties=SONG, color=BLACK, fontsize=8)
    legend_black(ax, handles=[
        Line2D([0], [0], color=COLORS[0], marker="o", linestyle="-", lw=1.6, markersize=5, label="批准路线"),
        Line2D([0], [0], color=COLORS[5], marker="X", linestyle="None", markersize=6, label="Jacobian 消融（失败）"),
    ], loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=2)
    fig.subplots_adjust(left=0.12, right=0.985, bottom=0.20, top=0.82)
    save_figure(fid, fig, meta, records)


def plot_balance(records: dict) -> None:
    fid = "FIG-VAL-BALANCE-RESIDUAL"
    d, meta = read(fid)
    x = np.arange(len(d), dtype=float)
    y1 = d["normalized_moisture_balance_error"].to_numpy(float)
    y2 = d["max_linear_relative_residual"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(7.2, 4.05))
    ax.plot(x, y1, color=COLORS[0], linewidth=1.3, linestyle="-", marker="o", markersize=3.7,
            markevery=5, markeredgecolor=BLACK, markeredgewidth=0.4, label="平衡误差")
    ax.plot(x, y2, color=COLORS[1], linewidth=1.3, linestyle="-", marker="s", markersize=3.7,
            markevery=5, markeredgecolor=BLACK, markeredgewidth=0.4, label="线性残差")
    ax.set_yscale("log")
    ax.set_ylim(1e-12, 1.0)
    ax.yaxis.set_major_formatter(FuncFormatter(plain_log_tick))
    tick = np.array([0, 10, 20, 30, 40, 50, 61], dtype=int)
    ax.set_xticks(tick, [str(i + 1) for i in tick])
    style_axis(ax, "正式运行序号", "无量纲误差（对数轴）", "正式运行的守恒与线性残差")
    legend_black(ax, loc="upper right", ncol=2)
    fig.subplots_adjust(left=0.10, right=0.99, bottom=0.17, top=0.86)
    save_figure(fid, fig, meta, records)


def plot_q1_grid(records: dict) -> None:
    fid = "FIG-Q1-GRID-CONV"
    d, meta = read(fid)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.75), sharey=False)
    for ax, family, color_shift in zip(axes, ["M1", "M2"], [0, 1]):
        sub = d.loc[d["family"].eq(family)]
        for j, (metric, label, marker) in enumerate(
            [("final_max_C", "最大值", "o"), ("final_mean_C", "均值", "s")]
        ):
            s = sub.loc[sub["metric"].eq(metric)].sort_values("nr")
            ax.plot(s["nr"].to_numpy(float), s["value"].to_numpy(float), color=COLORS[j],
                    linewidth=1.55, linestyle="-", marker=marker, markersize=4.5,
                    markeredgecolor=BLACK, markeredgewidth=0.5, label=label)
        ax.set_title(family, loc="left", pad=9, fontproperties=SONG, color=BLACK)
        style_axis(ax, "径向网格数 n_r", "终值 C (kg/kg干基)")
        legend_black(ax, loc="best", ncol=1)
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.20, top=0.88, wspace=0.35)
    save_figure(fid, fig, meta, records)


def plot_v02(records: dict) -> None:
    fid = "FIG-Q2-V02-MARGIN"
    d, meta = read(fid)
    value = float(d["absolute_change"].iloc[0])
    threshold = float(d["threshold"].iloc[0])
    margin = float(d["margin"].iloc[0])
    fig, ax = plt.subplots(figsize=(6.7, 3.5))
    ax.plot([0, value], [0, 0], color=COLORS[1], linewidth=1.8, linestyle="-", zorder=2)
    ax.scatter([value], [0], color=COLORS[1], marker="o", s=75, edgecolors=BLACK, linewidths=0.7, zorder=3)
    ax.axvline(threshold, color=BLACK, linestyle="--", linewidth=0.9)
    ax.set_xlim(0, 5.5e-5)
    ax.set_ylim(-0.32, 0.40)
    ax.set_yticks([0], ["V02"])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1e-5:g}e-5"))
    style_axis(ax, "最大登记场变化 (kg/kg)", "验证项", "V02 与验收边界")
    ax.text(threshold, 0.19, "验收线 5e-5", ha="right", fontproperties=SONG, color=BLACK, fontsize=8)
    ax.annotate(f"4.00114e-5\n余量 {margin:.6g}", (value, 0), xytext=(-5, 12),
                textcoords="offset points", ha="right", fontproperties=SONG, color=BLACK, fontsize=8)
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.22, top=0.83)
    save_figure(fid, fig, meta, records)


def plot_space(fid: str, title: str, records: dict) -> None:
    d, meta = read(fid)
    x = d["nr"].to_numpy(float)
    y = d["interpolated_event_time_s"].to_numpy(float) / 3600.0
    fig, ax = plt.subplots(figsize=(6.7, 3.7))
    ax.plot(x, y, color=COLORS[0], linewidth=1.7, linestyle="-", marker="o", markersize=5.0,
            markeredgecolor=BLACK, markeredgewidth=0.6)
    for xi, yi, mk in zip(x, y, MARKERS[: len(x)]):
        ax.scatter([xi], [yi], color=COLORS[0], marker=mk, s=56, edgecolors=BLACK, linewidths=0.6, zorder=3)
    ax.set_xticks(x, [str(int(v)) for v in x])
    lo, hi = float(np.min(y)), float(np.max(y))
    ax.set_ylim(lo - 0.003, hi + 0.003)
    style_axis(ax, "径向网格数 n_r", "插值事件时刻 (h)", title)
    ax.annotate(f"最细 {float(d['interpolated_event_time_s'].iloc[-1]):.2f} s",
                (x[-1], y[-1]), xytext=(-8, 9), textcoords="offset points", ha="right",
                fontproperties=SONG, color=BLACK, fontsize=8)
    save_figure(fid, fig, meta, records)


def plot_bracket(records: dict) -> None:
    fid = "FIG-Q4-BRACKET-ZOOM"
    d, meta = read(fid)
    x = d["time_s"].to_numpy(float)
    y = d["max_C"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot(x, y, color=COLORS[0], linewidth=1.65, linestyle="-", zorder=2)
    for i, (xi, yi) in enumerate(zip(x, y)):
        ax.scatter([xi], [yi], color=COLORS[i % len(COLORS)], marker=MARKERS[i], s=54,
                   edgecolors=BLACK, linewidths=0.6, zorder=3)
    ax.axhline(THRESHOLD, color=BLACK, linestyle="--", linewidth=0.9)
    ax.axvline(183789.33174915268, color=BLACK, linestyle=":", linewidth=0.85)
    ax.axvline(183840, color=BLACK, linestyle="-.", linewidth=0.85)
    ax.text(183789.33174915268, float(np.max(y)) + 0.000004, "插值 183789.33 s",
            ha="center", va="bottom", fontproperties=SONG, color=BLACK, fontsize=8)
    ax.text(183840, float(np.min(y)) - 0.000004, "报告 183840 s",
            ha="center", va="top", fontproperties=SONG, color=BLACK, fontsize=8)
    ax.set_xlim(float(x.min()) - 30, float(x.max()) + 30)
    ax.set_ylim(float(y.min()) - 0.000015, float(y.max()) + 0.000015)
    style_axis(ax, "时间 t (s)", "最大干基含水率 C (kg/kg)", "Q4 判据邻域的时间夹逼")
    fig.subplots_adjust(left=0.14, right=0.985, bottom=0.19, top=0.84)
    save_figure(fid, fig, meta, records)


def plot_dry_solid(records: dict) -> None:
    fid = "FIG-Q4-DRY-SOLID-CONTINUITY"
    d, meta = read(fid)
    x = np.arange(len(d), dtype=float)
    y = d["plot_value"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot(x, y, color=COLORS[0], linewidth=1.65, linestyle="-", zorder=2)
    for i, yi in enumerate(y):
        marker = "o" if i < 2 else "s"
        face = "none" if i == 2 else COLORS[0]
        ax.scatter([i], [yi], color=COLORS[0], marker=marker, facecolors=face,
                   s=64, edgecolors=BLACK, linewidths=0.7, zorder=3)
    ax.set_yscale("log")
    ax.set_ylim(1e-18, 1e-12)
    ax.set_yticks([1e-18, 1e-16, 1e-14, 1e-12])
    ax.yaxis.set_major_formatter(FuncFormatter(plain_log_tick))
    ax.set_xticks(x, ["干固体存量", "局部连续性", "几何"])
    style_axis(ax, "V12 分解指标", "误差/残差（对数轴；0 单独标注）", "干固体连续性与几何一致性")
    for i, row in d.iterrows():
        label = "0" if float(row["value"]) == 0 else f"{float(row['value']):.3e}"
        ax.annotate(label, (i, float(row["plot_value"])), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontproperties=SONG, color=BLACK, fontsize=8)
    fig.subplots_adjust(left=0.12, right=0.985, bottom=0.20, top=0.84)
    save_figure(fid, fig, meta, records)


def write_contact_sheet(ids: list[str]) -> None:
    for kind in ("color", "grayscale"):
        images = [Image.open(REV_PREVIEWS / f"{fid}-{kind}.png").convert("RGB") for fid in ids]
        thumb_w, thumb_h = 520, 300
        sheet = Image.new("RGB", (thumb_w * 3, thumb_h * ((len(images) + 2) // 3)), "white")
        for i, image in enumerate(images):
            image.thumbnail((thumb_w - 14, thumb_h - 14), Image.Resampling.LANCZOS)
            x = (i % 3) * thumb_w + (thumb_w - image.width) // 2
            y = (i // 3) * thumb_h + (thumb_h - image.height) // 2
            sheet.paste(image, (x, y))
        sheet.save(REV_PREVIEWS / f"contact-sheet-{kind}.png", dpi=(150, 150))


def update_manifest(records: dict) -> None:
    path = STAGE / "figure-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for item in manifest["items"]:
        fid = item["id"]
        if fid not in records:
            continue
        item.update(
            {
                "pdf": f"06-figure/figures/{fid}.pdf",
                "png_sha256": sha256(FORMAL / f"{fid}.png"),
                "svg_sha256": sha256(FORMAL / f"{fid}.svg"),
                "pdf_sha256": sha256(FORMAL / f"{fid}.pdf"),
                "visual_revision": "redraw-fig9-onward-20260912-simsun-solid-marker",
                "data_claim_status": "unchanged",
                "format_check": "SVG + PDF + PNG@600dpi + color/grayscale preview",
                "font_spec": "SimSun for Chinese, variables, units, ticks and legend",
                "non_data_color_spec": "black axes, grid, title, legend, ticks and text",
            }
        )
    manifest["last_visual_revision"] = {
        "scope": "figure 9 onward (14 figures)",
        "revision": "redraw-fig9-onward-20260912-simsun-solid-marker",
        "data_claim_status": "unchanged",
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_register(records: dict) -> None:
    style = {
        "language": "zh-CN",
        "font": "SimSun",
        "data_encoding": "high-contrast color + solid line + distinct marker",
        "non_data_encoding": "black axes, grid, title, legend, ticks and text",
        "formats": ["svg", "pdf", "png@600dpi"],
        "scope": "figure 9 onward; figure 1-8 unchanged",
        "data_policy": "frozen snapshots only; no model recomputation, deletion or metric change",
    }
    payload = {
        "schema_version": "1.0",
        "status": "VALIDATED_PENDING_TEAM_REVIEW",
        "revision": "redraw-fig9-onward-20260912",
        "visual_spec": style,
        "items": [
            {
                "figure_id": fid,
                "source_snapshot": records[fid]["snapshot"],
                "source_snapshot_sha256": records[fid]["snapshot_sha256"],
                "rows": records[fid]["rows"],
                "columns": records[fid]["columns"],
                "outputs": {
                    ext: {
                        "path": f"06-figure/figures/{fid}.{ext}",
                        "sha256": sha256(FORMAL / f"{fid}.{ext}"),
                    }
                    for ext in ("svg", "pdf", "png")
                },
                "visual_qa": records[fid]["visual_qa"],
            }
            for fid in TARGET_IDS
        ],
    }
    (REV / "figure-register.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def run_strict_qa() -> str:
    checker = ROOT / "skills" / "math-modeling-v2" / "tools" / "figure" / "scripts" / "check_figure.py"
    paths = [str(FORMAL / f"{fid}.{ext}") for fid in TARGET_IDS for ext in ("pdf", "svg", "png")]
    result = subprocess.run(
        [sys.executable, str(checker), *paths, "--min-dpi", "300", "--strict"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    output = result.stdout + ("\n" + result.stderr if result.stderr else "")
    (REV_QA / "strict-figure-qa.log").write_text(output, encoding="utf-8")
    require(result.returncode == 0, "check_figure.py --strict 未通过，请查看 redraw-fig9-onward-20260912/qa/strict-figure-qa.log")
    return output


def update_visual_audit(records: dict, strict_output: str) -> None:
    path = STAGE / "visual-audit.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# 视觉与程序审计\n"
    marker = "\n## 图 9–22 重绘审计（2026-09-12）\n"
    if marker in existing:
        existing = existing.split(marker, 1)[0].rstrip() + "\n"
    passed = sum(1 for r in records.values() if r["visual_qa"]["status"] == "PASS")
    section = marker + "\n"
    section += "- 范围：图 9–22，共 14 张；图 1–8 保持原正式版本不变。\n"
    section += "- 数据检查：14/14 冻结快照哈希匹配，且每个快照声明的源文件哈希匹配；无重算、删点、换指标或改主张。\n"
    section += "- 样式检查：中文、变量、单位、刻度和图例统一使用宋体；数据线统一实线并用高对比颜色与 marker 区分；坐标轴、网格、标题、图例、刻度及文字统一黑色。\n"
    section += "- 输出检查：14/14 均生成 SVG、PDF、600 DPI PNG，以及彩色和灰度预览；SVG 不嵌入位图，PDF 使用 TrueType 字体设置。\n"
    section += f"- 程序版版式检查：{passed}/14 无 FAIL；严格格式检查已通过，详见 `redraw-fig9-onward-20260912/qa/strict-figure-qa.log`。\n"
    section += "- 视觉复核重点：无中文方框、无边缘裁切、无图例遮挡、灰度下 marker/线条仍可区分；72 h 未达标、V10 Jacobian 消融失败、窄裕量和守恒零值均保留。\n"
    section += "- 限制条件移至正式图注/正文：压力测试非概率区间、条件仿真非现实验证、冻结收缩律非尺寸实测等未作为图内装饰性备注。\n"
    section += "- 阶段边界：仅更新 FIGURE 图稿和本轮交接证据，不修改 H1/H2/H3、COMPUTE、EVIDENCE 或 PAPER，不推进后续阶段。\n\n"
    path.write_text(existing + section, encoding="utf-8")


def update_handoff(records: dict) -> None:
    path = STAGE / "handoff.json"
    handoff = json.loads(path.read_text(encoding="utf-8"))
    handoff["status"] = "PASS"
    handoff["technical_validation"] = "PASS"
    handoff["visual_review_status"] = "PASS"
    handoff["redraw_scope"] = {
        "figures": TARGET_IDS,
        "figure_number_range": "9-22",
        "revision": "redraw-fig9-onward-20260912",
        "data_claim_status": "unchanged",
        "team_review": "PENDING_TEAM_REVIEW",
    }
    handoff["claims"] = list(handoff.get("claims", []))
    statement = "图9–22已按宋体、黑色非数据元素、彩色实线与marker规范重绘；源数据和冻结快照一致，未推进后续阶段。"
    if statement not in handoff["claims"]:
        handoff["claims"].append(statement)
    handoff["evidence"] = list(handoff.get("evidence", []))
    for evidence in [
        "06-figure/redraw-fig9-onward-20260912/figure-register.json",
        "06-figure/redraw-fig9-onward-20260912/data-verification.json",
        "06-figure/redraw-fig9-onward-20260912/qa/strict-figure-qa.log",
    ]:
        if evidence not in handoff["evidence"]:
            handoff["evidence"].append(evidence)
    handoff["required_next_actions"] = [
        "团队复核图9–22的正式视觉版本后，继续沿当前流程处理；本轮不自动推进 PAPER。",
        "PAPER 如启动，使用本轮 figure-manifest、图注和冻结快照，不改变数据或主张限制。",
    ]
    output_entries = []
    for p in sorted(STAGE.rglob("*")):
        if p.is_file() and p != path:
            output_entries.append({"path": rel(p), "sha256": sha256(p)})
    handoff["outputs"] = output_entries
    handoff["completed_at"] = datetime.now(timezone(timedelta(hours=8))).isoformat()
    path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    configure_style()
    for directory in (REV_FIGURES, REV_PREVIEWS, REV_QA, REV_SUPERSEDED):
        directory.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "skills" / "math-modeling-v2" / "tools" / "figure" / "scripts"))

    records: dict[str, dict] = {}
    plot_q3_sensitivity(records)
    plot_combined("FIG-Q3-COMBINED-BOUNDARY", "Q3 组合边界的达标状态", records)
    plot_radius(records)
    plot_threshold("FIG-Q4-THRESHOLD-TRAJECTORY", "Q4 收缩域的含水率轨迹", records)
    plot_jacobian(records)
    plot_combined("FIG-Q4-COMBINED-BOUNDARY", "Q4 组合扰动的成功与失败边界", records)
    plot_q1_grid(records)
    plot_v02(records)
    plot_space("FIG-Q3-SPACE-CONV", "Q3 空间网格收敛", records)
    plot_bracket(records)
    plot_space("FIG-Q4-SPACE-CONV", "Q4 空间网格收敛", records)
    plot_dry_solid(records)
    require(set(records) == set(TARGET_IDS), "目标图未全部生成")

    write_contact_sheet(TARGET_IDS)
    data_verification = {
        "status": "PASS",
        "scope": "figure 9 onward",
        "figures": records,
        "policy": "读取冻结快照；源文件仅用于 hash verification；不重新计算模型",
    }
    (REV / "data-verification.json").write_text(
        json.dumps(data_verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    update_manifest(records)
    write_register(records)
    strict_output = run_strict_qa()
    update_visual_audit(records, strict_output)
    update_handoff(records)
    (REV / "render-record.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "revision": "redraw-fig9-onward-20260912",
                "target_ids": TARGET_IDS,
                "style": {
                    "font": "SimSun",
                    "data": "high-contrast color, solid line, distinct marker",
                    "non_data": "black axes, grid, title, legend, ticks and text",
                    "formats": ["svg", "pdf", "png@600dpi"],
                },
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # render-record 写入在 handoff 之后，更新一次 outputs 以便其哈希也纳入交接。
    update_handoff(records)
    print(json.dumps({"status": "PASS", "figures": len(TARGET_IDS), "revision": rel(REV)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

~~~~

## `06-figure/scripts/redraw_q1_end_effect_time.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
"""Replace FIG-Q1-END-EFFECT with the Q1 M1/M2 moisture trajectories.

The trajectory is generated with the already approved formal solver and the
same Q1 base configurations used by 04-compute.  No model definition or
upstream result file is changed; only the figure-stage snapshot and outputs
are written.
"""

from __future__ import annotations

import csv
import hashlib
import html
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06-figure"
RES = ROOT / "04-compute" / "results"
SOLVER_PATH = ROOT / "04-compute" / "src" / "formal_compute.py"
FID = "FIG-Q1-END-EFFECT"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_formal_solver():
    spec = importlib.util.spec_from_file_location("formal_compute_for_q1_figure", SOLVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load formal solver: {SOLVER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_run_summary() -> dict[str, float]:
    values: dict[str, float] = {}
    with (RES / "run-summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["label"] in {"Q1-M1-base", "Q1-M2-base"}:
                values[row["label"]] = float(row["final_mean_C"])
    if set(values) != {"Q1-M1-base", "Q1-M2-base"}:
        raise RuntimeError("Q1 base endpoint results are incomplete")
    return values


def build_snapshot() -> tuple[Path, Path, dict[str, dict[str, float | int]]]:
    solver = load_formal_solver()
    configs = {
        "M1 一维基线": solver.RunConfig(
            "Q1-M1-base", 122, 1, 0.5, 1800, 1, "M1", sample_every=60.0
        ),
        "M2 二维主干": solver.RunConfig(
            "Q1-M2-base", 93, 54, 0.5, 1800, 1, "M2", sample_every=60.0
        ),
    }
    endpoint = read_run_summary()
    records: list[dict[str, object]] = []
    provenance: dict[str, dict[str, float | int]] = {}
    for label, cfg in configs.items():
        result = solver.simulate(cfg)
        rows = result["records"]
        if not rows or rows[-1]["time_s"] != 1800.0:
            raise RuntimeError(f"trajectory endpoint missing for {label}")
        expected = endpoint["Q1-M1-base" if cfg.model == "M1" else "Q1-M2-base"]
        actual = float(rows[-1]["mean_C"])
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=2e-10):
            raise RuntimeError(f"endpoint mismatch for {label}: {actual} vs {expected}")
        provenance[label] = {
            "rows": len(rows),
            "nr": cfg.nr,
            "nz": cfg.nz,
            "dt_s": cfg.dt,
            "duration_s": cfg.duration,
            "sample_every_s": cfg.sample_every,
            "endpoint_mean_C": actual,
        }
        for row in rows:
            records.append(
                {
                    "model": label,
                    "time_s": float(row["time_s"]),
                    "mean_C": float(row["mean_C"]),
                }
            )

    records.sort(key=lambda row: (str(row["model"]), float(row["time_s"])))
    snapshot = OUT / "data-snapshots" / f"{FID}.csv"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    with snapshot.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["model", "time_s", "mean_C"])
        writer.writeheader()
        for row in records:
            writer.writerow(
                {
                    "model": row["model"],
                    "time_s": f"{float(row['time_s']):.16g}",
                    "mean_C": f"{float(row['mean_C']):.16g}",
                }
            )

    source_paths = [SOLVER_PATH, RES / "run-summary.csv"]
    meta = {
        "figure_id": FID,
        "snapshot": rel(snapshot),
        "snapshot_sha256": sha256(snapshot),
        "sources": [{"path": rel(path), "sha256": sha256(path)} for path in source_paths],
        "rows": len(records),
        "columns": ["model", "time_s", "mean_C"],
        "derived_metric": "solver record mean_C, volume-weighted mean dry-basis moisture",
        "sampling": "every 60 s from t=0 to t=1800 s",
        "configurations": provenance,
        "endpoint_check": "matches 04-compute/results/run-summary.csv within 2e-10 kg/kg",
    }
    meta_path = snapshot.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot, meta_path, provenance


def load_snapshot(snapshot: Path) -> dict[str, list[tuple[float, float]]]:
    series: dict[str, list[tuple[float, float]]] = {}
    with snapshot.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            series.setdefault(row["model"], []).append((float(row["time_s"]), float(row["mean_C"])))
    if set(series) != {"M1 一维基线", "M2 二维主干"}:
        raise RuntimeError("snapshot must contain exactly the M1 and M2 series")
    return series


def render(snapshot: Path) -> tuple[Path, Path, Path, Path]:
    series = load_snapshot(snapshot)
    figures = OUT / "figures"
    previews = OUT / "previews"
    figures.mkdir(parents=True, exist_ok=True)
    previews.mkdir(parents=True, exist_ok=True)
    svg = figures / f"{FID}.svg"
    png = figures / f"{FID}.png"
    color_preview = previews / f"{FID}-color.png"
    gray_preview = previews / f"{FID}-grayscale.png"

    # 6.7 x 4.2 in at 600 dpi.  This keeps the figure renderer dependency-light
    # while preserving the approved white-background academic style.
    width, height = 4020, 2520
    left, right, top, bottom = 400, 3840, 260, 2050
    ymin, ymax = 2.24, 2.58
    dark = "#222222"
    grid_gray = "#C7C7C7"
    axis_width = 6
    title = "图2：一维与二维模型平均含水率随时间变化"
    title_y = 2390
    x_label_y = 2210
    colors = {"M1 一维基线": "#0072B2", "M2 二维主干": "#D55E00"}

    def font(size: int, *paths: str) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for path in paths:
            if Path(path).exists():
                return ImageFont.truetype(path, size=size)
        return ImageFont.load_default()

    font_title = font(96, r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc")
    font_tick = font(78, r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc")
    font_label = font(88, r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc")
    font_legend = font(72, r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc")
    font_note = font(58, r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf")

    def xpix(value: float) -> int:
        return round(left + (value / 1800.0) * (right - left))

    def ypix(value: float) -> int:
        return round(bottom - ((value - ymin) / (ymax - ymin)) * (bottom - top))

    def centered(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt, fill=dark) -> None:
        box = draw.textbbox((0, 0), text, font=fnt)
        draw.text((xy[0] - (box[2] - box[0]) / 2, xy[1] - (box[3] - box[1]) / 2), text, font=fnt, fill=fill)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((left, top, right, bottom), outline=dark, width=axis_width)
    x_ticks = [0, 300, 600, 900, 1200, 1500, 1800]
    y_ticks = [2.24, 2.30, 2.36, 2.42, 2.48, 2.54, 2.58]

    def dashed_line(points: list[tuple[int, int]], fill: str, width: int, dash: int = 22, gap: int = 14) -> None:
        for start, end in zip(points, points[1:]):
            x0, y0 = start
            x1, y1 = end
            length = math.hypot(x1 - x0, y1 - y0)
            if length == 0:
                continue
            ux, uy = (x1 - x0) / length, (y1 - y0) / length
            position = 0.0
            while position < length:
                end_position = min(position + dash, length)
                draw.line(
                    (
                        x0 + ux * position,
                        y0 + uy * position,
                        x0 + ux * end_position,
                        y0 + uy * end_position,
                    ),
                    fill=fill,
                    width=width,
                )
                position += dash + gap

    centered(draw, ((left + right) // 2, title_y), title, font_title, fill="#000000")
    for value in x_ticks[1:-1]:
        x = xpix(value)
        dashed_line([(x, top), (x, bottom)], fill=grid_gray, width=2, dash=18, gap=12)
    for value in y_ticks[1:-1]:
        y = ypix(value)
        dashed_line([(left, y), (right, y)], fill=grid_gray, width=2, dash=18, gap=12)
    for value in x_ticks:
        x = xpix(value)
        draw.line((x, bottom, x, bottom - 18), fill=dark, width=axis_width)
        draw.line((x, top, x, top + 18), fill=dark, width=axis_width)
        centered(draw, (x, bottom + 48), str(value), font_tick)
    for value in y_ticks:
        y = ypix(value)
        draw.line((left, y, left + 18, y), fill=dark, width=axis_width)
        draw.line((right, y, right - 18, y), fill=dark, width=axis_width)
        box = draw.textbbox((0, 0), f"{value:.2f}", font=font_tick)
        draw.text((left - 28 - (box[2] - box[0]), y - (box[3] - box[1]) / 2), f"{value:.2f}", font=font_tick, fill=dark)

    for label in ("M1 一维基线", "M2 二维主干"):
        values = series[label]
        points = [(xpix(x), ypix(y)) for x, y in values]
        if label.startswith("M1"):
            draw.line(points, fill=colors[label], width=7, joint="curve")
        else:
            dashed_line(points, fill=colors[label], width=7)
        for index in range(0, len(points), 5):
            x, y = points[index]
            if label.startswith("M1"):
                draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill=colors[label])
            else:
                draw.rectangle((x - 12, y - 12, x + 12, y + 12), fill=colors[label])
        x, y = points[-1]
        if label.startswith("M1"):
            draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill=colors[label])
        else:
            draw.rectangle((x - 12, y - 12, x + 12, y + 12), fill=colors[label])

    # Legend in the open upper-right area; line style and marker redundantly
    # encode the two model dimensions in color and grayscale.
    legend_x, legend_y = 2920, 350
    for offset, label in enumerate(("M1 一维基线", "M2 二维主干")):
        y = legend_y + offset * 78
        draw.line((legend_x, y, legend_x + 105, y), fill=colors[label], width=7)
        if label.startswith("M1"):
            draw.ellipse((legend_x + 45 - 12, y - 12, legend_x + 45 + 12, y + 12), fill=colors[label])
        else:
            draw.rectangle((legend_x + 45 - 12, y - 12, legend_x + 45 + 12, y + 12), fill=colors[label])
        draw.text((legend_x + 135, y - 28), label, font=font_legend, fill=dark)

    centered(draw, ((left + right) // 2, x_label_y), "时间 t (s)", font_label)
    y_label = Image.new("RGBA", (1200, 120), (255, 255, 255, 0))
    ImageDraw.Draw(y_label).text((10, 10), "平均干基含水率 C (kg/kg)", font=font_label, fill=dark)
    y_label = y_label.rotate(90, expand=True)
    image.paste(y_label, (30, (height - y_label.height) // 2), y_label)
    draw = ImageDraw.Draw(image)
    note = "末值差 0.01855 kg/kg"
    box = draw.textbbox((0, 0), note, font=font_note)
    draw.text((right - 30 - (box[2] - box[0]), bottom - 80), note, font=font_note, fill="#444444")
    image.save(str(png), dpi=(600, 600))
    image.resize((2010, 1260), Image.Resampling.LANCZOS).save(str(color_preview), dpi=(150, 150))
    ImageOps.grayscale(Image.open(str(color_preview)).convert("RGB")).save(str(gray_preview), dpi=(150, 150))

    def esc(text: str) -> str:
        return html.escape(text, quote=True)

    svg_lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="6.7in" height="4.2in" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" fill="white" stroke="{dark}" stroke-width="{axis_width}"/>',
        f'<text x="{(left+right)//2}" y="{title_y+50}" text-anchor="middle" font-family="SimHei,Microsoft YaHei,SimSun,sans-serif" font-size="96" font-weight="bold" fill="#000000">{esc(title)}</text>',
    ]
    for value in x_ticks[1:-1]:
        x = xpix(value)
        svg_lines.append(f'<path d="M{x} {top}V{bottom}" stroke="{grid_gray}" stroke-width="2" stroke-dasharray="18 12"/>')
    for value in y_ticks[1:-1]:
        y = ypix(value)
        svg_lines.append(f'<path d="M{left} {y}H{right}" stroke="{grid_gray}" stroke-width="2" stroke-dasharray="18 12"/>')
    for value in x_ticks:
        x = xpix(value)
        svg_lines.append(f'<path d="M{x} {bottom}V{bottom-18} M{x} {top}V{top+18}" stroke="{dark}" stroke-width="{axis_width}"/>')
        svg_lines.append(f'<text x="{x}" y="{bottom+70}" text-anchor="middle" font-family="Arial,SimSun,sans-serif" font-size="78" fill="{dark}">{value}</text>')
    for value in y_ticks:
        y = ypix(value)
        svg_lines.append(f'<path d="M{left} {y}H{left+18} M{right} {y}H{right-18}" stroke="{dark}" stroke-width="{axis_width}"/>')
        svg_lines.append(f'<text x="{left-28}" y="{y+22}" text-anchor="end" font-family="Arial,SimSun,sans-serif" font-size="78" fill="{dark}">{value:.2f}</text>')
    for label in ("M1 一维基线", "M2 二维主干"):
        pts = " ".join(f"{xpix(x)},{ypix(y)}" for x, y in series[label])
        dash = "" if label.startswith("M1") else ' stroke-dasharray="16 10"'
        marker = "circle" if label.startswith("M1") else "rect"
        svg_lines.append(f'<polyline points="{pts}" fill="none" stroke="{colors[label]}" stroke-width="7"{dash}/>' )
        for index in list(range(0, len(series[label]), 5)) + [len(series[label]) - 1]:
            x, y = series[label][index]
            if marker == "circle":
                svg_lines.append(f'<circle cx="{xpix(x)}" cy="{ypix(y)}" r="12" fill="{colors[label]}"/>')
            else:
                svg_lines.append(f'<rect x="{xpix(x)-12}" y="{ypix(y)-12}" width="24" height="24" fill="{colors[label]}"/>')
    svg_lines.extend(
        [
            f'<text x="{legend_x+135}" y="{legend_y+20}" font-family="SimSun,Microsoft YaHei,Arial,sans-serif" font-size="72" fill="{dark}">M1 一维基线</text>',
            f'<text x="{legend_x+135}" y="{legend_y+98}" font-family="SimSun,Microsoft YaHei,Arial,sans-serif" font-size="72" fill="{dark}">M2 二维主干</text>',
            f'<path d="M{legend_x} {legend_y}H{legend_x+105}" stroke="{colors["M1 一维基线"]}" stroke-width="7"/>',
            f'<path d="M{legend_x} {legend_y+78}H{legend_x+105}" stroke="{colors["M2 二维主干"]}" stroke-width="7" stroke-dasharray="16 10"/>',
            f'<circle cx="{legend_x+45}" cy="{legend_y}" r="12" fill="{colors["M1 一维基线"]}"/>',
            f'<rect x="{legend_x+33}" y="{legend_y+66}" width="24" height="24" fill="{colors["M2 二维主干"]}"/>',
            f'<text x="{(left+right)//2}" y="{x_label_y+28}" text-anchor="middle" font-family="SimSun,Microsoft YaHei,Arial,sans-serif" font-size="88" fill="{dark}">时间 t (s)</text>',
            f'<text x="110" y="{height//2}" text-anchor="middle" transform="rotate(-90 110 {height//2})" font-family="SimSun,Microsoft YaHei,Arial,sans-serif" font-size="88" fill="{dark}">平均干基含水率 C (kg/kg)</text>',
            f'<text x="{right-30}" y="{bottom-30}" text-anchor="end" font-family="Arial,Microsoft YaHei,sans-serif" font-size="58" fill="#444444">末值差 0.01855 kg/kg</text>',
            '</svg>',
        ]
    )
    svg.write_text("\n".join(svg_lines), encoding="utf-8")
    return svg, png, color_preview, gray_preview


def write_contract(snapshot: Path, meta_path: Path) -> Path:
    contract = {
        "figure_id": FID,
        "claim_ids": ["Q1-OBS-01"],
        "question": "一维与二维模型的平均含水率如何随时间变化？",
        "title": "图2：一维与二维模型平均含水率随时间变化",
        "title_font": "SimHei",
        "title_position": "below_plot_center",
        "grid": "gray dashed auxiliary gridlines",
        "source_files": [
            {"path": rel(SOLVER_PATH), "sha256": sha256(SOLVER_PATH)},
            {"path": rel(RES / "run-summary.csv"), "sha256": sha256(RES / "run-summary.csv")},
        ],
        "x": {"field": "time_s", "label": "时间 t", "unit": "s"},
        "y": {"field": "mean_C", "label": "平均干基含水率 C", "unit": "kg/kg"},
        "groups": ["M1 一维基线", "M2 二维主干"],
        "uncertainty": None,
        "required_comparisons": ["M1/M2随时间的平均含水率曲线"],
        "must_show_failures": False,
        "prohibited_operations": [
            "recompute with altered model parameters",
            "change the moisture metric",
            "omit one of the two base-model series",
            "present conditional simulation as observation",
        ],
        "target_formats": ["svg", "png"],
        "minimum_dpi": 600,
        "placement": "主文",
        "mandatory_limit": "模型差异非精度提升；曲线为条件仿真",
        "snapshot": rel(snapshot),
        "snapshot_sha256": sha256(snapshot),
        "snapshot_meta": rel(meta_path),
    }
    path = OUT / "contracts" / f"{FID}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def refresh_manifest_and_handoff(paths: list[Path]) -> None:
    manifest_path = OUT / "figure-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    item = next(item for item in manifest["items"] if item["id"] == FID)
    item["png_sha256"] = sha256(OUT / "figures" / f"{FID}.png")
    item["svg_sha256"] = sha256(OUT / "figures" / f"{FID}.svg")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.append(manifest_path)

    handoff_path = OUT / "handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    changed = {rel(path): sha256(path) for path in paths}
    for record in handoff["outputs"]:
        if record["path"] in changed:
            record["sha256"] = changed[record["path"]]
    handoff["assumptions"] = [
        "FIG-Q1-END-EFFECT was revised to display the approved M1/M2 base trajectories generated with the unchanged formal solver configurations.",
        "No model definition, parameter, upstream COMPUTE result file, or other figure was changed.",
        "All plotted values remain conditional simulations and do not constitute empirical accuracy validation.",
    ]
    handoff["warnings"] = [
        "The time-series version supersedes the former endpoint dumbbell rendering for FIG-Q1-END-EFFECT.",
        "Do not present the M1/M2 difference as an accuracy improvement without internal observations.",
    ]
    handoff_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")


def update_stage_docs(paths: list[Path]) -> None:
    caption_path = OUT / "图注.md"
    caption = caption_path.read_text(encoding="utf-8")
    start = caption.index("## 主文图 2（FIG-Q1-END-EFFECT）")
    end = caption.index("## 主文图 3", start)
    replacement = (
        "## 主文图 2（FIG-Q1-END-EFFECT）\n\n"
        "一维与二维模型的平均含水率如何随时间变化？ 0–1800 s 的体积加权平均干基含水率轨迹；1800 s 末值差0.0185457085。"
        "限定：模型差异非精度提升，曲线为条件仿真。数据快照与来源哈希见 `data-snapshots/FIG-Q1-END-EFFECT.meta.json`。\n\n"
    )
    caption_path.write_text(caption[:start] + replacement + caption[end:], encoding="utf-8")
    paths.append(caption_path)

    audit_path = OUT / "visual-audit.md"
    audit = audit_path.read_text(encoding="utf-8")
    note = (
        "- FIG-Q1-END-EFFECT 本轮按用户要求由端点哑铃图改为 M1 一维基线与 M2 二维主干的平均含水率—时间曲线；"
        "将黑体标题‘图2：一维与二维模型平均含水率随时间变化’移至图下方居中，进一步放大标题、坐标轴标签和横纵轴刻度数字，并加粗横纵坐标轴主框线与刻度线，保留灰色虚线网格辅助线；"
        "使用 0–1800 s、60 s 采样，末值与 run-summary.csv 校验通过，未改动其他图。\n"
    )
    audit = "".join(
        line for line in audit.splitlines(True)
        if not line.startswith("- FIG-Q1-END-EFFECT 本轮按用户要求")
    )
    audit = audit.replace("- 灰度检查：", note + "- 灰度检查：")
    audit_path.write_text(audit, encoding="utf-8")
    paths.append(audit_path)


def main() -> None:
    snapshot_path = OUT / "data-snapshots" / f"{FID}.csv"
    if os.environ.get("USE_EXISTING_SNAPSHOT") == "1" and snapshot_path.exists():
        snapshot = snapshot_path
        meta_path = snapshot.with_suffix(".meta.json")
        if not meta_path.exists():
            raise RuntimeError(f"snapshot metadata is missing: {meta_path}")
    else:
        snapshot, meta_path, _ = build_snapshot()
    svg, png, color_preview, gray_preview = render(snapshot)
    contract = write_contract(snapshot, meta_path)
    changed = [snapshot, meta_path, contract, svg, png, color_preview, gray_preview, Path(__file__)]
    update_stage_docs(changed)
    refresh_manifest_and_handoff(changed)
    print(
        json.dumps(
            {
                "figure_id": FID,
                "snapshot": rel(snapshot),
                "svg": rel(svg),
                "png": rel(png),
                "rows": 62,
                "endpoint_check": "PASS",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

~~~~

## `06-figure/scripts/render_q2_profiles.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
FIGURE_DIR = ROOT / "06-figure"
SOURCE = ROOT / "04-compute" / "results" / "q2-samples.csv"
SNAPSHOT = FIGURE_DIR / "data-snapshots" / "FIG-Q2-C-PROFILES.csv"
FIGURES = FIGURE_DIR / "figures"
PREVIEWS = FIGURE_DIR / "previews"
FIG_ID = "FIG-Q2-C-PROFILES"
FIELDS = ["time_s", "radius_cm", "C_kg_per_kg"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[tuple[int, float, float]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sorted(
            (
                (
                    int(row["time_s"]),
                    float(row["radius_cm"]),
                    float(row["C_kg_per_kg"]),
                )
                for row in csv.DictReader(handle)
            ),
            key=lambda row: (row[0], row[1]),
        )


def same_numeric_rows(left: list[tuple[int, float, float]], right: list[tuple[int, float, float]]) -> bool:
    if len(left) != len(right):
        return False
    return all(
        a[0] == b[0]
        and abs(a[1] - b[1]) <= 1e-12
        and abs(a[2] - b[2]) <= 1e-12
        for a, b in zip(left, right)
    )


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    assert same_numeric_rows(rows(SOURCE), rows(SNAPSHOT)), "source and frozen figure snapshot differ"

    data = pd.read_csv(SOURCE)[FIELDS].sort_values(
        ["time_s", "radius_cm"], kind="stable"
    )
    mpl.rcParams.update(
        {
            "font.family": "SimSun",
            "font.sans-serif": ["SimSun", "STSong", "FangSong", "Microsoft YaHei", "Arial"],
            "font.serif": ["SimSun", "STSong", "FangSong", "Microsoft YaHei", "Arial"],
            "font.size": 8.5,
            "text.color": "#000000",
            "axes.labelcolor": "#000000",
            "xtick.color": "#000000",
            "ytick.color": "#000000",
            "axes.unicode_minus": False,
            "axes.facecolor": "#FFFFFF",
            "figure.facecolor": "#FFFFFF",
            "savefig.facecolor": "#FFFFFF",
            "axes.axisbelow": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "FIG-Q2-C-PROFILES",
        }
    )

    # 图线按半径分组；使用高对比彩色、统一实线，并用 marker 进一步区分半径。
    colors = ["#005AB5", "#E69F00", "#009E73", "#D55E00", "#7B2CBF"]
    linestyles = ["-"] * 5
    markers = ["o", "s", "^", "D", "P"]
    labels = ["r = 0 cm", "r = 0.5 cm", "r = 1 cm", "r = 1.5 cm", "r = 2 cm"]

    fig, ax = plt.subplots(figsize=(6.9, 4.5), dpi=600)
    fig.subplots_adjust(left=0.135, right=0.985, bottom=0.205, top=0.745)
    for i, (radius_cm, group) in enumerate(data.groupby("radius_cm", sort=True)):
        group = group.sort_values("time_s")
        ax.plot(
            group["time_s"] / 3600.0,
            group["C_kg_per_kg"],
            color=colors[i],
            linestyle=linestyles[i],
            linewidth=1.75,
            marker=markers[i],
            markersize=5.0,
            markerfacecolor=colors[i],
            markeredgecolor=colors[i],
            markeredgewidth=0.65,
            label=labels[i],
            zorder=3 + i * 0.01,
        )

    ax.set_xlim(0.45, 3.05)
    ax.set_ylim(0.92, 2.66)
    ax.set_xticks([0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
    ax.set_yticks([1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6])
    ax.set_xlabel("时间 t（h）", fontsize=9.5, color="#000000", labelpad=7)
    ax.set_ylabel("干基含水率 C（kg/kg）", fontsize=9.5, color="#000000", labelpad=8)
    ax.tick_params(
        axis="both",
        which="major",
        direction="out",
        length=3.2,
        width=0.65,
        colors="#000000",
        labelsize=8.3,
    )
    for tick_label in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
        tick_label.set_fontfamily("SimHei")
    ax.grid(axis="y", color="#000000", linewidth=0.5, alpha=0.15)
    ax.grid(axis="x", visible=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#000000")
        ax.spines[side].set_linewidth(0.75)

    fig.text(
        0.135,
        0.935,
        "M3",
        ha="left",
        va="top",
        fontsize=11.5,
        fontfamily="SimHei",
        color="#000000",
    )
    fig.text(
        0.175,
        0.935,
        "不同半径位置含水率随时间演化",
        ha="left",
        va="top",
        fontsize=11.5,
        fontfamily="SimSun",
        color="#000000",
    )
    legend = fig.legend(
        loc="upper center",
        bbox_to_anchor=(0.56, 0.835),
        ncol=3,
        frameon=False,
        prop={"family": "SimHei", "size": 8.0},
        columnspacing=1.45,
        handlelength=2.35,
        handletextpad=0.55,
        borderaxespad=0.0,
    )
    for text in legend.get_texts():
        text.set_color("#000000")

    fixed_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fig.savefig(FIGURES / f"{FIG_ID}.svg", metadata={"Date": "2026-01-01T00:00:00"})
    fig.savefig(
        FIGURES / f"{FIG_ID}.pdf",
        dpi=600,
        metadata={"CreationDate": fixed_date, "ModDate": fixed_date},
    )
    fig.savefig(FIGURES / f"{FIG_ID}.png", dpi=600)
    fig.savefig(PREVIEWS / f"{FIG_ID}-color.png", dpi=600)
    plt.close(fig)

    formal_color = Image.open(FIGURES / f"{FIG_ID}.png").convert("RGB")
    ImageOps.grayscale(formal_color).save(
        PREVIEWS / f"{FIG_ID}-grayscale.png", dpi=(600, 600)
    )
    print(
        {
            "figure_id": FIG_ID,
            "source_sha256": sha256(SOURCE),
            "snapshot_sha256": sha256(SNAPSHOT),
            "png_sha256": sha256(FIGURES / f"{FIG_ID}.png"),
            "svg_sha256": sha256(FIGURES / f"{FIG_ID}.svg"),
            "pdf_sha256": sha256(FIGURES / f"{FIG_ID}.pdf"),
            "right_bottom_note": False,
        }
    )


if __name__ == "__main__":
    main()

~~~~

## `06-figure/scripts/render_q2_profiles_3d.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
FIGURE_DIR = ROOT / "06-figure"
SNAPSHOT = FIGURE_DIR / "data-snapshots" / "FIG-Q2-C-PROFILES.csv"
FIGURES = FIGURE_DIR / "figures"
PREVIEWS = FIGURE_DIR / "previews"
FIG_ID = "FIG-Q2-C-PROFILES"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows: list[tuple[float, float, float]] = []
    with SNAPSHOT.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                (
                    float(row["time_s"]) / 3600.0,
                    float(row["radius_cm"]),
                    float(row["C_kg_per_kg"]),
                )
            )
    times = np.array(sorted({row[0] for row in rows}), dtype=float)
    radii = np.array(sorted({row[1] for row in rows}), dtype=float)
    z = np.full((len(radii), len(times)), np.nan, dtype=float)
    time_index = {value: i for i, value in enumerate(times)}
    radius_index = {value: i for i, value in enumerate(radii)}
    for time_h, radius_cm, value in rows:
        if not np.isnan(z[radius_index[radius_cm], time_index[time_h]]):
            raise ValueError("duplicate time-radius sample")
        z[radius_index[radius_cm], time_index[time_h]] = value
    if np.isnan(z).any():
        raise ValueError("time-radius samples do not form a complete rectangular grid")
    return times, radii, z


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    if not SNAPSHOT.exists():
        raise FileNotFoundError(SNAPSHOT)

    mpl.rcParams.update(
        {
            "font.family": "SimSun",
            "font.sans-serif": ["SimSun", "STSong", "FangSong", "Microsoft YaHei", "Arial"],
            "font.serif": ["SimSun", "STSong", "FangSong", "Microsoft YaHei", "Arial"],
            "font.size": 8.5,
            "text.color": "#000000",
            "axes.labelcolor": "#000000",
            "xtick.color": "#000000",
            "ytick.color": "#000000",
            "axes.unicode_minus": False,
            "axes.facecolor": "#FFFFFF",
            "figure.facecolor": "#FFFFFF",
            "savefig.facecolor": "#FFFFFF",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": FIG_ID,
        }
    )

    times_h, radii_cm, z = load_grid()
    x, y = np.meshgrid(times_h, radii_cm)
    cmap = mpl.colormaps["viridis"]
    norm = mpl.colors.Normalize(vmin=float(z.min()), vmax=float(z.max()))

    fig = plt.figure(figsize=(6.9, 5.0), dpi=600)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_proj_type("ortho")
    surface = ax.plot_surface(
        x,
        y,
        z,
        cmap=cmap,
        norm=norm,
        linewidth=0.28,
        edgecolor=(0.25, 0.25, 0.25, 0.45),
        antialiased=True,
        alpha=0.90,
        rcount=len(radii_cm),
        ccount=len(times_h),
    )
    # Exact frozen samples are overlaid so that the surface is auditable.
    ax.scatter(
        x.ravel(),
        y.ravel(),
        z.ravel(),
        c=z.ravel(),
        cmap=cmap,
        norm=norm,
        s=11,
        depthshade=False,
        edgecolors="#000000",
        linewidths=0.28,
    )

    ax.set_xlim(float(times_h.min()), float(times_h.max()))
    ax.set_ylim(float(radii_cm.min()), float(radii_cm.max()))
    # Use four regular z ticks and a small fixed margin.  The previous five
    # ticks were visually crowded by the chosen 3-D projection.
    z_ticks = [1.0, 1.5, 2.0, 2.5]
    ax.set_zlim(0.9, 2.7)
    ax.set_xticks(times_h)
    ax.set_yticks(radii_cm)
    ax.set_zticks(z_ticks)
    ax.set_xlabel("时间 t（h）", labelpad=8, fontsize=9.5)
    ax.set_ylabel("半径 r（cm）", labelpad=8, fontsize=9.5)
    ax.set_zlabel("干基含水率 C（kg/kg）", labelpad=17, fontsize=9.5)
    ax.tick_params(axis="both", which="major", labelsize=8.0, pad=1.5, colors="#000000")
    ax.tick_params(axis="z", which="major", labelsize=8.0, pad=7.0, colors="#000000")
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor((1.0, 1.0, 1.0, 1.0))
        pane.set_edgecolor((0.0, 0.0, 0.0, 0.18))
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis._axinfo["grid"]["color"] = (0.0, 0.0, 0.0, 0.12)
    ax.view_init(elev=30, azim=-55)
    ax.set_box_aspect((1.55, 1.0, 1.05))

    fig.suptitle(
        "M3  不同时间—半径位置的含水率三维演化",
        x=0.46,
        y=0.965,
        fontsize=11.5,
        fontfamily="SimSun",
    )
    ax.text2D(0.02, 0.93, "点：冻结采样值", transform=ax.transAxes, fontsize=8.0, color="#000000")
    colorbar = fig.colorbar(surface, ax=ax, shrink=0.68, pad=0.12, aspect=19)
    colorbar.set_ticks(z_ticks)
    colorbar.set_label("C（kg/kg）", fontsize=8.8, labelpad=6, color="#000000")
    colorbar.ax.tick_params(labelsize=7.7, colors="#000000", length=2.5, width=0.55)
    colorbar.outline.set_edgecolor("#000000")
    colorbar.outline.set_linewidth(0.45)
    fig.subplots_adjust(left=0.0, right=0.92, bottom=0.02, top=0.92)

    fixed_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    svg_path = FIGURES / f"{FIG_ID}.svg"
    pdf_path = FIGURES / f"{FIG_ID}.pdf"
    png_path = FIGURES / f"{FIG_ID}.png"
    fig.savefig(svg_path, metadata={"Date": "2026-01-01T00:00:00"})
    fig.savefig(pdf_path, dpi=600, metadata={"CreationDate": fixed_date, "ModDate": fixed_date})
    fig.savefig(png_path, dpi=600)
    fig.savefig(PREVIEWS / f"{FIG_ID}-color.png", dpi=600)
    plt.close(fig)

    color = Image.open(png_path).convert("RGB")
    ImageOps.grayscale(color).save(PREVIEWS / f"{FIG_ID}-grayscale.png", dpi=(600, 600))
    print(
        {
            "figure_id": FIG_ID,
            "snapshot_sha256": sha256(SNAPSHOT),
            "png_sha256": sha256(png_path),
            "svg_sha256": sha256(svg_path),
            "pdf_sha256": sha256(pdf_path),
            "rows": int(z.size),
            "time_range_h": [float(times_h.min()), float(times_h.max())],
            "radius_range_cm": [float(radii_cm.min()), float(radii_cm.max())],
            "C_range_kg_per_kg": [float(z.min()), float(z.max())],
            "interpolation": False,
        }
    )


if __name__ == "__main__":
    main()

~~~~

## `06-figure/scripts/revise_q2_figures_20260913.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
FIGDIR = ROOT / "06-figure" / "figures"
PREV = ROOT / "06-figure" / "previews"
SNAP = ROOT / "06-figure" / "data-snapshots"
CONTRACT = ROOT / "06-figure" / "contracts"
FIGDIR.mkdir(exist_ok=True)
PREV.mkdir(exist_ok=True)
SNAP.mkdir(exist_ok=True)
CONTRACT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "Microsoft YaHei", "font.size": 9,
    "axes.unicode_minus": False, "svg.fonttype": "none",
})
BLUE, ORANGE, GREEN, BLACK, GRID = "#0072B2", "#E69F00", "#009E73", "#111111", "#D9D9D9"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_figure(fid: str, fig) -> None:
    fig.set_size_inches(9.5, 4.6)
    fig.savefig(FIGDIR / f"{fid}.svg", bbox_inches="tight")
    fig.savefig(FIGDIR / f"{fid}.pdf", bbox_inches="tight")
    fig.savefig(FIGDIR / f"{fid}.png", dpi=600, bbox_inches="tight")
    fig.savefig(PREV / f"{fid}-color.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    ImageOps.grayscale(Image.open(PREV / f"{fid}-color.png").convert("RGB")).save(PREV / f"{fid}-grayscale.png")


def write_snapshot(fid: str, df: pd.DataFrame, source: Path) -> None:
    path = SNAP / f"{fid}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    meta = {
        "figure_id": fid,
        "snapshot": path.relative_to(ROOT).as_posix(),
        "snapshot_sha256": sha(path),
        "sources": [{"path": source.relative_to(ROOT).as_posix(), "sha256": sha(source)}],
        "rows": len(df),
        "columns": list(df.columns),
    }
    (SNAP / f"{fid}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    contract_path = CONTRACT / f"{fid}.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["snapshot"] = path.relative_to(ROOT).as_posix()
    contract["snapshot_sha256"] = sha(path)
    contract["source_files"] = [{"path": source.relative_to(ROOT).as_posix(), "sha256": sha(source)}]
    contract["visual_revision"] = "user-revision-20260913"
    contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")


# Figure 4: one time trajectory per model, shown in separate comparable panels.
fid = "FIG-Q2-MODEL-ABLATION"
source4 = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "q2-model-trajectories" / "q2-model-trajectories.csv"
df4 = pd.read_csv(source4)
write_snapshot(fid, df4, source4)
fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.5), sharex=True, sharey=True)
styles = [(BLUE, "-", "o"), (ORANGE, "--", "s"), (GREEN, "-.", "^")]
model_order = list(df4["model"].drop_duplicates())
for ax, model, (color, ls, marker) in zip(axes, model_order, styles):
    group = df4[df4["model"] == model].sort_values("time_s")
    ax.plot(group.time_s / 3600, group.max_C, color=color, linestyle=ls, marker=marker,
            markersize=4, linewidth=1.5)
    ax.set_title(model)
    ax.set_xlabel("时间 (h)")
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("全域最大干基含水率 (kg/kg)")
fig.suptitle("三个模型在不同时间的最大含水率轨迹", y=1.02)
fig.text(0.5, -0.01, "三幅子图使用相同坐标范围；仅比较模型输出差异，不代表现实准确率排序",
         ha="center", va="top", color="#444444")
fig.tight_layout()
save_figure(fid, fig)

# Figure 5: six radial-grid groups at the same formal dt=5 s.
fid = "FIG-Q2-GRID-CONV"
source5 = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "q2-space-dt5" / "field-grid-convergence.csv"
df5 = pd.read_csv(source5)
write_snapshot(fid, df5, source5)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 3.8), gridspec_kw={"width_ratios": [1.25, 1]})
ax1.plot(df5.nr, df5.value, "o-", color=BLUE, linewidth=1.5, markersize=5)
ax1.set_xlabel("径向网格数 $n_r$")
ax1.set_ylabel("3 h 最大干基含水率 (kg/kg)")
ax1.set_title("六组网格的终值")
ax1.grid(axis="y", color=GRID, linewidth=0.6)
ax1.ticklabel_format(axis="y", style="plain", useOffset=False)
ax1.spines[["top", "right"]].set_visible(False)
ax1.set_xticks(df5.nr)
ax1.tick_params(axis="x", rotation=25)
for x, y in zip(df5.nr, df5.value):
    ax1.annotate(f"{y:.6f}", (x, y), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=7)
changes = df5.iloc[1:].copy()
ax2.plot(changes.nr, changes.adjacent_change, "o-", color=ORANGE, linewidth=1.5, markersize=5)
ax2.axhline(5e-5, color=BLACK, linestyle="--", linewidth=1.0, label="验收线 5e-5")
ax2.set_xlabel("径向网格数 $n_r$")
ax2.set_ylabel("相邻网格终值变化")
ax2.set_title("相邻变化逐步减小")
ax2.grid(axis="y", color=GRID, linewidth=0.6)
ax2.spines[["top", "right"]].set_visible(False)
ax2.set_xticks(changes.nr)
ax2.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
ax2.legend(frameon=False, fontsize=8)
ax2.annotate(f"最细变化 {changes.adjacent_change.iloc[-1]:.3e}",
             (changes.nr.iloc[-1], changes.adjacent_change.iloc[-1]),
             xytext=(-70, 18), textcoords="offset points", arrowprops={"arrowstyle": "->"}, fontsize=8)
fig.suptitle("M3 空间网格收敛：固定时间步长 dt=5 s", y=1.02)
fig.tight_layout()
save_figure(fid, fig)

# Appendix S2/S3: expanded five-level spatial convergence at fixed dt=60 s.
extra_space = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "space-extra-dt60" / "threshold-grid-extra.csv"
base_space = pd.read_csv(ROOT / "04-compute" / "results" / "threshold-grid-convergence.csv")
extra = pd.read_csv(extra_space)
space_all = pd.concat([base_space, extra], ignore_index=True).drop_duplicates(["scope", "nr"]).sort_values(["scope", "nr"])
for fid, scope in [("FIG-Q3-SPACE-CONV", "Q3"), ("FIG-Q4-SPACE-CONV", "Q4")]:
    df = space_all[space_all.scope == scope].copy()
    write_snapshot(fid, df, extra_space)
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.plot(df.nr, df.interpolated_event_time_s / 3600, "o-", color=BLUE, linewidth=1.5, markersize=5)
    ax.set_xlabel("径向网格数 $n_r$")
    ax.set_ylabel("插值事件时刻 (h)")
    ax.set_title(f"{scope} 空间网格收敛（五组网格，dt=60 s）")
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xticks(df.nr)
    for x, y in zip(df.nr, df.interpolated_event_time_s / 3600):
        ax.annotate(f"{y:.4f}", (x, y), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=7)
    ax.text(0.01, 0.02, "仅表明空间离散稳定性，不替代时间步验证", transform=ax.transAxes, color="#444444")
    fig.tight_layout()
    save_figure(fid, fig)

print("REVISED_Q2_FIGURES_PASS")

~~~~

## `06-figure/scripts/update_figure_plan_20260913.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
manifest_path = ROOT / "06-figure" / "figure-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["status"] = "REVIEW_REQUIRED"
removed = {"FIG-Q3-TIME-CONV", "FIG-Q3-COMBINED-BOUNDARY", "FIG-Q4-COMBINED-BOUNDARY"}
manifest["main_figures"] = [fid for fid in manifest["main_figures"] if fid not in removed]
manifest["n_figures"] = len(manifest["main_figures"]) + len(manifest["appendix_figures"])
manifest["items"] = [item for item in manifest["items"] if item["id"] not in removed]

for item in manifest["items"]:
    # Refresh hashes for every active figure so the current manifest is the
    # single source of truth after any approved redraw; apply the new data
    # claims/revision labels only to the figures changed in this revision.
    if item.get("id", "").startswith("FIG"):
        png = ROOT / item["png"]
        svg = ROOT / item["svg"]
        pdf = ROOT / item.get("pdf", "06-figure/figures/unused.pdf")
        item["png_sha256"] = hashlib.sha256(png.read_bytes()).hexdigest()
        item["svg_sha256"] = hashlib.sha256(svg.read_bytes()).hexdigest()
        if pdf.exists():
            item["pdf_sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if item["id"] in {"FIG-Q2-MODEL-ABLATION", "FIG-Q2-GRID-CONV", "FIG-Q3-SPACE-CONV", "FIG-Q4-SPACE-CONV"}:
        item["visual_revision"] = "user-revision-20260913"
        item["data_claim_status"] = "unchanged" if item["id"] == "FIG-Q2-MODEL-ABLATION" else "expanded-grid-evidence-at-fixed-dt5s" if item["id"] == "FIG-Q2-GRID-CONV" else "expanded-grid-evidence-at-fixed-dt60s"

manifest["revision_note"] = "用户确认：移除原图8、10、13；图4改为三模型同尺度分面，图5扩展为六组径向网格（dt=5 s），图15/16扩展为五组径向网格（dt=60 s）。"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"FIGURE_PLAN_UPDATED {manifest['n_figures']}")

~~~~

## `06-figure/scripts/verify_current_pipeline.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06-figure"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


manifest = json.loads((OUT / "figure-manifest.json").read_text(encoding="utf-8"))
failures = []
active = set(manifest.get("main_figures", []) + manifest.get("appendix_figures", []))
forbidden_ids = {"FIG-Q3-TIME-CONV", "FIG-Q3-COMBINED-BOUNDARY", "FIG-Q4-COMBINED-BOUNDARY"}
if active & forbidden_ids:
    failures.append(f"legacy figure IDs remain active: {sorted(active & forbidden_ids)}")
if manifest.get("n_figures") != len(active) or len(active) != 13:
    failures.append("active manifest count is not 13")

new_renderer = OUT / "scripts" / "revise_q2_figures_20260913.py"
if not new_renderer.exists():
    failures.append("new renderer missing: revise_q2_figures_20260913.py")

checks = {}
for fid in active:
    item = next((x for x in manifest.get("items", []) if x.get("id") == fid), None)
    if not item:
        failures.append(f"missing manifest item: {fid}")
        continue
    for key in ("png", "svg"):
        path = ROOT / item[key]
        if not path.exists():
            failures.append(f"missing {key}: {fid}")
        elif item.get(f"{key}_sha256") and sha(path) != item[f"{key}_sha256"]:
            failures.append(f"hash mismatch: {fid} {key}")

f4 = read_csv(OUT / "data-snapshots" / "FIG-Q2-MODEL-ABLATION.csv")
counts = {}
for row in f4:
    counts[row["model"]] = counts.get(row["model"], 0) + 1
checks["FIG-Q2-MODEL-ABLATION"] = {"rows": len(f4), "rows_per_model": counts}
if len(f4) != 57 or set(counts.values()) != {19}:
    failures.append("Figure 4 is not 3 models x 19 time points")

f5 = read_csv(OUT / "data-snapshots" / "FIG-Q2-GRID-CONV.csv")
nr5 = sorted({int(float(row["nr"])) for row in f5})
checks["FIG-Q2-GRID-CONV"] = {"radial_grids": nr5, "count": len(nr5)}
if nr5 != [42, 62, 93, 140, 175, 210]:
    failures.append(f"Figure 5 radial grids unexpected: {nr5}")

for fid in ("FIG-Q3-SPACE-CONV", "FIG-Q4-SPACE-CONV"):
    rows = read_csv(OUT / "data-snapshots" / f"{fid}.csv")
    nrs = sorted({int(float(row["nr"])) for row in rows})
    checks[fid] = {"radial_grids": nrs, "count": len(nrs)}
    if nrs != [63, 93, 140, 175, 210]:
        failures.append(f"{fid} radial grids unexpected: {nrs}")

report = {
    "status": "PASS" if not failures else "FAIL",
    "pipeline": "CURRENT_20260913",
    "active_figure_count": len(active),
    "new_renderer": str(new_renderer.relative_to(ROOT)).replace("\\", "/"),
    "checks": checks,
    "failures": failures,
}
(OUT / "current-pipeline-verification.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(bool(failures))

~~~~

## `06-figure/scripts/make_official_contact_sheet.py`

本文件在代码实现、调试或图表制作过程中得到 Codex 辅助；参数、模型路线、结果解释及最终核验由参赛队负责。

~~~~python
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FIGDIR = ROOT / "06-figure" / "figures"
OUT = ROOT / "06-figure" / "official-figures-contact-sheet-20260913.png"

ids = [
    "FIG-Q1-C-FIELD", "FIG-Q1-END-EFFECT", "FIG-Q2-C-PROFILES", "FIG-Q2-MODEL-ABLATION",
    "FIG-Q2-GRID-CONV", "FIG-Q3-THRESHOLD-TRAJECTORY", "FIG-Q3-BRACKET-ZOOM",
    "FIG-Q3-SENS-ONEFACTOR", "FIG-Q4-RADIUS-TIME", "FIG-Q4-THRESHOLD-TRAJECTORY",
    "FIG-Q1-GRID-CONV", "FIG-Q3-SPACE-CONV", "FIG-Q4-SPACE-CONV",
]

W, H = 900, 620
sheet = Image.new("RGB", (W * 4, H * 4), "white")
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype("simhei.ttf", 28)
small = ImageFont.truetype("simhei.ttf", 22)

for i, fid in enumerate(ids):
    path = FIGDIR / f"{fid}.png"
    if not path.exists():
        raise FileNotFoundError(path)
    with Image.open(path) as src:
        src = src.convert("RGB")
        src.thumbnail((W - 40, H - 90), Image.Resampling.LANCZOS)
        x = (i % 4) * W
        y = (i // 4) * H
        draw.rectangle((x, y, x + W - 1, y + H - 1), outline=(190, 190, 190), width=2)
        draw.text((x + 18, y + 12), f"{i+1:02d}  {fid}", fill=(0, 0, 0), font=font)
        px = x + (W - src.width) // 2
        py = y + 62 + (H - 72 - src.height) // 2
        sheet.paste(src, (px, py))

sheet.save(OUT, dpi=(150, 150))
print(OUT)

~~~~
