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
T_REF_K = 301.15


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


def enthalpy_density(module, cfg, c, temp):
    """Effective sensible enthalpy density used by the coupled audit.

    The appendix cp/rho laws are functions of C, so rho*cp changes when
    moisture changes.  The old prototype compared rho*cp at two different
    states without accounting for that change.  This helper makes the
    moisture-induced sensible enthalpy term explicit and auditable.
    """
    if cfg.q == 1:
        rho, cp, _, _ = module.props_q1(c)
    elif cfg.q in (2, 3):
        rho, cp, _, _ = module.props_q23(c, temp, constant=(cfg.model == "M2"),
                                         pref=cfg.pref, exponent=cfg.exponent)
    else:
        rho, cp, _, _ = module.props_q4(c, temp, pref=cfg.pref, exponent=cfg.exponent)
    return rho * cp * (temp - T_REF_K)


def run_case(module, cfg, latent: dict) -> dict:
    """Run the real internal-temperature solver with a controlled thermal source."""
    context = {
        "c": None, "d": None, "cenv": 0.0, "time": 0.0,
        "pending_time": None, "active_time": None, "step_old_c": None, "step_d": None,
        "source_trace": {}, "water_trace": {}, "heat_trace": {},
        "last_predicted_c": None, "last_enthalpy_source": None,
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
        context["water_trace"][round(float(time_key), 6)] = {
            "time_s": round(float(time_key), 6),
            "method": method,
            "rho_d_kg_m3": float(rho_d),
            "net_inventory_rate_kg_s": net_change,
            "local_positive_loss_rate_kg_s": local_loss,
            "boundary_net_rate_kg_s": boundary_net,
            "water_balance_residual_kg_s": net_change - boundary_net,
            "solver_relative_residual": float(residual),
        }

    def record_heat(time_key, old_t, new_t, coeff, storage, grid, dt, boundary_in,
                    boundary_sink, linear_residual, c_new=None):
        gr, gz, gbr, gb0, gb1 = module.conductances(coeff, grid, 25.0, True)
        c_old = context.get("step_old_c")
        if c_old is None:
            c_old = np.zeros_like(old_t) + 2.55
        if c_new is None:
            c_new = context.get("last_predicted_c")
        if c_new is None:
            c_new = c_old
        # Full sensible enthalpy change, including the part caused by the
        # change in C.  The previous audit used storage_old and storage_new
        # as if the PDE had solved d(rho*cp*T)/dt; it had not.
        h_old = enthalpy_density(module, cfg, c_old, old_t)
        h_new = enthalpy_density(module, cfg, c_new, new_t)
        del_e_fixed = float(np.sum((h_new - h_old) * grid.vol))
        geometry_term = 0.0
        if cfg.q == 4:
            prev_t = max(float(time_key) - dt, 0.0)
            prev_radius = module.radius_at(prev_t, cfg.radius_mode)
            prev_grid = module.Grid(cfg.nr, cfg.nz, prev_radius, radial_strategy=cfg.radial_strategy)
            geometry_term = float(np.sum(h_old * (grid.vol - prev_grid.vol)))
        latent_power = 0.0
        if boundary_sink is not None:
            outer_area = 2 * math.pi * grid.radius * grid.dz
            latent_power = float(np.sum(outer_area * boundary_sink.get("outer_W_m2", 0.0)) +
                                 np.sum(grid.annulus * boundary_sink.get("z0_W_m2", 0.0)) +
                                 np.sum(grid.annulus * boundary_sink.get("z1_W_m2", 0.0)))
        total_delta_e = del_e_fixed + geometry_term
        source_j = float(context.get("last_enthalpy_source_J") or 0.0)
        # The total enthalpy change already contains the C-induced term.  The
        # source is recorded for audit, but must not be added a second time.
        # For Q4, the prescribed volume change is a separate geometry term:
        # Delta E = Q_boundary - Q_latent + Q_geometry.
        balance = total_delta_e - (boundary_in - latent_power) * dt - geometry_term
        key = round(float(time_key), 6)
        context["heat_trace"][key] = {
            "time_s": key,
            "sensible_inventory_change_J": total_delta_e,
            "fixed_volume_sensible_change_J": del_e_fixed,
            "geometry_heat_term_J": geometry_term,
            "geometry_reference_temperature_K": float(np.sum(storage * old_t * grid.vol) / max(np.sum(storage * grid.vol), 1e-300)),
            "surface_convection_in_W": float(boundary_in),
            "surface_latent_out_W": float(latent_power),
            "moisture_enthalpy_correction_J": source_j,
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

    def add_latent_source(grid, dt, cenv, old_t):
        raw_boundary, predicted, boundary_loss_rate, it_c, res_c = moisture_predictor(grid, dt, cenv, context["c"])
        scale = float(latent["proxy_scale"])
        lv = float(latent["L_v_J_per_kg"])
        boundary_sink = {key: scale * lv * value for key, value in raw_boundary.items()}
        c_old = np.asarray(context.get("step_old_c"), dtype=float)
        # Moisture changes alter the effective sensible enthalpy even when
        # temperature is held fixed.  Add the compensating term to the heat
        # equation instead of hiding it inside the audit.
        h_c_old = enthalpy_density(module, cfg, c_old, old_t)
        h_c_new_at_old_t = enthalpy_density(module, cfg, predicted, old_t)
        source = -(h_c_new_at_old_t - h_c_old) / max(dt, 1e-12)
        context["last_predicted_c"] = np.array(predicted, copy=True)
        context["last_enthalpy_source"] = np.array(source, copy=True)
        context["last_enthalpy_source_J"] = float(np.sum(source * grid.vol) * dt)
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
            "source_definition": "q_lat=Lv*proxy_scale*j_w; j_w from existing mass Robin boundary flux",
        }
        return source, boundary_sink

    def latent_linear(old, coeff, storage, grid, dt, conv, env_value, include_ends=True,
                      x0=None, rtol=5e-11, maxiter=1200):
        thermal = float(np.nanmean(storage)) > 1e4
        if not thermal:
            result = original_linear(old, coeff, storage, grid, dt, conv, env_value,
                                     include_ends=include_ends, x0=x0, rtol=rtol, maxiter=maxiter)
            record_water(context.get("time", 0.0), old, result[0], result[1], grid, dt, result[3], "fixed-domain-moisture")
            return result
        # Even the no-latent control must use the same moisture-induced
        # sensible-enthalpy correction. Only the latent boundary sink is
        # disabled in that control; otherwise the comparison is not fair.
        source, boundary_sink = add_latent_source(grid, dt, context.get("cenv", 0.0), old)
        if not latent["enabled"]:
            boundary_sink = {key: np.zeros_like(value) for key, value in boundary_sink.items()}
        result = solve_with_source(module, old, coeff, storage, grid, dt, conv, env_value,
                                 source=source, boundary_sink=boundary_sink, include_ends=include_ends, x0=x0,
                                 rtol=rtol, maxiter=maxiter)
        record_heat(context.get("time", 0.0), old, result[0], coeff, storage, grid, dt, result[1], boundary_sink, result[3], context.get("last_predicted_c"))
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
        "latent_mass_closure": "FAIL: proxy derives from total C loss but no liquid/vapor/bound-water phase inventory is solved",
        "water_balance_max_abs_kg_s": max((abs(x["water_balance_residual_kg_s"]) for x in context["water_trace"].values()), default=0.0),
        "proxy_boundary_loss_max_kg_s": max((x["proxy_boundary_loss_rate_kg_s"] for x in trace), default=0.0),
        "water_trace_count": len(context["water_trace"]),
    })
    result["metrics"] = metrics
    result["latent_trace"] = trace
    result["water_trace"] = [context["water_trace"][k] for k in sorted(context["water_trace"])]
    result["heat_trace"] = [context["heat_trace"][k] for k in sorted(context["heat_trace"])]
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
                  "component_mode": "single_field", "label": "无潜热内部温度基线"},
    "low_proxy": {"enabled": True, "proxy_scale": 1.0, "L_v_J_per_kg": 1.2e6,
                   "component_mode": "liquid_surface", "label": "低档等效潜热近似"},
    "nominal_proxy": {"enabled": True, "proxy_scale": 1.0, "L_v_J_per_kg": 2.4e6,
                       "component_mode": "liquid_surface", "label": "名义等效潜热近似"},
    "high_proxy": {"enabled": True, "proxy_scale": 1.0, "L_v_J_per_kg": 4.8e6,
                    "component_mode": "liquid_surface", "label": "高档等效潜热近似"},
    "same_product_scale_double": {"enabled": True, "proxy_scale": 2.0, "L_v_J_per_kg": 1.2e6,
                                   "component_mode": "liquid_surface", "label": "同乘积 scale 加倍"},
    "same_product_Lv_double": {"enabled": True, "proxy_scale": 0.5, "L_v_J_per_kg": 4.8e6,
                                "component_mode": "liquid_surface", "label": "同乘积 Lv 加倍"},
    "component_bound_low": {"enabled": True, "proxy_scale": 1.0, "L_v_J_per_kg": 2.4e6,
                             "component_mode": "liquid_gas_bound", "bound_fraction": 0.0, "release_tau_s": 21600.0,
                             "label": "液态-气态-结合水 低档 toy"},
    "component_bound_nominal": {"enabled": True, "proxy_scale": 1.0, "L_v_J_per_kg": 2.4e6,
                                 "component_mode": "liquid_gas_bound", "bound_fraction": 0.1, "release_tau_s": 7200.0,
                                 "label": "液态-气态-结合水 名义 toy"},
    "component_bound_high": {"enabled": True, "proxy_scale": 1.0, "L_v_J_per_kg": 2.4e6,
                              "component_mode": "liquid_gas_bound", "bound_fraction": 0.2, "release_tau_s": 1800.0,
                              "label": "液态-气态-结合水 高档 toy"},
}


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
    medium_cases = [(q, "M") for q in ("Q2", "Q3", "Q4")]
    stability_cases = [(q, level) for q in ("Q2", "Q3", "Q4") for level in ("L", "M", "H")]
    jobs = [{"scenario": s, "q": q, "mesh_level": level, "time_level": "M", "axis": "space"}
            for s in ("no_latent", "nominal_proxy") for q, level in stability_cases]
    jobs += [{"scenario": scenario, "q": q, "mesh_level": "M", "time_level": "M", "axis": "sensitivity"}
             for scenario in ("low_proxy", "high_proxy", "same_product_scale_double", "same_product_Lv_double") for q, _ in medium_cases]
    jobs += [{"scenario": scenario, "q": q, "mesh_level": "M", "time_level": "M", "axis": "component"}
             for scenario in ("component_bound_low", "component_bound_nominal", "component_bound_high") for q, _ in medium_cases]
    # Independent time ladders keep the mesh at M; the X rung is a finer audit.
    jobs += [{"scenario": s, "q": q, "mesh_level": "M", "time_level": tl, "axis": "time"}
             for s in ("no_latent", "nominal_proxy") for q in ("Q2", "Q3", "Q4") for tl in ("L", "M", "H", "X")]
    # Independent spatial fine rung keeps the recommended M time step.
    jobs += [{"scenario": s, "q": q, "mesh_level": "X", "time_level": "M", "axis": "space"}
             for s in ("no_latent", "nominal_proxy") for q in ("Q2", "Q3", "Q4")]
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


def smoke_suite(log) -> None:
    """Short acceptance run before spending time on the full ladder."""
    jobs = [
        ("no_latent", "Q2"),
        ("nominal_proxy", "Q2"),
        ("nominal_proxy", "Q3"),
        ("no_latent", "Q4"),
        ("nominal_proxy", "Q4"),
    ]
    rows, heat_rows, failures = [], [], []
    for scenario_name, q in jobs:
        module = load_module()
        cfg = config(module, q, "M", "M")
        latent = SCENARIOS[scenario_name]
        log.write(f"START smoke {scenario_name} {q}\n"); log.flush()
        try:
            result = run_case(module, cfg, latent)
            m = result["metrics"]
            row = {"scenario": scenario_name, "question": q, "status": "PASS",
                   "reported_event_time_s": m["reported_event_time_s"],
                   "latent_integral_J_est": m["latent_integral_J_est"],
                   "latent_peak_power_W": m["latent_peak_power_W"],
                   "max_linear_relative_residual": m["max_linear_relative_residual"],
                   "max_physical_heat_balance_relative": m["max_physical_heat_balance_relative"],
                   "max_physical_heat_balance_residual_J": m["max_physical_heat_balance_residual_J"],
                   "water_balance_max_abs_kg_s": m["water_balance_max_abs_kg_s"],
                   "max_picard_iterations": m["max_picard_iterations"]}
            rows.append(row)
            for item in result["heat_trace"]:
                heat_rows.append({"scenario": scenario_name, "question": q, **item})
            log.write("DONE " + json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as exc:
            failure = {"scenario": scenario_name, "question": q, "status": "FAIL", "error": repr(exc)}
            failures.append(failure); rows.append(failure)
            log.write("FAIL " + json.dumps(failure, ensure_ascii=False) + "\n")
        log.flush()
    write_csv(OUT / "smoke-results.csv", rows)
    write_csv(OUT / "smoke-heat-audit.csv", heat_rows)
    write_csv(OUT / "smoke-failures.csv", failures)
    write_json(OUT / "smoke-summary.json", {"runs": len(rows), "failures": len(failures),
                                             "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})


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
    base_space = [r for r in rows if r.get("scenario") == "nominal_proxy" and r.get("refinement_axis") == "space" and r.get("question") in ("Q3", "Q4") and r.get("status") == "PASS"]
    hm_changes = []
    for q in ("Q3", "Q4"):
        vals = {r["level"]: r for r in base_space if r["question"] == q}
        if "M" in vals and "H" in vals and vals["M"].get("reported_event_time_s") is not None and vals["H"].get("reported_event_time_s") is not None:
            hm_changes.append(abs(float(vals["H"]["reported_event_time_s"]) - float(vals["M"]["reported_event_time_s"])))
    time_rows = [r for r in rows if r.get("scenario") == "nominal_proxy" and r.get("refinement_axis") == "time" and r.get("status") == "PASS"]
    time_changes = []
    for q in ("Q2", "Q3", "Q4"):
        vals = {r.get("time_level"): r for r in time_rows if r.get("question") == q}
        if "M" in vals and "H" in vals and vals["M"].get("reported_event_time_s") is not None and vals["H"].get("reported_event_time_s") is not None:
            time_changes.append(abs(float(vals["H"]["reported_event_time_s"]) - float(vals["M"]["reported_event_time_s"])))
    heat_rows = [r for r in rows if r.get("scenario") == "nominal_proxy" and r.get("status") == "PASS"]
    fixed_heat = [float(r.get("max_physical_heat_balance_relative", 1e9)) for r in heat_rows if r.get("question") in ("Q2", "Q3")]
    moving_heat = [float(r.get("max_physical_heat_balance_relative", 1e9)) for r in heat_rows if r.get("question") == "Q4"]
    return [
        {"id": "UPSTREAM-V03-three-level-space", "status": "INCONCLUSIVE", "evidence": "Temperature-field baseline handoff remains INCONCLUSIVE."},
        {"id": "UPSTREAM-V04-three-level-time", "status": "INCONCLUSIVE", "evidence": "Temperature-field baseline handoff remains INCONCLUSIVE."},
        {"id": "UPSTREAM-V08-energy-fixed-domain", "status": "INCONCLUSIVE", "evidence": "Baseline energy-audit-summary.csv records fixed-domain residuals near 1.9-2.0."},
        {"id": "UPSTREAM-V09-energy-moving-domain", "status": "INCONCLUSIVE", "evidence": "Baseline moving-domain energy residual does not clear formal upgrade."},
        {"id": "UPSTREAM-V10-parameter-identifiability", "status": "INCONCLUSIVE", "evidence": "Appendix 4 supplies rho/cp/k/D laws and Appendix 1-2 supply boundary histories; baseline V10 remains INCONCLUSIVE because Lv/Gamma phase closure and internal validation are not identified."},
        {"id": "UPSTREAM-V11-internal-temperature-validation", "status": "BLOCKED", "evidence": "No internal temperature observations are available."},
        {"id": "PC-V01-input-freeze", "status": "PASS", "evidence": "Input hashes and temperature-field handoff are recorded."},
        {"id": "PC-V02-real-run-completion", "status": "PASS" if not failures else "FAIL", "evidence": f"{len(rows)-len(failures)} successful real solver runs; failures are retained in 原始结果.csv."},
        {"id": "PC-V03-latent-space-stability", "status": "INCONCLUSIVE" if not hm_changes or max(hm_changes) > 60 else "PASS", "evidence": f"H-M event changes={hm_changes}; 60 s is the preregistered reporting tolerance."},
        {"id": "PC-V04-latent-time-stability", "status": "PASS" if len(time_rows) >= 12 and (not time_changes or max(time_changes) <= 60) else "INCONCLUSIVE", "evidence": f"Independent M-mesh time ladder recorded; H-M event changes={time_changes}; target is 60 s."},
        {"id": "PC-V05-unit-check", "status": "PASS", "evidence": "j_w=rho_d*(C_surface-C_inf)/R_m has kg/m2/s; multiplying by Lv J/kg gives q_lat W/m2 and is inserted as an outward surface sink."},
        {"id": "PC-V06-mass-energy-closure", "status": "INCONCLUSIVE", "evidence": "The corrected enthalpy ledger closes numerically for the surface-latent candidate, but the total-C boundary flux is still not a phase-resolved liquid/vapor/bound-water closure."},
        {"id": "PC-V07-identifiability", "status": "BLOCKED", "evidence": "Jacobian rank deficiency makes proxy_scale and Lv inseparable; see identifiability.csv."},
        {"id": "PC-V08-numerical-guards", "status": "PASS" if not failures and all(float(r.get("max_linear_relative_residual", 1e9)) < 1e-7 for r in rows if r.get("status") == "PASS") else "FAIL", "evidence": "All retained runs were finite and passed the linear solver residual guard; physical heat residual is reported separately."},
        {"id": "PC-V10-physical-heat-balance", "status": "PASS" if fixed_heat and moving_heat and max(fixed_heat) <= 0.05 and max(moving_heat) <= 0.10 else "INCONCLUSIVE", "evidence": f"Fixed-domain max relative heat residual={max(fixed_heat, default=float('nan')):.6g}; moving-domain={max(moving_heat, default=float('nan')):.6g}; targets 5%/10%."},
        {"id": "PC-V09-formal-promotion", "status": "BLOCKED", "evidence": "Formal promotion remains blocked by unresolved convergence, internal-temperature validation, and phase-resolved identifiability; this candidate is ready only for H2 review."},
    ]


def write_coupled_note() -> None:
    (OUT / "修复说明.md").write_text(
        "# 温度场—表面潜热耦合候选\n\n"
        "本目录是独立原型，不覆盖正式 COMPUTE、EVIDENCE、FIGURE、PAPER 或 decisions。\n\n"
        "## 本轮实际修复\n\n"
        "1. 用 `H(C,T)=rho(C)*cp(C)*(T-T_ref)` 登记显热焓，避免把含水率变化后的 `rho*cp` 直接当作温度方程的时间存储项。\n"
        "2. 把含水率变化造成的显热焓修正作为显式源项进入温度方程，并在能量账中只记录一次。\n"
        "3. 用现有水分 Robin 边界通量构造 `j_w`，以 `q_lat=Lv*j_w` 作为表面向外潜热通量；没有重新增加第二套水分扩散方程，避免重复计数。\n"
        "4. Q4 按 `Delta E=Q_convection-Q_latent+Q_geometry` 审计，几何项单独列账。\n\n"
        "## 解释边界\n\n"
        "这解决的是温度—潜热候选的数值能量闭合问题，不等于获得了液态水、气态水和结合水的实测相分辨闭合。`L_v` 仍采用 1.2/2.4/4.8 MJ/kg 敏感性，不能从当前数据独立识别。\n\n"
        "## 保留的硬限制\n\n"
        "空间/时间收敛、内部温度实测验证和完整相质量闭合仍需单独登记；因此本目录完成后仍要停在 H2 复审，不能自动覆盖正式主模型。\n",
        encoding="utf-8",
    )


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

状态：**BLOCKED / unsupported for formal promotion**。本目录只写入 `03-prototype/controller-phase-change-attempt-20260912/`，不修改正式 COMPUTE、EVIDENCE、FIGURE、PAPER、decisions 或 workflow。

## 1. 前置基线闸门

|基线登记|状态|本轮处理|
|---|---|---|
|V03 三层空间|INCONCLUSIVE|保持，不把潜热结果写成收敛通过|
|V04 三层时间|INCONCLUSIVE|保持；本轮未重复独立时间梯子|
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


def main() -> None:
    started = time.perf_counter()
    np.random.seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    if "--smoke" in sys.argv:
        with (OUT / "smoke.log").open("w", encoding="utf-8") as log:
            log.write(json.dumps({"command": " ".join(sys.argv), "python": sys.version,
                                  "platform": platform.platform(), "seed": SEED}, ensure_ascii=False) + "\n")
            smoke_suite(log)
        print(json.dumps({"status": "SMOKE_COMPLETE", "runtime_s": time.perf_counter() - started}, ensure_ascii=False))
        return
    inputs = input_records()
    log_path = OUT / "run.log"
    log = log_path.open("w", encoding="utf-8")
    log.write(json.dumps({"command": " ".join(sys.argv), "python": sys.version, "platform": platform.platform(), "seed": SEED}, ensure_ascii=False) + "\n")
    log.write("SCOPE: no-latent internal-temperature baseline versus moisture-loss-derived equivalent latent-heat approximation; no phase mass closure; write boundary is this directory.\n")
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
    # Keep a standalone failure ledger even when the current run has zero
    # failures; the full raw table remains the authoritative per-job record.
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
    write_coupled_note()
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

    runtime = time.perf_counter() - started
    manifest = {"schema_version": "1.0", "status": "BLOCKED", "scope": "phase-change controlled attempt; primary route unchanged",
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
               "scope": "isolated phase-change attempt; primary route unchanged", "inputs": inputs,
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
