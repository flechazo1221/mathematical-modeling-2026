from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def files() -> list[dict]:
    out = []
    for p in sorted(OUT.rglob("*")):
        if not p.is_file() or p.name in {"handoff.json", "manifest.json"}:
            continue
        if "__pycache__" in p.parts or p.suffix == ".pyc":
            continue
        out.append({"path": p.relative_to(ROOT).as_posix(), "sha256": digest(p), "bytes": p.stat().st_size})
    return out


def input_files() -> list[dict]:
    paths = [
        ROOT / "02-design" / "handoff.json",
        ROOT / "02-design" / "验证计划.json",
        ROOT / "02-design" / "H2-优化审计与方向.md",
        ROOT / "02-design" / "候选模型方案.md",
        ROOT / "decisions" / "H1-problem.json",
        ROOT / "decisions" / "H2-model.json",
        ROOT / "decisions" / "H3-claims.json",
        ROOT / "03-prototype" / "handoff.json",
        ROOT / "04-compute" / "temperature-field-revision-20260912" / "README.md",
        ROOT / "04-compute" / "temperature-field-revision-20260912" / "parameter-diagnosis-20260912.md",
        ROOT / "04-compute" / "src" / "formal_compute.py",
        ROOT / "04-compute" / "temperature-field-revision-20260912" / "formal_compute_revision.py",
    ]
    paths += sorted((ROOT / "input" / "A题" / "附件").rglob("*.xlsx"))
    return [{"path": p.relative_to(ROOT).as_posix(), "sha256": digest(p), "bytes": p.stat().st_size} for p in sorted(set(paths))]


handoff_path = OUT / "handoff.json"
handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
handoff["inputs"] = input_files()
handoff["completed_at"] = datetime.now(timezone.utc).astimezone().isoformat()
(OUT / "input-manifest.json").write_text(json.dumps({"created_at": handoff["completed_at"], "inputs": handoff["inputs"]}, ensure_ascii=False, indent=2), encoding="utf-8")
handoff["outputs"] = files()
handoff_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "manifest.json").write_text(json.dumps({"inputs": handoff["inputs"], "outputs": files()}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"handoff_outputs": len(handoff["outputs"]), "excluded_cache": True}, ensure_ascii=False))
