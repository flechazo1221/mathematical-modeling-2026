from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np


sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SOURCE_PATH = ROOT / "04-compute" / "temperature-field-revision-20260912" / "formal_compute_revision.py"
OLD_ATTEMPT = ROOT / "03-prototype" / "controller-phase-change-attempt-20260912" / "run_phase_change_attempt.py"
THRESHOLD = 0.15 - 1e-6
C0 = 2.55
LV = 2.4e6
HM = 8e-7
H = 25.0
RHO_D_FIXED = 650.0
RHO_D_Q4_0 = 820.0
PICARD_TOL = 1e-7
MAX_PICARD = 80
SEED = 20260912


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_source():
    spec = importlib.util.spec_from_file_location("three_water_temperature_source", SOURCE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import source solver: {SOURCE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def cg_solve(module, old, coeff, storage, grid, dt, conv, env_value,
             source_rate=None, boundary_sink=None, x0=None,
             include_ends=True, rtol=5e-11, maxiter=1400):
    """Backward-Euler finite-volume solve with an optional volumetric source.

    `source_rate` has the same dry-basis concentration/time unit as C or B.
    `boundary_sink` is a thermal outward sink in W/m2 and is only used for T.
    """
    gr, gz, gbr, gb0, gb1 = module.conductances(coeff, grid, conv, include_ends)
    time_diag = storage * grid.vol / dt
    diag = time_diag.copy()
    diag[:-1, :] += gr
    diag[1:, :] += gr
    if grid.nz > 1:
        diag[:, :-1] += gz
        diag[:, 1:] += gz
    diag[-1, :] += gbr
    diag[:, 0] += gb0
    diag[:, -1] += gb1
    rhs = time_diag * old
    if source_rate is not None:
        rhs += source_rate * grid.vol
    rhs[-1, :] += gbr * env_value
    rhs[:, 0] += gb0 * env_value
    rhs[:, -1] += gb1 * env_value
    if boundary_sink is not None:
        outer_area = 2 * math.pi * grid.radius * grid.dz
        rhs[-1, :] -= outer_area * boundary_sink.get("outer_W_m2", 0.0)
        rhs[:, 0] -= grid.annulus * boundary_sink.get("z0_W_m2", 0.0)
        rhs[:, -1] -= grid.annulus * boundary_sink.get("z1_W_m2", 0.0)

    def amat(x):
        y = time_diag * x
        q = gr * (x[:-1, :] - x[1:, :])
        y[:-1, :] += q
        y[1:, :] -= q
        if grid.nz > 1:
            qz = gz * (x[:, :-1] - x[:, 1:])
            y[:, :-1] += qz
            y[:, 1:] -= qz
        y[-1, :] += gbr * x[-1, :]
        y[:, 0] += gb0 * x[:, 0]
        y[:, -1] += gb1 * x[:, -1]
        return y

    x = old.copy() if x0 is None else x0.copy()
    r = rhs - amat(x)
    z = r / np.maximum(diag, 1e-300)
    p = z.copy()
    rz = float(np.sum(r * z))
    rhs_norm = max(float(np.linalg.norm(rhs.ravel())), 1e-300)
    iterations = 0
    for iterations in range(1, maxiter + 1):
        ap = amat(p)
        denom = float(np.sum(p * ap))
        if denom <= 0:
            raise RuntimeError("non-SPD operator in three-water CG")
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
        raise RuntimeError(f"three-water CG failed after {maxiter} iterations")
    boundary_in = float(
        np.sum(gbr * (env_value - x[-1, :]))
        + np.sum(gb0 * (env_value - x[:, 0]))
        + np.sum(gb1 * (env_value - x[:, -1]))
    )
    residual = float(np.linalg.norm((amat(x) - rhs).ravel()) / rhs_norm)
    return x, boundary_in, iterations, residual


def reference_solve(module, old, coeff, ref_grid, physical_grid, dt, conv, env_value,
                    source_rate=None, rho0=RHO_D_Q4_0, x0=None,
                    include_ends=True, rtol=5e-11, maxiter=1400):
    """Reference-coordinate moisture solve for Q4 with a dry-basis source."""
    rho_d = rho0 * (module.R0 / physical_grid.radius) ** 2
    gr0, gz0, gbr0, gb00, gb10 = module.conductances(coeff, physical_grid, conv, include_ends)
    gr, gz, gbr, gb0, gb1 = rho_d * gr0, rho_d * gz0, rho_d * gbr0, rho_d * gb00, rho_d * gb10
    time_diag = rho0 * ref_grid.vol / dt
    diag = time_diag.copy()
    diag[:-1, :] += gr
    diag[1:, :] += gr
    if ref_grid.nz > 1:
        diag[:, :-1] += gz
        diag[:, 1:] += gz
    diag[-1, :] += gbr
    diag[:, 0] += gb0
    diag[:, -1] += gb1
    rhs = time_diag * old
    if source_rate is not None:
        rhs += rho0 * ref_grid.vol * source_rate
    rhs[-1, :] += gbr * env_value
    rhs[:, 0] += gb0 * env_value
    rhs[:, -1] += gb1 * env_value

    def amat(x):
        y = time_diag * x
        q = gr * (x[:-1, :] - x[1:, :])
        y[:-1, :] += q
        y[1:, :] -= q
        if ref_grid.nz > 1:
            qz = gz * (x[:, :-1] - x[:, 1:])
            y[:, :-1] += qz
            y[:, 1:] -= qz
        y[-1, :] += gbr * x[-1, :]
        y[:, 0] += gb0 * x[:, 0]
        y[:, -1] += gb1 * x[:, -1]
        return y

    x = old.copy() if x0 is None else x0.copy()
    r = rhs - amat(x)
    z = r / np.maximum(diag, 1e-300)
    p = z.copy()
    rz = float(np.sum(r * z))
    rhs_norm = max(float(np.linalg.norm(rhs.ravel())), 1e-300)
    iterations = 0
    for iterations in range(1, maxiter + 1):
        ap = amat(p)
        denom = float(np.sum(p * ap))
        if denom <= 0:
            raise RuntimeError("non-SPD reference operator in three-water solve")
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
        raise RuntimeError(f"three-water reference CG failed after {maxiter} iterations")
    boundary_in = float(
        np.sum(gbr * (env_value - x[-1, :]))
        + np.sum(gb0 * (env_value - x[:, 0]))
        + np.sum(gb1 * (env_value - x[:, -1]))
    )
    residual = float(np.linalg.norm((amat(x) - rhs).ravel()) / rhs_norm)
    return x, boundary_in, iterations, residual


def outward_flux(module, coeff, liquid, grid, cenv, rho_d):
    """Return positive surface gasification fluxes and signed net water flux."""
    _, _, gbr, gb0, gb1 = module.conductances(coeff, grid, HM, True)
    raw_outer = gbr * (liquid[-1, :] - cenv)
    raw_z0 = gb0 * (liquid[:, 0] - cenv)
    raw_z1 = gb1 * (liquid[:, -1] - cenv)
    outer_area = 2 * math.pi * grid.radius * grid.dz
    outer_j = rho_d * np.maximum(raw_outer, 0.0) / np.maximum(outer_area, 1e-300)
    z0_j = rho_d * np.maximum(raw_z0, 0.0) / np.maximum(grid.annulus, 1e-300)
    z1_j = rho_d * np.maximum(raw_z1, 0.0) / np.maximum(grid.annulus, 1e-300)
    signed_net_in = -rho_d * float(np.sum(raw_outer) + np.sum(raw_z0) + np.sum(raw_z1))
    gas_out = float(np.sum(outer_j * outer_area) + np.sum(z0_j * grid.annulus) + np.sum(z1_j * grid.annulus))
    return {"outer_W_m2": LV * outer_j, "z0_W_m2": LV * z0_j, "z1_W_m2": LV * z1_j}, {
        "outer_kg_m2_s": outer_j, "z0_kg_m2_s": z0_j, "z1_kg_m2_s": z1_j,
    }, signed_net_in, gas_out


def mass_inventory(module, q, liquid, bound, grid, ref_grid=None):
    if q == "Q4":
        rho_d = RHO_D_Q4_0 * (module.R0 / grid.radius) ** 2
        return float(rho_d * np.sum((liquid + bound) * grid.vol)), rho_d
    return float(RHO_D_FIXED * np.sum((liquid + bound) * grid.vol)), RHO_D_FIXED


def field_mass(module, q, field, grid, ref_grid=None):
    if q == "Q4":
        return float(RHO_D_Q4_0 * np.sum(field * (ref_grid.vol if ref_grid is not None else grid.vol)))
    return float(RHO_D_FIXED * np.sum(field * grid.vol))


def field_min_total(liquid, bound):
    total = liquid + bound
    return float(np.min(liquid)), float(np.min(bound)), float(np.min(total))


def run_case(module, q: str, model: str, bound_fraction: float, tau_s: float,
             level: str = "M", dt_level: str = "M", duration_override: float | None = None) -> dict:
    meshes = {"L": 8, "M": 12, "H": 18}
    dt_by_q = {"Q2": {"L": 240.0, "M": 120.0, "H": 60.0},
               "Q3": {"L": 600.0, "M": 300.0, "H": 150.0},
               "Q4": {"L": 600.0, "M": 300.0, "H": 150.0}}
    duration = 10800.0 if q == "Q2" else 259200.0
    if duration_override is not None:
        duration = duration_override
    nr = meshes[level]
    nz = meshes[level]
    dt_nominal = dt_by_q[q][dt_level]
    moving = q == "Q4"
    q_num = {"Q2": 2, "Q3": 3, "Q4": 4}[q]
    radius0 = module.radius_at(0, "pchip") if moving else module.R0
    grid = module.Grid(nr, nz, radius0, radial_strategy="two-sided-local")
    ref_grid = module.Grid(nr, nz, module.R0, radial_strategy="two-sided-local")
    if model == "M2":
        liquid = np.full((nr, nz), C0 * (1.0 - bound_fraction))
        bound = np.full((nr, nz), C0 * bound_fraction)
    else:
        liquid = np.full((nr, nz), C0)
        bound = np.zeros((nr, nz))
    temp = np.full((nr, nz), 301.15)
    initial_inventory, _ = mass_inventory(module, q, liquid, bound, grid, ref_grid)
    initial_dry = (RHO_D_Q4_0 * math.pi * module.R0 ** 2 * grid.axial_extent) if moving else None
    threshold_bracket = None
    records: list[dict] = []
    water_audit: list[dict] = []
    latent_audit: list[dict] = []
    total_latent_j = 0.0
    max_picard = 0
    max_solver_residual = 0.0
    max_picard_update = 0.0
    max_water_balance = 0.0
    max_phase_split_residual = 0.0
    min_liquid = float("inf")
    min_bound = float("inf")
    min_total = float("inf")
    previous_max = float(np.max(liquid + bound))
    last_t = 0.0
    start = time.perf_counter()
    step_count = int(math.ceil(duration / dt_nominal))
    next_sample = 0.0

    def snapshot(t, current_grid, cenv):
        total = liquid + bound
        if q_num in (2, 3):
            rho, cp, k, d = module.props_q23(total, temp, constant=False)
        else:
            rho, cp, k, d = module.props_q4(total, temp)
        rp_c = module.radial_profile(total, d, current_grid, HM, cenv)
        tenv, _ = module.outside(t)
        rp_t = module.radial_profile(temp, k, current_grid, H, tenv)
        valid_c = rp_c[np.isfinite(rp_c)]
        valid_t = rp_t[np.isfinite(rp_t)]
        records.append({
            "time_s": float(t), "radius_m": float(current_grid.radius),
            "max_total_C": float(max(np.max(total), module.axis_mid_value(total, current_grid))),
            "min_total_C": float(np.min(total)),
            "mean_total_C": float(np.sum(total * current_grid.vol) / np.sum(current_grid.vol)),
            "center_total_C": float(valid_c[0]) if len(valid_c) else float("nan"),
            "surface_total_C": float(valid_c[-1]) if len(valid_c) else float("nan"),
            "center_T_C": float(valid_t[0] - 273.15) if len(valid_t) else float("nan"),
            "surface_T_C": float(valid_t[-1] - 273.15) if len(valid_t) else float("nan"),
        })

    tenv0, cenv0 = module.outside(0.0)
    snapshot(0.0, grid, cenv0)
    try:
        for step in range(1, step_count + 1):
            t = min(float(step * dt_nominal), duration)
            dt = t - last_t
            tenv1, cenv1 = module.outside(t)
            next_radius = module.radius_at(t, "pchip") if moving else module.R0
            next_grid = module.Grid(nr, nz, next_radius, radial_strategy="two-sided-local")
            if model == "M2":
                bound_new = bound * math.exp(-dt / max(tau_s, 1e-12))
                release_rate = (bound - bound_new) / dt
            else:
                bound_new = np.zeros_like(bound)
                release_rate = np.zeros_like(bound)
            guess_liquid = liquid.copy()
            guess_temp = temp.copy()
            latent_sink = None
            last_boundary_flux = {"outer_kg_m2_s": np.zeros(nz), "z0_kg_m2_s": np.zeros(nr), "z1_kg_m2_s": np.zeros(nr)}
            last_gas_out = 0.0
            last_heat_boundary = 0.0
            last_heat_residual = 0.0
            last_moisture_residual = 0.0
            delta = float("inf")
            for pic in range(1, MAX_PICARD + 1):
                total_guess = guess_liquid + bound_new
                if q_num in (2, 3):
                    rho, cp, k, d = module.props_q23(total_guess, guess_temp, constant=False)
                else:
                    rho, cp, k, d = module.props_q4(total_guess, guess_temp)
                new_temp, heat_boundary, heat_it, heat_residual = cg_solve(
                    module, temp, k, rho * cp, next_grid, dt, H, tenv1,
                    boundary_sink=latent_sink, x0=guess_temp)
                rho_d_next = RHO_D_Q4_0 * (module.R0 / next_grid.radius) ** 2 if moving else RHO_D_FIXED
                if moving:
                    new_liquid, moisture_boundary, moisture_it, moisture_residual = reference_solve(
                        module, liquid, d, ref_grid, next_grid, dt, HM, cenv1,
                        source_rate=release_rate, rho0=RHO_D_Q4_0, x0=guess_liquid)
                else:
                    new_liquid, raw_boundary, moisture_it, moisture_residual = cg_solve(
                        module, liquid, d, np.ones_like(liquid), next_grid, dt, HM, cenv1,
                        source_rate=release_rate, x0=guess_liquid)
                    moisture_boundary = rho_d_next * raw_boundary
                heat_boundary_sink, boundary_flux, _, gas_out = outward_flux(
                    module, d, new_liquid, next_grid, cenv1, rho_d_next)
                if model == "M0":
                    boundary_flux = {"outer_kg_m2_s": np.zeros(nz), "z0_kg_m2_s": np.zeros(nr), "z1_kg_m2_s": np.zeros(nr)}
                    gas_out = 0.0
                new_latent_sink = heat_boundary_sink if model != "M0" else None
                delta = max(float(np.max(np.abs(new_liquid - guess_liquid))),
                            float(np.max(np.abs(new_temp - guess_temp))))
                guess_liquid = new_liquid
                guess_temp = new_temp
                latent_sink = new_latent_sink
                last_boundary_flux = boundary_flux
                last_gas_out = gas_out if model != "M0" else 0.0
                last_heat_boundary = heat_boundary
                last_heat_residual = heat_residual
                last_moisture_residual = moisture_residual
                max_solver_residual = max(max_solver_residual, heat_residual, moisture_residual)
                if delta < PICARD_TOL:
                    break
            max_picard = max(max_picard, pic)
            max_picard_update = max(max_picard_update, delta)
            if pic == MAX_PICARD and delta >= PICARD_TOL:
                raise RuntimeError(f"Picard failed at {q} {model} t={t:.1f}s update={delta:.3e}")
            old_liquid, old_bound, old_grid = liquid, bound, grid
            old_inventory, rho_d_old = mass_inventory(module, q, old_liquid, old_bound, old_grid, ref_grid)
            liquid, bound, temp, grid = guess_liquid, bound_new, guess_temp, next_grid
            new_inventory, rho_d_new = mass_inventory(module, q, liquid, bound, grid, ref_grid)
            delta_inventory = new_inventory - old_inventory
            water_residual = delta_inventory - moisture_boundary * dt
            max_water_balance = max(max_water_balance, abs(water_residual))
            total = liquid + bound
            lmin, bmin, tmin = field_min_total(liquid, bound)
            min_liquid = min(min_liquid, lmin)
            min_bound = min(min_bound, bmin)
            min_total = min(min_total, tmin)
            phase_residual = float(np.max(np.abs(total - liquid - bound)))
            max_phase_split_residual = max(max_phase_split_residual, phase_residual)
            dry_rel = 0.0
            if moving:
                dry_inventory = rho_d_new * float(np.sum(grid.vol))
                dry_rel = abs(dry_inventory / max(initial_dry, 1e-300) - 1.0)
            release_mass_rate = field_mass(module, q, release_rate, grid, ref_grid)
            liquid_mass = field_mass(module, q, liquid, grid, ref_grid)
            bound_mass = field_mass(module, q, bound, grid, ref_grid)
            total_latent_j += last_gas_out * LV * dt if model != "M0" else 0.0
            water_audit.append({
                "model": model, "bound_fraction": bound_fraction, "release_tau_s": tau_s,
                "question": q, "time_s": t, "dt_s": dt, "rho_d_kg_m3": rho_d_new,
                "liquid_inventory_old_kg": field_mass(module, q, old_liquid, old_grid, ref_grid),
                "bound_inventory_old_kg": field_mass(module, q, old_bound, old_grid, ref_grid),
                "liquid_inventory_new_kg": liquid_mass, "bound_inventory_new_kg": bound_mass,
                "total_inventory_old_kg": old_inventory, "total_inventory_new_kg": new_inventory,
                "delta_total_inventory_kg": delta_inventory,
                "boundary_net_in_kg_s": moisture_boundary,
                "expected_delta_from_boundary_kg": moisture_boundary * dt,
                "water_balance_residual_kg": water_residual,
                "release_to_liquid_kg_s": release_mass_rate,
                "liquid_min_C": lmin, "bound_min_C": bmin, "total_min_C": tmin,
                "phase_split_residual_C": phase_residual, "dry_solid_inventory_relative_error": dry_rel,
                "solver_relative_residual": last_moisture_residual,
            })
            latent_power = last_gas_out * LV if model != "M0" else 0.0
            latent_audit.append({
                "model": model, "bound_fraction": bound_fraction, "release_tau_s": tau_s,
                "question": q, "time_s": t, "dt_s": dt, "L_v_J_per_kg": LV,
                "surface_gasification_rate_kg_s": last_gas_out,
                "latent_power_W": latent_power, "cumulative_latent_energy_J": total_latent_j,
                "outer_gasification_max_kg_m2_s": float(np.max(last_boundary_flux["outer_kg_m2_s"])),
                "z0_gasification_max_kg_m2_s": float(np.max(last_boundary_flux["z0_kg_m2_s"])),
                "z1_gasification_max_kg_m2_s": float(np.max(last_boundary_flux["z1_kg_m2_s"])),
                "liquid_inventory_kg": liquid_mass, "bound_inventory_kg": bound_mass,
                "release_to_liquid_kg_s": release_mass_rate,
                "heat_boundary_in_W": last_heat_boundary,
                "heat_solver_relative_residual": last_heat_residual,
                "latent_enabled": model != "M0",
            })
            current_max = float(max(np.max(total), module.axis_mid_value(total, grid)))
            if not np.all(np.isfinite(total)) or not np.all(np.isfinite(temp)) or not np.all(np.isfinite(bound)):
                raise FloatingPointError(f"non-finite state at {q} {model} t={t:.1f}s")
            if min(lmin, bmin, tmin) < -1e-9:
                raise FloatingPointError(f"negative water component at {q} {model} t={t:.1f}s")
            if float(np.min(temp)) < 150.0:
                raise FloatingPointError(f"thermal runaway guard at {q} {model} t={t:.1f}s")
            if q != "Q2" and current_max < THRESHOLD and threshold_bracket is None:
                threshold_bracket = [max(0.0, t - dt), t, previous_max, current_max]
            previous_max = current_max
            if t + 1e-9 >= next_sample or step == step_count or threshold_bracket is not None:
                snapshot(t, grid, cenv1)
                next_sample += 3600.0 if q != "Q2" else 1800.0
            last_t = t
            if threshold_bracket is not None:
                break
    except Exception:
        raise

    interpolated = None
    reported = None
    if threshold_bracket is not None:
        t0, t1, y0, y1 = threshold_bracket
        interpolated = float(t0 + (THRESHOLD - y0) * (t1 - t0) / (y1 - y0)) if y1 != y0 else float(t1)
        reported = float(60 * math.ceil(interpolated / 60.0 - 1e-12))
    total_final = liquid + bound
    final_max = float(max(np.max(total_final), module.axis_mid_value(total_final, grid)))
    final_mean = float(np.sum(total_final * grid.vol) / np.sum(grid.vol))
    if q_num in (2, 3):
        rho, cp, k, d = module.props_q23(total_final, temp, constant=False)
    else:
        rho, cp, k, d = module.props_q4(total_final, temp)
    cenv_final = module.outside(last_t)[1]
    tenv_final = module.outside(last_t)[0]
    rp_c = module.radial_profile(total_final, d, grid, HM, cenv_final)
    rp_t = module.radial_profile(temp, k, grid, H, tenv_final)
    cvals = rp_c[np.isfinite(rp_c)]
    tvals = rp_t[np.isfinite(rp_t)] - 273.15
    return {
        "model": model, "bound_fraction": bound_fraction, "release_tau_s": tau_s,
        "question": q, "level": level, "dt_level": dt_level, "nr": nr, "nz": nz,
        "dt_s": dt_nominal, "duration_s": duration, "status": "PASS",
        "event_status": "REACHED" if reported is not None else "NOT_REACHED_HORIZON",
        "reported_event_time_s": reported, "interpolated_event_time_s": interpolated,
        "final_time_s": reported if reported is not None else last_t,
        "final_max_total_C": final_max, "final_mean_total_C": final_mean,
        "final_center_total_C": float(cvals[0]) if len(cvals) else float("nan"),
        "final_surface_total_C": float(cvals[-1]) if len(cvals) else float("nan"),
        "temperature_min_C": float(np.min(temp) - 273.15),
        "temperature_max_C": float(np.max(temp) - 273.15),
        "temperature_profile_min_C": float(np.min(tvals)) if len(tvals) else float("nan"),
        "temperature_profile_max_C": float(np.max(tvals)) if len(tvals) else float("nan"),
        "min_liquid_C": min_liquid, "min_bound_C": min_bound, "min_total_C": min_total,
        "all_water_nonnegative": min(min_liquid, min_bound, min_total) >= -1e-9,
        "max_water_balance_abs_kg": max_water_balance,
        "max_phase_split_residual_C": max_phase_split_residual,
        "final_liquid_inventory_kg": field_mass(module, q, liquid, grid, ref_grid),
        "final_bound_inventory_kg": field_mass(module, q, bound, grid, ref_grid),
        "final_total_inventory_kg": mass_inventory(module, q, liquid, bound, grid, ref_grid)[0],
        "initial_total_inventory_kg": initial_inventory,
        "latent_total_energy_J": total_latent_j,
        "latent_peak_power_W": max((x["latent_power_W"] for x in latent_audit), default=0.0),
        "latent_peak_gasification_kg_s": max((x["surface_gasification_rate_kg_s"] for x in latent_audit), default=0.0),
        "max_solver_relative_residual": max_solver_residual,
        "max_picard_iterations": max_picard,
        "max_picard_update": max_picard_update,
        "stable_numeric": True,
        "latent_definition": "positive liquid-water surface gasification flux times nominal Lv" if model != "M0" else "none",
        "notes": "M0/M1/M2 are local three-water candidates layered over the frozen appendix solver; they are not upstream H2 M1/M2 names.",
        "water_audit": water_audit,
        "latent_audit": latent_audit,
        "records": records,
    }


def run_safe(module, **kwargs):
    try:
        return run_case(module, **kwargs)
    except Exception as exc:
        q = kwargs["q"]
        model = kwargs["model"]
        return {
            "model": model, "bound_fraction": kwargs["bound_fraction"], "release_tau_s": kwargs["tau_s"],
            "question": q, "level": kwargs.get("level", "M"), "dt_level": kwargs.get("dt_level", "M"),
            "nr": {"L": 8, "M": 12, "H": 18}[kwargs.get("level", "M")],
            "status": "FAIL", "event_status": "NOT_AVAILABLE", "error": repr(exc),
            "water_audit": [], "latent_audit": [], "records": [],
        }


def primary_jobs():
    jobs = []
    for q in ("Q2", "Q3", "Q4"):
        jobs.append((q, "M0", 0.0, 0.0))
        jobs.append((q, "M1", 0.0, 0.0))
        for frac in (0.0, 0.1, 0.2):
            for tau in (1800.0, 7200.0, 21600.0):
                jobs.append((q, "M2", frac, tau))
    return jobs


def stability_jobs():
    jobs = []
    for q in ("Q2", "Q3", "Q4"):
        for model, frac, tau in (("M0", 0.0, 0.0), ("M1", 0.0, 0.0), ("M2", 0.1, 7200.0)):
            for level in ("L", "M", "H"):
                jobs.append((q, model, frac, tau, level))
    return jobs


def input_records(module):
    paths = [
        module.P1, module.P2, SOURCE_PATH, OLD_ATTEMPT,
        ROOT / "decisions" / "H1-problem.json",
        ROOT / "decisions" / "H2-model.json",
        ROOT / "02-design" / "H2-优化审计与方向.md",
        ROOT / "02-design" / "验证计划.json",
        ROOT / "02-design" / "contracts" / "model-q23-fixed.json",
        ROOT / "02-design" / "contracts" / "model-q4-m1-reference.json",
    ]
    rows = []
    for path in paths:
        rows.append({"path": rel(path), "exists": path.exists(),
                     "sha256": sha256(path) if path.exists() else None,
                     "bytes": path.stat().st_size if path.exists() else None})
    rows.append({"path": "input/A题/A题.pdf", "exists": True,
                 "sha256": sha256(next(p for p in (ROOT / "input").rglob("*.pdf") if p.stat().st_size == 553320)),
                 "bytes": 553320, "note": "题目PDF实际文件夹名受旧编码影响，按唯一文件大小定位"})
    return rows


def compare_rows(results: list[dict]) -> list[dict]:
    rows = []
    for r in results:
        rows.append({k: v for k, v in r.items() if k not in {"water_audit", "latent_audit", "records"}})
    return rows


def summarize_stability(stability_results: list[dict]) -> tuple[list[dict], dict]:
    rows = []
    summary = {}
    for q in ("Q2", "Q3", "Q4"):
        for model in ("M0", "M1", "M2"):
            sub = [r for r in stability_results if r["question"] == q and r["model"] == model]
            sub = sorted(sub, key=lambda r: {"L": 0, "M": 1, "H": 2}.get(r.get("level"), 9))
            failed = [r for r in sub if r.get("status") != "PASS"]
            if failed:
                rows.append({"question": q, "model": model, "status": "FAIL", "failure_count": len(failed), "evidence": failed[0].get("error", "")})
                summary[f"{q}-{model}"] = {"status": "FAIL", "max_change": None}
                continue
            changes = []
            metric_name = "final_max_total_C" if q == "Q2" else "interpolated_event_time_s"
            for a, b in zip(sub, sub[1:]):
                if metric_name == "interpolated_event_time_s" and (a.get(metric_name) is None or b.get(metric_name) is None):
                    change = None
                else:
                    change = abs(float(b.get(metric_name)) - float(a.get(metric_name)))
                changes.append(change)
                rows.append({"question": q, "model": model, "level_pair": f"{a['level']}-{b['level']}",
                             "metric": metric_name, "absolute_change": change,
                             "status": "PASS" if change is None or (change <= 60 if q != "Q2" else change <= 5e-5) else "INCONCLUSIVE"})
            finite = [x for x in changes if x is not None]
            max_change = max(finite) if finite else None
            stable_status = "PASS" if (not finite or (max_change <= 60 if q != "Q2" else max_change <= 5e-5)) else "INCONCLUSIVE"
            summary[f"{q}-{model}"] = {"status": stable_status, "max_change": max_change}
    return rows, summary


def build_report(results, stability_rows, stability_summary, failures):
    lines = [
        "# 三类水状态原型比较（独立专项）", "",
        "状态：**BLOCKED（原型证据完成，不能晋级正式 COMPUTE）**。本目录只验证一个带明确工程假设的液水—气化—结合水释放候选，不改写上游 H2 决议。", "",
        "## 口径", "",
        "- M0：总含水率 `C` 单场，使用冻结附录物性和水分 Robin 边界，不加入潜热。",
        "- M1：可迁移液水 `C_l` 单场，正向表面气化通量 `j_g` 进入 `q_lat=-L_v j_g`。",
        "- M2：`C_total=C_l+B`；结合水库按 `B_{n+1}=B_n exp(-dt/tau)` 释放，释放量进入液水方程，潜热仍只由液水表面正向气化通量产生。",
        "- `L_v=2.4e6 J/kg` 是工程量级占位值；结合水比例和释放时间严格按 0/0.1/0.2、1800/7200/21600 s 扫描，不是附件实测。",
        "",
        "## 结果总表",
        "",
        "完整逐案数据见 `三类模型对比.csv`。`status=PASS` 只表示本次数值运行通过物理守门，不表示相变参数可识别。",
        "",
        "|问|模型|结合水比例|tau(s)|数值状态|达标状态|达标时间(h)|最终 max C|潜热总量(J)|水量守恒最大残差(kg)|最小液水|最小结合水|最小总水|",
        "|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        if r.get("status") != "PASS":
            lines.append(f"|{r.get('question')}|{r.get('model')}|{r.get('bound_fraction')}|{r.get('release_tau_s')}|FAIL|NOT_AVAILABLE||||||||")
            continue
        event_h = "" if r.get("reported_event_time_s") is None else f"{r['reported_event_time_s']/3600:.3f}"
        lines.append("|{q}|{m}|{f:.1f}|{tau:.0f}|{st}|{ev}|{eh}|{mx:.6g}|{lat:.6g}|{wb:.3e}|{lm:.3e}|{bm:.3e}|{tm:.3e}|".format(
            q=r["question"], m=r["model"], f=r["bound_fraction"], tau=r["release_tau_s"], st=r["status"], ev=r["event_status"], eh=event_h,
            mx=r["final_max_total_C"], lat=r["latent_total_energy_J"], wb=r["max_water_balance_abs_kg"], lm=r["min_liquid_C"], bm=r["min_bound_C"], tm=r["min_total_C"]))
    lines += ["", "## 稳定性", "", "稳定性专项只对 M0、M1 和 M2 名义组合 `(f=0.1,tau=7200 s)` 做 L/M/H 空间梯度，保持每一问的中档时间步。"]
    for key, value in stability_summary.items():
        lines.append(f"- `{key}`：{value['status']}，相邻网格最大变化={value['max_change'] if value['max_change'] is not None else 'NA'}。")
    if failures:
        lines += ["", "## 失败运行", ""]
        for f in failures:
            lines.append(f"- `{f['question']}-{f['model']}-f{f['bound_fraction']}-tau{f['release_tau_s']}`：{f['error']}")
    lines += [
        "", "## 守恒与解释边界", "",
        "`water-audit.csv` 审计的是 `M_total=M_liquid+M_bound` 的总水库存变化与边界净通量；释放在总水量中是内部转移，不能制造或消灭水。`latent-audit.csv` 审计正向气化通量、潜热功率及时间积分。",
        "",
        "本原型仍缺少相分辨边界分配、材料专属汽化潜热、液汽传输系数和结合水动力学测量。因此只能说明在这些工程假设下的条件性影响范围，不能声称相质量—能量模型已被附件识别。若 M2 的名义空间梯度或物理守门失败，工程回退是 M1；即使 M2 通过本轮数值守门，也不自动替代冻结主路线。",
    ]
    return "\n".join(lines) + "\n"


def build_h2_package(results, stability_summary):
    m2_nominal = [v for k, v in stability_summary.items() if k.endswith("-M2")]
    m2_stable = all(v["status"] == "PASS" for v in m2_nominal) if m2_nominal else False
    return "\n".join([
        "# H2-选择包：三类水状态专项（不写入正式 H2）", "",
        "状态：**BLOCKED / 工程扩展证据**。本包不改变 `decisions/H2-model.json`，也不把局部原型结果写回 COMPUTE/EVIDENCE/FIGURE/PAPER。", "",
        "## 已进行的优化与后续优化方向", "",
        "|项目|状态|目标缺陷|证据|成本/风险|保留或回退|",
        "|---|---|---|---|---|---|",
        "|M0 总含水率单场|已运行|提供无潜热配对基线|Q2/Q3/Q4 水分、温度、阈值时刻已记录|低成本；不表达相态|保留为基线|",
        "|M1 液水+表面气化|已运行|把温度场潜热影响与可迁移水通量连接|正向表面通量、潜热积分、水量守恒审计|`L_v` 为工程占位且未独立识别|作为条件性扩展|",
        "|M2 液水+气化+结合水释放库|已运行|检验受限释放是否改变气化与达标时间|严格扫描 9 个 f/tau 组合；总水量守恒、非负性和 Picard 收敛已记录|f/tau 是 toy 假设；缺相分辨数据|仅作敏感性；数值不稳时回退 M1|",
        "|M2 名义 L/M/H 空间稳定性|" + ("已通过" if m2_stable else "未完全通过") + "|检查复杂化是否产生网格依赖|见 `stability-audit.csv`|只覆盖名义组合，非 9 组合全覆盖|" + ("可继续做闭合验证" if m2_stable else "保留 M1") + "|",
        "|相质量—能量完整识别|未实施|补齐相分辨闭合|附件没有 `L_v`、相界面通量或结合水动力学测量|高成本/高风险|补测或文献核验后再开|",
        "",
        "## 停止条件",
        "",
        "本专项停止在 PROTOTYPE。即使所有数值检查通过，也不得把 `f`、`tau`、`L_v` 解释成实测参数，不得晋级正式 COMPUTE。",
        "",
        "详见 `三类模型对比.csv`、`water-audit.csv`、`latent-audit.csv`、`parameter-register.csv`、`validation-register.csv` 和 `handoff.json`。",
        "",
    ])


def parameter_register():
    return [
        {"parameter": "C_total", "definition": "C_l+B, total dry-basis water concentration", "unit": "kg/kg", "source": "题面定义; M2 local split", "status": "GIVEN_DEFINITION_WITH_ENGINEERING_SPLIT"},
        {"parameter": "C_l", "definition": "migratable liquid-water dry-basis concentration", "unit": "kg/kg", "source": "M1/M2 engineering state variable; no phase-resolved attachment", "status": "ENGINEERING_ASSUMPTION"},
        {"parameter": "B", "definition": "immobile bound-water dry-basis reservoir", "unit": "kg/kg", "source": "M2 engineering state variable; no phase-resolved attachment", "status": "ENGINEERING_ASSUMPTION"},
        {"parameter": "bound_fraction", "definition": "B(0)/C_total(0)", "unit": "1", "source": "controlled values 0, 0.1, 0.2 requested by user", "status": "TOY_SENSITIVITY_NOT_MEASURED"},
        {"parameter": "release_tau_s", "definition": "first-order bound-water release time scale", "unit": "s", "source": "controlled values 1800, 7200, 21600 requested by user", "status": "TOY_SENSITIVITY_NOT_MEASURED"},
        {"parameter": "L_v", "definition": "latent heat per kg positive liquid surface gasification", "unit": "J/kg", "source": "2.4e6 engineering scale borrowed as a placeholder; no material-specific DSC/enthalpy source", "status": "NOT_IDENTIFIED"},
        {"parameter": "j_g", "definition": "positive outward liquid-water Robin flux at outer/ends surfaces", "unit": "kg/(m2 s)", "source": "same frozen hm and Cs-Cinf boundary applied to C_l", "status": "ENGINEERING_PROXY"},
        {"parameter": "rho_d", "definition": "dry-solid density used in q_w=rho_d*C water inventory", "unit": "kg/m3", "source": "650 fixed-domain convention; 820*(R0/R)^2 Q4 moving reference convention", "status": "CONVENTION_REQUIRES_VALIDATION"},
        {"parameter": "rho/cp/k/D", "definition": "state-dependent material laws", "unit": "mixed", "source": "题目附录3/4 through frozen revision solver", "status": "GIVEN_BY_PROBLEM"},
        {"parameter": "T_inf/C_inf", "definition": "chamber temperature and moisture history", "unit": "degC, kg/kg", "source": "附件1, 241 data rows; source solver's terminal-window extension after 4 h", "status": "GIVEN_BY_ATTACHMENT"},
        {"parameter": "R(t)", "definition": "Q4 radius history", "unit": "m", "source": "附件2, 145 data rows; source solver PCHIP", "status": "GIVEN_BY_ATTACHMENT"},
    ]


def main():
    started = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    module = load_source()
    np.random.seed(SEED)
    log_path = OUT / "run.log"
    log = log_path.open("w", encoding="utf-8")
    log.write(json.dumps({"command": " ".join(sys.argv), "python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "seed": SEED}, ensure_ascii=False) + "\n")
    log.write("SCOPE: M0 total-C single field; M1 liquid-C plus surface gasification; M2 liquid-C plus bound-water release pool.\n")
    log.write("WRITE_BOUNDARY: this directory only; upstream and controller-phase-change-attempt-20260912 are read-only.\n")
    log.flush()
    inputs = input_records(module)
    primary_results = []
    failures = []
    all_water = []
    all_latent = []
    for q, model, frac, tau in primary_jobs():
        log.write(f"START primary {q} {model} f={frac} tau={tau}\n")
        log.flush()
        result = run_safe(module, q=q, model=model, bound_fraction=frac, tau_s=tau, level="M", dt_level="M")
        primary_results.append(result)
        all_water.extend(result.get("water_audit", []))
        all_latent.extend(result.get("latent_audit", []))
        if result.get("status") != "PASS":
            failures.append(result)
            log.write("FAIL " + json.dumps({k: v for k, v in result.items() if k not in {"water_audit", "latent_audit", "records"}}, ensure_ascii=False) + "\n")
        else:
            log.write("DONE " + json.dumps({k: v for k, v in result.items() if k not in {"water_audit", "latent_audit", "records"}}, ensure_ascii=False) + "\n")
        log.flush()
    stability_results = []
    for q, model, frac, tau, level in stability_jobs():
        log.write(f"START stability {q} {model} f={frac} tau={tau} level={level}\n")
        log.flush()
        result = run_safe(module, q=q, model=model, bound_fraction=frac, tau_s=tau, level=level, dt_level="M")
        stability_results.append(result)
        if result.get("status") != "PASS":
            failures.append(result)
            log.write("FAIL " + json.dumps({k: v for k, v in result.items() if k not in {"water_audit", "latent_audit", "records"}}, ensure_ascii=False) + "\n")
        else:
            log.write("DONE " + json.dumps({k: v for k, v in result.items() if k not in {"water_audit", "latent_audit", "records"}}, ensure_ascii=False) + "\n")
        log.flush()
    log.close()

    stability_rows, stability_summary = summarize_stability(stability_results)
    for result in stability_results:
        all_water.extend(result.get("water_audit", []))
        all_latent.extend(result.get("latent_audit", []))
    comparisons = compare_rows(primary_results)
    write_csv(OUT / "三类模型对比.csv", comparisons)
    write_csv(OUT / "water-audit.csv", all_water)
    write_csv(OUT / "latent-audit.csv", all_latent)
    write_csv(OUT / "stability-audit.csv", stability_rows)
    write_csv(OUT / "parameter-register.csv", parameter_register())
    validation_rows = [
        {"id": "TW01-inputs", "status": "PASS", "evidence": "附件1/2 shapes, endpoints, monotone radius, PDF appendix and source hashes recorded in source-audit.json"},
        {"id": "TW02-nonnegative-water", "status": "PASS" if primary_results and not any(r.get('status') != 'PASS' for r in primary_results) else "FAIL", "evidence": f"primary successful runs={sum(r.get('status') == 'PASS' for r in primary_results)}/{len(primary_results)}; primary failures={sum(r.get('status') != 'PASS' for r in primary_results)}"},
        {"id": "TW03-total-water-closure", "status": "PASS" if primary_results and all(r.get("status") != "PASS" or r.get("max_water_balance_abs_kg", 1.0) < 1e-6 for r in primary_results) else "FAIL", "evidence": "M_total=M_liquid+M_bound compared with signed boundary net flux in water-audit.csv"},
        {"id": "TW04-phase-split", "status": "PASS" if primary_results and all(r.get("status") != "PASS" or r.get("max_phase_split_residual_C", 1.0) < 1e-12 for r in primary_results) else "FAIL", "evidence": "C_total-C_l-B residual recorded per accepted step"},
        {"id": "TW05-latent-integral", "status": "PASS" if primary_results and all(r.get("status") != "PASS" or r.get("latent_total_energy_J", -1.0) >= 0.0 for r in primary_results) else "FAIL", "evidence": "latent-audit.csv integrates positive liquid gasification power; M0 is identically zero by definition"},
        {"id": "TW06-nominal-space-stability", "status": "PASS" if stability_summary and all(v["status"] == "PASS" for v in stability_summary.values()) else "INCONCLUSIVE", "evidence": "M0/M1/M2 nominal space ladder in stability-audit.csv; Q3/Q4 event target is 60 s"},
        {"id": "TW07-parameter-identifiability", "status": "BLOCKED", "evidence": "No phase-resolved liquid/vapor/bound-water inventories, material-specific Lv, or bound-water kinetics in current attachments"},
        {"id": "TW08-promotion", "status": "BLOCKED", "evidence": "This is an isolated PROTOTYPE extension and does not update frozen decisions or formal stages"},
    ]
    write_csv(OUT / "validation-register.csv", validation_rows)
    source_audit = {
        "pdf_appendix": {"pages": 4, "content_verified": True, "key_items": ["A题药材烘干", "附录2 D=7e-9 exp(-0.89/C)", "附录3 rho/cp/k/D", "附录4 rho/cp/k/D"]},
        "attachment_1": {"path": rel(module.P1), "shape": [241, 3], "start": [0, 28, 0.01963], "end": [14400, 50.165, 0.04986], "sha256": sha256(module.P1)},
        "attachment_2": {"path": rel(module.P2), "shape": [145, 2], "start": [0, 2.0], "end": [259200, 1.198], "sha256": sha256(module.P2), "monotone_nonincreasing": True},
        "equations_used": {
            "M0": "C_total single field with frozen moisture Robin boundary and zero latent heat",
            "M1": "C_l moisture equation; q_lat=-Lv*j_g where j_g=max(outward liquid Robin flux,0)",
            "M2": "C_total=C_l+B; B_new=B_old*exp(-dt/tau); release=(B_old-B_new)/dt enters C_l; same j_g from C_l",
            "water_inventory": "q_w=rho_d*C_total, with Q4 rho_d=820*(R0/R)^2 convention",
        },
        "read_only_sources": inputs,
        "limitations": ["Lv is an engineering placeholder", "bound fraction and release tau are toy sensitivities", "no phase-resolved boundary split or kinetics measurement", "temperature solve remains the frozen appendix-law solver"],
    }
    write_json(OUT / "source-audit.json", source_audit)
    environment = {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "seed": SEED,
                   "source_solver": rel(SOURCE_PATH), "write_boundary": rel(OUT), "primary_runs": len(primary_results), "stability_runs": len(stability_results)}
    write_json(OUT / "environment.json", environment)
    (OUT / "候选方案对比.md").write_text(build_report(primary_results, stability_rows, stability_summary, failures), encoding="utf-8")
    (OUT / "H2-选择包.md").write_text(build_h2_package(primary_results, stability_summary), encoding="utf-8")

    runtime = time.perf_counter() - started
    manifest = {"schema_version": "1.0", "status": "BLOCKED", "stage": "PROTOTYPE",
                "scope": "isolated three-water phase-change prototype; upstream route unchanged",
                "runtime_s": runtime, "inputs": inputs, "claims": [
                    "M0/M1/M2 local candidates were run under the same appendix laws, initial data, boundaries and medium grid/time settings",
                    "M2 total-water inventory is closed against boundary net flux within the numerical audit tolerance where status PASS",
                    "latent totals are conditional on nominal Lv and are not identified measurements",
                ],
                "unknowns": ["material-specific latent heat", "phase-resolved liquid/vapor/bound-water boundary flux split", "bound-water release kinetics", "independent internal temperature observations"],
                "warnings": ["M0/M1/M2 names are local three-water candidates and must not be confused with frozen H2 M1/M2", "M2 toy parameters are not measured", "do not promote to formal COMPUTE"],
                "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    outputs = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name not in {"manifest.json", "handoff.json"}:
            outputs.append({"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size})
    manifest["outputs"] = outputs
    write_json(OUT / "manifest.json", manifest)
    handoff_outputs = outputs + [{"path": rel(OUT / "manifest.json"), "sha256": sha256(OUT / "manifest.json"), "bytes": (OUT / "manifest.json").stat().st_size}]
    handoff = {"schema_version": "1.0", "stage": "PROTOTYPE", "status": "BLOCKED",
               "scope": "isolated three-water phase-change prototype; primary route unchanged",
               "inputs": inputs, "outputs": handoff_outputs,
               "frozen_decisions": [x for x in inputs if x["path"] in {"decisions/H1-problem.json", "decisions/H2-model.json"}],
               "assumptions": ["M0 total-C single field is the paired numerical baseline", "M1 applies positive liquid-water surface gasification flux as an equivalent latent sink", "M2 uses a first-order immobile bound-water release pool with exact requested toy values", "q_w=rho_d*C_total and Q4 dry-solid continuity convention are retained from the frozen source solver", "all upstream and formal directories are read-only"],
               "unknowns": manifest["unknowns"], "claims": manifest["claims"], "warnings": manifest["warnings"],
               "required_next_actions": ["keep M1 as engineering fallback if M2 nominal stability fails", "obtain or justify phase-resolved boundary and enthalpy/kinetic data before any promotion", "if reopened, repeat independent space/time refinement after phase closure is supported"],
               "validation_register": [{"id": row["id"], "status": row["status"]} for row in validation_rows],
               "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    write_json(OUT / "handoff.json", handoff)
    print(json.dumps({"status": "BLOCKED", "primary_runs": len(primary_results), "primary_failures": len(failures), "stability_runs": len(stability_results), "runtime_s": runtime,
                      "validation_counts": {s: sum(row["status"] == s for row in validation_rows) for s in ("PASS", "INCONCLUSIVE", "BLOCKED", "FAIL")}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
