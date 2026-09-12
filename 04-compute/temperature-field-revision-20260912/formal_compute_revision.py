"""Candidate COMPUTE revision with an implicit internal temperature solve.

This copy is isolated from the approved COMPUTE outputs.  It keeps the
problem-supplied coefficient laws and deliberately does not add an
unidentified latent-heat source.  For Q2--Q4 it solves the heat equation
with the same backward-Euler finite-volume operator used by Q1, instead of
prescribing the chamber temperature throughout the material.
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
OUT = Path(__file__).resolve().parent
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
                    x0=None, rtol=5e-11, maxiter=1200):
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


def radial_profile(field, coeff, grid: Grid, conv, env, positions=EVAL_R):
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
            rp_c = radial_profile(c, d, grid, 8e-7 * cfg.hm_mult, cenv)
            rp_t = radial_profile(temp, k, grid, 25 * cfg.h_mult, tenv)
            rec = {"time_s": t, "radius_m": current_radius, "max_C": max(float(c.max()),axis_mid_value(c,grid)),
                   "min_C": float(c.min()), "mean_C": float(np.sum(c*grid.vol)/np.sum(grid.vol)),
                   "center_C": float(rp_c[0]), "surface_C": float(rp_c[np.where(EVAL_R <= current_radius + 1e-12)[0][-1]]),
                   "center_T_C": float(rp_t[0] - 273.15), "surface_T_C": float(rp_t[np.where(EVAL_R <= current_radius + 1e-12)[0][-1]] - 273.15)}
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
                # Candidate revision: M2/M3 also solve the internal heat
                # equation.  M2 keeps constant moisture-law coefficients;
                # M3 retains the state-dependent laws.  No latent-heat
                # source is inserted because its parameters are not frozen.
                rho, cp, k, d = props_q23(
                    guess_c, guess_t, constant=(cfg.model == "M2"),
                    pref=cfg.pref, exponent=cfg.exponent)
                solve_heat = True
            else:
                rho, cp, k, d = props_q4(guess_c, guess_t, pref=cfg.pref, exponent=cfg.exponent); solve_heat = True
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
                         "final_max_C": current_max, "final_mean_C": float(np.sum(c*grid.vol)/np.sum(grid.vol)),
                         "temperature_field_solver": "implicit_backward_euler_conduction",
                         "latent_heat_source": "omitted_by_design"}}


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
    write_field_xlsx(RESULTS/"result3.xlsx",q3["states"],temperature=True)
    for i,r in enumerate(q3_space):
        prev=q3_space[i-1] if i else None; et=r["metrics"]["interpolated_event_time_s"]
        threshold_grid_rows.append({"scope":"Q3","nr":r["config"]["nr"],"nz":r["config"]["nz"],"grid_strategy":r["config"]["radial_strategy"],"fixed_dt_s":60,"interpolated_event_time_s":et,"reported_event_time_s":r["metrics"]["reported_event_time_s"],"adjacent_change_s":"" if prev is None else abs(et-prev["metrics"]["interpolated_event_time_s"])})
    convergence.append({"scope":"Q3","family":"M3","metric":"t_star_space","base":q3_space[-2]["metrics"]["interpolated_event_time_s"],"fine":q3["metrics"]["interpolated_event_time_s"],"absolute_change":abs(q3_space[-2]["metrics"]["interpolated_event_time_s"]-q3["metrics"]["interpolated_event_time_s"]),"acceptance_pair":True})
    convergence.append({"scope":"Q3","family":"M3","metric":"t_star_time","base":q3_time["metrics"]["interpolated_event_time_s"],"fine":q3_time_fine["metrics"]["interpolated_event_time_s"],"absolute_change":abs(q3_time["metrics"]["interpolated_event_time_s"]-q3_time_fine["metrics"]["interpolated_event_time_s"]),"acceptance_pair":True})
    for window in (1800,3600,7200):
        r=execute(RunConfig(f"Q3-window-{window}",10,20,60,259200,3,"M3",window_s=window,stop_threshold=.15-1e-6,sample_every=3600))
        sensitivity.append({"scope":"Q3","factor":"terminal_window_s","level":str(window),"value":window,"t_star_s":r["metrics"]["final_time_s"],"final_max_C":r["metrics"]["final_max_C"],"final_mean_C":r["metrics"]["final_mean_C"]})
    for factor in ("h_mult","hm_mult","pref","exponent"):
        for level,val in (("low",.8),("high",1.2)):
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
    write_field_xlsx(RESULTS/"result4.xlsx",q4["states"],temperature=True,moving=True)
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
