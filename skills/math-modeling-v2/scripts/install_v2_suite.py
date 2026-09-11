#!/usr/bin/env python3
"""Install the v2 skill suite without replacing the legacy math-modeling skill."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from validate_v2_suite import validate_suite


INSTALL_PARTS = ("skills", "shared", "scripts", "references", "assets", "tools")


def default_skills_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return Path(codex_home) / "skills" if codex_home else Path.home() / ".codex" / "skills"


def install(source_root: Path, skills_root: Path) -> tuple[Path, Path | None]:
    source = source_root.resolve()
    destination_root = skills_root.resolve()
    destination_root.mkdir(parents=True, exist_ok=True)
    target = destination_root / "math-modeling-v2"

    with tempfile.TemporaryDirectory(prefix="math-modeling-v2-", dir=destination_root) as temp:
        staged = Path(temp) / "math-modeling-v2"
        staged.mkdir()
        for name in INSTALL_PARTS:
            source_part = source / name
            if not source_part.exists():
                raise FileNotFoundError(f"missing install part: {source_part}")
            shutil.copytree(source_part, staged / name)

        errors = validate_suite(staged)
        if errors:
            raise ValueError("staged suite is invalid:\n- " + "\n- ".join(errors))

        backup = None
        if target.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = destination_root / f"math-modeling-v2.backup-{stamp}"
            target.rename(backup)
        try:
            staged.rename(target)
        except Exception:
            if backup and backup.exists() and not target.exists():
                backup.rename(target)
            raise
    return target, backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
    )
    parser.add_argument("--skills-root", type=Path, default=default_skills_root())
    args = parser.parse_args()

    try:
        target, backup = install(args.source_root, args.skills_root)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"Installed v2 suite: {target}")
    if backup:
        print(f"Previous v2 preserved at: {backup}")
    print("Restart Codex or open a new task to refresh skill discovery.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
