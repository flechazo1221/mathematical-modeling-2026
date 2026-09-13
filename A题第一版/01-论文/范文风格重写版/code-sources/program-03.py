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

