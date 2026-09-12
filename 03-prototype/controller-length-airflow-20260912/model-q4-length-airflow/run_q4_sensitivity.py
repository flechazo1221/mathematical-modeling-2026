"""Independent Q4 candidate prototype: axial-length and external-airflow sensitivity.

This file deliberately writes only below the task-specific directory.  It is a
standalone, conservative extension of the frozen Q4 moisture solver:

* R(t) is the approved attachment-2 PCHIP radius;
* the half-cylinder is represented in (r,z), with exposed side and one end;
* rho_d is advanced by the affine dry-solid continuity map, not by an
  unsupported algebraic rho(C)/(1+C) closure;
* q_w = rho_d*C is the water inventory;
* the moisture equation is assembled in material/reference-cell storage and
  current physical flux conductances;
* length, airflow and radiation are separate scenario factors.

The axial law in scenario C is an explicit adversarial envelope, not an
observation: L/L0=(R/R0)^2.  Airflow correlation values are relative scalings
of the frozen effective hm because the approved boundary potential is
Cs-Cinf, not a directly measured vapor-concentration difference.
"""

from __future__ import annotations

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


TASK_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_DIR = PROJECT_ROOT / "input" / "A题" / "附件"
MODEL_DIR = TASK_DIR / "model-q4-length-airflow"
RESULTS_DIR = TASK_DIR / "results"
LOG_DIR = TASK_DIR / "logs"

R0 = 0.02
L0 = 0.25
RHO_D0 = 820.0
C0 = 2.55
T0_K = 301.15
HM0 = 8.0e-7
H0 = 25.0
THRESHOLD = 0.15 - 1.0e-6
DT_BASE = 60.0
# The controlled scenario comparison uses the same 10x20 Q4 one-factor
# sensitivity grid already used by the current compute route.  One separate
# 210x32/60 s run is retained as a resolution control; it is never mixed into
# the scenario ranking.
NR_BASE = 10
NZ_BASE = 20
NR_FINE = 210
NZ_FINE = 32
RADIAL_STRATEGY = "two-sided-local"
Z_STRETCH = 1.7
SEED = 20260912

NU_AIR = 1.70e-5       # m2/s, conditional air-property value
D_VAPOR = 2.60e-5      # m2/s, conditional vapor diffusivity value
SC_AIR = NU_AIR / D_VAPOR
U_REF = 1.0            # m/s, only a scaling reference for the effective hm
SIGMA = 5.670374419e-8
EMISSIVITY = 0.90


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_xlsx(name: str) -> np.ndarray:
    path = INPUT_DIR / name
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    return np.asarray(rows, dtype=float)


ENV = load_xlsx("附件1.xlsx")
RADIUS_DATA = load_xlsx("附件2.xlsx")
if ENV.shape != (241, 3):
    raise RuntimeError(f"附件1 shape audit failed: {ENV.shape}")
if RADIUS_DATA.shape != (145, 2):
    raise RuntimeError(f"附件2 shape audit failed: {RADIUS_DATA.shape}")
if not (ENV[0, 0] == 0 and ENV[-1, 0] == 14400):
    raise RuntimeError("附件1 endpoints failed")
if not (RADIUS_DATA[0, 0] == 0 and RADIUS_DATA[-1, 0] == 259200):
    raise RuntimeError("附件2 endpoints failed")
if not np.all(np.diff(RADIUS_DATA[:, 1]) <= 1e-12):
    raise RuntimeError("附件2 radius is not monotone non-increasing")

R_TIME = RADIUS_DATA[:, 0]
R_VALUES = RADIUS_DATA[:, 1] / 100.0


def pchip_slopes(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    h = np.diff(x)
    delta = np.diff(y) / h
    n = len(x)
    d = np.zeros(n)
    for k in range(1, n - 1):
        if delta[k - 1] * delta[k] > 0:
            w1 = 2 * h[k] + h[k - 1]
            w2 = h[k] + 2 * h[k - 1]
            d[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k])

    def endpoint(h0: float, h1: float, del0: float, del1: float) -> float:
        val = ((2 * h0 + h1) * del0 - h0 * del1) / (h0 + h1)
        if val * del0 <= 0:
            return 0.0
        if del0 * del1 < 0 and abs(val) > abs(3 * del0):
            return 3 * del0
        return val

    d[0] = endpoint(h[0], h[1], delta[0], delta[1])
    d[-1] = endpoint(h[-1], h[-2], delta[-1], delta[-2])
    return d


R_SLOPES = pchip_slopes(R_TIME, R_VALUES)


def radius_at(t: float) -> float:
    if t <= R_TIME[0]:
        return float(R_VALUES[0])
    if t >= R_TIME[-1]:
        return float(R_VALUES[-1])
    i = int(np.searchsorted(R_TIME, t) - 1)
    h = R_TIME[i + 1] - R_TIME[i]
    s = (t - R_TIME[i]) / h
    h00 = 2 * s**3 - 3 * s**2 + 1
    h10 = s**3 - 2 * s**2 + s
    h01 = -2 * s**3 + 3 * s**2
    h11 = s**3 - s**2
    return float(h00 * R_VALUES[i] + h10 * h * R_SLOPES[i]
                 + h01 * R_VALUES[i + 1] + h11 * h * R_SLOPES[i + 1])


def radius_dot(t: float) -> float:
    if t <= R_TIME[0]:
        return float(R_SLOPES[0])
    if t >= R_TIME[-1]:
        return float(R_SLOPES[-1])
    i = int(np.searchsorted(R_TIME, t) - 1)
    h = R_TIME[i + 1] - R_TIME[i]
    s = (t - R_TIME[i]) / h
    # derivative of the cubic Hermite basis
    dh00 = 6 * s**2 - 6 * s
    dh10 = 3 * s**2 - 4 * s + 1
    dh01 = -6 * s**2 + 6 * s
    dh11 = 3 * s**2 - 2 * s
    return float((dh00 * R_VALUES[i] + dh10 * h * R_SLOPES[i]
                  + dh01 * R_VALUES[i + 1] + dh11 * h * R_SLOPES[i + 1]) / h)


def terminal_value(col: int, window_s: int = 3600) -> float:
    mask = ENV[:, 0] >= ENV[-1, 0] - window_s
    return float(np.mean(ENV[mask, col]))


def outside(t: float, window_s: int = 3600) -> tuple[float, float]:
    if t <= ENV[-1, 0]:
        return (float(np.interp(t, ENV[:, 0], ENV[:, 1])) + 273.15,
                float(np.interp(t, ENV[:, 0], ENV[:, 2])))
    return terminal_value(1, window_s) + 273.15, terminal_value(2, window_s)


@dataclass
class Grid:
    nr: int
    nz: int
    radius: float
    length: float
    radial_strategy: str = RADIAL_STRATEGY
    stretch: float = Z_STRETCH

    def __post_init__(self) -> None:
        s = np.linspace(0.0, 1.0, self.nr + 1)
        if self.radial_strategy == "uniform":
            self.rf = self.radius * s
        elif self.radial_strategy == "two-sided-local":
            self.rf = self.radius * (s - 0.65 * np.sin(2 * np.pi * s) / (2 * np.pi))
        else:
            raise ValueError(self.radial_strategy)
        if np.any(np.diff(self.rf) <= 0):
            raise RuntimeError("non-positive radial cell width")
        self.rc = (2.0 / 3.0) * (self.rf[1:]**3 - self.rf[:-1]**3) / (
            self.rf[1:]**2 - self.rf[:-1]**2)
        if self.nz <= 1:
            self.zf = np.array([0.0, self.length])
        else:
            q = np.linspace(0.0, 1.0, self.nz + 1)
            self.zf = (self.length / 2.0) * (1.0 - (1.0 - q) ** self.stretch)
        self.zc = 0.5 * (self.zf[:-1] + self.zf[1:])
        self.dr = np.diff(self.rf)
        self.dz = np.diff(self.zf)
        self.annulus = np.pi * np.diff(self.rf**2)
        self.vol = self.annulus[:, None] * self.dz[None, :]
        self.half_length = self.length / 2.0


def harmonic(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return 2.0 * a * b / np.maximum(a + b, 1e-300)


def conductances(coeff: np.ndarray, grid: Grid, conv: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    gr = harmonic(coeff[:-1, :], coeff[1:, :]) * (
        2.0 * np.pi * grid.rf[1:-1, None] * grid.dz[None, :]
    ) / (grid.rc[1:, None] - grid.rc[:-1, None])
    if grid.nz > 1:
        gz = harmonic(coeff[:, :-1], coeff[:, 1:]) * grid.annulus[:, None] / (
            grid.zc[None, 1:] - grid.zc[None, :-1]
        )
        # z=0 is a symmetry plane; only the exposed z=L/2 face has Robin flux.
        gz_end = grid.annulus / (
            (grid.half_length - grid.zc[-1]) / np.maximum(coeff[:, -1], 1e-300)
            + 1.0 / conv
        )
    else:
        gz = np.zeros((grid.nr, 0))
        gz_end = np.zeros(grid.nr)
    gside = (2.0 * np.pi * grid.radius * grid.dz) / (
        (grid.radius - grid.rc[-1]) / np.maximum(coeff[-1, :], 1e-300)
        + 1.0 / conv
    )
    return gr, gz, gside, gz_end


def cg_solve(old: np.ndarray, coeff: np.ndarray, storage: np.ndarray,
             grid: Grid, dt: float, conv: float, env_value: float,
             x0: np.ndarray | None = None, rtol: float = 5e-11,
             maxiter: int = 500) -> tuple[np.ndarray, float, int, float,
                                          tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    gr, gz, gside, gz_end = conductances(coeff, grid, conv)
    time_diag = storage * grid.vol / dt
    diag = time_diag.copy()
    diag[:-1, :] += gr
    diag[1:, :] += gr
    if grid.nz > 1:
        diag[:, :-1] += gz
        diag[:, 1:] += gz
    diag[-1, :] += gside
    diag[:, -1] += gz_end
    rhs = time_diag * old
    rhs[-1, :] += gside * env_value
    rhs[:, -1] += gz_end * env_value

    def amat(x: np.ndarray) -> np.ndarray:
        y = time_diag * x
        q = gr * (x[:-1, :] - x[1:, :])
        y[:-1, :] += q
        y[1:, :] -= q
        if grid.nz > 1:
            qz = gz * (x[:, :-1] - x[:, 1:])
            y[:, :-1] += qz
            y[:, 1:] -= qz
        y[-1, :] += gside * x[-1, :]
        y[:, -1] += gz_end * x[:, -1]
        return y

    x = old.copy() if x0 is None else x0.copy()
    r = rhs - amat(x)
    z = r / np.maximum(diag, 1e-300)
    p = z.copy()
    rz = float(np.sum(r * z))
    rhs_norm = max(float(np.linalg.norm(rhs.ravel())), 1e-300)
    it = 0
    for it in range(1, maxiter + 1):
        ap = amat(p)
        denom = float(np.sum(p * ap))
        if denom <= 0:
            raise RuntimeError("non-SPD operator in CG")
        alpha = rz / denom
        x += alpha * p
        r -= alpha * ap
        if float(np.linalg.norm(r.ravel())) <= rtol * rhs_norm:
            break
        z = r / np.maximum(diag, 1e-300)
        rz_new = float(np.sum(r * z))
        p = z + (rz_new / rz) * p
        rz = rz_new
    else:
        raise RuntimeError(f"CG failed after {maxiter} iterations")
    residual = float(np.linalg.norm((amat(x) - rhs).ravel()) / rhs_norm)
    boundary_in = float(np.sum(gside * (env_value - x[-1, :]))
                        + np.sum(gz_end * (env_value - x[:, -1])))
    return x, boundary_in, it, residual, (gr, gz, gside, gz_end)


def cg_reference(old: np.ndarray, coeff: np.ndarray, ref_grid: Grid,
                 physical_grid: Grid, rho_d: float, dt: float, conv: float,
                 env_value: float, x0: np.ndarray | None = None) -> tuple[
                     np.ndarray, float, int, float,
                     tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    _, _, _, _ = (old, coeff, ref_grid, physical_grid)  # type-checking aid
    gr, gz, gside, gz_end = conductances(coeff, physical_grid, conv)
    gr *= rho_d
    gz *= rho_d
    gside *= rho_d
    gz_end *= rho_d
    time_diag = RHO_D0 * ref_grid.vol / dt
    diag = time_diag.copy()
    diag[:-1, :] += gr
    diag[1:, :] += gr
    if ref_grid.nz > 1:
        diag[:, :-1] += gz
        diag[:, 1:] += gz
    diag[-1, :] += gside
    diag[:, -1] += gz_end
    rhs = time_diag * old
    rhs[-1, :] += gside * env_value
    rhs[:, -1] += gz_end * env_value

    def amat(x: np.ndarray) -> np.ndarray:
        y = time_diag * x
        q = gr * (x[:-1, :] - x[1:, :])
        y[:-1, :] += q
        y[1:, :] -= q
        if ref_grid.nz > 1:
            qz = gz * (x[:, :-1] - x[:, 1:])
            y[:, :-1] += qz
            y[:, 1:] -= qz
        y[-1, :] += gside * x[-1, :]
        y[:, -1] += gz_end * x[:, -1]
        return y

    x = old.copy() if x0 is None else x0.copy()
    r = rhs - amat(x)
    z = r / np.maximum(diag, 1e-300)
    p = z.copy()
    rz = float(np.sum(r * z))
    rhs_norm = max(float(np.linalg.norm(rhs.ravel())), 1e-300)
    it = 0
    for it in range(1, 501):
        ap = amat(p)
        denom = float(np.sum(p * ap))
        if denom <= 0:
            raise RuntimeError("non-SPD reference operator")
        alpha = rz / denom
        x += alpha * p
        r -= alpha * ap
        if float(np.linalg.norm(r.ravel())) <= 5e-11 * rhs_norm:
            break
        z = r / np.maximum(diag, 1e-300)
        rz_new = float(np.sum(r * z))
        p = z + (rz_new / rz) * p
        rz = rz_new
    else:
        raise RuntimeError("reference CG failed after 500 iterations")
    residual = float(np.linalg.norm((amat(x) - rhs).ravel()) / rhs_norm)
    boundary_in = float(np.sum(gside * (env_value - x[-1, :]))
                        + np.sum(gz_end * (env_value - x[:, -1])))
    return x, boundary_in, it, residual, (gr, gz, gside, gz_end)


def props_q4(c: np.ndarray, temp_k: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rho = 760.0 + 90.0 * c
    cp = 1850.0 + 2150.0 * c / (c + 1.0)
    k = 0.12 + 0.20 * c / (c + 1.0)
    d = 4.2e-4 * np.exp(-0.30 / np.maximum(c, 1e-9)) * np.exp(-3850.0 / temp_k)
    return rho, cp, k, d


def surface_from_cell(cell: np.ndarray, coeff: np.ndarray, grid: Grid,
                      conv: float, env_value: float) -> tuple[np.ndarray, np.ndarray]:
    side = (coeff[-1, :] * cell[-1, :] / (grid.radius - grid.rc[-1])
            + conv * env_value) / (
                coeff[-1, :] / (grid.radius - grid.rc[-1]) + conv)
    end = (coeff[:, -1] * cell[:, -1] / (grid.half_length - grid.zc[-1])
           + conv * env_value) / (
               coeff[:, -1] / (grid.half_length - grid.zc[-1]) + conv)
    return side, end


def sh_cylinder(velocity: float, diameter: float) -> float:
    """Churchill-Bernstein-style external crossflow Sh analogue.

    This is not identified from the supplied experiment.  It is used only to
    generate a bounded relative hm scenario under the frozen Cs-Cinf closure.
    """
    re = max(velocity, 0.0) * diameter / NU_AIR
    if re <= 0:
        return 0.30
    term = 0.62 * math.sqrt(re) * SC_AIR ** (1.0 / 3.0)
    term /= (1.0 + (0.4 / SC_AIR) ** (2.0 / 3.0)) ** 0.25
    term *= (1.0 + (re / 282000.0) ** (5.0 / 8.0)) ** (4.0 / 5.0)
    return 0.30 + term


SH_REF_PER_M = sh_cylinder(U_REF, 2.0 * R0) / (2.0 * R0)


def hm_from_airflow(velocity: float, radius: float) -> float:
    diameter = max(2.0 * radius, 1e-6)
    return HM0 * (sh_cylinder(velocity, diameter) / diameter) / SH_REF_PER_M


def length_ratio(radius: float, alpha: float) -> float:
    s = max(radius / R0, 1e-12)
    return s ** alpha


def length_ratio_dot(radius: float, radius_dot_value: float, alpha: float) -> float:
    s = max(radius / R0, 1e-12)
    if alpha == 0:
        return 0.0
    return alpha * s ** (alpha - 1.0) * radius_dot_value / R0


@dataclass
class RunConfig:
    label: str
    group: str
    alpha: float
    nr: int = NR_BASE
    nz: int = NZ_BASE
    dt: float = DT_BASE
    duration: float = 259200.0
    hm_mode: str = "frozen"
    hm_value: float = HM0
    airflow_u: float = 0.0
    thermal_mode: str = "prescribed"
    radiation_on: bool = False
    terminal_window_s: int = 3600


def simulate(cfg: RunConfig, log) -> dict:
    start = time.perf_counter()
    moving_radius = radius_at(0.0)
    moving_length = L0 * length_ratio(moving_radius, cfg.alpha)
    grid = Grid(cfg.nr, cfg.nz, moving_radius, moving_length)
    ref_grid = Grid(cfg.nr, cfg.nz, R0, L0)
    c = np.full((cfg.nr, cfg.nz), C0)
    temp = np.full_like(c, T0_K)
    initial_inventory = float(RHO_D0 * np.sum(c * grid.vol))
    cumulative_flux = 0.0
    max_balance = 0.0
    max_boundary_residual = 0.0
    max_geom_rel = 0.0
    max_area_rel = 0.0
    max_dry_rel = 0.0
    max_local_dry_rel = 0.0
    max_continuity_rel = 0.0
    max_cg = 0
    max_linear_res = 0.0
    max_picard = 0
    max_picard_update = 0.0
    max_rdot = 0.0
    max_ldot = 0.0
    max_axial_speed = 0.0
    hm_min = float("inf")
    hm_max = 0.0
    hrad_min = float("inf")
    hrad_max = 0.0
    records: list[dict] = []
    prev_t = 0.0
    prev_max = C0
    bracket = None
    next_sample = 0.0
    nsteps = int(math.ceil(cfg.duration / cfg.dt))

    def record(t: float, grid_now: Grid, c_now: np.ndarray, t_now: np.ndarray,
               hm_now: float, hrad_now: float) -> None:
        nonlocal next_sample
        _, _, _, d_now = props_q4(c_now, t_now)
        c_side, c_end = surface_from_cell(c_now, d_now, grid_now, hm_now, outside(t, cfg.terminal_window_s)[1])
        _, _, k_now, _ = props_q4(c_now, t_now)
        t_side, t_end = surface_from_cell(t_now, k_now, grid_now, H0 + hrad_now,
                                          outside(t, cfg.terminal_window_s)[0])
        while t + 1e-9 >= next_sample:
            records.append({
                "time_s": float(t),
                "radius_m": float(grid_now.radius),
                "length_m": float(grid_now.length),
                "volume_half_m3": float(np.sum(grid_now.vol)),
                "max_C": float(np.max(c_now)),
                "min_C": float(np.min(c_now)),
                "mean_C": float(np.sum(c_now * grid_now.vol) / np.sum(grid_now.vol)),
                "center_C": float(c_now[0, 0]),
                "side_surface_C": float(np.average(c_side, weights=grid_now.dz)),
                "end_surface_C": float(np.average(c_end, weights=grid_now.annulus)),
                "center_T_C": float(t_now[0, 0] - 273.15),
                "side_surface_T_C": float(np.average(t_side, weights=grid_now.dz) - 273.15),
                "end_surface_T_C": float(np.average(t_end, weights=grid_now.annulus) - 273.15),
                "hm_effective_m_s": float(hm_now),
                "hrad_W_m2K": float(hrad_now),
            })
            next_sample += 3600.0

    # Store the initial state before stepping.  The initial surface reconstruction
    # is diagnostic only and does not alter the uniform initial field.
    tenv0, cenv0 = outside(0.0, cfg.terminal_window_s)
    record(0.0, grid, c, temp, HM0 if cfg.hm_mode == "frozen" else hm_from_airflow(cfg.airflow_u, R0), 0.0)

    for step in range(1, nsteps + 1):
        t = min(step * cfg.dt, cfg.duration)
        tenv1, cenv1 = outside(t, cfg.terminal_window_s)
        rnext = radius_at(t)
        lnext = L0 * length_ratio(rnext, cfg.alpha)
        next_grid = Grid(cfg.nr, cfg.nz, rnext, lnext)
        hm_now = cfg.hm_value if cfg.hm_mode == "frozen" else hm_from_airflow(cfg.airflow_u, rnext)
        hm_min = min(hm_min, hm_now)
        hm_max = max(hm_max, hm_now)
        guess_c = c.copy()
        guess_t = temp.copy()
        hrad_now = 0.0
        converged = False
        for pic in range(1, 25):
            rho, cp, k, d = props_q4(guess_c, guess_t)
            if cfg.thermal_mode == "prescribed":
                new_t = np.full_like(guess_t, tenv1)
                it_t = 0
                res_t = 0.0
                hrad_now = 0.0
            else:
                # Linearized radiation coefficient, evaluated from the current
                # mean side surface estimate.  This is intentionally low-order.
                _, kside = surface_from_cell(guess_t, k, next_grid, H0, tenv1)
                ts_guess = float(np.mean(kside))
                if cfg.radiation_on:
                    hrad_now = EMISSIVITY * SIGMA * (tenv1 + ts_guess) * (tenv1**2 + ts_guess**2)
                else:
                    hrad_now = 0.0
                new_t, _, it_t, res_t, _ = cg_solve(
                    temp, k, rho * cp, next_grid, t - prev_t, H0 + hrad_now,
                    tenv1, x0=guess_t)
            new_c, bflux, it_c, res_c, ops_c = cg_reference(
                c, d, ref_grid, next_grid,
                RHO_D0 * (R0 / rnext) ** 2 * (L0 / lnext),
                t - prev_t, hm_now, cenv1, x0=guess_c)
            delta = max(float(np.max(np.abs(new_c - guess_c))),
                        float(np.max(np.abs(new_t - guess_t))))
            guess_c = new_c
            guess_t = new_t
            max_cg = max(max_cg, it_c, it_t)
            max_linear_res = max(max_linear_res, res_c, res_t)
            if delta < 1e-7:
                converged = True
                break
        max_picard = max(max_picard, pic)
        max_picard_update = max(max_picard_update, delta)
        if not converged:
            raise RuntimeError(f"Picard failed at t={t} s, update={delta}")
        c, temp = guess_c, guess_t

        rho_d_prev = RHO_D0 * (R0 / grid.radius) ** 2 * (L0 / grid.length)
        rho_d_now = RHO_D0 * (R0 / rnext) ** 2 * (L0 / lnext)
        cumulative_flux += bflux * (t - prev_t)
        inventory = float(rho_d_now * np.sum(c * next_grid.vol))
        balance = abs((inventory - initial_inventory) - cumulative_flux) / max(abs(initial_inventory), 1e-30)
        max_balance = max(max_balance, balance)

        v_geom = np.pi * rnext**2 * lnext / 2.0
        geom_rel = abs(float(np.sum(next_grid.vol)) / v_geom - 1.0)
        max_geom_rel = max(max_geom_rel, geom_rel)
        side_area_mesh = float(2.0 * np.pi * rnext * np.sum(next_grid.dz))
        end_area_mesh = float(np.sum(next_grid.annulus))
        side_area_geom = float(np.pi * rnext * lnext)
        end_area_geom = float(np.pi * rnext**2)
        area_rel = max(abs(side_area_mesh / side_area_geom - 1.0),
                       abs(end_area_mesh / end_area_geom - 1.0))
        max_area_rel = max(max_area_rel, area_rel)
        dry_mass = rho_d_now * float(np.sum(next_grid.vol))
        dry_rel = abs(dry_mass / (RHO_D0 * np.pi * R0**2 * L0 / 2.0) - 1.0)
        max_dry_rel = max(max_dry_rel, dry_rel)
        cell_dry_rel = np.max(np.abs(rho_d_now * next_grid.vol
                                     / (rho_d_prev * grid.vol) - 1.0))
        max_local_dry_rel = max(max_local_dry_rel, float(cell_dry_rel))

        rdot = radius_dot(0.5 * (prev_t + t))
        ldot = L0 * length_ratio_dot(radius_at(0.5 * (prev_t + t)), rdot, cfg.alpha)
        max_rdot = max(max_rdot, abs(rdot))
        max_ldot = max(max_ldot, abs(ldot))
        max_axial_speed = max(max_axial_speed, abs(ldot) / 2.0)
        # The affine map gives J(t)/J(0)=(R/R0)^2(L/L0) and
        # rho_d/rho_d0=J(0)/J(t). Audit the discrete continuity identity on
        # every material cell directly; do not divide a finite-difference
        # derivative by a near-zero plateau velocity.
        cell_continuity_residual = np.max(np.abs(
            rho_d_now * next_grid.vol / (rho_d_prev * grid.vol) - 1.0))
        max_continuity_rel = max(max_continuity_rel, float(cell_continuity_residual))

        # Boundary residual: compare the assembled Robin conductance with the
        # reconstructed physical surface flux using the same current area.
        d_final = props_q4(c, temp)[3]
        side_c, end_c = surface_from_cell(c, d_final, next_grid, hm_now, cenv1)
        gr, gz, gside, gz_end = ops_c
        q_num = np.r_[gside * (cenv1 - c[-1, :]), gz_end * (cenv1 - c[:, -1])]
        q_phys = np.r_[rho_d_now * hm_now * (2.0 * np.pi * rnext * next_grid.dz) * (cenv1 - side_c),
                        rho_d_now * hm_now * next_grid.annulus * (cenv1 - end_c)]
        boundary_res = np.max(np.abs(q_num - q_phys)) / max(abs(float(np.sum(q_num))), 1e-30)
        max_boundary_residual = max(max_boundary_residual, float(boundary_res))

        current_max = float(np.max(c))
        if not np.all(np.isfinite(c)) or not np.all(np.isfinite(temp)) or float(np.min(c)) < -1e-10:
            raise FloatingPointError(f"physical guard failed at t={t} s")
        if current_max < THRESHOLD:
            bracket = (prev_t, t, prev_max, current_max)
            record(t, next_grid, c, temp, hm_now, hrad_now)
            grid = next_grid
            prev_t = t
            prev_max = current_max
            hrad_min = min(hrad_min, hrad_now)
            hrad_max = max(hrad_max, hrad_now)
            break
        record(t, next_grid, c, temp, hm_now, hrad_now)
        grid = next_grid
        prev_t = t
        prev_max = current_max
        hrad_min = min(hrad_min, hrad_now)
        hrad_max = max(hrad_max, hrad_now)
    else:
        hrad_min = 0.0 if hrad_min == float("inf") else hrad_min

    event_time = None
    reported_time = None
    if bracket is not None:
        t0, t1, y0, y1 = bracket
        event_time = float(t0 + (THRESHOLD - y0) * (t1 - t0) / (y1 - y0)) if y1 != y0 else float(t1)
        reported_time = float(60.0 * math.ceil(event_time / 60.0 - 1e-12))
    final_time = reported_time if reported_time is not None else prev_t
    runtime = time.perf_counter() - start
    result = {
        "config": cfg.__dict__,
        "metrics": {
            "runtime_s": runtime,
            "steps_completed": int(round(prev_t / cfg.dt)),
            "max_cg_iterations": max_cg,
            "max_linear_relative_residual": max_linear_res,
            "max_picard_iterations": max_picard,
            "max_picard_update": max_picard_update,
            "max_normalized_moisture_balance_error": max_balance,
            "max_robin_boundary_relative_residual": max_boundary_residual,
            "max_geometry_relative_error": max_geom_rel,
            "max_boundary_area_relative_error": max_area_rel,
            "max_dry_solid_inventory_relative_error": max_dry_rel,
            "max_local_dry_cell_mass_relative_error": max_local_dry_rel,
            "max_analytic_dry_continuity_relative_residual": max_continuity_rel,
            "max_abs_Rdot_m_s": max_rdot,
            "max_abs_Ldot_m_s": max_ldot,
            "max_abs_axial_material_speed_m_s": max_axial_speed,
            "hm_min_m_s": 0.0 if hm_min == float("inf") else hm_min,
            "hm_max_m_s": hm_max,
            "hrad_min_W_m2K": 0.0 if hrad_min == float("inf") else hrad_min,
            "hrad_max_W_m2K": hrad_max,
            "threshold": THRESHOLD,
            "threshold_bracket": bracket,
            "interpolated_event_time_s": event_time,
            "reported_event_time_s": reported_time,
            "final_time_s": final_time,
            "final_max_C": float(np.max(c)),
            "final_mean_C": float(np.sum(c * grid.vol) / np.sum(grid.vol)),
            "radius_at_final_m": float(grid.radius),
            "length_at_final_m": float(grid.length),
            "volume_ratio_final": float(np.sum(grid.vol) / (np.pi * R0**2 * L0 / 2.0)),
            "dry_density_ratio_final": float((RHO_D0 * (R0 / grid.radius)**2 * (L0 / grid.length)) / RHO_D0),
        },
        "records": records,
    }
    log(f"DONE {cfg.label}: t_star={reported_time}, final_max={result['metrics']['final_max_C']:.6g}, "
        f"hm=[{result['metrics']['hm_min_m_s']:.3e},{result['metrics']['hm_max_m_s']:.3e}], "
        f"balance={max_balance:.3e}, runtime={runtime:.1f}s")
    return result


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0])
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "run.log"
    with log_path.open("w", encoding="utf-8") as lf:
        def log(msg: str) -> None:
            line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
            print(line, flush=True)
            lf.write(line + "\n")
            lf.flush()

        log(f"START seed={SEED} python={sys.executable} platform={platform.platform()}")
        log(f"PROJECT_ROOT={PROJECT_ROOT}")
        log(f"inputs ENV={sha256(INPUT_DIR / '附件1.xlsx')} RADIUS={sha256(INPUT_DIR / '附件2.xlsx')}")
        log(f"base grid nr={NR_BASE} nz={NZ_BASE} dt={DT_BASE}s threshold={THRESHOLD}")

        configs = [
            RunConfig("length-A-no-axial-shrink", "length_sensitivity", 0.0),
            RunConfig("length-B-radius-proportional", "length_sensitivity", 1.0),
            RunConfig("length-C-upper-envelope-alpha2", "length_sensitivity", 2.0),
            RunConfig("hm-fixed-low-0.8", "hm_fixed_interval", 0.0, hm_value=0.8 * HM0),
            RunConfig("hm-fixed-base-1.0", "hm_fixed_interval", 0.0, hm_value=HM0),
            RunConfig("hm-fixed-high-1.2", "hm_fixed_interval", 0.0, hm_value=1.2 * HM0),
        ]
        for velocity in (0.0, 0.5, 1.0, 2.0, 4.0):
            configs.append(RunConfig(f"airflow-u{velocity:g}mps", "airflow_correlation", 0.0,
                                     hm_mode="airflow_correlation", airflow_u=velocity))
        configs.extend([
            RunConfig("radiation-off-low-order", "radiation_low_order", 0.0,
                      thermal_mode="solved", radiation_on=False),
            RunConfig("radiation-on-low-order", "radiation_low_order", 0.0,
                      thermal_mode="solved", radiation_on=True),
            RunConfig("length-A-fine-control", "convergence_control", 0.0,
                      nr=NR_FINE, nz=NZ_FINE, dt=DT_BASE),
        ])

        results = []
        trajectories = []
        failures = []
        for cfg in configs:
            log(f"START {cfg.label} cfg={cfg.__dict__}")
            try:
                out = simulate(cfg, log)
                results.append({"label": cfg.label, "group": cfg.group, **cfg.__dict__, **out["metrics"]})
                for row in out["records"]:
                    trajectories.append({"label": cfg.label, "group": cfg.group, **row})
                with (MODEL_DIR / f"{cfg.label}.json").open("w", encoding="utf-8") as f:
                    json.dump(json_safe(out), f, ensure_ascii=False, indent=2)
            except Exception as exc:
                failures.append({"label": cfg.label, "group": cfg.group, "error": repr(exc)})
                log(f"FAIL {cfg.label}: {exc!r}")

        write_csv(RESULTS_DIR / "scenario-results.csv", results)
        write_csv(RESULTS_DIR / "trajectories-hourly.csv", trajectories)
        write_csv(RESULTS_DIR / "failures.csv", failures)

        manifest = {
            "schema_version": "1.0",
            "task": "Q4 length shrinkage and external airflow candidate prototype",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "seed": SEED,
            "project_root": str(PROJECT_ROOT),
            "write_boundary": str(TASK_DIR),
            "inputs": {
                "attachment1": {"path": "input/A题/附件/附件1.xlsx", "sha256": sha256(INPUT_DIR / "附件1.xlsx")},
                "attachment2": {"path": "input/A题/附件/附件2.xlsx", "sha256": sha256(INPUT_DIR / "附件2.xlsx")},
            },
            "frozen_settings": {
                "R_interpolation": "attachment-2 monotone PCHIP",
                "environment_extension": "attachment-1 terminal one-hour mean after 4 h",
                "R0_m": R0, "L0_m": L0, "rho_d0_kg_m3": RHO_D0,
                "h_W_m2K": H0, "hm_base_m_s": HM0,
                "grid_base": {"nr": NR_BASE, "nz": NZ_BASE, "dt_s": DT_BASE, "radial_strategy": RADIAL_STRATEGY},
                "threshold": THRESHOLD, "report_resolution_s": 60,
                "water_inventory": "q_w=rho_d*C; half-cylinder inventory consistently used",
            },
            "length_scenarios": {
                "A": "alpha=0, L/L0=1; no axial shrink",
                "B": "alpha=1, L/L0=R/R0; radius-proportional sensitivity only",
                "C": "alpha=2, L/L0=(R/R0)^2; aggressive pre-registered envelope, not observed",
            },
            "airflow_correlation": {
                "formula": "Sh=0.3+[0.62 Re^0.5 Sc^(1/3)/(1+(0.4/Sc)^(2/3))^0.25]*(1+(Re/282000)^(5/8))^(4/5)",
                "mapped_effective_hm": "hm=hm_base*((Sh/d)/(Sh_ref/d_ref))",
                "velocity_scenarios_m_s": [0.0, 0.5, 1.0, 2.0, 4.0],
                "caveat": "relative scaling only; raw vapor Sh*Dv/d is not directly commensurable with frozen Cs-Cinf hm",
            },
            "radiation": {
                "formula": "h_rad=epsilon*sigma*(T_sur+T_s)*(T_sur^2+T_s^2)",
                "epsilon": EMISSIVITY, "view_factor": 1.0,
                "mode": "low-order linearized Robin extension; no CFD or radiative field solved",
            },
            "outputs": [
                "model-q4-length-airflow/*.json",
                "results/scenario-results.csv",
                "results/trajectories-hourly.csv",
                "results/failures.csv",
                "logs/run.log",
            ],
            "failures": failures,
        }
        with (TASK_DIR / "reproduction-manifest.json").open("w", encoding="utf-8") as f:
            json.dump(json_safe(manifest), f, ensure_ascii=False, indent=2)
        log(f"COMPLETE successes={len(results)} failures={len(failures)}")


if __name__ == "__main__":
    main()
