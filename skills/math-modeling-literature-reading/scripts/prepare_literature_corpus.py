#!/usr/bin/env python3
"""Normalize CAJ/PDF/text literature into local page chunks without changing sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED = {".caj", ".pdf", ".txt", ".md"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as stream:
            return stream.read(5) == b"%PDF-"
    except OSError:
        return False


def decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def clean_page(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\x00", "").splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def run_command(command: list[str], cwd: Path) -> tuple[int, str]:
    process = subprocess.run(
        command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=300, check=False,
    )
    return process.returncode, decode_text(process.stdout)[-8000:]


def converter_prefix(value: str | None) -> list[str] | None:
    candidate = value or shutil.which("caj2pdf")
    if not candidate:
        return None
    path = Path(candidate)
    return [sys.executable, str(path)] if path.suffix.lower() == ".py" else [str(candidate)]


def convert_caj(source: Path, destination: Path, converter: list[str] | None, cwd: Path) -> tuple[str, str]:
    paired = source.with_suffix(".pdf")
    if paired.is_file() and is_pdf(paired):
        return str(paired), "same-stem PDF supplied by user"
    if is_pdf(source):
        return str(source), "CAJ extension with PDF signature"
    if not converter:
        return "", "caj2pdf command not available"
    destination.parent.mkdir(parents=True, exist_ok=True)
    code, log = run_command([*converter, "convert", str(source), "-o", str(destination)], cwd)
    if code == 0 and destination.is_file() and is_pdf(destination):
        return str(destination), log or "converted by caj2pdf"
    return "", log or f"caj2pdf exited with {code}"


def extract_pdf(path: Path, pdftotext: str) -> tuple[list[str], str]:
    process = subprocess.run(
        [pdftotext, "-enc", "UTF-8", "-layout", str(path), "-"],
        cwd=path.parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=300, check=False,
    )
    output = decode_text(process.stdout)
    if process.returncode != 0:
        return [], decode_text(process.stderr)[-8000:]
    pages = [clean_page(page) for page in output.split("\f")]
    while pages and not pages[-1]:
        pages.pop()
    return pages, ""


def text_is_usable(pages: list[str]) -> bool:
    visible = sum(len(re.sub(r"\s+", "", page)) for page in pages)
    return visible >= max(200, 40 * max(1, len(pages)))


def chunk_pages(source_id: str, pages: list[str], size: int, overlap: int) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    sequence = 0
    for page_number, page in enumerate(pages, 1):
        start = 0
        while start < len(page):
            end = min(len(page), start + size)
            if end < len(page):
                split = page.rfind("\n", start + int(size * 0.6), end)
                if split > start:
                    end = split
            text = page[start:end].strip()
            if text:
                sequence += 1
                chunks.append({
                    "chunk_id": f"{source_id}-C{sequence:04d}",
                    "source_id": source_id,
                    "page": page_number,
                    "char_start": start,
                    "char_end": end,
                    "text": text,
                })
            if end >= len(page):
                break
            start = max(start + 1, end - overlap)
    return chunks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--caj2pdf", help="Optional path to caj2pdf command or Python entry script")
    parser.add_argument("--pdftotext", help="Optional path to pdftotext")
    parser.add_argument("--ocrmypdf", help="Optional path to ocrmypdf")
    parser.add_argument("--chunk-chars", type=int, default=1600)
    parser.add_argument("--overlap-chars", type=int, default=160)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.chunk_chars < 400 or not 0 <= args.overlap_chars < args.chunk_chars // 2:
        print("ERROR: invalid chunk or overlap size", file=sys.stderr)
        return 2
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not input_dir.is_dir():
        print(f"ERROR: input directory missing: {input_dir}", file=sys.stderr)
        return 2
    pdftotext = args.pdftotext or shutil.which("pdftotext")
    converter = converter_prefix(args.caj2pdf)
    ocrmypdf = args.ocrmypdf or shutil.which("ocrmypdf")
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir = output_dir / "normalized"
    text_dir = output_dir / "text"
    work_dir = output_dir / "work"
    for directory in (normalized_dir, text_dir, work_dir):
        directory.mkdir(parents=True, exist_ok=True)

    candidates = sorted(
        (path for path in input_dir.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED),
        key=lambda path: str(path.relative_to(input_dir)).casefold(),
    )
    caj_stems = {path.with_suffix("").resolve() for path in candidates if path.suffix.lower() == ".caj"}
    sources = [path for path in candidates if not (
        path.suffix.lower() == ".pdf" and path.with_suffix("").resolve() in caj_stems
    )]
    manifest: list[dict[str, Any]] = []
    all_chunks: list[dict[str, Any]] = []

    for number, source in enumerate(sources, 1):
        source_id = f"L{number:02d}"
        record: dict[str, Any] = {
            "source_id": source_id,
            "path": str(source),
            "relative_path": source.relative_to(input_dir).as_posix(),
            "sha256": sha256(source),
            "bytes": source.stat().st_size,
            "source_format": source.suffix.lower().lstrip("."),
            "status": "pending",
        }
        pages: list[str] = []
        try:
            if source.suffix.lower() in {".txt", ".md"}:
                pages = [clean_page(decode_text(source.read_bytes()))]
                record["normalization"] = "direct text"
            else:
                pdf_path = source
                if source.suffix.lower() == ".caj":
                    converted = normalized_dir / f"{source_id}.pdf"
                    resolved, log = convert_caj(source, converted, converter, work_dir)
                    record["conversion_log"] = log
                    if not resolved:
                        record["status"] = "needs_manual_conversion"
                        manifest.append(record)
                        continue
                    pdf_path = Path(resolved)
                    record["normalized_pdf"] = str(pdf_path.resolve())
                if not pdftotext:
                    record["status"] = "pdftotext_missing"
                    manifest.append(record)
                    continue
                pages, error = extract_pdf(pdf_path, pdftotext)
                if error:
                    record["extraction_log"] = error
                if not text_is_usable(pages) and ocrmypdf:
                    ocr_pdf = normalized_dir / f"{source_id}-ocr.pdf"
                    code, log = run_command([str(ocrmypdf), "--skip-text", str(pdf_path), str(ocr_pdf)], work_dir)
                    record["ocr_log"] = log
                    if code == 0 and is_pdf(ocr_pdf):
                        pages, error = extract_pdf(ocr_pdf, pdftotext)
                        record["normalized_pdf"] = str(ocr_pdf.resolve())
                        if error:
                            record["extraction_log"] = error
                if not text_is_usable(pages):
                    record["status"] = "ocr_required"
                    record["page_count"] = len(pages)
                    manifest.append(record)
                    continue

            chunks = chunk_pages(source_id, pages, args.chunk_chars, args.overlap_chars)
            text_path = text_dir / f"{source_id}.txt"
            rendered = "\n\n".join(f"[[PAGE {index}]]\n{page}" for index, page in enumerate(pages, 1))
            text_path.write_text(rendered + "\n", encoding="utf-8")
            record.update({
                "status": "ready",
                "page_count": len(pages),
                "text_chars": sum(len(page) for page in pages),
                "chunk_count": len(chunks),
                "text_path": str(text_path.resolve()),
                "text_sha256": sha256(text_path),
            })
            all_chunks.extend(chunks)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            record["status"] = "failed"
            record["error"] = str(exc)
        manifest.append(record)

    chunks_path = output_dir / "chunks.jsonl"
    chunks_path.write_text(
        "".join(json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in all_chunks),
        encoding="utf-8",
    )
    payload = {
        "schema_version": "1.0",
        "generated_at": now_iso(),
        "input_dir": str(input_dir),
        "tools": {"caj2pdf": converter, "pdftotext": pdftotext, "ocrmypdf": ocrmypdf},
        "source_count": len(manifest),
        "ready_count": sum(item["status"] == "ready" for item in manifest),
        "chunk_count": len(all_chunks),
        "sources": manifest,
    }
    manifest_path = output_dir / "corpus-manifest.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {payload['ready_count']}/{len(manifest)} sources and {len(all_chunks)} chunks")
    print(f"Manifest: {manifest_path}")
    return 0 if payload["ready_count"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
