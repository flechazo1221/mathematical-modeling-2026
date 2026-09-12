"""Run only the high-resolution B/C length controls for the parent prototype."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_q4_sensitivity as m  # noqa: E402


def safe(v):
    if isinstance(v, dict):
        return {str(k): safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [safe(x) for x in v]
    try:
        import numpy as np
        if isinstance(v, (np.floating, np.integer)):
            return v.item()
    except Exception:
        pass
    return v


def main() -> None:
    out_dir = m.MODEL_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = m.LOG_DIR / "fine-controls.log"
    rows = []
    with log_path.open("w", encoding="utf-8") as log_file:
        def log(msg: str) -> None:
            line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
            print(line, flush=True)
            log_file.write(line + "\n")
            log_file.flush()

        for alpha, label in ((1.0, "length-B-radius-proportional-fine-control"),
                             (2.0, "length-C-upper-envelope-alpha2-fine-control")):
            cfg = m.RunConfig(label, "convergence_control", alpha,
                              nr=m.NR_FINE, nz=m.NZ_FINE, dt=m.DT_BASE)
            log(f"START {label} cfg={cfg.__dict__}")
            result = m.simulate(cfg, log)
            with (out_dir / f"{label}.json").open("w", encoding="utf-8") as f:
                json.dump(safe(result), f, ensure_ascii=False, indent=2)
            rows.append({"label": label, "group": cfg.group, **cfg.__dict__, **result["metrics"]})
    path = m.RESULTS_DIR / "fine-length-controls.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
