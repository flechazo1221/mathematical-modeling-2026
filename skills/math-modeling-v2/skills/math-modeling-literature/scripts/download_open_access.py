#!/usr/bin/env python3
"""Resolve and download legal open-access PDFs with a traceable manifest."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


USER_AGENT = "MathModelingLiterature/1.0 (open-access resolver)"
MAX_BYTES = 100 * 1024 * 1024


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


def is_public_http_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return False
        host = parsed.hostname.lower().rstrip(".")
        if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal")):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            # Validate the public hostname rather than resolved addresses. Some managed
            # runtimes intentionally resolve public hosts through a non-global proxy IP.
            return "." in host and bool(re.fullmatch(r"[a-z0-9.-]+", host))
    except (ValueError, OSError):
        return False


class PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if not is_public_http_url(newurl):
            raise urllib.error.URLError("redirect target is not a public HTTP(S) URL")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(PublicRedirectHandler())


def request_json(url: str) -> dict[str, Any] | None:
    if not is_public_http_url(url):
        return None
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with OPENER.open(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
        return None


def exact_enough(work: dict[str, Any], title: str, year: int | None) -> bool:
    wanted = set(normalize_title(title).split())
    found = set(normalize_title(work.get("display_name") or work.get("title")).split())
    overlap = len(wanted & found) / max(len(wanted), len(found), 1)
    work_year = work.get("publication_year")
    year_ok = not year or not work_year or abs(int(year) - int(work_year)) <= 1
    return overlap >= 0.9 and year_ok


def resolve_openalex(candidate: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    fields = "id,doi,display_name,publication_year,open_access,best_oa_location,locations"
    doi = normalize_doi(candidate.get("doi"))
    if doi:
        filt = urllib.parse.quote(f"doi:https://doi.org/{doi}", safe=":/")
        url = f"https://api.openalex.org/works?filter={filt}&per-page=1&select={fields}"
        data = request_json(url) or {}
        results = data.get("results") or []
        work = results[0] if results else None
    else:
        title = str(candidate.get("title") or "").strip()
        if not title:
            return None, []
        query = urllib.parse.urlencode({"search": title, "per-page": 5, "select": fields})
        data = request_json(f"https://api.openalex.org/works?{query}") or {}
        work = next((item for item in data.get("results") or [] if exact_enough(
            item, title, candidate.get("year") or candidate.get("publication_year")
        )), None)

    if not work:
        return None, []
    urls: list[str] = []
    locations = [work.get("best_oa_location")] + list(work.get("locations") or [])
    for location in locations:
        if not isinstance(location, dict) or not location.get("is_oa"):
            continue
        pdf_url = location.get("pdf_url")
        if pdf_url and pdf_url not in urls and is_public_http_url(pdf_url):
            urls.append(pdf_url)
    return work, urls


def safe_stem(index: int, candidate: dict[str, Any]) -> str:
    title = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", " ", str(candidate.get("title") or "paper"))
    title = " ".join(title.split())[:120].rstrip(" .") or "paper"
    year = candidate.get("year") or candidate.get("publication_year") or "n.d."
    return f"{index:03d}_{year}_{title}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_pdf_file(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(5) == b"%PDF-"
    except OSError:
        return False


def download_pdf(url: str, destination: Path) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf,application/octet-stream;q=0.8",
    })
    part = destination.with_suffix(destination.suffix + ".part")
    total = 0
    try:
        with OPENER.open(req, timeout=60) as response, part.open("wb") as handle:
            final_url = response.geturl()
            if not is_public_http_url(final_url):
                raise ValueError("final URL is not public")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ValueError("PDF exceeds 100 MiB limit")
                handle.write(chunk)
        with part.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise ValueError("response is not a PDF")
        part.replace(destination)
        return final_url, sha256_file(destination)
    except Exception:
        if part.exists():
            part.unlink()
        raise


def load_candidates(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("candidates") or data.get("selected_candidates")
    if not isinstance(items, list):
        raise ValueError("input must be a list or contain candidates/selected_candidates")
    return [item for item in items if isinstance(item, dict)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--limit", type=int, help="Optional maximum number of selected records")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        candidates = load_candidates(args.input)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.limit is not None:
        if args.limit < 1:
            print("ERROR: --limit must be positive", file=sys.stderr)
            return 2
        candidates = candidates[:args.limit]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, 1):
        record: dict[str, Any] = {
            "title": candidate.get("title"),
            "doi": normalize_doi(candidate.get("doi")),
            "status": "pending",
            "attempted_urls": [],
        }
        try:
            work, urls = resolve_openalex(candidate)
            record["openalex_id"] = work.get("id") if work else None
            record["attempted_urls"] = urls
            if not urls:
                record["status"] = "no_open_access_pdf"
            else:
                destination = args.output_dir / f"{safe_stem(index, candidate)}.pdf"
                if destination.exists() and is_pdf_file(destination):
                    record.update({
                        "status": "existing",
                        "file": str(destination.resolve()),
                        "sha256": sha256_file(destination),
                    })
                else:
                    errors: list[str] = []
                    for url in urls:
                        try:
                            final_url, digest = download_pdf(url, destination)
                            record.update({
                                "status": "downloaded",
                                "source_url": final_url,
                                "file": str(destination.resolve()),
                                "sha256": digest,
                            })
                            break
                        except (OSError, ValueError, urllib.error.URLError) as exc:
                            errors.append(f"{url}: {exc}")
                    if record["status"] == "pending":
                        record["status"] = "download_failed"
                        record["errors"] = errors
        except Exception as exc:
            record["status"] = "resolution_failed"
            record["errors"] = [str(exc)]
        records.append(record)

    counts: dict[str, int] = {}
    for record in records:
        status = str(record["status"])
        counts[status] = counts.get(status, 0) + 1
    payload = {
        "schema_version": "1.0",
        "generated_at": now_iso(),
        "input": str(args.input.resolve()),
        "counts": counts,
        "records": records,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Processed {len(records)} records; manifest: {args.manifest.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
