import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
manifest_path = ROOT / "06-figure" / "figure-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["status"] = "REVIEW_REQUIRED"
removed = {"FIG-Q3-TIME-CONV", "FIG-Q3-COMBINED-BOUNDARY", "FIG-Q4-COMBINED-BOUNDARY"}
manifest["main_figures"] = [fid for fid in manifest["main_figures"] if fid not in removed]
manifest["n_figures"] = len(manifest["main_figures"]) + len(manifest["appendix_figures"])
manifest["items"] = [item for item in manifest["items"] if item["id"] not in removed]

for item in manifest["items"]:
    # Refresh hashes for every active figure so the current manifest is the
    # single source of truth after any approved redraw; apply the new data
    # claims/revision labels only to the figures changed in this revision.
    if item.get("id", "").startswith("FIG"):
        png = ROOT / item["png"]
        svg = ROOT / item["svg"]
        pdf = ROOT / item.get("pdf", "06-figure/figures/unused.pdf")
        item["png_sha256"] = hashlib.sha256(png.read_bytes()).hexdigest()
        item["svg_sha256"] = hashlib.sha256(svg.read_bytes()).hexdigest()
        if pdf.exists():
            item["pdf_sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if item["id"] in {"FIG-Q2-MODEL-ABLATION", "FIG-Q2-GRID-CONV", "FIG-Q3-SPACE-CONV", "FIG-Q4-SPACE-CONV"}:
        item["visual_revision"] = "user-revision-20260913"
        item["data_claim_status"] = "unchanged" if item["id"] == "FIG-Q2-MODEL-ABLATION" else "expanded-grid-evidence-at-fixed-dt5s" if item["id"] == "FIG-Q2-GRID-CONV" else "expanded-grid-evidence-at-fixed-dt60s"

manifest["revision_note"] = "用户确认：移除原图8、10、13；图4改为三模型同尺度分面，图5扩展为六组径向网格（dt=5 s），图15/16扩展为五组径向网格（dt=60 s）。"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"FIGURE_PLAN_UPDATED {manifest['n_figures']}")
