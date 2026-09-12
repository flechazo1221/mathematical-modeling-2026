from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("figure_id")
parser.add_argument("--note", required=True)
args = parser.parse_args()

revision = Path(__file__).resolve().parents[1]
figure_stage = revision.parent
source_dir = revision / "figures"
formal_dir = figure_stage / "figures"
superseded_dir = revision / "superseded"
manifest_path = figure_stage / "figure-manifest.json"
approval_path = revision / "approval-register.json"

for ext in ("png", "svg", "pdf"):
    source = source_dir / f"{args.figure_id}.{ext}"
    if not source.exists():
        raise FileNotFoundError(source)

superseded_dir.mkdir(parents=True, exist_ok=True)
formal_dir.mkdir(parents=True, exist_ok=True)
for ext in ("png", "svg", "pdf"):
    formal = formal_dir / f"{args.figure_id}.{ext}"
    backup = superseded_dir / f"{args.figure_id}.{ext}"
    if formal.exists() and not backup.exists():
        shutil.copy2(formal, backup)
    shutil.copy2(source_dir / f"{args.figure_id}.{ext}", formal)

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
item = next(x for x in manifest["items"] if x["id"] == args.figure_id)
item["png_sha256"] = sha256(formal_dir / f"{args.figure_id}.png")
item["svg_sha256"] = sha256(formal_dir / f"{args.figure_id}.svg")
item["pdf"] = f"06-figure/figures/{args.figure_id}.pdf"
item["pdf_sha256"] = sha256(formal_dir / f"{args.figure_id}.pdf")
item["visual_revision"] = "beautified-20260912"
item["approval_status"] = "TEAM_APPROVED"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if approval_path.exists():
    approvals = json.loads(approval_path.read_text(encoding="utf-8"))
else:
    approvals = {
        "schema_version": "1.0",
        "visual_style": {
            "reference": "user-provided academic plot style",
            "axes": "white background, thin four-sided frame, inward ticks, no grid",
            "fonts": "Chinese axes in SimSun; digits and Latin labels in Arial; caption in SimHei",
            "series": "restrained colored solid lines with direct labels",
            "caption": "below plot; no extra note directly below caption"
        },
        "approved_figures": []
    }

approvals["approved_figures"] = [
    x for x in approvals["approved_figures"] if x["figure_id"] != args.figure_id
]
approvals["approved_figures"].append({
    "figure_id": args.figure_id,
    "status": "TEAM_APPROVED",
    "approved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "note": args.note,
    "files": {
        ext: {
            "path": f"06-figure/figures/{args.figure_id}.{ext}",
            "sha256": sha256(formal_dir / f"{args.figure_id}.{ext}")
        }
        for ext in ("png", "svg", "pdf")
    }
})
approval_path.write_text(json.dumps(approvals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps(approvals["approved_figures"][-1], ensure_ascii=False, indent=2))
