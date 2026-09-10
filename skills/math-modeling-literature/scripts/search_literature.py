#!/usr/bin/env python3
"""Run traceable multi-query literature discovery with the suite's hybrid search."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize_doi(value: Any) -> str | None:
    if not value:
        return None
    doi = str(value).strip().lower()
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi)
    return doi.rstrip(".,; ") or None


def normalize_title(value: Any) -> str:
    return " ".join(re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", str(value or "").lower()).split())


def paper_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return dict(value)


def merge_candidate(existing: dict[str, Any], incoming: dict[str, Any], query: str) -> None:
    existing["matched_queries"] = sorted(set(existing.get("matched_queries", [])) | {query})
    existing["sources"] = sorted(set(existing.get("sources", [])) | set(incoming.get("sources", [])))
    existing["cross_validated"] = len(existing["sources"]) >= 2
    for field in ("authors", "year", "citations", "doi", "abstract", "venue", "volume", "issue", "pages", "url"):
        old = existing.get(field)
        new = incoming.get(field)
        if not old and new:
            existing[field] = new
        elif field == "citations" and isinstance(new, int) and new > int(old or 0):
            existing[field] = new


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", required=True, help="Repeat for each approved search query")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit-per-query", type=int, default=12)
    parser.add_argument("--year-from", type=int)
    parser.add_argument("--year-to", type=int)
    parser.add_argument("--field", choices=[
        "mathematics", "computer_science", "engineering", "statistics",
        "operations_research", "physics", "economics",
    ])
    parser.add_argument("--email", help="OpenAlex polite-pool email")
    parser.add_argument("--anysearch-api-key", help="Defaults to ANYSEARCH_API_KEY")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.limit_per_query < 1 or args.limit_per_query > 100:
        print("ERROR: --limit-per-query must be between 1 and 100", file=sys.stderr)
        return 2

    suite_root = Path(__file__).resolve().parents[3]
    search_scripts = suite_root / "tools" / "paper_search" / "scripts"
    if not search_scripts.is_dir():
        print(f"ERROR: bundled paper-search scripts not found: {search_scripts}", file=sys.stderr)
        return 2
    sys.path.insert(0, str(search_scripts))
    from hybrid_scholar import HybridScholar  # type: ignore

    scholar = HybridScholar(email=args.email, anysearch_api_key=args.anysearch_api_key)
    merged: dict[str, dict[str, Any]] = {}
    runs: list[dict[str, Any]] = []

    for query in dict.fromkeys(q.strip() for q in args.query if q.strip()):
        result = scholar.search_papers(
            query=query,
            limit=args.limit_per_query,
            year_from=args.year_from,
            year_to=args.year_to,
            field_filter=args.field,
        )
        stats = dict(result.get("stats", {}))
        runs.append({"query": query, "stats": stats})
        for group in ("cross_validated", "openalex_only", "anysearch_only"):
            for raw in result.get(group, []):
                paper = paper_dict(raw)
                paper["doi"] = normalize_doi(paper.get("doi"))
                paper["matched_queries"] = [query]
                paper["result_group"] = group
                paper["sources"] = sorted(set(paper.get("sources") or []))
                paper["cross_validated"] = len(paper["sources"]) >= 2
                key = f"doi:{paper['doi']}" if paper["doi"] else (
                    f"title:{normalize_title(paper.get('title'))}:{paper.get('year') or ''}"
                )
                if key in merged:
                    merge_candidate(merged[key], paper, query)
                else:
                    merged[key] = paper

    candidates = list(merged.values())
    candidates.sort(key=lambda p: (
        bool(p.get("cross_validated")),
        len(p.get("matched_queries", [])),
        int(p.get("citations") or 0),
    ), reverse=True)
    payload = {
        "schema_version": "1.0",
        "generated_at": now_iso(),
        "engine_policy": "OpenAlex + AnySearch; degraded runs remain visible in search_runs",
        "search_runs": runs,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(candidates)} unique candidates to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
