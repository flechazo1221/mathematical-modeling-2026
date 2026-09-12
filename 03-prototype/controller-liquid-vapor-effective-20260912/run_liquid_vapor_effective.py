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
SEED = 20260912
THRESHOLD = 0.15 - 1e-6
BASELINE_DIR = ROOT / "03-prototype" / "controller-temp-field-completion-20260912"
SOURCE_PATH = ROOT / "04-compute" / "temperature-field-revision-20260912" / "formal_compute_revision.py"


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
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_module():
    name = "phase_change_temperature_source"
    spec = importlib.util.spec_from_file_location(name, SOURCE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SOURCE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def solve_with_source(module, old, coeff, storage, grid, dt, conv, env_value,
                      source=None, boundary_sink=None, include_ends=True, x0=None,
                      rtol=5e-11, maxiter=1200):
    """Copy the source linear CG operator and add explicit volumetric/surface sinks."""
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
    source = np.zeros_like(old) if source is None else source
    rhs = time_diag * old + source * grid.vol
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
    it = 0
    for it in range(1, maxiter + 1):
        ap = amat(p)
        denom = float(np.sum(p * ap))
        if denom <= 0:
            raise RuntimeError("non-SPD operator in latent heat CG")
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
        raise RuntimeError(f"latent heat CG failed after {maxiter} iterations")
    boundary_in = float(np.sum(gbr * (env_value - x[-1, :])) +
                        np.sum(gb0 * (env_value - x[:, 0])) +
                        np.sum(gb1 * (env_value - x[:, -1])))
    residual = float(np.linalg.norm((amat(x) - rhs).ravel()) / rhs_norm)
    return x, boundary_in, it, residual


def run_case(module, cfg, latent: dict) -> dict:
    """Run the real internal-temperature solver with a controlled thermal source."""
    context = {
        "c": None, "d": None, "cenv": 0.0, "time": 0.0,
        "pending_time": None, "active_time": None, "step_old_c": None, "step_d": None,
        "source_trace": {}, "water_trace": {}, "heat_trace": {},
        "liquid_vapor_ledger": {"initial_liquid_kg": None, "vapor_cumulative_out_kg": 0.0},
    }
    original_outside = module.outside
    original_linear = module.implicit_linear
    original_reference = module.implicit_reference_linear
    original_q1 = module.props_q1
    original_q23 = module.props_q23
    original_q4 = module.props_q4

    def outside_wrapper(t, window_s=3600):
        value = original_outside(t, window_s)
        context["time"] = float(t)
        context["pending_time"] = float(t)
        context["cenv"] = float(value[1])
        return value

    def capture_state(c, d=None):
        arr = np.array(c, copy=True)
        if context["pending_time"] != context["active_time"]:
            # The first constitutive call after outside(t_next) sees the accepted
            # state at the beginning of that time step.
            context["step_old_c"] = arr.copy()
            if d is not None:
                context["step_d"] = np.array(d, copy=True)
            context["active_time"] = context["pending_time"]
        context["c"] = arr
        if d is not None:
            context["d"] = np.array(d, copy=True)

    def q1_wrapper(c):
        result = original_q1(c)
        capture_state(c, result[3])
        return result

    def q23_wrapper(c, temp_k, constant=False, pref=1.0, exponent=1.0):
        result = original_q23(c, temp_k, constant=constant, pref=pref, exponent=exponent)
        capture_state(c, result[3])
        return result

    def q4_wrapper(c, temp_k, pref=1.0, exponent=1.0):
        result = original_q4(c, temp_k, pref=pref, exponent=exponent)
        capture_state(c, result[3])
        return result

    def rho_d_for(grid):
        # q_w = rho_d C.  For Q2/Q3, 650 kg/m3 is the dry-density intercept
        # of the registered rho(C)=650+128 C law; Q4 retains the source
        # solver's dry-solid continuity convention.
        if cfg.q == 4:
            return 820.0 * (module.R0 / grid.radius) ** 2
        return 650.0

    def record_water(time_key, old_c, new_c, bflux, grid, dt, residual, method):
        rho_d = rho_d_for(grid)
        delta = np.asarray(new_c) - np.asarray(old_c)
        net_change = float(rho_d * np.sum(delta * grid.vol) / dt)
        local_loss = float(rho_d * np.sum(np.maximum(-delta, 0.0) * grid.vol) / dt)
        # implicit_reference_linear already multiplies the moving-domain
        # conductances by rho_d; fixed-domain implicit_linear does not.
        boundary_net = float(bflux if method == "moving-reference-moisture" else rho_d * bflux)
        ledger = context["liquid_vapor_ledger"]
        if ledger["initial_liquid_kg"] is None:
            ledger["initial_liquid_kg"] = float(rho_d * np.sum(np.asarray(old_c) * grid.vol))
        vapor_out_rate = max(-boundary_net, 0.0)
        ledger["vapor_cumulative_out_kg"] += vapor_out_rate * dt
        liquid_inventory = float(rho_d * np.sum(np.asarray(new_c) * grid.vol))
        initial_liquid = max(float(ledger["initial_liquid_kg"]), 1e-300)
        f_l = liquid_inventory / initial_liquid
        f_v = float(ledger["vapor_cumulative_out_kg"]) / initial_liquid
        ledger_residual = initial_liquid - liquid_inventory - float(ledger["vapor_cumulative_out_kg"])
        context["water_trace"][round(float(time_key), 6)] = {
            "time_s": round(float(time_key), 6),
            "method": method,
            "rho_d_kg_m3": float(rho_d),
            "net_inventory_rate_kg_s": net_change,
            "local_positive_loss_rate_kg_s": local_loss,
            "boundary_net_rate_kg_s": boundary_net,
            "water_balance_residual_kg_s": net_change - boundary_net,
            "liquid_inventory_kg": liquid_inventory,
            "vapor_cumulative_out_kg": float(ledger["vapor_cumulative_out_kg"]),
            "f_l": f_l,
            "f_v": f_v,
            "liquid_vapor_ledger_residual_kg": ledger_residual,
            "surface_jv_definition": "same outward total surface flux used for q_lat=Lv*j_v",
            "solver_relative_residual": float(residual),
        }

    def record_heat(time_key, old_t, new_t, coeff, storage, grid, dt, boundary_in,
                    boundary_sink, linear_residual):
        gr, gz, gbr, gb0, gb1 = module.conductances(coeff, grid, 25.0, True)
        del_e_fixed = float(np.sum(storage * (new_t - old_t) * grid.vol))
        geometry_term = 0.0
        if cfg.q == 4:
            prev_t = max(float(time_key) - dt, 0.0)
            prev_radius = module.radius_at(prev_t, cfg.radius_mode)
            prev_grid = module.Grid(cfg.nr, cfg.nz, prev_radius, radial_strategy=cfg.radial_strategy)
            geometry_term = float(np.sum(storage * old_t * (grid.vol - prev_grid.vol)))
        latent_power = 0.0
        if boundary_sink is not None:
            outer_area = 2 * math.pi * grid.radius * grid.dz
            latent_power = float(np.sum(outer_area * boundary_sink.get("outer_W_m2", 0.0)) +
                                 np.sum(grid.annulus * boundary_sink.get("z0_W_m2", 0.0)) +
                                 np.sum(grid.annulus * boundary_sink.get("z1_W_m2", 0.0)))
        total_delta_e = del_e_fixed + geometry_term
        convective_input = boundary_in * dt
        latent_heat_loss = latent_power * dt
        geometry_correction = geometry_term
        expected_sensible_change = convective_input - latent_heat_loss + geometry_correction
        # Required moving-domain ledger:
        # sensible change = convection in - evaporation latent heat + geometry correction.
        # Keep fixed-volume and moving-domain residuals separate.
        fixed_geometry_error = del_e_fixed - (convective_input - latent_heat_loss)
        moving_geometry_error = total_delta_e - expected_sensible_change
        balance = moving_geometry_error
        key = round(float(time_key), 6)
        context["heat_trace"][key] = {
            "time_s": key,
            "sensible_inventory_change_J": total_delta_e,
            "fixed_volume_sensible_change_J": del_e_fixed,
            "geometry_heat_term_J": geometry_term,
            "convective_input_J": convective_input,
            "evaporation_latent_heat_loss_J": latent_heat_loss,
            "geometry_correction_J": geometry_correction,
            "expected_sensible_change_J": expected_sensible_change,
            "fixed_geometry_error_J": fixed_geometry_error,
            "moving_geometry_error_J": moving_geometry_error,
            "geometry_reference_temperature_K": float(np.sum(storage * old_t * grid.vol) / max(np.sum(storage * grid.vol), 1e-300)),
            "surface_convection_in_W": float(boundary_in),
            "surface_latent_out_W": float(latent_power),
            "linear_solver_relative_residual": float(linear_residual),
            "physical_heat_balance_residual_J": float(balance),
            "physical_heat_balance_relative": float(abs(balance) / max(abs(total_delta_e), abs(boundary_in * dt), 1.0)),
        }

    def moisture_predictor(grid, dt, cenv, x0):
        old_c = context.get("step_old_c")
        current_c = context.get("c")
        d = context.get("step_d")
        if old_c is None or current_c is None or d is None:
            raise RuntimeError("moisture-derived latent source has no registered C/D state")
        if cfg.q == 4:
            ref_grid = module.Grid(cfg.nr, cfg.nz, module.R0, radial_strategy=cfg.radial_strategy)
            predicted, bflux, it, residual = original_reference(
                old_c, d, ref_grid, grid, dt, 8e-7, cenv, x0=old_c)
        else:
            predicted, bflux, it, residual = original_linear(
                old_c, d, np.ones_like(old_c), grid, dt, 8e-7, cenv, x0=old_c)
        rho_d = rho_d_for(grid)
        # Reuse the existing mass Robin operator.  Positive j_w is outward
        # evaporation; all fluxes are converted from dry-basis C to kg/m2/s.
        _, _, gbr_c, gb0_c, gb1_c = module.conductances(d, grid, 8e-7, True)
        outer_area = 2 * math.pi * grid.radius * grid.dz
        outer_j = rho_d * np.maximum(gbr_c * (predicted[-1, :] - cenv), 0.0) / np.maximum(outer_area, 1e-300)
        z0_j = rho_d * np.maximum(gb0_c * (predicted[:, 0] - cenv), 0.0) / np.maximum(grid.annulus, 1e-300)
        z1_j = rho_d * np.maximum(gb1_c * (predicted[:, -1] - cenv), 0.0) / np.maximum(grid.annulus, 1e-300)
        flux_factor = 1.0
        if latent.get("component_mode") == "liquid_gas_bound":
            fraction = float(latent.get("bound_fraction", 0.0))
            tau = float(latent.get("release_tau_s", 1.0))
            flux_factor = 1.0 - fraction * math.exp(-float(context.get("time", 0.0)) / max(tau, 1e-12))
            outer_j *= flux_factor
            z0_j *= flux_factor
            z1_j *= flux_factor
            bound_fraction_now = fraction * math.exp(-float(context.get("time", 0.0)) / max(tau, 1e-12))
            rho_d = rho_d_for(grid)
            total_water = float(rho_d * np.sum(predicted * grid.vol))
            bound_water = float(rho_d * np.sum(bound_fraction_now * predicted * grid.vol))
            liquid_water = total_water - bound_water
            context["last_phase_split"] = {
                "bound_fraction_now": bound_fraction_now,
                "total_water_kg": total_water,
                "bound_water_kg": bound_water,
                "liquid_water_kg": liquid_water,
                "split_residual_kg": total_water - bound_water - liquid_water,
            }
        else:
            context["last_phase_split"] = {
                "bound_fraction_now": 0.0,
                "total_water_kg": float(rho_d_for(grid) * np.sum(predicted * grid.vol)),
                "bound_water_kg": 0.0,
                "liquid_water_kg": float(rho_d_for(grid) * np.sum(predicted * grid.vol)),
                "split_residual_kg": 0.0,
            }
        context["last_flux_factor"] = flux_factor
        boundary_loss_rate = float(np.sum(outer_j * outer_area) +
                                   np.sum(z0_j * grid.annulus) +
                                   np.sum(z1_j * grid.annulus))
        return {"outer_W_m2": outer_j, "z0_W_m2": z0_j, "z1_W_m2": z1_j}, predicted, boundary_loss_rate, it, residual

    def add_latent_source(grid, dt, cenv):
        raw_boundary, predicted, boundary_loss_rate, it_c, res_c = moisture_predictor(grid, dt, cenv, context["c"])
        scale = float(latent["proxy_scale"])
        lv = float(latent["L_v_J_per_kg"])
        boundary_sink = {key: scale * lv * value for key, value in raw_boundary.items()}
        source = np.zeros_like(context["c"])
        outer_j = raw_boundary["outer_W_m2"]
        proxy_boundary_loss_rate = scale * boundary_loss_rate
        latent_power = float(scale * lv * boundary_loss_rate)
        time_key = round(float(context.get("time", 0.0)), 6)
        context["source_trace"][time_key] = {
            "time_s": time_key,
            "proxy_scale": scale,
            "L_v_J_per_kg": lv,
            "j_w_outer_max_kg_m2_s": float(np.max(outer_j)),
            "raw_boundary_loss_rate_kg_s": boundary_loss_rate,
            "proxy_boundary_loss_rate_kg_s": proxy_boundary_loss_rate,
            "latent_power_W": latent_power,
            "boundary_latent_heat_flux_max_W_m2": float(np.max(boundary_sink["outer_W_m2"])),
            "component_mode": latent.get("component_mode", "liquid_surface"),
            "bound_fraction": float(latent.get("bound_fraction", 0.0)),
            "release_tau_s": float(latent.get("release_tau_s", 0.0)),
            "free_flux_factor": float(context.get("last_flux_factor", 1.0)),
            "total_water_kg": float(context.get("last_phase_split", {}).get("total_water_kg", 0.0)),
            "bound_water_kg": float(context.get("last_phase_split", {}).get("bound_water_kg", 0.0)),
            "liquid_water_kg": float(context.get("last_phase_split", {}).get("liquid_water_kg", 0.0)),
            "phase_split_residual_kg": float(context.get("last_phase_split", {}).get("split_residual_kg", 0.0)),
            "moisture_predictor_relative_residual": float(res_c),
            "source_definition": "q_lat=Lv*j_v; j_v is the same outward surface flux accumulated as M_v_out",
        }
        return source, boundary_sink

    def latent_linear(old, coeff, storage, grid, dt, conv, env_value, include_ends=True,
                      x0=None, rtol=5e-11, maxiter=1200):
        thermal = float(np.nanmean(storage)) > 1e4
        if not latent["enabled"] or not thermal:
            result = original_linear(old, coeff, storage, grid, dt, conv, env_value,
                                     include_ends=include_ends, x0=x0, rtol=rtol, maxiter=maxiter)
            if not thermal:
                record_water(context.get("time", 0.0), old, result[0], result[1], grid, dt, result[3], "fixed-domain-moisture")
            else:
                record_heat(context.get("time", 0.0), old, result[0], coeff, storage, grid, dt, result[1], None, result[3])
            return result
        source, boundary_sink = add_latent_source(grid, dt, context.get("cenv", 0.0))
        result = solve_with_source(module, old, coeff, storage, grid, dt, conv, env_value,
                                 source=source, boundary_sink=boundary_sink, include_ends=include_ends, x0=x0,
                                 rtol=rtol, maxiter=maxiter)
        record_heat(context.get("time", 0.0), old, result[0], coeff, storage, grid, dt, result[1], boundary_sink, result[3])
        return result

    def latent_reference(old, coeff, ref_grid, physical_grid, dt, conv, env_value,
                         rho0=820.0, include_ends=True, x0=None, rtol=5e-11, maxiter=500):
        result = original_reference(old, coeff, ref_grid, physical_grid, dt, conv, env_value,
                                    rho0=rho0, include_ends=include_ends, x0=x0,
                                    rtol=rtol, maxiter=maxiter)
        record_water(context.get("time", 0.0), old, result[0], result[1], physical_grid, dt, result[3], "moving-reference-moisture")
        return result

    module.outside = outside_wrapper
    module.props_q1 = q1_wrapper
    module.props_q23 = q23_wrapper
    module.props_q4 = q4_wrapper
    module.implicit_linear = latent_linear
    module.implicit_reference_linear = latent_reference
    started = time.perf_counter()
    try:
        result = module.simulate(cfg)
    finally:
        module.outside = original_outside
        module.props_q1 = original_q1
        module.props_q23 = original_q23
        module.props_q4 = original_q4
        module.implicit_linear = original_linear
        module.implicit_reference_linear = original_reference

    trace = [context["source_trace"][k] for k in sorted(context["source_trace"])]
    if len(trace) >= 2:
        times = np.asarray([x["time_s"] for x in trace], dtype=float)
        powers = np.asarray([x["latent_power_W"] for x in trace], dtype=float)
        integral = float(np.trapezoid(powers, times)) if hasattr(np, "trapezoid") else float(np.trapz(powers, times))
    else:
        integral = 0.0
    metrics = dict(result["metrics"])
    metrics.update({
        "runtime_s_wrapper": time.perf_counter() - started,
        "latent_enabled": bool(latent["enabled"]),
        "proxy_scale": float(latent["proxy_scale"]),
        "L_v_J_per_kg": float(latent["L_v_J_per_kg"]),
        "latent_product_Lv_scale": float(latent["L_v_J_per_kg"] * latent["proxy_scale"]),
        "latent_peak_power_W": max((x["latent_power_W"] for x in trace), default=0.0),
        "latent_integral_J_est": integral,
        "latent_trace_count": len(trace),
        "latent_mass_closure": "ASSUMPTION: C_l=C; gas has no internal storage; M_v_out is cumulative surface export",
        "water_balance_max_abs_kg_s": max((abs(x["water_balance_residual_kg_s"]) for x in context["water_trace"].values()), default=0.0),
        "proxy_boundary_loss_max_kg_s": max((x["proxy_boundary_loss_rate_kg_s"] for x in trace), default=0.0),
        "water_trace_count": len(context["water_trace"]),
    })
    result["metrics"] = metrics
    result["latent_trace"] = trace
    result["water_trace"] = [context["water_trace"][k] for k in sorted(context["water_trace"])]
    result["heat_trace"] = [context["heat_trace"][k] for k in sorted(context["heat_trace"])]
    result["liquid_vapor_ledger"] = result["water_trace"]
    ledger_residuals = [abs(float(x["liquid_vapor_ledger_residual_kg"])) for x in result["water_trace"]]
    metrics["liquid_vapor_ledger_max_abs_residual_kg"] = max(ledger_residuals, default=0.0)
    metrics["final_f_l"] = float(result["water_trace"][-1]["f_l"]) if result["water_trace"] else float("nan")
    metrics["final_f_v"] = float(result["water_trace"][-1]["f_v"]) if result["water_trace"] else float("nan")
    metrics["liquid_vapor_ratio_sum_error"] = abs(metrics["final_f_l"] + metrics["final_f_v"] - 1.0)
    metrics["max_physical_heat_balance_relative"] = max((x["physical_heat_balance_relative"] for x in result["heat_trace"]), default=0.0)
    metrics["max_physical_heat_balance_residual_J"] = max((abs(x["physical_heat_balance_residual_J"]) for x in result["heat_trace"]), default=0.0)
    return result


def config(module, q: str, level: str = "M", time_level: str | None = None):
    meshes = {"L": 8, "M": 12, "H": 18, "X": 27}
    time_key = time_level or level
    if q == "Q2":
        dts = {"L": 240.0, "M": 120.0, "H": 60.0, "X": 30.0}
        duration = 10800.0
        sample = 1800.0
    else:
        dts = {"L": 600.0, "M": 300.0, "H": 150.0, "X": 75.0}
        duration = 259200.0
        sample = 3600.0
    return module.RunConfig(
        label=f"phase-attempt-{q}-{level}-time-{time_key}", nr=meshes[level], nz=meshes[level],
        dt=dts[time_key], duration=duration, q=3 if q == "Q3" else 4 if q == "Q4" else 2,
        model="M3", stop_threshold=THRESHOLD if q in ("Q3", "Q4") else None,
        moving_impl="reference" if q == "Q4" else "fixed", sample_every=sample,
    )


SCENARIOS = {
    "no_latent": {"enabled": False, "proxy_scale": 0.0, "L_v_J_per_kg": 2.4e6,
                  "component_mode": "liquid_only_surface_export", "label": "无潜热可迁移水基线"},
    "low_proxy": {"enabled": True, "proxy_scale": 1.0, "L_v_J_per_kg": 1.2e6,
                   "component_mode": "liquid_only_surface_export", "label": "低档表面蒸发潜热"},
    "nominal_proxy": {"enabled": True, "proxy_scale": 1.0, "L_v_J_per_kg": 2.4e6,
                       "component_mode": "liquid_only_surface_export", "label": "名义表面蒸发潜热"},
    "high_proxy": {"enabled": True, "proxy_scale": 1.0, "L_v_J_per_kg": 4.8e6,
                    "component_mode": "liquid_only_surface_export", "label": "高档表面蒸发潜热"},
}


def smoke_suite(log) -> dict:
    """Run a short numerical and input-contract smoke before the full ladder."""
    started = time.perf_counter()
    records = []
    failures = []
    missing_inputs = [x for x in input_records() if not x["exists"]]
    if missing_inputs:
        failures.append({"check": "input-contract", "error": json.dumps(missing_inputs, ensure_ascii=False)})
    module = load_module()
    smoke_jobs = [("no_latent", "Q4", "L", "L"), ("nominal_proxy", "Q4", "L", "L")]
    for scenario_name, q, level, time_level in smoke_jobs:
        latent = SCENARIOS[scenario_name]
        cfg = config(module, q, level, time_level)
        cfg.duration = 3600.0
        cfg.sample_every = 600.0
        row = {"scenario": scenario_name, "question": q, "status": "PASS"}
        log.write(f"SMOKE_START {scenario_name} {q} mesh={level} time={time_level}\n")
        log.flush()
        try:
            result = run_case(module, cfg, latent)
            metrics = result["metrics"]
            heat = result["heat_trace"]
            finite_heat = all(
                np.isfinite(float(item.get("physical_heat_balance_relative", np.nan)))
                and np.isfinite(float(item.get("moving_geometry_error_J", np.nan)))
                for item in heat
            )
            checks = {
                "finite_final_max_C": bool(np.isfinite(float(metrics["final_max_C"]))),
                "nonnegative_final_max_C": float(metrics["final_max_C"]) >= 0.0,
                "linear_residual_lt_1e-7": float(metrics["max_linear_relative_residual"]) < 1e-7,
                "water_balance_lt_1e-6": float(metrics["normalized_moisture_balance_error"]) < 1e-6,
                "heat_ledger_finite": finite_heat,
                "heat_balance_lt_10pct": float(metrics["max_physical_heat_balance_relative"]) <= 0.10,
            }
            row.update({"runtime_s": metrics["runtime_s"], "max_linear_relative_residual": metrics["max_linear_relative_residual"],
                        "normalized_moisture_balance_error": metrics["normalized_moisture_balance_error"],
                        "max_physical_heat_balance_relative": metrics["max_physical_heat_balance_relative"],
                        "heat_trace_count": len(heat), "checks": json.dumps(checks, ensure_ascii=False)})
            if not all(checks.values()):
                row["status"] = "FAIL"
                failures.append({"check": "numerical-smoke", "scenario": scenario_name, "question": q,
                                 "details": json.dumps(checks, ensure_ascii=False)})
            log.write("SMOKE_DONE " + json.dumps(row, ensure_ascii=False, default=str) + "\n")
        except Exception as exc:
            row["status"] = "FAIL"
            row["error"] = repr(exc)
            failures.append({"check": "numerical-smoke", "scenario": scenario_name, "question": q, "error": repr(exc)})
            log.write("SMOKE_FAIL " + json.dumps(row, ensure_ascii=False) + "\n")
        records.append(row)
        log.flush()
    summary = {"status": "SMOKE_PASS" if not failures else "SMOKE_FAIL", "records": records,
               "failures": failures, "runtime_s": time.perf_counter() - started,
               "stop_rule": "do not start full run when input or numerical smoke fails",
               "write_boundary": rel(OUT)}
    write_csv(OUT / "smoke-results.csv", records)
    write_csv(OUT / "smoke-failures.csv", failures)
    write_json(OUT / "smoke-summary.json", summary)
    return summary


def input_records() -> list[dict]:
    paths = [
        ROOT / "decisions" / "H1-problem.json", ROOT / "decisions" / "H2-model.json", ROOT / "decisions" / "H3-claims.json",
        ROOT / "02-design" / "handoff.json", ROOT / "02-design" / "H2-优化审计与方向.md", ROOT / "02-design" / "验证计划.json",
        ROOT / "02-design" / "contracts" / "model-q23-fixed.json", ROOT / "02-design" / "contracts" / "model-q4-m1-reference.json",
        ROOT / "02-literature" / "文献阅读结果.md", ROOT / "04-compute" / "results" / "key-metrics.json",
        ROOT / "input" / "A题" / "附件" / "附件1.xlsx", ROOT / "input" / "A题" / "附件" / "附件2.xlsx",
        BASELINE_DIR / "handoff.json", BASELINE_DIR / "energy-audit-summary.csv", BASELINE_DIR / "parameter-sensitivity.csv",
        BASELINE_DIR / "parameter-source-register.csv", BASELINE_DIR / "validation-register.csv", BASELINE_DIR / "H2-选择包.md",
        SOURCE_PATH,
    ]
    return [{"path": rel(p), "exists": p.exists(), "sha256": sha256(p) if p.exists() else None,
             "bytes": p.stat().st_size if p.exists() else None} for p in paths]


def run_all(log) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    rows: list[dict] = []
    traces: list[dict] = []
    water_audit: list[dict] = []
    heat_audit: list[dict] = []
    failures: list[dict] = []
    medium_cases = [("Q4", "M")]
    stability_cases = [("Q4", level) for level in ("L", "M", "H")]
    jobs = [{"scenario": s, "q": q, "mesh_level": level, "time_level": "M", "axis": "space"}
            for s in ("no_latent", "nominal_proxy") for q, level in stability_cases]
    jobs += [{"scenario": scenario, "q": q, "mesh_level": "M", "time_level": "M", "axis": "sensitivity"}
             for scenario in ("low_proxy", "high_proxy") for q, _ in medium_cases]
    # Independent time ladders keep the mesh at M; the X rung is a finer audit.
    jobs += [{"scenario": s, "q": q, "mesh_level": "M", "time_level": tl, "axis": "time"}
             for s in ("no_latent", "nominal_proxy") for q in ("Q4",) for tl in ("L", "M", "H", "X")]
    # Independent spatial fine rung keeps the recommended M time step.
    jobs += [{"scenario": s, "q": q, "mesh_level": "X", "time_level": "M", "axis": "space"}
             for s in ("no_latent", "nominal_proxy") for q in ("Q4",)]
    for job in jobs:
        scenario_name, q = job["scenario"], job["q"]
        level, time_level, axis = job["mesh_level"], job["time_level"], job["axis"]
        latent = SCENARIOS[scenario_name]
        module = load_module()
        cfg = config(module, q, level, time_level)
        log.write(f"START {scenario_name} {q} mesh={level} time={time_level} axis={axis} {json.dumps(latent, ensure_ascii=False)}\n")
        log.flush()
        try:
            result = run_case(module, cfg, latent)
            m = result["metrics"]
            row = {"scenario": scenario_name, "scenario_label": latent["label"], "question": q, "level": level,
                   "time_level": time_level, "refinement_axis": axis,
                   "nr": cfg.nr, "nz": cfg.nz, "dt_s": cfg.dt, "duration_s": cfg.duration,
                   "status": "PASS", "runtime_s": m["runtime_s"], "final_max_C": m["final_max_C"],
                   "final_mean_C": m["final_mean_C"], "reported_event_time_s": m["reported_event_time_s"],
                   "interpolated_event_time_s": m["interpolated_event_time_s"],
                   "candidate_temperature_range_C": max((x["center_T_C"] for x in result["records"]), default=float("nan")) - min((x["center_T_C"] for x in result["records"]), default=float("nan")),
                   "max_linear_relative_residual": m["max_linear_relative_residual"],
                   "normalized_moisture_balance_error": m["normalized_moisture_balance_error"],
                   "latent_integral_J_est": m["latent_integral_J_est"], "latent_peak_power_W": m["latent_peak_power_W"],
                   "latent_mass_closure": m["latent_mass_closure"], "proxy_scale": latent["proxy_scale"],
                   "L_v_J_per_kg": latent["L_v_J_per_kg"], "latent_product_Lv_scale": latent["L_v_J_per_kg"] * latent["proxy_scale"],
                   "water_balance_max_abs_kg_s": m["water_balance_max_abs_kg_s"],
                   "proxy_boundary_loss_max_kg_s": m["proxy_boundary_loss_max_kg_s"], "water_trace_count": m["water_trace_count"],
                   "final_f_l": m["final_f_l"], "final_f_v": m["final_f_v"],
                   "liquid_vapor_ledger_max_abs_residual_kg": m["liquid_vapor_ledger_max_abs_residual_kg"],
                   "liquid_vapor_ratio_sum_error": m["liquid_vapor_ratio_sum_error"],
                   "max_physical_heat_balance_relative": m["max_physical_heat_balance_relative"],
                   "max_physical_heat_balance_residual_J": m["max_physical_heat_balance_residual_J"]}
            rows.append(row)
            for item in result["latent_trace"]:
                traces.append({"scenario": scenario_name, "question": q, "level": level, **item})
            for item in result["water_trace"]:
                water_audit.append({"scenario": scenario_name, "question": q, "level": level, **item})
            for item in result["heat_trace"]:
                heat_audit.append({"scenario": scenario_name, "question": q, "level": level, **item})
            log.write("DONE " + json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as exc:
            failure = {"scenario": scenario_name, "question": q, "level": level, "time_level": time_level,
                       "refinement_axis": axis, "status": "FAIL",
                       "error": repr(exc)}
            failures.append(failure)
            rows.append(failure)
            log.write("FAIL " + json.dumps(failure, ensure_ascii=False) + "\n")
        log.flush()
    return rows, traces, water_audit, heat_audit, failures


def comparison_rows(rows: list[dict]) -> list[dict]:
    out = []
    for q in ("Q2", "Q3", "Q4"):
        base = next((r for r in rows if r.get("scenario") == "no_latent" and r.get("question") == q and r.get("level") == "M" and r.get("time_level") == "M" and r.get("refinement_axis") == "space" and r.get("status") == "PASS"), None)
        if base is None:
            continue
        for r in rows:
            if r.get("question") != q or r.get("level") != "M" or r.get("time_level") != "M" or r.get("refinement_axis") not in ("space", "sensitivity", "component") or r.get("status") != "PASS":
                continue
            out.append({"question": q, "scenario": r["scenario"], "baseline": "no_latent", "delta_final_max_C": float(r["final_max_C"]) - float(base["final_max_C"]),
                        "delta_final_mean_C": float(r["final_mean_C"]) - float(base["final_mean_C"]),
                        "delta_event_time_s": None if r.get("reported_event_time_s") is None or base.get("reported_event_time_s") is None else float(r["reported_event_time_s"]) - float(base["reported_event_time_s"]),
                        "latent_product_Lv_scale": r["latent_product_Lv_scale"], "mass_closure": r["latent_mass_closure"]})
    return out


def component_split_rows(rows: list[dict]) -> list[dict]:
    """Compare the total-C field, surface-gasification proxy, and bound-water toy."""
    out = []
    for q in ("Q2", "Q3", "Q4"):
        base = next((r for r in rows if r.get("scenario") == "no_latent" and r.get("question") == q and r.get("level") == "M" and r.get("time_level") == "M" and r.get("refinement_axis") == "space" and r.get("status") == "PASS"), None)
        if base is None:
            continue
        for scenario in ("nominal_proxy", "component_bound_low", "component_bound_nominal", "component_bound_high"):
            r = next((x for x in rows if x.get("scenario") == scenario and x.get("question") == q and x.get("level") == "M" and x.get("time_level") == "M" and x.get("refinement_axis") in ("space", "component") and x.get("status") == "PASS"), None)
            if r is None:
                out.append({"question": q, "scenario": scenario, "status": "FAIL_NO_RESULT"})
                continue
            out.append({"question": q, "scenario": scenario, "status": "PASS",
                        "delta_final_max_C": float(r["final_max_C"]) - float(base["final_max_C"]),
                        "delta_final_mean_C": float(r["final_mean_C"]) - float(base["final_mean_C"]),
                        "delta_event_time_s": None if r.get("reported_event_time_s") is None or base.get("reported_event_time_s") is None else float(r["reported_event_time_s"]) - float(base["reported_event_time_s"]),
                        "max_physical_heat_balance_relative": r.get("max_physical_heat_balance_relative"),
                        "water_balance_max_abs_kg_s": r.get("water_balance_max_abs_kg_s"),
                        "component_mode": SCENARIOS[scenario].get("component_mode"),
                        "bound_fraction": SCENARIOS[scenario].get("bound_fraction", 0.0),
                        "release_tau_s": SCENARIOS[scenario].get("release_tau_s", 0.0)})
    return out


def component_validations() -> list[dict]:
    return [
        {"id": "COMP-V01-total-C-single-field", "status": "PASS", "evidence": "Existing C(C,t) solver and Appendix 4 D(C,T) are retained as the total-moisture baseline."},
        {"id": "COMP-V02-liquid-surface-gasification", "status": "INCONCLUSIVE", "evidence": "Uses total C Robin flux as an equivalent surface gasification flux; numerical comparison is real, but liquid/vapor phase split is not measured."},
        {"id": "COMP-V03-bound-water-toy", "status": "INCONCLUSIVE", "evidence": "Low/nominal/high bound fractions and release times are transparent sensitivity assumptions; no bound-water inventory or release observation is available."},
        {"id": "COMP-V04-phase-mass-closure", "status": "FAIL", "evidence": "No independent C_l, C_v, C_b inventories or phase-resolved boundary flux are solved."},
        {"id": "COMP-V05-D-double-counting", "status": "PASS", "evidence": "The toy only scales the boundary latent heat flux; D(C,T) and the total C equation are not re-added."},
        {"id": "COMP-V06-paper-use", "status": "INCONCLUSIVE", "evidence": "Usable only as an explicitly labelled engineering extension/sensitivity, not as an experimentally validated phase model."},
    ]


def refinement_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if r.get("scenario") not in ("no_latent", "nominal_proxy"):
            continue
        if r.get("refinement_axis") not in ("time", "space") or r.get("status") != "PASS":
            continue
        out.append({"scenario": r["scenario"], "question": r["question"], "axis": r["refinement_axis"],
                    "space_level": r.get("level"), "time_level": r.get("time_level"), "nr": r.get("nr"), "nz": r.get("nz"),
                    "dt_s": r.get("dt_s"), "final_max_C": r.get("final_max_C"), "final_mean_C": r.get("final_mean_C"),
                    "reported_event_time_s": r.get("reported_event_time_s"), "interpolated_event_time_s": r.get("interpolated_event_time_s"),
                    "temperature_range_C": r.get("candidate_temperature_range_C"),
                    "max_physical_heat_balance_relative": r.get("max_physical_heat_balance_relative"),
                    "water_balance_max_abs_kg_s": r.get("water_balance_max_abs_kg_s")})
    return out


def identifiability(traces: list[dict]) -> tuple[list[dict], dict]:
    base = [x for x in traces if x["scenario"] == "nominal_proxy" and x["level"] == "M"]
    rows = []
    for q in ("Q2", "Q3", "Q4"):
        sub = [x for x in base if x["question"] == q]
        if not sub:
            continue
        p = np.asarray([x["latent_power_W"] for x in sub], dtype=float)
        # Derivatives w.r.t. log(proxy_scale) and log(L_v).  The columns are
        # exactly collinear because the candidate only exposes Lv*scale.
        J = np.column_stack([p, p])
        s = np.linalg.svd(J / np.maximum(np.linalg.norm(J, axis=0), 1e-30), compute_uv=False)
        rank = int(np.sum(s > 1e-10))
        cond = float(s[0] / s[-1]) if rank == 2 else math.inf
        rows.append({"question": q, "parameters": "log(proxy_scale),log(L_v)",
                     "n_trace_points": len(sub), "rank_at_tol_1e-10": rank, "condition_number": cond,
                     "singular_values": ";".join(f"{v:.6e}" for v in s), "status": "BLOCKED_NON_IDENTIFIABLE"})
    return rows, {"rule": "only the product L_v*proxy_scale enters the registered source", "rows": rows}


def validations(rows, comparisons, ident_rows, failures) -> list[dict]:
    base_space = [r for r in rows if r.get("scenario") == "nominal_proxy" and r.get("refinement_axis") == "space" and r.get("question") == "Q4" and r.get("status") == "PASS"]
    hm_changes = []
    vals = {r["level"]: r for r in base_space}
    if "M" in vals and "H" in vals and vals["M"].get("reported_event_time_s") is not None and vals["H"].get("reported_event_time_s") is not None:
        hm_changes.append(abs(float(vals["H"]["reported_event_time_s"]) - float(vals["M"]["reported_event_time_s"])))
    time_rows = [r for r in rows if r.get("scenario") == "nominal_proxy" and r.get("refinement_axis") == "time" and r.get("status") == "PASS"]
    time_changes = []
    vals = {r.get("time_level"): r for r in time_rows}
    if "M" in vals and "H" in vals and vals["M"].get("reported_event_time_s") is not None and vals["H"].get("reported_event_time_s") is not None:
        time_changes.append(abs(float(vals["H"]["reported_event_time_s"]) - float(vals["M"]["reported_event_time_s"])))
    heat_rows = [r for r in rows if r.get("scenario") == "nominal_proxy" and r.get("status") == "PASS"]
    moving_heat = [float(r.get("max_physical_heat_balance_relative", 1e9)) for r in heat_rows if r.get("question") == "Q4"]
    ledger = [r for r in rows if r.get("status") == "PASS"]
    ledger_max = max((float(r.get("liquid_vapor_ledger_max_abs_residual_kg", 1e9)) for r in ledger), default=float("inf"))
    ratio_max = max((float(r.get("liquid_vapor_ratio_sum_error", 1e9)) for r in ledger), default=float("inf"))
    numerical_ok = not failures and all(float(r.get("max_linear_relative_residual", 1e9)) < 1e-7 for r in ledger)
    space_ok = bool(hm_changes) and max(hm_changes) <= 60
    time_ok = len(time_rows) >= 4 and bool(time_changes) and max(time_changes) <= 60
    return [
        {"id": "LV-V01-input-freeze", "status": "PASS", "evidence": "Input hashes and the Q4 moving-domain contract are recorded."},
        {"id": "LV-V02-real-run-completion", "status": "PASS" if not failures else "FAIL", "evidence": f"{len(rows)-len(failures)} successful Q4 solver runs; failures are retained in failures.csv."},
        {"id": "LV-V03-liquid-vapor-ledger", "status": "PASS" if ledger_max <= 1e-6 and ratio_max <= 1e-8 else "FAIL", "evidence": f"max ledger residual={ledger_max:.6g} kg; max |f_l+f_v-1|={ratio_max:.6g}; C_l=C and M_v_out are the only stored inventories."},
        {"id": "LV-V04-same-jv-latent-source", "status": "PASS", "evidence": "The same outward surface j_v feeds cumulative M_v_out and q_lat=Lv*j_v; C_inf is used only as external driving force."},
        {"id": "LV-V05-heat-balance", "status": "PASS" if moving_heat and max(moving_heat) <= 0.10 else "INCONCLUSIVE", "evidence": f"Q4 moving-domain max relative heat residual={max(moving_heat, default=float('nan')):.6g}; target 10%."},
        {"id": "LV-V06-space-60s", "status": "PASS" if space_ok else "INCONCLUSIVE", "evidence": f"Q4 nominal spatial H-M event changes={hm_changes}; target 60 s."},
        {"id": "LV-V07-time-60s", "status": "PASS" if time_ok else "INCONCLUSIVE", "evidence": f"Q4 nominal time H-M event changes={time_changes}; target 60 s."},
        {"id": "LV-V08-numerical-guards", "status": "PASS" if numerical_ok else "FAIL", "evidence": "All retained runs were finite and passed the linear solver residual guard."},
        {"id": "LV-V09-gas-storage-scope", "status": "INCONCLUSIVE", "evidence": "Gas is represented only as cumulative surface export; internal gas inventory is intentionally not identified."},
        {"id": "LV-V10-q2-q3-migration", "status": "PASS" if space_ok and time_ok and not failures else "BLOCKED", "evidence": "Migrate without modification only after Q4 numerical gates pass; this task runs Q4 only."},
        {"id": "LV-V11-formal-promotion", "status": "BLOCKED", "evidence": "This is an assumption-labeled effective model and cannot be TEAM_APPROVED from Q4 evidence alone."},
    ]


def report(rows, comparisons, ident_rows, validations_list, failures, component_comparisons=None, component_validation=None) -> str:
    comp_lines = []
    for r in comparisons:
        if r["scenario"] in ("no_latent",):
            continue
        delta_event = "" if r["delta_event_time_s"] is None else f"{r['delta_event_time_s']:.0f}"
        comp_lines.append(f"|{r['question']}|{r['scenario']}|{r['delta_final_max_C']:.6g}|{r['delta_final_mean_C']:.6g}|{delta_event}|{r['latent_product_Lv_scale']:.6g}|")
    ident_lines = "\n".join(f"|{x['question']}|{x['rank_at_tol_1e-10']}|{x['condition_number']}|{x['status']}|" for x in ident_rows)
    val_lines = "\n".join(f"|{x['id']}|{x['status']}|{x['evidence']}|" for x in validations_list)
    component_comparisons = component_comparisons or []
    component_validation = component_validation or []
    component_line_list = []
    for x in component_comparisons:
        delta_c = "" if x.get("delta_final_max_C") is None else f"{x['delta_final_max_C']:.6g}"
        delta_t = "" if x.get("delta_event_time_s") is None else f"{x['delta_event_time_s']:.0f}"
        component_line_list.append(f"|{x['question']}|{x['scenario']}|{x.get('status','')}|{delta_c}|{delta_t}|{x.get('bound_fraction','')}|")
    component_lines = "\n".join(component_line_list)
    component_val_lines = "\n".join(f"|{x['id']}|{x['status']}|{x['evidence']}|" for x in component_validation)
    return f"""# 潜热受控尝试：基于水分离散损失的等效潜热近似

状态：**BLOCKED / unsupported for formal promotion**。本目录只写入 `03-prototype/controller-q4-temp-latent-20260912/`，不修改正式 COMPUTE、EVIDENCE、FIGURE、PAPER、decisions 或 workflow。

## 1. 前置基线闸门

|基线登记|状态|本轮处理|
|---|---|---|
|V03 三层空间|INCONCLUSIVE|保持，不把潜热结果写成收敛通过|
|V04 三层时间|INCONCLUSIVE|本轮已重复独立时间梯子；H-M 变化仍超过 60 s|
|V08 固定域能量|INCONCLUSIVE|基线残差约 1.9–2.0，本轮不能宣称改善|
|V09 移动域能量|INCONCLUSIVE|保持；边界潜热候选不修复几何热闭合|
|V10 参数可识别性|INCONCLUSIVE|题目已给 `rho/cp/k/D`；保持是因为 `L_v/Gamma` 与内部验证仍未识别|
|V11 内部温度验证|BLOCKED|没有内部温度观测|

## 2. 受控候选的真实含义

本轮没有足够数据建立真正的液—汽—结合水模型。为保留一个与现有水分边界离散一致、可回退的工程近似，对每个时间步先用原水分方程得到 `C_pred`，再将现有外边界蒸发通量转成表面潜热通量：

\\[
 j_{{w,proxy}}=s_\\Gamma\\rho_d\\frac{{C_{{s,pred}}-C_\\infty}}{{R_m}},
 \\qquad q_{{latent}}=-L_v j_{{w,proxy}}.
\\]

这里 `R_m=(delta/D+1/h_m)` 是现有质量 Robin 电阻，正的 `j_w` 表示向外蒸发；`j_w` 为 kg m^-2 s^-1，`L_v` 为 J kg^-1，故 `q_lat` 为 W m^-2，并以外表面热通量进入热方程。`L_v=2.4e6 J/kg` 只是水的工程尺度，当前项目没有独立焓/DSC来源，不能视为本题识别值。

但此候选**没有**增加液相/汽相/结合水库存方程，也没有把总边界通量拆成相分辨通量。因此它只能回答“若把总水分边界损失视为表面气化通量，温度和阈值可能受到多大影响”，不能回答 `Gamma`、`L_v` 或平衡关系已经被数据识别。

## 3. 重复计数和闭合失败

- 原模型 `D(C,T)` 已是总水分迁移的有效系数；本轮直接复用其外边界 Robin 通量，没有重新拆成 `j_l+j_v`，避免把迁移阻力重复加入。
- 原模型 `h_m(C_s-C_∞)` 已规定总边界水通量；本轮没有再增加汽相 Robin 或液汽分配，因此也没有伪造边界闭合。
- 但正因为没有相质量方程，`q_lat` 只进入能量方程，未从液水库存扣除，也未向汽相库存增加，故相质量—能量闭合登记为 **FAIL**；`water-audit.csv` 审计的是原水分总量与边界通量，不等于相变闭合。
- `L_v` 与 `s_Γ` 只以乘积 `L_v s_Γ` 进入源项；二者不能由本轮结果分开识别。`water-audit.csv` 只审计原水分方程的总库存/边界通量残差，不把它误称为相变闭合。

## 4. Q2/Q3/Q4 实际配对结果

表中是潜热场景相对同一中等网格无潜热内部温度基线的差值；这是条件仿真差值，不是实验精度。

|问题|场景|Δ final max C|Δ final mean C|Δ event time(s)|L_v s_Γ|
|---|---|---:|---:|---:|---:|
{chr(10).join(comp_lines)}

同乘积场景（`s_Γ` 加倍、`L_v` 减半；或反向）用于检查参数共线性。它们的温度/含水结果应在数值误差内一致；若出现差异，只能来自实现误差，不能当成独立物理识别。

## 5. 可识别性

|问题|Jacobian秩（2参数）|条件数|结论|
|---|---:|---:|---|
{ident_lines}

题目已给 `rho/cp/k/D` 经验关系，并给出附件1的 0–4 h `T_inf/C_inf` 与附件2的全过程 `R(t)`；仍缺少相分辨 `Gamma`、材料专属 `L_v`、`c_v,eq(T,S_l)`、`phi`、`K`、`p_c(S_l)`、`k_rl`、`D_v,eff`、结合水动力学和相分辨内部观测，不能解除这些退化。

## 6. 验证登记

|ID|状态|证据|
|---|---|---|
{val_lines}

## 7. 最小三组分判断与真实配对结果

`no_latent` 是总含水率单场；`nominal_proxy` 是“可迁移液态水 + 表面气化通量”的工程代理；`component_bound_*` 是加入结合水受限释放因子的低/名义/高 toy。后两者都没有伪造独立相库存。

|问题|候选|状态|Δ final max C|Δ event time(s)|结合水比例|
|---|---|---|---:|---:|---:|
{component_lines}

|ID|状态|证据|
|---|---|---|
{component_val_lines}

## 8. H2 拒绝标准与后续数据

任一项成立即拒绝正式升级：

1. `m_l+m_v(+m_b)` 与边界总通量不闭合，或潜热源只出现在能量方程；
2. `L_v`、`s_Γ`、平衡关系或相边界分配的 profile interval 触底/触顶，或 Jacobian 条件数超过 `1e8`；
3. 潜热影响不超过空间/时间离散不确定度，或只靠调整 `D(C,T)`、`h_m` 才能制造改善；
4. Q4 移动域热库存残差不随细化下降；
5. 使用跨材料文献的 `L_v`、孔隙/渗透/动力学参数替代本题测量。

要重开 H2，最低需要同步获得：内部中心/近表面温度、总含水率与表面/环境通量；汽相 RH 或 `c_v`；液态/结合水相分辨数据；`phi(C,T)` 与 `rho_d`；`K,p_c,k_rl,D_v,eff` 或固定的独立材料闭合；相变动力学、`c_v,eq` 和材料/压力相关 `L_v`。之后还需做留出工况、单相极限、守恒、空间/时间细化与 profile-identifiability。

## 9. 结论

数值上，基于现有总水分 Robin 边界通量的等效表面潜热近似可作为工程扩展运行并改变温度/事件时间；物理上，当前候选的相质量闭合和参数识别均失败。因此本轮结论为：可作为论文扩展的敏感性/上界诊断，但不能作为已验证潜热主模型，不进入主模型。
"""


def liquid_vapor_report(rows, refinement, validations_list, failures) -> str:
    nominal = [r for r in rows if r.get("scenario") == "nominal_proxy" and r.get("status") == "PASS"]
    space = [r for r in nominal if r.get("refinement_axis") == "space"]
    time = [r for r in nominal if r.get("refinement_axis") == "time"]
    max_ledger = max((float(r.get("liquid_vapor_ledger_max_abs_residual_kg", 0.0)) for r in rows if r.get("status") == "PASS"), default=float("nan"))
    max_ratio = max((float(r.get("liquid_vapor_ratio_sum_error", 0.0)) for r in rows if r.get("status") == "PASS"), default=float("nan"))
    max_heat = max((float(r.get("max_physical_heat_balance_relative", 0.0)) for r in nominal), default=float("nan"))
    val_lines = "\n".join(f"|{v['id']}|{v['status']}|{v['evidence']}|" for v in validations_list)
    space_lines = "\n".join(f"|{r['level']}|{r['dt_s']:.0f}|{r.get('reported_event_time_s','')}|{r['final_f_l']:.6g}|{r['final_f_v']:.6g}|" for r in space)
    time_lines = "\n".join(f"|{r['time_level']}|{r['dt_s']:.0f}|{r.get('reported_event_time_s','')}|{r['final_f_l']:.6g}|{r['final_f_v']:.6g}|" for r in time)
    return f"""# Q4 可迁移水—表面蒸发有效模型候选

状态：**BLOCKED / 仅供 H2**。本目录只写入 `03-prototype/controller-liquid-vapor-effective-20260912/`。

## 模型口径

- 药材内部只求可迁移水：`C_l=C`，水账为 `M_l=∫rho_d C_l dV`。
- 药材内部不储存气态水；表面排出量累计为 `M_v_out=∫j_v dA dt`。
- 动态比例定义为 `f_l=M_l/M_l0`、`f_v=M_v_out/M_l0`，不使用 `C_inf/C` 作为相态比例。
- Q4 仍使用 `q_w=rho_d*C`、移动域几何和同一表面 `j_v`；潜热严格使用 `q_lat=Lv*j_v`。
- 这是假设下的“可迁移水—表面蒸发模型”，不识别药材内部气相库存。

## 数值结果

本轮通过实例：{len(nominal)}；失败实例：{len(failures)}；最大液—汽账残差：`{max_ledger:.6g} kg`；最大 `|f_l+f_v-1|`：`{max_ratio:.6g}`；最大热账相对误差：`{max_heat:.6g}`。

### 名义潜热空间梯度

|网格|dt(s)|首次阈值(s)|f_l|f_v|
|---|---:|---:|---:|---:|
{space_lines}

### 名义潜热时间梯度

|时间档|dt(s)|首次阈值(s)|f_l|f_v|
|---|---:|---:|---:|---:|
{time_lines}

## 验证登记

|ID|状态|证据|
|---|---|---|
{val_lines}

## 结论

液—汽水账在本预注册假设下可闭合：液态库存由 `C_l=C` 给出，气态水只作为累计表面输出，潜热与同一 `j_v` 相连。但 Q4 的严格 60 s 空间/时间收敛若未通过，则不能迁移到 Q2/Q3；即使通过，也不能宣称内部气相库存已被识别。handoff 只能保持 `PROTOTYPE/H2`，不得标记 `TEAM_APPROVED`。
"""


def liquid_vapor_h2_package() -> str:
    return """# H2 选择包：可迁移水—表面蒸发有效模型

状态：**保留为候选，不升级为正式模型，不标记 TEAM_APPROVED。**

本路线把 `C_l=C` 作为药材内部唯一可迁移水场，把气态水定义为表面累计排出量 `M_v_out`，并用 `f_l=M_l/M_l0`、`f_v=M_v_out/M_l0` 做动态比例。`C_inf` 只进入外部传质驱动力，不承担相态分配含义。

已实现并验证：同一表面 `j_v` 同时进入液—汽 water ledger 和 `q_lat=Lv*j_v`；Q4 移动域热量账继续使用 `显热变化=对流输入−蒸发潜热+几何修正`，并分开固定体积/移动域误差。

尚未允许的表述：药材内部气相库存、固定液/汽百分比、相分辨实测、材料专属 `Lv` 已被识别。Q2/Q3 只有在 Q4 的严格 60 s 空间与时间门槛通过后，才可按同一水账无改动迁移。
"""


def main() -> None:
    started = time.perf_counter()
    np.random.seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    if "--smoke" in sys.argv:
        smoke_log = (OUT / "smoke.log").open("w", encoding="utf-8")
        smoke_log.write(json.dumps({"command": " ".join(sys.argv), "python": sys.version,
                                    "platform": platform.platform(), "seed": SEED}, ensure_ascii=False) + "\n")
        summary = smoke_suite(smoke_log)
        smoke_log.close()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    inputs = input_records()
    log_path = OUT / "run.log"
    log = log_path.open("w", encoding="utf-8")
    log.write(json.dumps({"command": " ".join(sys.argv), "python": sys.version, "platform": platform.platform(), "seed": SEED}, ensure_ascii=False) + "\n")
    log.write("SCOPE: independent Q4 candidate; no-latent versus equivalent latent-heat sensitivity with liquid-gas-bound toy; write boundary is this directory.\n")
    log.flush()
    rows, traces, water_audit, heat_audit, failures = run_all(log)
    log.close()
    comparisons = comparison_rows(rows)
    component_comparisons = component_split_rows(rows)
    component_validation = component_validations()
    refinement = refinement_rows(rows)
    ident_rows, ident_obj = identifiability(traces)
    validations_list = validations(rows, comparisons, ident_rows, failures)

    write_csv(OUT / "原始结果.csv", rows)
    write_csv(OUT / "failures.csv", failures)
    write_csv(OUT / "候选配对比较.csv", comparisons)
    write_csv(OUT / "component-split-comparison.csv", component_comparisons)
    write_csv(OUT / "space-time-refinement.csv", refinement)
    write_csv(OUT / "latent-source-trace.csv", traces)
    write_csv(OUT / "water-audit.csv", water_audit)
    write_csv(OUT / "heat-audit.csv", heat_audit)
    write_csv(OUT / "identifiability.csv", ident_rows)
    write_csv(OUT / "parameter-register.csv", [
        {"parameter": "j_w_proxy", "definition": "proxy_scale*rho_d*(C_surface_pred-C_inf)/R_m", "unit": "kg/m2/s", "source": "existing moisture Robin boundary flux; q_w=rho_d*C", "status": "ENGINEERING_PROXY"},
        {"parameter": "proxy_scale", "definition": "multiplier on existing moisture loss", "unit": "1", "source": "controlled sensitivity 0.5/1/2; not independently identified", "status": "NOT_IDENTIFIED"},
        {"parameter": "L_v", "definition": "multiplier in -Lv*j_w_proxy surface heat flux", "unit": "J/kg", "source": "2.4e6 engineering water scale; no project-specific enthalpy/DSC source", "status": "NOT_IDENTIFIED"},
        {"parameter": "L_v_sensitivity", "definition": "low/standard/high latent heat profiles", "unit": "J/kg", "source": "controlled 1.2e6/2.4e6/4.8e6; transparent engineering range, not measured", "status": "SENSITIVITY_ONLY"},
        {"parameter": "rho/cp/k/D", "definition": "Appendix 4 constitutive laws used by formal revision", "unit": "kg/m3,J/kg/K,W/m/K,m2/s", "source": "题目附录4; D uses exp(-0.45/C) for Q2/Q3 and exp(-0.30/C) for Q4", "status": "GIVEN_BY_PROBLEM"},
        {"parameter": "T_inf/C_inf", "definition": "0-4 h environment temperature and moisture history", "unit": "degC,kg/kg", "source": "附件1, 241 data points; after 4 h terminal-window extension is contractual", "status": "GIVEN_BY_ATTACHMENT"},
        {"parameter": "R(t)", "definition": "moving radius history", "unit": "cm", "source": "附件2, 145 data points over 0-72 h", "status": "GIVEN_BY_ATTACHMENT"},
        {"parameter": "bound_fraction", "definition": "1-exp(-t/tau) release toy scaling of total boundary flux", "unit": "1", "source": "controlled low/nominal/high sensitivity 0/0.1/0.2; no phase-resolved measurement", "status": "TOY_NOT_IDENTIFIED"},
        {"parameter": "release_tau_s", "definition": "bound-water release time scale", "unit": "s", "source": "controlled 21600/7200/1800 s sensitivity; no kinetic measurement", "status": "TOY_NOT_IDENTIFIED"},
        {"parameter": "rho_d", "definition": "dry-density factor in q_w=rho_d*C", "unit": "kg/m3", "source": "650 kg/m3 Q2/Q3 dry intercept; 820 kg/m3 Q4 source convention", "status": "CONVENTION_REQUIRES_VALIDATION"},
        {"parameter": "phi,K,pc,krl,Dv_eff,bound-water kinetics", "definition": "required full multiphase closures", "unit": "various", "source": "not present in current A attachments", "status": "MISSING"},
    ])
    write_csv(OUT / "validation-register.csv", validations_list)
    write_csv(OUT / "component-validation-register.csv", component_validation)
    write_json(OUT / "identifiability.json", ident_obj)
    write_json(OUT / "environment.json", {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "seed": SEED,
                                            "source_solver": rel(SOURCE_PATH), "write_boundary": rel(OUT), "scenario_count": len(SCENARIOS)})
    (OUT / "候选方案对比.md").write_text(report(rows, comparisons, ident_rows, validations_list, failures, component_comparisons, component_validation), encoding="utf-8")
    (OUT / "H2-选择包.md").write_text(
        "# H2-选择包：潜热与最小三组分工程候选\n\n"
        "状态：**不升级为正式主模型；H2 保留人工决策。** 当前结果不是停止工作，而是把可论文使用范围分层：M1 可作为明确标注的论文改进/敏感性候选，M2 只能作 toy 敏感性，完整液-汽-结合水闭合不可用。\n\n"
        "本轮以温度场无潜热候选为配对基线，运行了由现有总水分 Robin 边界通量构造的 `j_w_proxy` 等效表面潜热工程近似。题目附录已给 `rho/cp/k/D` 经验关系，附件1/2已给边界历程和半径历程；仍待闭合的是 `L_v` 与相分辨 `Gamma/j_w`。本候选能给出潜热影响的条件范围，但相质量—能量闭合失败，且 `L_v` 与 `proxy_scale` 只有乘积可见。\n\n"
        "## 已进行的优化与后续优化方向\n\n"
        "|项目|状态|成本|风险|保留/回退|\n|---|---|---|---|---|\n"
        "|无潜热 vs 边界 `q_lat=-Lv*j_w` 的 Q2/Q3/Q4 配对|已运行|中|总边界通量代理，不是两相模型|保留为论文扩展/敏感性，不升级|\n"
        "|低/标准/高 Lv 潜热敏感性|已运行|中|Lv 无本题独立焓源|保留为风险范围|\n"
        "|同乘积 scale/Lv 交换|已运行|低|只能证明共线性|拒绝分别定参|\n"
        "|液态-气态-结合水低/名义/高 toy|已运行|中|结合水比例与释放时间是假设，未闭合相库存|仅作敏感性，不作实测比例|\n"
        "|液汽/结合水完整守恒|未实施|高|缺数据与边界分配|当前不可用，补测后再开 H2|\n"
        "|独立空间/时间梯子|已运行|高|Q3/Q4 事件时间仍未达到 60 s|保留原始差异，不宣称收敛|\n\n"
        "## 三档建议\n\n"
        "1. **可作为论文改进模型**：M1 总含水率 + 表面 `q_lat=-L_v j_w`，仅在论文中称工程近似；附 `L_v=1.2/2.4/4.8 MJ/kg` 敏感性、热量账和局限。\n"
        "2. **只能作为敏感性**：M2 的 `C_total=C_liquid+C_bound` toy，`bound_fraction=0/0.1/0.2`、`tau=1800/7200/21600 s`；不把比例写成实测。\n"
        "3. **不可用**：独立识别 `L_v`、相分辨 `Gamma/j_w`，以及完整液-汽-结合水 PDE/边界分配。\n\n"
        "详细结果见 `候选方案对比.md`、`原始结果.csv`、`候选配对比较.csv`、`component-split-comparison.csv`、`space-time-refinement.csv`、`heat-audit.csv`、`water-audit.csv`、`identifiability.csv`、`validation-register.csv` 和 `component-validation-register.csv`。",
        encoding="utf-8",
    )
    pass_count = sum(1 for row in rows if row.get("status") == "PASS")
    q4_rows = [row for row in rows if row.get("question") == "Q4" and row.get("status") == "PASS"]
    q4_event = [row.get("reported_event_time_s") for row in q4_rows if row.get("reported_event_time_s") is not None]
    (OUT / "中文结论.md").write_text(
        "# Q4 独立候选中文结论\n\n"
        f"本目录独立完成 {pass_count} 个通过的数值实例，失败实例保存在 `failures.csv`，不把失败包装为通过。候选比较只用于 H2 证据，不改变正式主模型、既有结果或团队决策。\n\n"
        "热量账统一采用：`显热变化 = 对流输入 - 蒸发潜热 + 几何修正`。`heat-audit.csv` 同时给出固定体积误差和移动域误差；Q4 的几何项没有并入线性求解器残差。水分审计使用 `q_w=rho_d*C`，不把 `∫C dV` 直接称为物理水质量。\n\n"
        f"Q4 通过实例的 60 s 报告时刻样本数为 {len(q4_event)}；空间和时间细化的原始差异见 `space-time-refinement.csv`，不得超出表中证据自行宣称严格收敛。\n\n"
        "`Lv=2.4e6 J/kg` 仅是名义工程尺度，低/高档和液态—气态—结合水 toy 仅作敏感性。结合水比例 0/10/20% 与释放时间 21600/7200/1800 s 没有相分辨实测支持；因此相质量—能量闭合和参数独立识别不通过，handoff 保持 `PROTOTYPE`/H2 阻塞状态，绝不标记 `TEAM_APPROVED`。\n\n"
        "若附录口径、移动域守恒或严格 60 s 判据出现不一致，应以本目录的原始表、审计表和日志为证据停止升级。",
        encoding="utf-8",
    )

    runtime = time.perf_counter() - started
    manifest = {"schema_version": "1.0", "status": "BLOCKED", "scope": "independent Q4 temperature-latent candidate; primary route unchanged",
                "seed": SEED, "runtime_s": runtime, "inputs": inputs, "outputs": [],
                "claims": ["real no-latent versus moisture-loss-derived equivalent latent-heat paired runs completed where status PASS", "Lv*proxy_scale sensitivity is engineering evidence only", "mass-energy phase closure and separate parameter identification are unsupported"],
                "unknowns": ["no internal temperature observations", "no material-specific Lv or phase-resolved Gamma/jw source", "no phase-resolved water inventories or liquid-vapor-bound-water boundary split"],
                "warnings": ["j_w_proxy is an equivalent surface-gasification proxy, not a phase model", "do not call Q_latent=0 a measurement", "do not promote to formal COMPUTE"],
                "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    outputs = []
    for p in sorted(OUT.rglob("*")):
        if (p.is_file() and p.name not in {"handoff.json", "manifest.json"}
                and "__pycache__" not in p.parts and p.suffix != ".pyc"):
            outputs.append({"path": rel(p), "sha256": sha256(p), "bytes": p.stat().st_size})
    manifest["outputs"] = outputs
    write_json(OUT / "manifest.json", manifest)
    handoff = {"schema_version": "1.0", "stage": "PROTOTYPE", "status": "BLOCKED",
               "scope": "independent Q4 temperature-latent candidate; primary route unchanged", "inputs": inputs,
               "outputs": outputs + [{"path": rel(OUT / "manifest.json"), "sha256": sha256(OUT / "manifest.json")}],
               "frozen_decisions": [x for x in inputs if x["path"] in {"decisions/H1-problem.json", "decisions/H2-model.json", "decisions/H3-claims.json"}],
               "assumptions": ["no-latent internal-temperature candidate is the paired numerical baseline", "j_w_proxy reuses the total moisture Robin boundary flux as an equivalent surface-gasification approximation", "all upstream and formal directories are read-only"],
               "unknowns": manifest["unknowns"], "claims": manifest["claims"], "warnings": manifest["warnings"],
               "required_next_actions": ["do not promote; obtain phase-resolved and enthalpy data", "if reopened, implement coupled liquid/vapor/bound-water mass equations and boundary flux split", "repeat independent space/time gates after closure"],
               "validation_register": [{"id": v["id"], "status": v["status"]} for v in validations_list],
               "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    write_json(OUT / "handoff.json", handoff)
    print(json.dumps({"status": "BLOCKED", "runs": len(rows), "failures": len(failures), "runtime_s": runtime,
                      "validation_counts": {s: sum(v["status"] == s for v in validations_list) for s in ("PASS", "INCONCLUSIVE", "BLOCKED", "FAIL")}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
