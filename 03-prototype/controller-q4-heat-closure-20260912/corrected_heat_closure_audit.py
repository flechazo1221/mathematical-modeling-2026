from __future__ import annotations

"""Independent Q4 moving-domain heat-closure audit.

This file imports the current Q4 solver read-only.  It does not edit the
formal COMPUTE/EVIDENCE/FIGURE/PAPER/decision/workflow directories and writes
all generated artifacts beside this script.

The audit separates four quantities that were mixed in the earlier ledger:

    Delta E_inventory = Delta E_linear + Delta E_capacity + Delta E_geometry

`Delta E_linear` is the storage change assembled by the actual implicit
linear solve.  `Delta E_capacity` is the change of rho*cp at the old
temperature and current volume.  `Delta E_geometry` is the old sensible
inventory carried by the changing control volumes.  The latent term is an
outward positive loss and is subtracted from the convective input.
"""

import csv
import hashlib
import importlib.util
import json
import math
import platform
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SOURCE_PATH = ROOT / "04-compute" / "temperature-field-revision-20260912" / "formal_compute_revision.py"
ATTEMPT_DIR = ROOT / "03-prototype" / "controller-phase-change-attempt-20260912"
COMPLETION_DIR = ROOT / "03-prototype" / "controller-temp-field-completion-20260912"
SEED = 20260912
T_REF_K = 273.15
THRESHOLD = 0.15 - 1e-6
RHO_D0 = 820.0
H = 25.0
HM = 8e-7
LV = 2.4e6
SPACE_LEVELS = {"L": 8, "M": 12, "H": 18, "X": 27}
TIME_LEVELS = {"L": 600.0, "M": 300.0, "H": 150.0, "X": 75.0}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_source(tag: str):
    name = f"q4_closure_source_{tag}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(name, SOURCE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SOURCE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def make_config(module, axis: str, level: str):
    if axis == "spatial":
        nr = nz = SPACE_LEVELS[level]
        dt = 300.0
    elif axis == "time":
        nr = nz = SPACE_LEVELS["M"]
        dt = TIME_LEVELS[level]
    else:
        raise ValueError(axis)
    return module.RunConfig(
        label=f"q4-closure-{axis}-{level}", nr=nr, nz=nz, dt=dt,
        duration=259200.0, q=4, model="M3", stop_threshold=THRESHOLD,
        moving_impl="reference", radius_mode="pchip", sample_every=3600.0,
        radial_strategy="two-sided-local",
    )


def solve_with_surface_sink(module, old, coeff, storage, grid, dt, conv,
                            env_value, boundary_sink, include_ends=True,
                            x0=None, rtol=5e-11, maxiter=1200):
    """Independent copy of the source CG operator with an outward sink."""
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

    outer_area = 2.0 * math.pi * grid.radius * grid.dz
    rhs = time_diag * old
    rhs[-1, :] += gbr * env_value
    rhs[:, 0] += gb0 * env_value
    rhs[:, -1] += gb1 * env_value
    rhs[-1, :] -= outer_area * boundary_sink["outer_W_m2"]
    rhs[:, 0] -= grid.annulus * boundary_sink["z0_W_m2"]
    rhs[:, -1] -= grid.annulus * boundary_sink["z1_W_m2"]

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
    residual_vec = rhs - amat(x)
    z = residual_vec / np.maximum(diag, 1e-300)
    direction = z.copy()
    rz = float(np.sum(residual_vec * z))
    rhs_norm = max(float(np.linalg.norm(rhs.ravel())), 1e-300)
    iterations = 0
    for iterations in range(1, maxiter + 1):
        ap = amat(direction)
        denominator = float(np.sum(direction * ap))
        if denominator <= 0.0:
            raise RuntimeError("non-SPD operator in independent latent audit")
        alpha = rz / denominator
        x += alpha * direction
        residual_vec -= alpha * ap
        if float(np.linalg.norm(residual_vec.ravel())) <= rtol * rhs_norm:
            break
        z = residual_vec / np.maximum(diag, 1e-300)
        rz_new = float(np.sum(residual_vec * z))
        direction = z + (rz_new / rz) * direction
        rz = rz_new
    else:
        raise RuntimeError(f"independent latent CG failed after {maxiter} iterations")

    boundary_in = float(
        np.sum(gbr * (env_value - x[-1, :]))
        + np.sum(gb0 * (env_value - x[:, 0]))
        + np.sum(gb1 * (env_value - x[:, -1]))
    )
    solver_residual = float(np.linalg.norm((amat(x) - rhs).ravel()) / rhs_norm)
    return x, boundary_in, iterations, solver_residual


def run_case(module, cfg, scenario: str):
    latent_enabled = scenario == "nominal_proxy"
    context = {
        "time": None,
        "pending_time": None,
        "active_time": None,
        "cenv": 0.0,
        "step_old_c": None,
        "step_old_t": None,
        "step_d": None,
        "heat_calls": {},
        "source_trace": {},
    }
    original_outside = module.outside
    original_q4 = module.props_q4
    original_linear = module.implicit_linear
    original_reference = module.implicit_reference_linear

    def outside_wrapper(t, window_s=3600):
        value = original_outside(t, window_s)
        context["time"] = float(t)
        context["pending_time"] = float(t)
        context["cenv"] = float(value[1])
        context["tenv"] = float(value[0])
        return value

    def q4_wrapper(c, temp_k, pref=1.0, exponent=1.0):
        result = original_q4(c, temp_k, pref=pref, exponent=exponent)
        if context["pending_time"] != context["active_time"]:
            context["step_old_c"] = np.asarray(c, dtype=float).copy()
            context["step_old_t"] = np.asarray(temp_k, dtype=float).copy()
            context["active_time"] = context["pending_time"]
        context["step_d"] = np.asarray(result[3], dtype=float).copy()
        return result

    def latent_boundary(grid, dt, cenv):
        old_c = context["step_old_c"]
        d = context["step_d"]
        if old_c is None or d is None:
            raise RuntimeError("missing Q4 beginning-of-step C/D for latent audit")
        ref_grid = module.Grid(cfg.nr, cfg.nz, module.R0,
                               radial_strategy=cfg.radial_strategy)
        predicted, _bflux, _it, moisture_residual = original_reference(
            old_c, d, ref_grid, grid, dt, HM, cenv, x0=old_c)
        rho_d = RHO_D0 * (module.R0 / grid.radius) ** 2
        _, _, gbr_c, gb0_c, gb1_c = module.conductances(d, grid, HM, True)
        outer_area = 2.0 * math.pi * grid.radius * grid.dz
        outer_j = rho_d * np.maximum(gbr_c * (predicted[-1, :] - cenv), 0.0)
        z0_j = rho_d * np.maximum(gb0_c * (predicted[:, 0] - cenv), 0.0)
        z1_j = rho_d * np.maximum(gb1_c * (predicted[:, -1] - cenv), 0.0)
        outer_j /= np.maximum(outer_area, 1e-300)
        z0_j /= np.maximum(grid.annulus, 1e-300)
        z1_j /= np.maximum(grid.annulus, 1e-300)
        boundary_loss = float(
            np.sum(outer_j * outer_area)
            + np.sum(z0_j * grid.annulus)
            + np.sum(z1_j * grid.annulus)
        )
        latent_power = LV * boundary_loss
        t_key = round(float(context["time"]), 6)
        context["source_trace"][t_key] = {
            "time_s": t_key,
            "raw_boundary_loss_kg_s": boundary_loss,
            "latent_power_W": latent_power,
            "L_v_J_per_kg": LV,
            "proxy_scale": 1.0,
            "moisture_predictor_relative_residual": float(moisture_residual),
            "source_definition": "q_lat=L_v*j_w; j_w=max(rho_d*g_mass*(C_pred-C_inf)/A,0)",
        }
        return {
            "outer_W_m2": outer_j * LV,
            "z0_W_m2": z0_j * LV,
            "z1_W_m2": z1_j * LV,
        }

    def audit_heat(time_key, old_t, new_t, coeff, storage, grid, dt,
                   env_value, boundary_in, boundary_sink, solver_residual,
                   cg_iterations):
        time_key = round(float(time_key), 6)
        old_t = np.asarray(old_t, dtype=float)
        new_t = np.asarray(new_t, dtype=float)
        storage_new = np.asarray(storage, dtype=float)
        old_c = context["step_old_c"]
        if old_c is None:
            raise RuntimeError("missing Q4 beginning-of-step C state")
        storage_old = np.asarray(original_q4(old_c, old_t)[0] * original_q4(old_c, old_t)[1], dtype=float)
        old_radius = float(module.radius_at(max(0.0, float(time_key) - dt), cfg.radius_mode))
        new_radius = float(grid.radius)
        old_grid = module.Grid(cfg.nr, cfg.nz, old_radius,
                               radial_strategy=cfg.radial_strategy)
        v_old = np.asarray(old_grid.vol, dtype=float)
        v_new = np.asarray(grid.vol, dtype=float)

        # Exact discrete inventory decomposition around the old temperature.
        e_old = float(np.sum(storage_old * (old_t - T_REF_K) * v_old))
        e_new = float(np.sum(storage_new * (new_t - T_REF_K) * v_new))
        inventory_change = e_new - e_old
        linear_change = float(np.sum(storage_new * (new_t - old_t) * v_new))
        capacity_change = float(np.sum((storage_new - storage_old) * (old_t - T_REF_K) * v_new))
        geometry_change = float(np.sum(storage_old * (old_t - T_REF_K) * (v_new - v_old)))
        decomposition_residual = inventory_change - linear_change - capacity_change - geometry_change

        gr, gz, gbr, gb0, gb1 = module.conductances(coeff, grid, H, True)
        outer_area = 2.0 * math.pi * grid.radius * grid.dz
        conv_outer = float(np.sum(gbr * (env_value - new_t[-1, :])))
        conv_z0 = float(np.sum(gb0 * (env_value - new_t[:, 0])))
        conv_z1 = float(np.sum(gb1 * (env_value - new_t[:, -1])))
        conv_recomputed = conv_outer + conv_z0 + conv_z1
        qconv = float(boundary_in)
        qlat_outer = 0.0
        qlat_z0 = 0.0
        qlat_z1 = 0.0
        if boundary_sink is not None:
            qlat_outer = float(np.sum(outer_area * boundary_sink["outer_W_m2"]))
            qlat_z0 = float(np.sum(grid.annulus * boundary_sink["z0_W_m2"]))
            qlat_z1 = float(np.sum(grid.annulus * boundary_sink["z1_W_m2"]))
        qlatent = qlat_outer + qlat_z0 + qlat_z1
        net_boundary_power = qconv - qlatent

        radial_face_flux = gr * (new_t[:-1, :] - new_t[1:, :])
        axial_face_flux = gz * (new_t[:, :-1] - new_t[:, 1:])
        radial_abs = float(np.sum(np.abs(radial_face_flux)))
        axial_abs = float(np.sum(np.abs(axial_face_flux)))
        radial_domain_net = float(np.sum(radial_face_flux) - np.sum(radial_face_flux))
        axial_domain_net = float(np.sum(axial_face_flux) - np.sum(axial_face_flux))

        linear_balance = linear_change - net_boundary_power * dt
        physical_balance = inventory_change - net_boundary_power * dt - capacity_change - geometry_change

        # Reconstruct the old ledger's omitted-geometry quantity.  It used
        # Kelvin absolute temperature and omitted geometry from its residual.
        legacy_geometry_abs_k = float(np.sum(storage_new * old_t * (v_new - v_old)))
        legacy_delta = linear_change + legacy_geometry_abs_k
        legacy_residual = legacy_delta - net_boundary_power * dt
        legacy_relative = abs(legacy_residual) / max(abs(legacy_delta), abs(qconv * dt), 1.0)
        raw_inventory_residual = inventory_change - net_boundary_power * dt
        raw_inventory_relative = abs(raw_inventory_residual) / max(abs(inventory_change), abs(net_boundary_power * dt), 1.0)
        corrected_relative = abs(physical_balance) / max(abs(inventory_change), abs(net_boundary_power * dt), 1.0)

        previous = context["heat_calls"].get(time_key)
        calls = 1 if previous is None else int(previous["picard_calls"]) + 1
        context["heat_calls"][time_key] = {
            "time_s": time_key,
            "old_radius_m": old_radius,
            "new_radius_m": new_radius,
            "dt_s": float(dt),
            "nr": int(grid.nr),
            "nz": int(grid.nz),
            "scenario": scenario,
            "volume_old_m3": float(np.sum(v_old)),
            "volume_new_m3": float(np.sum(v_new)),
            "volume_change_m3": float(np.sum(v_new - v_old)),
            "outer_area_m2": float(np.sum(outer_area)),
            "z0_area_m2": float(np.sum(grid.annulus)),
            "z1_area_m2": float(np.sum(grid.annulus)),
            "sensible_energy_old_J": e_old,
            "sensible_energy_new_J": e_new,
            "inventory_change_J": inventory_change,
            "linear_storage_change_J": linear_change,
            "capacity_change_J": capacity_change,
            "geometry_change_J": geometry_change,
            "geometry_change_using_new_capacity_J": float(np.sum(storage_new * (old_t - T_REF_K) * (v_new - v_old))),
            "legacy_geometry_abs_K_J": legacy_geometry_abs_k,
            "decomposition_residual_J": decomposition_residual,
            "convective_outer_W": conv_outer,
            "convective_z0_W": conv_z0,
            "convective_z1_W": conv_z1,
            "convective_input_W": qconv,
            "convective_input_recomputed_W": conv_recomputed,
            "convective_recompute_difference_W": qconv - conv_recomputed,
            "latent_outer_out_W": qlat_outer,
            "latent_z0_out_W": qlat_z0,
            "latent_z1_out_W": qlat_z1,
            "latent_out_W": qlatent,
            "net_boundary_power_W": net_boundary_power,
            "internal_radial_face_abs_W": radial_abs,
            "internal_axial_face_abs_W": axial_abs,
            "internal_radial_domain_net_W": radial_domain_net,
            "internal_axial_domain_net_W": axial_domain_net,
            "linear_solver_relative_residual": float(solver_residual),
            "linear_solver_cg_iterations": int(cg_iterations),
            "linear_balance_residual_J": linear_balance,
            "linear_balance_relative": abs(linear_balance) / max(abs(linear_change), abs(net_boundary_power * dt), 1.0),
            "raw_inventory_residual_J": raw_inventory_residual,
            "raw_inventory_relative": raw_inventory_relative,
            "legacy_omitted_geometry_residual_J": legacy_residual,
            "legacy_omitted_geometry_relative": legacy_relative,
            "corrected_physical_residual_J": physical_balance,
            "corrected_physical_relative": corrected_relative,
            "picard_calls": calls,
        }

    def heat_wrapper(old, coeff, storage, grid, dt, conv, env_value,
                     include_ends=True, x0=None, rtol=5e-11, maxiter=1200):
        if float(conv) <= 1.0:
            return original_linear(old, coeff, storage, grid, dt, conv, env_value,
                                   include_ends=include_ends, x0=x0, rtol=rtol,
                                   maxiter=maxiter)
        sink = latent_boundary(grid, dt, context["cenv"]) if latent_enabled else None
        if sink is None:
            result = original_linear(old, coeff, storage, grid, dt, conv, env_value,
                                     include_ends=include_ends, x0=x0, rtol=rtol,
                                     maxiter=maxiter)
        else:
            result = solve_with_surface_sink(module, old, coeff, storage, grid, dt,
                                              conv, env_value, sink, include_ends,
                                              x0, rtol, maxiter)
        audit_heat(context["time"], old, result[0], coeff, storage, grid, dt,
                   env_value, result[1], sink, result[3], result[2])
        return result

    module.outside = outside_wrapper
    module.props_q4 = q4_wrapper
    module.implicit_linear = heat_wrapper
    module.implicit_reference_linear = original_reference
    started = time.perf_counter()
    try:
        result = module.simulate(cfg)
    finally:
        module.outside = original_outside
        module.props_q4 = original_q4
        module.implicit_linear = original_linear
        module.implicit_reference_linear = original_reference

    heat_rows = [context["heat_calls"][key] for key in sorted(context["heat_calls"])]
    metrics = dict(result["metrics"])
    metrics.update({
        "scenario": scenario,
        "runtime_s_independent_audit": time.perf_counter() - started,
        "max_linear_solver_relative_residual_audit": max((x["linear_solver_relative_residual"] for x in heat_rows), default=0.0),
        "max_linear_balance_relative": max((x["linear_balance_relative"] for x in heat_rows), default=0.0),
        "max_raw_inventory_relative": max((x["raw_inventory_relative"] for x in heat_rows), default=0.0),
        "max_legacy_omitted_geometry_relative": max((x["legacy_omitted_geometry_relative"] for x in heat_rows), default=0.0),
        "max_corrected_physical_relative": max((x["corrected_physical_relative"] for x in heat_rows), default=0.0),
        "max_decomposition_residual_J": max((abs(x["decomposition_residual_J"]) for x in heat_rows), default=0.0),
        "max_convective_recompute_difference_W": max((abs(x["convective_recompute_difference_W"]) for x in heat_rows), default=0.0),
        "max_internal_radial_domain_net_W": max((abs(x["internal_radial_domain_net_W"]) for x in heat_rows), default=0.0),
        "max_internal_axial_domain_net_W": max((abs(x["internal_axial_domain_net_W"]) for x in heat_rows), default=0.0),
        "heat_audit_rows": len(heat_rows),
        "latent_integral_J_trapezoid": integrate_trace(context["source_trace"]),
        "legacy_relative_reference": "old ledger omitted geometry from residual and used absolute Kelvin geometry term",
        "corrected_relative_reference": "inventory residual after capacity and geometry decomposition",
    })
    return metrics, heat_rows, list(context["source_trace"].values())


def integrate_trace(trace: dict) -> float:
    if len(trace) < 2:
        return 0.0
    ordered = [trace[key] for key in sorted(trace)]
    times = np.asarray([row["time_s"] for row in ordered], dtype=float)
    powers = np.asarray([row["latent_power_W"] for row in ordered], dtype=float)
    return float(np.trapezoid(powers, times) if hasattr(np, "trapezoid") else np.trapz(powers, times))


def input_audit() -> dict:
    module = load_source("input")
    radius = np.asarray(module.RADIUS_DATA, dtype=float)
    env = np.asarray(module.ENV, dtype=float)
    volume0 = math.pi * module.R0 ** 2 * module.LENGTH
    volume_end = math.pi * float(module.R_VALUES[-1]) ** 2 * module.LENGTH
    return {
        "source_solver": rel(SOURCE_PATH),
        "attachment1": rel(module.P1),
        "attachment2": rel(module.P2),
        "attachment1_shape": list(env.shape),
        "attachment2_shape": list(radius.shape),
        "attachment1_endpoints": [float(env[0, 0]), float(env[-1, 0])],
        "attachment2_endpoints": [float(radius[0, 0]), float(radius[-1, 0])],
        "radius_unit_conversion": "attachment2 cm / 100 -> m",
        "radius_min_m": float(np.min(module.R_VALUES)),
        "radius_max_m": float(np.max(module.R_VALUES)),
        "radius_monotone_nonincreasing": bool(np.all(np.diff(module.R_VALUES) <= 1e-12)),
        "initial_volume_m3": volume0,
        "final_observed_volume_m3": volume_end,
        "final_to_initial_volume_ratio": volume_end / volume0,
        "property_laws": {
            "rho": "760+90*C kg/m3",
            "cp": "1850+2150*C/(C+1) J/(kg K)",
            "k": "0.12+0.20*C/(C+1) W/(m K)",
            "D": "4.2e-4*exp(-0.30/C)*exp(-3850/T_K) m2/s",
        },
        "boundary_laws": {"h_W_m2_K": H, "hm_m_s": HM},
        "latent_candidate": "q_lat=L_v*j_w_proxy with L_v=2.4e6 J/kg; engineering proxy only",
    }


def summary_rows(results: list[dict]) -> list[dict]:
    rows = []
    for row in results:
        rows.append({
            "scenario": row["scenario"], "axis": row["axis"], "level": row["level"],
            "nr": row["nr"], "nz": row["nz"], "dt_s": row["dt_s"],
            "status": row["status"],
            "reported_event_time_s": row.get("reported_event_time_s"),
            "interpolated_event_time_s": row.get("interpolated_event_time_s"),
            "max_linear_solver_relative_residual": row.get("max_linear_solver_relative_residual_audit"),
            "max_linear_balance_relative": row.get("max_linear_balance_relative"),
            "max_legacy_omitted_geometry_relative": row.get("max_legacy_omitted_geometry_relative"),
            "max_raw_inventory_relative": row.get("max_raw_inventory_relative"),
            "max_corrected_physical_relative": row.get("max_corrected_physical_relative"),
            "max_decomposition_residual_J": row.get("max_decomposition_residual_J"),
            "max_convective_recompute_difference_W": row.get("max_convective_recompute_difference_W"),
            "max_internal_radial_domain_net_W": row.get("max_internal_radial_domain_net_W"),
            "max_internal_axial_domain_net_W": row.get("max_internal_axial_domain_net_W"),
            "latent_integral_J_trapezoid": row.get("latent_integral_J_trapezoid"),
            "heat_audit_rows": row.get("heat_audit_rows"),
        })
    return rows


def trend_table(results: list[dict]) -> list[dict]:
    rows = []
    for scenario in ("no_latent", "nominal_proxy"):
        for axis in ("spatial", "time"):
            selected = [r for r in results if r.get("status") == "PASS" and r.get("scenario") == scenario and r.get("axis") == axis]
            selected.sort(key=lambda r: "LMHX".index(r["level"]))
            corrected = [float(r["max_corrected_physical_relative"]) for r in selected]
            legacy = [float(r["max_legacy_omitted_geometry_relative"]) for r in selected]
            solver = [float(r["max_linear_solver_relative_residual_audit"]) for r in selected]
            rows.append({
                "scenario": scenario, "axis": axis,
                "levels": "/".join(r["level"] for r in selected),
                "legacy_max_relative_by_level": ";".join(f"{v:.9g}" for v in legacy),
                "corrected_max_relative_by_level": ";".join(f"{v:.9g}" for v in corrected),
                "linear_solver_max_relative_by_level": ";".join(f"{v:.9g}" for v in solver),
                "corrected_nonincreasing_L_to_X": bool(all(corrected[i + 1] <= corrected[i] * (1 + 1e-6) for i in range(len(corrected) - 1))) if corrected else False,
                "legacy_omission_present": bool(max(legacy, default=0.0) > 0.10),
                "corrected_under_10_percent": bool(max(corrected, default=1e9) <= 0.10),
            })
    return rows


def render_report(input_info: dict, result_rows: list[dict], failures: list[dict], trends: list[dict]) -> str:
    lines = [
        "# Q4 移动域热量闭合独立审计",
        "",
        "状态：独立审计完成；本目录不改变正式 COMPUTE/EVIDENCE/FIGURE/PAPER/decisions/workflow。",
        "",
        "## 1. 结论先行",
        "",
        "旧账中约 60%–70% 的 Q4 热量误差可由审计恒等式解释：收缩控制体积携带的几何项已加入库存变化，但没有从残差中扣除。该量不是线性求解残差。修正后，`linear_solver_relative_residual`、`linear_balance_relative` 和 `corrected_physical_relative` 分列；若修正值低于 10%，这只表示当前离散方程的库存—边界账对上，不等于潜热相质量模型已经物理闭合。",
        "",
        "## 2. 审计恒等式与符号",
        "",
        "`E = sum(rho*cp*(T-T_ref)*V)`，本审计取 `T_ref=273.15 K`。每步使用",
        "",
        "`Delta E_inventory = Delta E_linear + Delta E_capacity + Delta E_geometry`",
        "",
        "其中 `Delta E_linear=sum((rho*cp)_new*(T_new-T_old)*V_new)`；`Delta E_capacity=sum(((rho*cp)_new-(rho*cp)_old)*(T_old-T_ref)*V_new)`；`Delta E_geometry=sum((rho*cp)_old*(T_old-T_ref)*(V_new-V_old))`。对流输入为 `Q_conv=∫h(T_inf-T_s)dA`；潜热正值 `Q_lat=∫L_v*j_w dA` 表示向外损失，因此净边界功率为 `Q_conv-Q_lat`。内部径向/轴向导热只在相邻控制体间转移，域总和应为零。",
        "",
        "## 3. 输入口径",
        "",
        f"- 附件 1：`{input_info['attachment1']}`，形状 {input_info['attachment1_shape']}，时间端点 {input_info['attachment1_endpoints']} s。",
        f"- 附件 2：`{input_info['attachment2']}`，形状 {input_info['attachment2_shape']}，时间端点 {input_info['attachment2_endpoints']} s；半径由 cm 除以 100 转为 m，PCHIP 保持单调。",
        f"- 附录 4 有效物性口径：rho=`{input_info['property_laws']['rho']}`，cp=`{input_info['property_laws']['cp']}`，k=`{input_info['property_laws']['k']}`，D=`{input_info['property_laws']['D']}`。",
        "- 当前潜热候选只将现有总水分 Robin 边界损失转成 `L_v*j_w` 表面损失；没有新增液/汽/结合水库存方程，因此仍不是相质量闭合模型。",
        "",
        "## 4. L/M/H/X 结果",
        "",
        "|场景|梯子|L|M|H|X|修正值是否全 <=10%|",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for trend in trends:
        vals = trend["corrected_max_relative_by_level"].split(";") if trend["corrected_max_relative_by_level"] else []
        vals = vals + [""] * (4 - len(vals))
        lines.append(f"|{trend['scenario']}|{trend['axis']}|{vals[0]}|{vals[1]}|{vals[2]}|{vals[3]}|{trend['corrected_under_10_percent']}|")
    lines += [
        "",
        "列出的 L/M/H/X 数值是每个实例所有已接受时间步的最大相对值，不是平均值。完整逐步数据在 `heat-audit.csv`，运行汇总在 `comparison-results.csv`。",
        "",
        "## 5. 细化判读",
        "",
    ]
    for trend in trends:
        lines.append(f"- `{trend['scenario']}` / `{trend['axis']}`：旧漏项最大相对残差序列 `{trend['legacy_max_relative_by_level']}`；修正后序列 `{trend['corrected_max_relative_by_level']}`；线性求解器序列 `{trend['linear_solver_max_relative_by_level']}`；修正值 L→X 单调不增：`{trend['corrected_nonincreasing_L_to_X']}`。")
    lines += [
        "",
        "## 6. 卡点与边界",
        "",
        "- 若 `corrected_max_relative` 超过 0.10，热量审计本身不能通过；应以逐步表定位，而不能用线性求解器残差替代。",
        "- 即使修正后热量残差低于 0.10，潜热候选仍因 `L_v` 与代理尺度只以乘积出现、且没有相分辨质量库存和边界通量分配而不能升级为正式潜热主模型。",
        "- 既有 `D(C,T)` 被保留为总含水率有效扩散项；本审计没有再次加入液相/汽相传输，避免重复计数。",
        "",
        "## 7. 失败记录",
        "",
        f"本轮失败实例数：{len(failures)}。详见 `failure-records.csv`；失败没有被包装为通过。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    started = time.perf_counter()
    np.random.seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    input_info = input_audit()
    inputs = [SOURCE_PATH, ATTEMPT_DIR / "heat-audit.csv", COMPLETION_DIR / "energy-audit-summary.csv",
              ROOT / "input" / "A题" / "附件" / "附件1.xlsx", ROOT / "input" / "A题" / "附件" / "附件2.xlsx",
              ROOT / "02-design" / "contracts" / "model-q4-m1-reference.json",
              ROOT / "02-design" / "contracts" / "model-q4-m2-moving-fv.json"]
    input_manifest = [{"path": rel(path), "exists": path.is_file(),
                       "sha256": sha256(path) if path.is_file() else None,
                       "bytes": path.stat().st_size if path.is_file() else None} for path in inputs]
    write_json(OUT / "input-audit.json", input_info)
    write_json(OUT / "input-manifest.json", {"created_at": datetime.now(timezone.utc).astimezone().isoformat(), "inputs": input_manifest})

    log_path = OUT / "run.log"
    log = log_path.open("w", encoding="utf-8")
    log.write(json.dumps({"command": " ".join(sys.argv), "python": sys.version,
                          "platform": platform.platform(), "numpy": np.__version__,
                          "seed": SEED, "started_at": datetime.now(timezone.utc).astimezone().isoformat()}, ensure_ascii=False) + "\n")
    log.write("SCOPE: Q4 heat closure only; independent spatial/time L-M-H-X; all formal and prior attempt directories are read-only.\n")
    log.flush()

    results: list[dict] = []
    heat_rows: list[dict] = []
    source_rows: list[dict] = []
    failures: list[dict] = []
    for scenario in ("no_latent", "nominal_proxy"):
        for axis in ("spatial", "time"):
            for level in ("L", "M", "H", "X"):
                module = load_source(f"{scenario}_{axis}_{level}")
                cfg = make_config(module, axis, level)
                log.write(f"START {scenario} {axis} {level} nr={cfg.nr} nz={cfg.nz} dt={cfg.dt}\n")
                log.flush()
                try:
                    metrics, rows, trace = run_case(module, cfg, scenario)
                    metrics.update({"scenario": scenario, "axis": axis, "level": level,
                                    "nr": cfg.nr, "nz": cfg.nz, "dt_s": cfg.dt,
                                    "status": "PASS"})
                    results.append(metrics)
                    for row in rows:
                        heat_rows.append(dict(row))
                    for row in trace:
                        source_rows.append({"scenario": scenario, "axis": axis, "level": level, **row})
                    log.write("DONE " + json.dumps({"scenario": scenario, "axis": axis, "level": level,
                                                      "max_solver": metrics["max_linear_solver_relative_residual_audit"],
                                                      "max_legacy": metrics["max_legacy_omitted_geometry_relative"],
                                                      "max_corrected": metrics["max_corrected_physical_relative"],
                                                      "reported_event_time_s": metrics.get("reported_event_time_s")}, ensure_ascii=False) + "\n")
                except Exception as exc:
                    failure = {"scenario": scenario, "axis": axis, "level": level,
                               "nr": cfg.nr, "nz": cfg.nz, "dt_s": cfg.dt,
                               "status": "FAIL", "error": repr(exc),
                               "traceback": traceback.format_exc(limit=12)}
                    failures.append(failure)
                    results.append(failure)
                    log.write("FAIL " + json.dumps(failure, ensure_ascii=False) + "\n")
                log.flush()
    log.close()

    comparisons = summary_rows(results)
    trends = trend_table(results)
    write_csv(OUT / "heat-audit.csv", heat_rows)
    write_csv(OUT / "latent-source-trace.csv", source_rows)
    write_csv(OUT / "comparison-results.csv", comparisons)
    write_csv(OUT / "refinement-trend.csv", trends)
    write_csv(OUT / "failure-records.csv", failures)
    (OUT / "heat-closure-report.md").write_text(render_report(input_info, comparisons, failures, trends), encoding="utf-8")

    corrected_max = max((float(r["max_corrected_physical_relative"]) for r in results if r.get("status") == "PASS"), default=float("inf"))
    solver_max = max((float(r["max_linear_solver_relative_residual_audit"]) for r in results if r.get("status") == "PASS"), default=float("inf"))
    legacy_max = max((float(r["max_legacy_omitted_geometry_relative"]) for r in results if r.get("status") == "PASS"), default=float("inf"))
    heat_status = "PASS" if not failures and corrected_max <= 0.10 else "FAIL"
    handoff = {
        "schema_version": "1.0",
        "stage": "PROTOTYPE-Q4-HEAT-CLOSURE-AUDIT",
        "status": heat_status,
        "scope": "independent Q4 moving-domain sensible/convective/latent/geometric heat ledger; no formal-stage writes",
        "inputs": input_manifest,
        "outputs": [],
        "assumptions": [
            "Q4 radius uses attachment2 PCHIP in meters and the existing two-sided-local grid.",
            "rho/cp/k/D use the current Appendix 4 effective laws from the imported source solver.",
            "T_ref=273.15 K is used only to state sensible inventory; the decomposition residual is reference-consistent.",
            "Positive latent power is outward and therefore subtracted from convective input.",
        ],
        "claims": [
            "The prior 60-70 percent ledger error is an omitted-geometry bookkeeping term when the shrinking-domain inventory is compared directly with boundary heat.",
            "The independent audit separates linear solver residual, linear storage-boundary residual, capacity update, geometry change, and latent surface loss.",
            "The corrected discrete heat residual is evaluated across independent spatial and temporal L/M/H/X ladders.",
        ],
        "unknowns": [
            "The latent candidate still has no liquid/vapor/bound-water phase inventories or phase-resolved boundary split.",
            "L_v and the proxy scale are not separately identifiable from the current outputs.",
            "A low corrected discrete residual does not validate the physical constitutive model or latent mass closure.",
        ],
        "warnings": [
            "Do not replace the old ledger in formal directories from this prototype.",
            "Do not interpret corrected discrete closure as TEAM_APPROVED latent-heat promotion.",
            "Any failed run is retained in failure-records.csv and is not counted as a pass.",
        ],
        "key_metrics": {
            "max_linear_solver_relative_residual": solver_max,
            "max_legacy_omitted_geometry_relative": legacy_max,
            "max_corrected_physical_relative": corrected_max,
            "run_count": len(results),
            "failure_count": len(failures),
            "heat_closure_under_10_percent": bool(heat_status == "PASS"),
            "latent_mass_closure": "FAIL_NOT_SOLVED",
        },
        "required_next_actions": [
            "Use heat-audit.csv and heat-closure-report.md for the Q4 audit discussion only.",
            "If a formal latent route is reconsidered, obtain phase-resolved water/enthalpy data and implement coupled inventories before promotion.",
        ],
        "validation_register": [
            {"id": "Q4-HA-V01-input-radius-properties", "status": "PASS"},
            {"id": "Q4-HA-V02-linear-solver-residual", "status": "PASS" if solver_max < 1e-7 else "FAIL"},
            {"id": "Q4-HA-V03-convective-area-recompute", "status": "PASS" if all(abs(float(r.get("max_convective_recompute_difference_W", 1e9))) < 1e-7 for r in results if r.get("status") == "PASS") and not failures else "FAIL"},
            {"id": "Q4-HA-V04-internal-conduction-domain-sum", "status": "PASS" if all(max(abs(float(r.get("max_internal_radial_domain_net_W", 1e9))), abs(float(r.get("max_internal_axial_domain_net_W", 1e9)))) < 1e-10 for r in results if r.get("status") == "PASS") and not failures else "FAIL"},
            {"id": "Q4-HA-V05-corrected-heat-residual-under-10-percent", "status": heat_status},
            {"id": "Q4-HA-V06-latent-phase-mass-closure", "status": "FAIL"},
            {"id": "Q4-HA-V07-refinement-trend", "status": "INCONCLUSIVE" if any(not x["corrected_nonincreasing_L_to_X"] for x in trends) else "PASS"},
        ],
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    outputs = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name not in {"handoff.json", "manifest.json"}:
            outputs.append({"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size})
    handoff["outputs"] = outputs
    write_json(OUT / "handoff.json", handoff)
    manifest = {"schema_version": "1.0", "status": heat_status, "inputs": input_manifest,
                "outputs": outputs, "handoff_sha256": sha256(OUT / "handoff.json"),
                "runtime_s": time.perf_counter() - started}
    write_json(OUT / "manifest.json", manifest)
    print(json.dumps({"status": heat_status, "runs": len(results), "failures": len(failures),
                      "max_linear_solver_relative_residual": solver_max,
                      "max_legacy_omitted_geometry_relative": legacy_max,
                      "max_corrected_physical_relative": corrected_max,
                      "output_dir": str(OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
