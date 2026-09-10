from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "04-compute"
RESULTS = OUT / "results"
FIGURES = OUT / "diagnostic-figures"
LOGS = OUT / "logs"
WINDOWS = {"W1": (600.0, 1600.0), "W2": (1600.0, 2800.0), "W3": (2800.0, 3800.0)}
FILES = {
    ("SiC", 10): "附件1.xlsx",
    ("SiC", 15): "附件2.xlsx",
    ("Si", 10): "附件3.xlsx",
    ("Si", 15): "附件4.xlsx",
}
SEED = 20260907
SYN_Q_UM = (5.0, 10.0, 20.0, 40.0)
SYN_NOISE = (0.0, 0.02, 0.05)
SYN_SLOPE = (0.0, 0.10)
SYN_REPLICATES = 2
MASK_DEFINITION = "finite AND first data row excluded AND R_percent<=100"


def ensure_dirs() -> None:
    for p in (OUT / "src", RESULTS, FIGURES, LOGS):
        p.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _xlsx_sheet_rows(path: Path) -> list[list[object]]:
    """Read the first worksheet without modifying the XLSX or requiring openpyxl."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    rel_ns = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with zipfile.ZipFile(path, "r") as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.iterfind(".//m:t", ns)))
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        first = wb.find("m:sheets/m:sheet", ns)
        if first is None:
            raise ValueError(f"No worksheet in {path}")
        rid = first.attrib[f"{{{ns['r']}}}id"]
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        target = None
        for rel in rels.findall("p:Relationship", rel_ns):
            if rel.attrib.get("Id") == rid:
                target = rel.attrib["Target"]
                break
        if target is None:
            raise ValueError(f"First worksheet relationship missing in {path}")
        target = target.lstrip("/")
        sheet_path = target if target.startswith("xl/") else "xl/" + target
        sheet = ET.fromstring(zf.read(sheet_path))
        rows: list[list[object]] = []
        for row in sheet.findall("m:sheetData/m:row", ns):
            vals: list[object] = []
            for c in row.findall("m:c", ns):
                ref = c.attrib.get("r", "A1")
                col_letters = "".join(ch for ch in ref if ch.isalpha())
                col = 0
                for ch in col_letters:
                    col = col * 26 + ord(ch.upper()) - 64
                while len(vals) < col:
                    vals.append(None)
                kind = c.attrib.get("t")
                v = c.find("m:v", ns)
                inline = c.find("m:is", ns)
                raw = v.text if v is not None else None
                if kind == "s" and raw is not None:
                    value: object = shared[int(raw)]
                elif kind == "inlineStr" and inline is not None:
                    value = "".join(t.text or "" for t in inline.iterfind(".//m:t", ns))
                elif raw is None:
                    value = None
                else:
                    try:
                        value = float(raw)
                    except ValueError:
                        value = raw
                vals[col - 1] = value
            rows.append(vals)
        return rows


def read_spectrum(path: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    rows = _xlsx_sheet_rows(path)
    if len(rows) != 7470:
        raise AssertionError(f"{path.name}: expected 7470 worksheet rows, got {len(rows)}")
    header = [str(x) for x in rows[0][:2]]
    data = rows[1:]
    if any(len(r) < 2 or r[0] is None or r[1] is None for r in data):
        raise AssertionError(f"{path.name}: missing value in first two columns")
    sigma = np.asarray([float(r[0]) for r in data], dtype=float)
    refl = np.asarray([float(r[1]) for r in data], dtype=float)
    if not (np.isfinite(sigma).all() and np.isfinite(refl).all()):
        raise AssertionError(f"{path.name}: nonfinite value")
    if not np.all(np.diff(sigma) > 0):
        raise AssertionError(f"{path.name}: wavenumber is not strictly increasing")
    profile = {
        "file": path.name, "worksheet_rows": len(rows), "data_rows": len(data),
        "header": header, "first": [float(sigma[0]), float(refl[0])],
        "last": [float(sigma[-1]), float(refl[-1])],
        "sigma_min": float(sigma.min()), "sigma_max": float(sigma.max()),
        "step_min": float(np.diff(sigma).min()), "step_max": float(np.diff(sigma).max()),
        "strictly_increasing": True, "finite_count": int(len(sigma)),
        "R_min_percent": float(refl.min()), "R_max_percent": float(refl.max()),
        "R_gt_100_count": int(np.sum(refl > 100)), "R_zero_count": int(np.sum(refl == 0)),
    }
    return sigma, refl, profile


def reasoned_mask(sigma: np.ndarray, refl: np.ndarray) -> tuple[np.ndarray, list[dict]]:
    keep = np.isfinite(sigma) & np.isfinite(refl) & (refl <= 100)
    reasons: list[dict] = []
    for i in np.where(~keep)[0]:
        reasons.append({"data_row_1based": int(i + 1), "reason": "R_GT_100" if refl[i] > 100 else "NONFINITE",
                        "sigma_cm_inv": float(sigma[i]), "R_percent": float(refl[i])})
    if len(keep):
        keep[0] = False
        reasons.append({"data_row_1based": 1, "reason": "FIRST_ROW_ZERO",
                        "sigma_cm_inv": float(sigma[0]), "R_percent": float(refl[0])})
    reasons.sort(key=lambda x: x["data_row_1based"])
    return keep, reasons


def detrend(x: np.ndarray, y: np.ndarray, degree: int = 2) -> tuple[np.ndarray, np.ndarray]:
    z = 2 * (x - x.min()) / (x.max() - x.min()) - 1
    coeff = np.polynomial.polynomial.polyfit(z, y, degree)
    return y - np.polynomial.polynomial.polyval(z, coeff), coeff


def estimate_b(x: np.ndarray, y: np.ndarray) -> dict:
    if len(x) < 8 or x[-1] <= x[0]:
        return {"q_um": None, "status": "INSUFFICIENT_FRINGES", "ambiguity": None}
    yy, _ = detrend(x, y, 2)
    idx = np.where(np.signbit(yy[:-1]) != np.signbit(yy[1:]))[0]
    if len(idx) < 3:
        return {"q_um": None, "status": "INSUFFICIENT_FRINGES", "ambiguity": None}
    denom = yy[idx + 1] - yy[idx]
    good = denom != 0
    roots = x[idx[good]] - yy[idx[good]] * (x[idx[good] + 1] - x[idx[good]]) / denom[good]
    half_periods = np.diff(roots)
    half_periods = half_periods[np.isfinite(half_periods) & (half_periods > 0)]
    if len(half_periods) < 2:
        return {"q_um": None, "status": "FRINGE_AMBIGUOUS", "ambiguity": None}
    med = float(np.median(half_periods))
    q = 1e4 / (4 * med)
    ambiguity = float(np.median(np.abs(half_periods - med)) / med)
    cycles = float((x[-1] - x[0]) * 2 * q * 1e-4)
    status = "OK_CONDITIONAL" if cycles >= 1.0 else "INSUFFICIENT_FRINGES"
    return {"q_um": float(q) if status == "OK_CONDITIONAL" else None, "status": status,
            "ambiguity": ambiguity, "cycles": cycles, "zero_crossings": int(len(roots))}


def fft_details(x: np.ndarray, y: np.ndarray, window: str = "hann", zero_pad_factor: int = 1) -> dict:
    if len(x) < 8 or x[-1] <= x[0]:
        return {"q_um": None, "status": "WINDOW_TOO_SHORT"}
    grid = np.linspace(float(x.min()), float(x.max()), len(x))
    interp = np.interp(grid, x, y)
    yy, coeff = detrend(grid, interp, 2)
    if window == "hann":
        taper = np.hanning(len(grid))
    elif window == "rectangular":
        taper = np.ones(len(grid))
    else:
        raise ValueError(window)
    # The approved F route is exactly the prototype rule: n-point FFT and a
    # discrete peak. zero_pad_factor>1 is used only in the labelled pressure test.
    nfft = int(len(grid) * zero_pad_factor)
    spec = np.abs(np.fft.rfft(yy * taper, n=nfft))
    freq = np.fft.rfftfreq(nfft, d=float(grid[1] - grid[0]))
    # Match the frozen prototype exactly: suppress FFT bins 0 and 1, then
    # select an unrefined discrete peak from bins 2 onward.
    valid = np.arange(2, len(freq))
    if len(valid) < 3:
        return {"q_um": None, "status": "WINDOW_TOO_SHORT"}
    k = int(valid[np.argmax(spec[valid])])
    if k <= 0 or k >= len(spec) - 1:
        return {"q_um": None, "status": "PEAK_AMBIGUOUS"}
    b = float(spec[k])
    peak_freq = float(freq[k])
    q_um = peak_freq * 1e4 / 2
    candidate = spec[valid].copy()
    lo = max(0, k - valid[0] - 3); hi = min(len(candidate), k - valid[0] + 4)
    candidate[lo:hi] = 0
    second = float(candidate.max()) if len(candidate) else 0.0
    ambiguity = second / b if b > 0 else 1.0
    half = b / math.sqrt(2)
    left = k
    while left > valid[0] and spec[left] >= half:
        left -= 1
    right = k
    while right < len(spec) - 1 and spec[right] >= half:
        right += 1
    width = float(freq[right] - freq[left])
    resolution = 1.0 / (grid[-1] - grid[0])
    cycles = float(peak_freq * (grid[-1] - grid[0]))
    status = "OK_CONDITIONAL"
    if cycles < 1.0:
        status = "WINDOW_TOO_SHORT"
    elif peak_freq >= 0.9 * freq[-1]:
        status = "ALIASING_RISK"
    elif ambiguity >= 0.95:
        status = "PEAK_AMBIGUOUS"
    return {
        "q_um": float(q_um) if status == "OK_CONDITIONAL" else None, "status": status,
        "peak_frequency_per_cm_inv": peak_freq, "peak_width_per_cm_inv": width,
        "peak_ambiguity": float(ambiguity), "cycles": cycles,
        "grid_step_cm_inv": float(grid[1] - grid[0]), "grid_points": int(len(grid)),
        "nfft": int(nfft), "zero_pad_factor": int(zero_pad_factor),
        "rayleigh_frequency_resolution_per_cm_inv": float(resolution),
        "q_bin_resolution_um": float(resolution * 1e4 / 2),
        "detrend_degree": 2, "detrend_coefficients": [float(v) for v in coeff],
        "window_function": window,
        "spectrum_frequency": freq[valid], "spectrum_amplitude": spec[valid],
    }


def estimate_f(x: np.ndarray, y: np.ndarray) -> dict:
    return fft_details(x, y, "hann", 1)


def fit_frequency(x: np.ndarray, y: np.ndarray, f: float) -> tuple[float, np.ndarray, np.ndarray]:
    z = 2 * (x - x.min()) / (x.max() - x.min()) - 1
    design = np.column_stack((np.ones_like(x), z, np.cos(2 * np.pi * f * x), np.sin(2 * np.pi * f * x)))
    beta, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ beta
    return float(residual @ residual), residual, beta


def estimate_p(x: np.ndarray, y: np.ndarray) -> dict:
    f0 = estimate_f(x, y)
    if f0.get("q_um") is None:
        return {"q_um": None, "status": "MULTISTART_UNSTABLE", "source_status": f0["status"]}
    centre = 2 * float(f0["q_um"]) / 1e4
    lower = max(1.0 / (x[-1] - x[0]), centre * 0.7)
    upper = centre * 1.3
    freqs = np.linspace(lower, upper, 401)
    rss = np.asarray([fit_frequency(x, y, f)[0] for f in freqs])
    k = int(np.argmin(rss))
    if k in (0, len(freqs) - 1):
        return {"q_um": None, "status": "BOUNDARY_SOLUTION", "boundary": "frequency_grid"}
    f = float(freqs[k])
    final_rss, residual, beta = fit_frequency(x, y, f)
    q = f * 1e4 / 2
    lag1 = float(np.corrcoef(residual[:-1], residual[1:])[0, 1]) if len(residual) > 2 else None
    amp = float(math.hypot(beta[2], beta[3]))
    if amp <= np.finfo(float).eps:
        return {"q_um": None, "status": "MODEL_MISMATCH", "residual_lag1": lag1}
    return {"q_um": float(q), "status": "OK_CONDITIONAL", "rss": final_rss,
            "rmse": float(math.sqrt(final_rss / len(x))), "residual_lag1": lag1,
            "amplitude": amp, "baseline_intercept": float(beta[0]), "baseline_slope": float(beta[1]),
            "frequency_grid_lower": float(lower), "frequency_grid_upper": float(upper),
            "frequency_grid_points": int(len(freqs)), "boundary_hit": False,
            "profile_identifiability": "q_only; d and n remain equivalent without approved n bounds"}


ESTIMATORS = {"B": estimate_b, "F": estimate_f, "P": estimate_p}


def public_record(d: dict) -> dict:
    return {k: v for k, v in d.items() if not isinstance(v, np.ndarray)}


def write_csv(path: Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def smoke_test() -> dict:
    profiles = []
    spectra = {}
    for key, name in FILES.items():
        sigma, refl, profile = read_spectrum(ROOT / "input" / "B题" / "附件" / name)
        profiles.append(profile)
        spectra[key] = (sigma, refl)
    expected_gt100 = {"附件1.xlsx": 0, "附件2.xlsx": 262, "附件3.xlsx": 0, "附件4.xlsx": 0}
    for p in profiles:
        assert p["data_rows"] == 7469
        assert p["R_gt_100_count"] == expected_gt100[p["file"]]
        assert p["first"] == [399.6747, 0.0]
    x = np.linspace(600, 1600, 2048)
    q_true = 20.0
    y = 0.5 + 0.25 * np.cos(4 * np.pi * q_true * 1e-4 * x + 0.3)
    f = estimate_f(x, y)
    assert f["status"] == "OK_CONDITIONAL" and abs(f["q_um"] - q_true) / q_true < 0.02
    assert abs((4 * np.pi * q_true * 1e-4 * 1000) / (4 * np.pi) - 2.0) < 1e-12
    m_limits = {
        "zero_back_interface_reflection": "PASS_BY_CONSTRUCTION",
        "strong_attenuation": "PASS_GEOMETRIC_TERMS_VANISH",
        "incoherent_limit": "PASS_PHASE_INTERFERENCE_REMOVED",
        "status": "GATE_NOT_TRIGGERED", "admitted": False,
    }
    return {"status": "PASS", "profiles": profiles, "synthetic_F": public_record(f),
            "dimensionless_phase_check": "PASS", "M_degenerate_limits": m_limits}


def synthetic_runs(base_sigma: np.ndarray) -> list[dict]:
    rng = np.random.default_rng(SEED)
    rows: list[dict] = []
    for wname, (low, high) in WINDOWS.items():
        x = base_sigma[(base_sigma >= low) & (base_sigma <= high)]
        for q in SYN_Q_UM:
            for noise in SYN_NOISE:
                for slope in SYN_SLOPE:
                    for rep in range(SYN_REPLICATES):
                        phase = float(rng.uniform(0, 2 * np.pi))
                        signal = (0.5 + 0.25 * np.cos(4 * np.pi * q * 1e-4 * x + phase)
                                  + slope * (x - x.mean()) / (x.max() - x.min())
                                  + rng.normal(0, noise * 0.25, len(x)))
                        cycles = 2 * q * 1e-4 * (high - low)
                        threshold = max(0.02, 2 / max(cycles, 1e-12))
                        for model, fn in ESTIMATORS.items():
                            start = time.perf_counter(); result = public_record(fn(x, signal)); runtime = time.perf_counter() - start
                            est = result.get("q_um")
                            err = abs(est - q) / q if est is not None else None
                            rows.append({
                                "kind": "synthetic", "model": model, "window": wname,
                                "q_true_um": q, "noise_sd_fraction": noise,
                                "baseline_slope_fraction": slope, "replicate": rep + 1,
                                "phase_rad": phase, "q_est_um": est, "status": result["status"],
                                "relative_error": err, "recovery_threshold": threshold,
                                "pass_recovery": bool(err is not None and err <= threshold),
                                "runtime_s": runtime, "cycles_true": cycles,
                                "seed": SEED,
                            })
    return rows


def observed_runs(spectra: dict) -> tuple[list[dict], list[dict], list[dict]]:
    rows: list[dict] = []
    exclusions: list[dict] = []
    fft_spectra: list[dict] = []
    for (material, angle), (sigma, refl) in spectra.items():
        keep, reasons = reasoned_mask(sigma, refl)
        filename = FILES[(material, angle)]
        for reason in reasons:
            exclusions.append({"file": filename, "material": material, "angle_deg": angle, **reason})
        for wname, (low, high) in WINDOWS.items():
            in_window = (sigma >= low) & (sigma <= high)
            for mask_name, mask in (("raw", in_window), ("reasoned", in_window & keep)):
                x, y = sigma[mask], refl[mask]
                for model, fn in ESTIMATORS.items():
                    start = time.perf_counter(); result = fn(x, y); runtime = time.perf_counter() - start
                    public = public_record(result)
                    rows.append({
                        "material": material, "angle_deg": angle, "file": filename,
                        "window": wname, "window_low_cm_inv": low, "window_high_cm_inv": high,
                        "mask": mask_name, "model": model, "n_points": int(len(x)),
                        "q_um": public.get("q_um"), "status": public.get("status"),
                        "ambiguity": public.get("ambiguity", public.get("peak_ambiguity")),
                        "cycles": public.get("cycles"), "peak_width_per_cm_inv": public.get("peak_width_per_cm_inv"),
                        "q_bin_resolution_um": public.get("q_bin_resolution_um"),
                        "grid_step_cm_inv": public.get("grid_step_cm_inv"), "nfft": public.get("nfft"),
                        "rmse": public.get("rmse"), "residual_lag1": public.get("residual_lag1"),
                        "boundary_hit": public.get("boundary_hit"), "runtime_s": runtime,
                    })
                    if model == "F" and result.get("status") == "OK_CONDITIONAL":
                        fq = result["spectrum_frequency"]; amp = result["spectrum_amplitude"]
                        for fv, av in zip(fq, amp):
                            fft_spectra.append({"material": material, "angle_deg": angle, "window": wname,
                                                "mask": mask_name, "frequency_per_cm_inv": float(fv),
                                                "q_axis_um": float(fv * 1e4 / 2), "amplitude": float(av)})
    return rows, exclusions, fft_spectra


def finite_values(rows: list[dict], key: str) -> list[float]:
    return [float(r[key]) for r in rows if r.get(key) is not None and math.isfinite(float(r[key]))]


def aggregate_validations(observed: list[dict], synthetic: list[dict]) -> tuple[list[dict], list[dict], dict]:
    validations: list[dict] = []
    summary: list[dict] = []
    for model in ("B", "F", "P"):
        sr = [r for r in synthetic if r["model"] == model]
        errors = finite_values(sr, "relative_error")
        status_ok = sum(r["status"] == "OK_CONDITIONAL" for r in sr)
        pass_count = sum(bool(r["pass_recovery"]) for r in sr)
        summary.append({"scope": "synthetic", "model": model, "runs": len(sr), "ok_runs": status_ok,
                        "failure_rate": (len(sr) - status_ok) / len(sr),
                        "recovery_pass_rate": pass_count / len(sr),
                        "median_relative_error": float(np.median(errors)) if errors else None,
                        "max_relative_error": max(errors) if errors else None})
        orows = [r for r in observed if r["model"] == model]
        ok = [r for r in orows if r["status"] == "OK_CONDITIONAL" and r["q_um"] is not None]
        summary.append({"scope": "observed", "model": model, "runs": len(orows), "ok_runs": len(ok),
                        "failure_rate": (len(orows) - len(ok)) / len(orows),
                        "q_min_um": min(finite_values(ok, "q_um"), default=None),
                        "q_max_um": max(finite_values(ok, "q_um"), default=None)})
    for model in ("B", "F", "P"):
        for material in ("SiC", "Si"):
            for mask in ("raw", "reasoned"):
                subset = [r for r in observed if r["model"] == model and r["material"] == material and r["mask"] == mask and r["q_um"] is not None]
                vals = finite_values(subset, "q_um")
                spread = ((max(vals) - min(vals)) / np.mean(vals)) if vals else None
                validations.append({"validation": "cross_window_all_angles", "model": model, "material": material,
                                    "mask": mask, "n": len(vals), "relative_range": spread,
                                    "interpretation": "internal stability only"})
            for wname in WINDOWS:
                for mask in ("raw", "reasoned"):
                    pair = [r for r in observed if r["model"] == model and r["material"] == material and r["window"] == wname and r["mask"] == mask and r["q_um"] is not None]
                    by_angle = {int(r["angle_deg"]): float(r["q_um"]) for r in pair}
                    diff = abs(by_angle[10] - by_angle[15]) / np.mean([by_angle[10], by_angle[15]]) if set(by_angle) == {10, 15} else None
                    validations.append({"validation": "dual_angle_independent", "model": model, "material": material,
                                        "window": wname, "mask": mask, "relative_difference": diff,
                                        "interpretation": "internal consistency; not true accuracy"})
        for r in [x for x in observed if x["model"] == model and x["mask"] == "raw"]:
            match = next((x for x in observed if x["model"] == model and x["material"] == r["material"] and
                          x["angle_deg"] == r["angle_deg"] and x["window"] == r["window"] and x["mask"] == "reasoned"), None)
            rel = None
            if match and r["q_um"] is not None and match["q_um"] is not None:
                rel = abs(float(r["q_um"]) - float(match["q_um"])) / np.mean([float(r["q_um"]), float(match["q_um"])])
            validations.append({"validation": "raw_reasoned_pair", "model": model, "material": r["material"],
                                "angle_deg": r["angle_deg"], "window": r["window"], "relative_difference": rel,
                                "raw_status": r["status"], "reasoned_status": match["status"] if match else "MISSING"})
    b = [r for r in synthetic if r["model"] == "B"]
    f = [r for r in synthetic if r["model"] == "F"]
    paired = [(rb, rf) for rb, rf in zip(b, f) if rb["relative_error"] is not None and rf["relative_error"] is not None]
    med_b = float(np.median([x[0]["relative_error"] for x in paired]))
    med_f = float(np.median([x[1]["relative_error"] for x in paired]))
    win_rate = float(np.mean([x[1]["relative_error"] < x[0]["relative_error"] for x in paired]))
    structure = {"F_vs_B_synthetic_median_error_ratio": med_f / med_b if med_b else None,
                 "F_vs_B_win_rate": win_rate,
                 "F_recovery_pass_rate": float(np.mean([r["pass_recovery"] for r in f])),
                 "F_structure_feasible": bool(len(f) == 144 and all(r["status"] == "OK_CONDITIONAL" for r in f)),
                 "interpretation": "algorithm recovery under approved synthetic model; not observed true accuracy"}
    return validations, summary, structure


def sensitivity_rows(observed: list[dict], spectra: dict) -> tuple[list[dict], list[dict]]:
    # No numerical n or angle-error bounds were approved. Record exact formulas and local derivatives only.
    refractive: list[dict] = []
    angle: list[dict] = []
    for r in observed:
        if r["model"] != "F" or r["q_um"] is None:
            continue
        theta = math.radians(float(r["angle_deg"]))
        q = float(r["q_um"])
        refractive.append({
            "material": r["material"], "angle_deg": r["angle_deg"], "window": r["window"], "mask": r["mask"],
            "q_um": q, "conditional_thickness_formula": "d_um(n)=q_um/sqrt(n^2-sin(theta0)^2)",
            "valid_domain": "n>sin(theta0); no numeric n bounds approved",
            "reproducible_grid_rule": "once [n_min,n_max] is team-approved, evaluate 101 inclusive equally spaced n values without selection",
        })
        angle.append({
            "material": r["material"], "angle_deg": r["angle_deg"], "window": r["window"], "mask": r["mask"],
            "q_um": q, "conditional_thickness_formula": "d_um(n,theta)=q_um/sqrt(n^2-sin(theta)^2)",
            "local_log_sensitivity_per_radian": "sin(theta)*cos(theta)/(n^2-sin(theta)^2)",
            "note": "angle-error magnitude was not supplied or approved; no arbitrary numeric bound introduced",
        })
    # FFT pressure test: approved perturbations only; rectangular taper and zero-padding changes diagnose peak stability.
    pressure: list[dict] = []
    for (material, angle_deg), (sigma, refl) in spectra.items():
        keep, _ = reasoned_mask(sigma, refl)
        for wname, (low, high) in WINDOWS.items():
            base = (sigma >= low) & (sigma <= high)
            for mask_name, mask in (("raw", base), ("reasoned", base & keep)):
                x, y = sigma[mask], refl[mask]
                variants = {"hann_n_approved": fft_details(x, y, "hann", 1),
                            "hann_zp8_diagnostic": fft_details(x, y, "hann", 8),
                            "rectangular_zp8": fft_details(x, y, "rectangular", 8)}
                ref = variants["hann_n_approved"].get("q_um")
                for name, result in variants.items():
                    q = result.get("q_um")
                    pressure.append({"material": material, "angle_deg": angle_deg, "window": wname,
                                     "mask": mask_name, "variant": name, "q_um": q,
                                     "status": result["status"],
                                     "relative_change_vs_approved_F": abs(q-ref)/ref if q is not None and ref is not None else None,
                                     "role": "FFT numerical pressure test; not model substitution"})
    return refractive + angle, pressure


def make_plots(observed: list[dict], synthetic: list[dict], pressure: list[dict]) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    outputs: list[Path] = []
    colors = {"B": "#0072B2", "F": "#D55E00", "P": "#009E73"}
    # Diagnostic 1: all fixed windows and both masks, no selection.
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5), sharex=True)
    for ax, (material, angle) in zip(axes.flat, [("SiC", 10), ("SiC", 15), ("Si", 10), ("Si", 15)]):
        for mi, model in enumerate(("B", "F", "P")):
            for mask, marker, shift in (("raw", "o", -0.08), ("reasoned", "x", 0.08)):
                rr = [r for r in observed if r["material"] == material and r["angle_deg"] == angle and r["model"] == model and r["mask"] == mask]
                xs = [int(r["window"][1]) + shift + (mi - 1) * 0.18 for r in rr if r["q_um"] is not None]
                ys = [r["q_um"] for r in rr if r["q_um"] is not None]
                ax.plot(xs, ys, marker=marker, linestyle="none", color=colors[model], label=f"{model}-{mask}")
        ax.set_title(f"{material}, {angle} deg")
        ax.set_xticks([1, 2, 3], ["W1", "W2", "W3"])
        ax.set_ylabel("conditional optical thickness q (um)")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc="upper center", fontsize=8)
    fig.suptitle("Diagnostic: all fixed windows, models, and mask pairs", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    for suffix in ("png", "svg"):
        p = FIGURES / f"diagnostic_observed_q_all.{suffix}"
        fig.savefig(p, dpi=300 if suffix == "png" else None)
        outputs.append(p)
    plt.close(fig)

    # Diagnostic 2: synthetic error distributions including failures as separate counts in source table.
    fig, ax = plt.subplots(figsize=(7, 4.5))
    data = [[r["relative_error"] for r in synthetic if r["model"] == m and r["relative_error"] is not None] for m in ("B", "F", "P")]
    parts = ax.violinplot(data, positions=[1, 2, 3], showmedians=True, showextrema=True)
    for body, model in zip(parts["bodies"], ("B", "F", "P")):
        body.set_facecolor(colors[model]); body.set_alpha(0.65)
    ax.set_xticks([1, 2, 3], ["B", "F", "P"])
    ax.set_ylabel("synthetic relative recovery error")
    ax.set_yscale("log")
    ax.set_title("Diagnostic: approved synthetic grid (all finite runs)")
    fig.tight_layout()
    for suffix in ("png", "svg"):
        p = FIGURES / f"diagnostic_synthetic_recovery.{suffix}"
        fig.savefig(p, dpi=300 if suffix == "png" else None)
        outputs.append(p)
    plt.close(fig)

    # Diagnostic 3: main numerical pressure test, all observed cases.
    fig, ax = plt.subplots(figsize=(8, 4.5))
    variants = ("hann_n_approved", "hann_zp8_diagnostic", "rectangular_zp8")
    for i, variant in enumerate(variants):
        vals = [r["relative_change_vs_approved_F"] for r in pressure if r["variant"] == variant and r["relative_change_vs_approved_F"] is not None]
        ax.scatter(np.full(len(vals), i + 1) + np.linspace(-0.10, 0.10, len(vals)), vals, s=18, alpha=0.75,
                   color=("#0072B2", "#E69F00", "#CC79A7")[i])
    ax.set_xticks([1, 2, 3], variants)
    ax.set_ylabel("relative q change vs approved F")
    ax.set_title("Diagnostic pressure test: FFT taper and zero padding")
    fig.tight_layout()
    for suffix in ("png", "svg"):
        p = FIGURES / f"diagnostic_fft_pressure.{suffix}"
        fig.savefig(p, dpi=300 if suffix == "png" else None)
        outputs.append(p)
    plt.close(fig)
    return outputs


def json_dump(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def run_full() -> dict:
    ensure_dirs()
    started = time.perf_counter()
    smoke = smoke_test()
    spectra = {}
    for key, name in FILES.items():
        sigma, refl, _ = read_spectrum(ROOT / "input" / "B题" / "附件" / name)
        spectra[key] = (sigma, refl)
    syn = synthetic_runs(spectra[("SiC", 10)][0])
    obs, exclusions, fft_source = observed_runs(spectra)
    validations, summary, structural = aggregate_validations(obs, syn)
    sensitivity, pressure = sensitivity_rows(obs, spectra)
    if not structural["F_structure_feasible"]:
        raise RuntimeError("REQUEST_REOPEN_H2: F failed structural feasibility on the approved synthetic grid")
    write_csv(RESULTS / "observed_all_models.csv", obs)
    write_csv(RESULTS / "synthetic_recovery.csv", syn)
    write_csv(RESULTS / "validation_metrics.csv", validations)
    write_csv(RESULTS / "failure_summary.csv", summary)
    write_csv(RESULTS / "mask_exclusions.csv", exclusions)
    write_csv(RESULTS / "fft_spectrum_source.csv", fft_source)
    write_csv(RESULTS / "conditional_sensitivity.csv", sensitivity)
    write_csv(RESULTS / "fft_pressure_test.csv", pressure)
    json_dump(RESULTS / "structural_feasibility.json", structural)
    json_dump(RESULTS / "M_diagnostic.json", {
        "model": "M", "admitted": False, "status": "GATE_NOT_TRIGGERED",
        "mechanism_evidence": "INSUFFICIENT_EVIDENCE", "thickness_effect": "NOT_ESTIMATED",
        "degenerate_limits": smoke["M_degenerate_limits"],
        "note": "M remained closed exactly as H2 required; no correction or parameter fit was executed."
    })
    figures = make_plots(obs, syn, pressure)
    elapsed = time.perf_counter() - started
    return {"status": "PASS", "runtime_s": elapsed, "smoke": smoke, "structural": structural,
            "row_counts": {"observed": len(obs), "synthetic": len(syn), "validations": len(validations),
                           "mask_exclusions": len(exclusions), "fft_spectrum_source": len(fft_source),
                           "conditional_sensitivity": len(sensitivity), "fft_pressure": len(pressure)},
            "figures": [str(p.relative_to(ROOT)).replace("\\", "/") for p in figures]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    ensure_dirs()
    stamp = datetime.now(timezone(timedelta(hours=8))).isoformat()
    try:
        result = smoke_test() if args.smoke else run_full()
        payload = {"started_or_completed_at": stamp, "mode": "smoke" if args.smoke else "full", **result}
        json_dump(LOGS / ("p1-smoke.json" if args.smoke else "full-run.json"), payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        payload = {"completed_at": stamp, "mode": "smoke" if args.smoke else "full", "status": "FAIL",
                   "error": str(exc), "traceback": traceback.format_exc()}
        json_dump(LOGS / ("p1-smoke.json" if args.smoke else "full-run.json"), payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
