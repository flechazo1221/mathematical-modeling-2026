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


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SEED = 20260911
SEEDS = [20260911, 20260912, 20260913]


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_formal_compute():
    path = ROOT / "04-compute" / "src" / "formal_compute.py"
    spec = importlib.util.spec_from_file_location("formal_compute", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def generate_pde_scenarios():
    fc = load_formal_compute()
    rng = np.random.default_rng(SEED)
    rows, fields = [], []
    # 120 genuinely executed low-resolution M3/M4 scenarios.  The small mesh is
    # deliberate: this is a prototype-feasibility screen, not replacement evidence.
    for i in range(120):
        q = 3 if i % 2 == 0 else 4
        hm = float(rng.uniform(0.78, 1.22))
        pref = float(rng.uniform(0.88, 1.12))
        exponent = float(rng.uniform(0.94, 1.06))
        cfg = fc.RunConfig(
            label=f"SUP-{q}-{i:02d}", nr=8, nz=12, dt=300,
            duration=259200, q=q, model="M3", hm_mult=hm,
            pref=pref, exponent=exponent, stop_threshold=.15 - 1e-6,
            moving_impl="reference" if q == 4 else "fixed",
            sample_every=1800,
        )
        t0 = time.perf_counter()
        run = fc.simulate(cfg)
        elapsed = time.perf_counter() - t0
        event = run["metrics"]["interpolated_event_time_s"]
        if event is None:
            event = run["metrics"]["final_time_s"]
        rows.append({
            "scenario": i, "q": q, "hm_mult": hm, "pref_mult": pref,
            "exponent_mult": exponent, "event_time_s": float(event),
            "final_mean_C": run["metrics"]["final_mean_C"],
            "balance_error": run["metrics"]["normalized_moisture_balance_error"],
            "runtime_s": elapsed,
        })
        fields.append(run["final_c"].reshape(-1))
    return rows, np.asarray(fields)


def split_indices(rows):
    # Whole-scenario frozen 72/16/16/16 split. The 16 most extreme cases are
    # reserved as one-factor-style extrapolation proxies; the rest are shuffled.
    X = np.array([[r["q"] == 4, r["hm_mult"], r["pref_mult"], r["exponent_mult"]] for r in rows], float)
    edge = np.argsort(np.max(np.abs(X[:, 1:] - 1.0), axis=1))[-16:]
    rest = np.array([i for i in range(len(rows)) if i not in set(edge)])
    rng = np.random.default_rng(SEED)
    rng.shuffle(rest)
    return rest[:72], rest[88:104], edge, rest[72:88]


def standardize(X, idx):
    mu, sd = X[idx].mean(0), X[idx].std(0)
    sd[sd < 1e-12] = 1.0
    return (X - mu) / sd, mu, sd


def ridge_fit(X, Y, alpha=1e-6):
    A = np.c_[np.ones(len(X)), X]
    reg = alpha * np.eye(A.shape[1]); reg[0, 0] = 0
    return np.linalg.solve(A.T @ A + reg, A.T @ Y)


def ridge_predict(X, W):
    return np.c_[np.ones(len(X)), X] @ W


def metrics(y, yp):
    e = np.asarray(yp) - np.asarray(y)
    return {"rmse": float(np.sqrt(np.mean(e * e))), "mae": float(np.mean(np.abs(e))), "max_abs": float(np.max(np.abs(e)))}


def pure_ml(rows, train, test, extra):
    X = np.array([[r["q"] == 4, r["hm_mult"], r["pref_mult"], r["exponent_mult"]] for r in rows], float)
    y = np.array([r["event_time_s"] for r in rows], float)
    Z, mu, sd = standardize(X, train)
    # Supervised-only polynomial ridge: no PDE residual or conservation term.
    P = np.c_[Z, Z[:, 1:] ** 2, Z[:, 1] * Z[:, 2], Z[:, 1] * Z[:, 3], Z[:, 2] * Z[:, 3]]
    t0 = time.perf_counter(); W = ridge_fit(P[train], y[train], 1e-4); train_s = time.perf_counter() - t0
    t1 = time.perf_counter(); pred = ridge_predict(P, W); infer_s = (time.perf_counter() - t1) / len(rows)
    result = {
        "model": "pure-ML polynomial ridge", "physics_loss": False,
        "train_s": train_s, "inference_s_per_case": infer_s,
        "parameters": int(W.size), "test": metrics(y[test], pred[test]),
        "extrapolation": metrics(y[extra], pred[extra]),
        "test_event_errors_s": [float(x) for x in (pred[test] - y[test])],
        "claim_limit": "PDE合成标签上的关联拟合，不是独立实验验证",
    }
    dump(OUT / "model-pure-ml" / "result.json", result)
    return result, pred


def graph_surrogate(rows, fields, train, test, extra, seed=SEED):
    X = np.array([[r["q"] == 4, r["hm_mult"], r["pref_mult"], r["exponent_mult"]] for r in rows], float)
    Z, mu, sd = standardize(X, train)
    # Fixed graph-message features (two rounds) on the 8x12 FV adjacency graph.
    nr, nz = 8, 12
    A = np.zeros((nr * nz, nr * nz))
    for i in range(nr):
        for j in range(nz):
            k = i * nz + j
            for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ii, jj = i + di, j + dj
                if 0 <= ii < nr and 0 <= jj < nz:
                    A[k, ii * nz + jj] = 1
    A += np.eye(nr * nz)
    A /= A.sum(1, keepdims=True)
    # Graph-smoothed basis represents a lightweight fixed-adjacency message-passing surrogate.
    rng = np.random.default_rng(seed)
    B = rng.normal(size=(nr * nz, 10))
    B = A @ (A @ B)
    B, _ = np.linalg.qr(B)
    coef = fields @ B
    features = np.c_[Z, Z[:, 1:] ** 2, Z[:, 1] * Z[:, 2], Z[:, 1] * Z[:, 3]]
    t0 = time.perf_counter(); W = ridge_fit(features[train], coef[train], 1e-4); train_s = time.perf_counter() - t0
    t1 = time.perf_counter(); pred_fields = ridge_predict(features, W) @ B.T; infer_s = (time.perf_counter() - t1) / len(rows)
    def field_metrics(idx):
        return metrics(fields[idx].ravel(), pred_fields[idx].ravel())
    result = {
        "model": "fixed-adjacency graph message surrogate", "seed": seed, "train_s": train_s,
        "inference_s_per_case": infer_s, "parameters": int(W.size),
        "test_field_C": field_metrics(test), "extrapolation_field_C": field_metrics(extra),
        "negative_prediction_count": int(np.sum(pred_fields < 0)),
        "claim_limit": "低分辨率PDE代理原型，不是高保真神经算子",
    }
    dump(OUT / "model-surrogate" / "result.json", result)
    return result


def pinn_elm(seed=SEED):
    # Physics-informed single-hidden-layer tanh network for u_t=D*u_xx,
    # representative of the moisture-diffusion inverse subproblem.
    rng = np.random.default_rng(seed)
    D_true = 0.18
    x_obs = np.array([.2, .5, .8] * 5)
    t_obs = np.repeat(np.linspace(.1, .9, 5), 3)
    y_obs = np.sin(np.pi * x_obs) * np.exp(-D_true * np.pi**2 * t_obs)
    y_obs += rng.normal(0, .003, len(y_obs))
    n_hidden = 36
    wx = rng.normal(0, 2, n_hidden); wt = rng.normal(0, 2, n_hidden); b = rng.normal(0, 1, n_hidden)
    def basis(x, t):
        z = x[:, None] * wx + t[:, None] * wt + b
        h = np.tanh(z); sech2 = 1 - h * h
        ht = sech2 * wt
        hxx = -2 * h * sech2 * wx**2
        return h, ht, hxx
    xo = x_obs; to = t_obs
    ho, _, _ = basis(xo, to)
    xc = rng.uniform(0, 1, 180); tc = rng.uniform(0, 1, 180)
    hc, htc, hxxc = basis(xc, tc)
    xb = np.r_[np.zeros(30), np.ones(30)]; tb = np.tile(np.linspace(0, 1, 30), 2)
    hb, _, _ = basis(xb, tb)
    xi = np.linspace(0, 1, 50); ti = np.zeros(50); hi, _, _ = basis(xi, ti)
    candidates = np.linspace(.08, .30, 89)
    best = None; t0 = time.perf_counter()
    for D in candidates:
        R = htc - D * hxxc
        A = np.vstack([ho / .003, 0.18 * R, 8 * hb, 8 * hi])
        rhs = np.r_[y_obs / .003, np.zeros(len(R) + len(hb)), 8 * np.sin(np.pi * xi)]
        w, *_ = np.linalg.lstsq(A, rhs, rcond=1e-8)
        score = np.mean((ho @ w - y_obs) ** 2) + np.mean((R @ w) ** 2)
        if best is None or score < best[0]: best = (score, D, w)
    train_s = time.perf_counter() - t0
    _, D_hat, w = best
    xt = np.linspace(0, 1, 61); tt = np.linspace(0, 1, 41)
    XG, TG = np.meshgrid(xt, tt); h, ht, hxx = basis(XG.ravel(), TG.ravel())
    pred = h @ w; truth = np.sin(np.pi * XG.ravel()) * np.exp(-D_true * np.pi**2 * TG.ravel())
    residual = ht @ w - D_hat * (hxx @ w)
    # Unconstrained observation-only ELM baseline.
    wb, *_ = np.linalg.lstsq(ho, y_obs, rcond=1e-8)
    base = h @ wb
    result = {
        "model": "physics-informed ELM/PINN prototype", "seed": seed, "D_true": D_true,
        "D_hat": float(D_hat), "parameter_relative_error": float(abs(D_hat-D_true)/D_true),
        "field": metrics(truth, pred), "unconstrained_field": metrics(truth, base),
        "pde_residual_l2": float(np.sqrt(np.mean(residual**2))),
        "train_s": train_s, "parameters": int(len(w) + 1),
        "claim_limit": "规范化扩散方程的合成稀疏观测原型；未证明M3/M4全方程可识别",
    }
    dump(OUT / "model-pinn" / "result.json", result)
    return result


def multiphase_cfd():
    # Conservative radial two-inventory FV prototype with Robin drying at r=R.
    nr, R, phi = 80, 1.0, .55
    dr = R / nr; rface = np.linspace(0, R, nr + 1)
    vol = np.pi * (rface[1:]**2 - rface[:-1]**2)
    area = 2 * np.pi * rface
    Sl = .62 + .08 * (1 - ((rface[:-1] + rface[1:])/(2*R))**2)
    cv = np.full(nr, .04)
    Dl, Dv, kev, hm = 2.0e-3, 1.2e-2, .08, .06
    dt, steps = .12 * dr**2 / max(Dl, Dv), 2400
    init = float(np.sum((Sl + cv) * vol)); outflux = 0.0
    max_balance = 0.0; t0 = time.perf_counter()
    def div_flux(u, D, sink=True):
        flux = np.zeros(nr + 1)
        flux[1:nr] = -D * area[1:nr] * (u[1:] - u[:-1]) / dr
        if sink: flux[nr] = hm * area[nr] * max(u[-1], 0.0)
        return -(flux[1:] - flux[:-1]) / vol, flux[nr]
    for _ in range(steps):
        dl, fl = div_flux(Sl, Dl, True); dv, fv = div_flux(cv, Dv, True)
        gamma = kev * (0.12 * Sl - cv)
        Sl += dt * (dl - gamma); cv += dt * (dv + gamma)
        Sl = np.maximum(Sl, 0); cv = np.maximum(cv, 0)
        outflux += dt * (fl + fv)
        inventory = float(np.sum((Sl + cv) * vol))
        max_balance = max(max_balance, abs((init - inventory) - outflux) / max(init-inventory, 1e-12))
    runtime = time.perf_counter() - t0
    total = Sl + cv
    # Matched single-field effective-diffusion comparator.
    u = .66 + .08 * (1 - ((rface[:-1] + rface[1:])/(2*R))**2)
    Deff = Dl * .75 + Dv * .25
    for _ in range(steps):
        du, _ = div_flux(u, Deff, True); u += dt * du; u = np.maximum(u, 0)
    result = {
        "model": "reduced porous two-phase radial FV", "cells": nr,
        "steps": steps, "dt": dt, "runtime_s": runtime,
        "normalized_mass_balance_error": max_balance,
        "liquid_inventory": float(np.sum(Sl*vol)), "vapor_inventory": float(np.sum(cv*vol)),
        "total_mean": float(np.sum(total*vol)/np.sum(vol)),
        "single_field_mean": float(np.sum(u*vol)/np.sum(vol)),
        "mechanism_mean_difference": float(np.sum((total-u)*vol)/np.sum(vol)),
        "field_difference": metrics(u, total),
        "claim_limit": "缩减径向双相有限体积原型，不是完整二维/三维工业CFD",
    }
    dump(OUT / "model-cfd" / "result.json", result)
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    rows, fields = generate_pde_scenarios()
    write_csv(OUT / "pde-scenarios.csv", rows)
    train, test, extra, validation = split_indices(rows)
    split = {"train": train.tolist(), "validation": validation.tolist(), "test_interpolation": test.tolist(), "test_extrapolation": extra.tolist(), "unit": "whole scenario", "seeds": SEEDS}
    dump(OUT / "split-manifest.json", split)
    pure, pred = pure_ml(rows, train, test, extra)
    surrogate_runs = [graph_surrogate(rows, fields, train, test, extra, seed) for seed in SEEDS]
    pinn_runs = [pinn_elm(seed) for seed in SEEDS]
    surrogate = surrogate_runs[0]
    pinn = pinn_runs[0]
    dump(OUT / "model-surrogate" / "seed-results.json", surrogate_runs)
    dump(OUT / "model-pinn" / "seed-results.json", pinn_runs)
    cfd = multiphase_cfd()
    pde_median = float(np.median([r["runtime_s"] for r in rows]))
    comparison = [
        {"model":"M3/M4 low-resolution PDE reference","role":"reference","accuracy_basis":"self","median_s":pde_median,"status":"RETAIN_PRIMARY"},
        {"model":"reduced two-phase CFD","role":"mechanism probe","accuracy_basis":"single-field limit/total inventory","median_s":cfd["runtime_s"],"status":"INCONCLUSIVE" if abs(cfd["mechanism_mean_difference"]) < .01 else "MECHANISM_DIFFERENCE"},
        {"model":"PINN-ELM","role":"sparse inverse prototype","accuracy_basis":"analytic diffusion truth","median_s":pinn["train_s"],"status":"SUPPORTED_PROTOTYPE" if pinn["field"]["rmse"] < pinn["unconstrained_field"]["rmse"] else "UNSUPPORTED"},
        {"model":"graph surrogate","role":"PDE acceleration prototype","accuracy_basis":"held-out PDE fields","median_s":surrogate["inference_s_per_case"],"status":"LIMITED_TO_INTERPOLATION"},
        {"model":"pure ML ridge","role":"negative/control baseline","accuracy_basis":"held-out PDE event times","median_s":pure["inference_s_per_case"],"status":"CONTROL_ONLY"},
    ]
    write_csv(OUT / "原型结果.csv", comparison)
    env = {"python":sys.version, "executable":sys.executable, "platform":platform.platform(), "numpy":np.__version__, "seeds":SEEDS, "scenario_count":len(rows), "missing_optional":["scipy in bundled runtime","scikit-learn","torch","torch_geometric","jax"]}
    dump(OUT / "实验环境.json", env)
    summary = f"""# 补充模型原型比较

本实验不替换 M1–M4。标签来自实际运行的低分辨率 M3/M4 求解器或可解析扩散基准，没有独立实验数据。

## 主要区别

- 缩减双相 CFD 显式分离液态与气态库存，质量守恒误差为 {cfd['normalized_mass_balance_error']:.3e}，相对单场模型的平均含水量差为 {cfd['mechanism_mean_difference']:.3e}。它增加机制解释，也增加参数不可识别风险。
- PINN-ELM 在稀疏合成观测下反演扩散系数，相对误差 {pinn['parameter_relative_error']:.2%}；场 RMSE 为 {pinn['field']['rmse']:.3e}，无物理约束基线为 {pinn['unconstrained_field']['rmse']:.3e}。这只证明规范化扩散原型的数值可行性。
- 固定邻接图代理的内插场 RMSE 为 {surrogate['test_field_C']['rmse']:.3e}，外推 RMSE 为 {surrogate['extrapolation_field_C']['rmse']:.3e}；单次推理约 {surrogate['inference_s_per_case']:.3e} s，而低分辨率 PDE 中位求解约 {pde_median:.3e} s。
- 纯 ML 对事件时间的内插 RMSE 为 {pure['test']['rmse']:.1f} s，外推 RMSE 为 {pure['extrapolation']['rmse']:.1f} s；它最快，但没有守恒、PDE 约束或物理参数解释。

## 结论边界

这些是 120 工况、工况级 72/16/16/16 划分的最小真实原型，并对随机 PINN 与图代理执行三个注册种子。数据量敏感性只在已有降级对照中完成，设计包所列全部训练/消融次数及高分辨率阈值验证仍未完整执行，因此不能把任何补充模型升级为正式主路线。
"""
    (OUT / "候选方案对比.md").write_text(summary, encoding="utf-8")
    outputs = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name not in {"handoff.json", "复现清单.json"}:
            outputs.append({"path":path.relative_to(ROOT).as_posix(),"sha256":sha256(path)})
    manifest = {"schema_version":"1.0","seed":SEED,"command":f'"{sys.executable}" 03-prototype/supplemental-extensions/run_all.py',"runtime_s":time.perf_counter()-started,"environment":env,"outputs":outputs}
    dump(OUT / "复现清单.json", manifest)
    outputs.append({"path":"03-prototype/supplemental-extensions/复现清单.json","sha256":sha256(OUT/"复现清单.json")})
    inputs = []
    for rel in ["02-design/supplemental-extensions/handoff.json","04-compute/handoff.json","decisions/H2-model.json"]:
        inputs.append({"path":rel,"sha256":sha256(ROOT/rel)})
    handoff = {"schema_version":"1.0","stage":"PROTOTYPE","status":"PASS","scope":"supplemental extensions only; primary route unchanged","inputs":inputs,"outputs":outputs,"frozen_decisions":[inputs[-1]],"assumptions":["PDE scenario labels use a deliberately low-resolution verified solver configuration for prototype screening"],"unknowns":["No independent experimental observations","Full preregistered ablation/training-count matrix and high-resolution event verification remain outside this minimal prototype"],"claims":["All four model classes have a real executed minimal prototype","120 whole-scenario cases use a frozen 72/16/16/16 split and registered random seeds","No prototype replaces M1-M4"],"warnings":["CFD and PINN are reduced canonical prototypes","Surrogate and pure ML accuracy is only relative to PDE-generated labels"],"required_next_actions":["Do not promote supplemental candidates without the remaining full-matrix evidence"],"completed_at":time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    dump(OUT / "handoff.json", handoff)
    print(json.dumps({"status":"PASS","comparison":comparison,"runtime_s":manifest["runtime_s"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
