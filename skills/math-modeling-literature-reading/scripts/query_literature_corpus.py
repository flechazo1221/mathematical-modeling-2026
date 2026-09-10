#!/usr/bin/env python3
"""Return a bounded set of relevant literature chunks for token-efficient reading."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def terms(text: str) -> list[str]:
    lowered = text.lower()
    english = re.findall(r"[a-z][a-z0-9_-]{1,}", lowered)
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", lowered)
    chinese: list[str] = []
    for run in chinese_runs:
        if len(run) <= 3:
            chinese.append(run)
        chinese.extend(run[index:index + 2] for index in range(len(run) - 1))
    return english + chinese


def load_chunks(path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict) or not value.get("text"):
                raise ValueError(f"invalid chunk at line {line_number}")
            chunks.append(value)
    return chunks


def score_chunks(chunks: list[dict[str, Any]], query: str) -> list[tuple[float, dict[str, Any]]]:
    query_terms = set(terms(query))
    if not query_terms:
        return []
    document_frequency: Counter[str] = Counter()
    tokenized: list[Counter[str]] = []
    for chunk in chunks:
        counts = Counter(terms(str(chunk["text"])))
        tokenized.append(counts)
        document_frequency.update(set(counts) & query_terms)
    total = max(1, len(chunks))
    ranked: list[tuple[float, dict[str, Any]]] = []
    for chunk, counts in zip(chunks, tokenized):
        score = 0.0
        for token in query_terms:
            frequency = counts.get(token, 0)
            if frequency:
                inverse = math.log((total + 1) / (document_frequency[token] + 0.5)) + 1
                score += inverse * (1 + math.log(frequency))
        normalized_query = re.sub(r"\s+", "", query.lower())
        normalized_text = re.sub(r"\s+", "", str(chunk["text"]).lower())
        if len(normalized_query) >= 4 and normalized_query in normalized_text:
            score += 8.0
        if score > 0:
            ranked.append((score, chunk))
    ranked.sort(key=lambda item: (item[0], item[1].get("chunk_id", "")), reverse=True)
    return ranked


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", required=True, type=Path)
    parser.add_argument("--query", action="append", required=True)
    parser.add_argument("--top-k", type=int, default=3, help="Maximum chunks contributed by each query")
    parser.add_argument("--max-chars", type=int, default=18000, help="Hard output text budget")
    parser.add_argument("--source-id", action="append", help="Optional source filter such as L01")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.top_k < 1 or args.max_chars < 500:
        print("ERROR: invalid output bounds", file=sys.stderr)
        return 2
    try:
        chunks = load_chunks(args.chunks)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.source_id:
        allowed = set(args.source_id)
        chunks = [chunk for chunk in chunks if chunk.get("source_id") in allowed]

    selected: dict[str, dict[str, Any]] = {}
    for query in dict.fromkeys(item.strip() for item in args.query if item.strip()):
        for score, chunk in score_chunks(chunks, query)[:args.top_k]:
            key = str(chunk.get("chunk_id"))
            record = selected.setdefault(key, {"chunk": chunk, "queries": [], "score": score})
            record["queries"].append(query)
            record["score"] = max(record["score"], score)

    ordered = sorted(selected.values(), key=lambda item: item["score"], reverse=True)
    used = 0
    emitted = 0
    print("# Retrieved literature chunks")
    for item in ordered:
        chunk = item["chunk"]
        header = (
            f"\n## {chunk.get('chunk_id')} | source {chunk.get('source_id')} | "
            f"PDF page {chunk.get('page')} | score {item['score']:.2f}\n"
            f"Queries: {'; '.join(item['queries'])}\n\n"
        )
        text = str(chunk["text"])
        remaining = args.max_chars - used - len(header)
        if remaining <= 0:
            break
        if len(text) > remaining:
            text = text[:remaining].rstrip() + "\n[truncated by max-chars]"
        print(header + text)
        used += len(header) + len(text)
        emitted += 1
        if used >= args.max_chars:
            break
    print(f"\nRetrieved {emitted} unique chunks within {used} text characters.")
    return 0 if emitted else 3


if __name__ == "__main__":
    raise SystemExit(main())
