from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from common import ROOT, load_json_lenient


URL_RE = re.compile(r"https?://[^\s)>\]}\"']+")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
ARXIV_RE = re.compile(r"\b(?:arXiv:)?(\d{4}\.\d{4,5}(?:v\d+)?)\b", re.I)
RANK_RE = re.compile(r"^\s*(?:\d+[\.)]|rank\s*(\d+)[:.)-])\s*(.+)$", re.I)

SOURCE_TYPES = {
    "arxiv.org": "arxiv",
    "doi.org": "academic_paper",
    "dl.acm.org": "academic_paper",
    "ieeexplore.ieee.org": "academic_paper",
    "github.com": "github_repository",
    "docs.github.com": "documentation",
    "openai.com": "company_blog",
    "anthropic.com": "company_blog",
    "deepmind.google": "company_blog",
    "ai.google.dev": "documentation",
    "developers.google.com": "documentation",
    "microsoft.com": "company_blog",
    "research.google": "company_blog",
}


def classify_url(url: str) -> str:
    domain = urlparse(url).netloc.lower().removeprefix("www.")
    for key, value in SOURCE_TYPES.items():
        if domain == key or domain.endswith("." + key):
            return value
    if "conference" in domain or "conf" in domain:
        return "conference_page"
    if "blog" in domain:
        return "personal_blog"
    return "unknown"


def normalize_items(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return [{"text": str(value)}]


def extract_rankings(payload: dict, parsed, text: str) -> list[dict]:
    rows = []
    if isinstance(parsed, dict):
        for idx, item in enumerate(normalize_items(parsed.get("ranked_items")), start=1):
            if not isinstance(item, dict):
                item = {"text": str(item)}
            rank = item.get("rank") or idx
            acronym = item.get("acronym") or item.get("venue") or item.get("conference")
            full_name = item.get("full_name") or item.get("name") or item.get("title")
            justification = item.get("justification") or item.get("impact_summary") or item.get("summary") or item.get("text")
            rows.append(base_row(payload) | {
                "rank": rank,
                "acronym": clean_scalar(acronym),
                "full_name": clean_scalar(full_name),
                "justification": clean_scalar(justification),
            })
    if rows:
        return rows

    for idx, line in enumerate(text.splitlines(), start=1):
        match = RANK_RE.match(line)
        if not match:
            continue
        content = match.group(2).strip()
        acronym = content.split(":", 1)[0].split("-", 1)[0].strip()
        rows.append(base_row(payload) | {
            "rank": idx,
            "acronym": acronym[:40],
            "full_name": content[:200],
            "justification": content,
        })
    return rows


def extract_citations(payload: dict, parsed, text: str) -> list[dict]:
    rows = []
    refs = normalize_items(parsed.get("references") if isinstance(parsed, dict) else None)
    if isinstance(parsed, dict):
        refs += [item for item in normalize_items(parsed.get("ranked_items")) if isinstance(item, dict) and ("doi" in item or "url" in item or "arxiv_id" in item)]
    for item in refs:
        if not isinstance(item, dict):
            item = {"title": str(item)}
        rows.append(base_row(payload) | {
            "title": clean_scalar(item.get("title") or item.get("name") or item.get("source_or_topic")),
            "authors": clean_scalar(item.get("authors") or item.get("authors_or_organization") or item.get("organization_or_authors")),
            "venue": clean_scalar(item.get("venue") or item.get("venue_or_source_type") or item.get("source_type")),
            "year": clean_scalar(item.get("year")),
            "doi": clean_scalar(item.get("doi")),
            "arxiv_id": clean_scalar(item.get("arxiv_id")),
            "url": clean_scalar(item.get("url")),
        })

    if rows:
        return rows

    urls = URL_RE.findall(text)
    dois = DOI_RE.findall(text)
    arxivs = ARXIV_RE.findall(text)
    for url in urls:
        rows.append(base_row(payload) | {"title": "", "authors": "", "venue": "", "year": "", "doi": "", "arxiv_id": "", "url": url})
    for doi in dois:
        rows.append(base_row(payload) | {"title": "", "authors": "", "venue": "", "year": "", "doi": doi, "arxiv_id": "", "url": f"https://doi.org/{doi}"})
    for arxiv in arxivs:
        rows.append(base_row(payload) | {"title": "", "authors": "", "venue": "arXiv", "year": "", "doi": "", "arxiv_id": arxiv, "url": f"https://arxiv.org/abs/{arxiv}"})
    return dedupe_dicts(rows)


def extract_links(payload: dict, citations: list[dict]) -> list[dict]:
    rows = []
    for cit in citations:
        url = cit.get("url") or ""
        if not url and cit.get("doi"):
            url = f"https://doi.org/{cit['doi']}"
        if not url and cit.get("arxiv_id"):
            url = f"https://arxiv.org/abs/{cit['arxiv_id']}"
        if not url:
            continue
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        rows.append(base_row(payload) | {
            "url": url,
            "domain": domain,
            "source_type": classify_url(url),
            "claimed_purpose": cit.get("title") or cit.get("venue") or "",
            "validation_status": "unvalidated",
        })
    return dedupe_dicts(rows)


def base_row(payload: dict) -> dict:
    return {
        "model": payload.get("model", ""),
        "provider": payload.get("provider", ""),
        "prompt_id": payload.get("prompt_id", ""),
        "run_id": payload.get("run_id", ""),
    }


def clean_scalar(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).replace("\n", " ").strip()


def dedupe_dicts(rows: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for row in rows:
        key = tuple(sorted(row.items()))
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse raw model responses into rankings, citations, and source links.")
    parser.add_argument("--input", default="data/raw_responses")
    parser.add_argument("--output", default="data/parsed")
    args = parser.parse_args()

    input_dir = ROOT / args.input
    output_dir = ROOT / args.output
    rankings, citations, links = [], [], []

    for path in sorted(input_dir.glob("**/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        text = payload.get("response_text", "")
        parsed = load_json_lenient(text)
        rs = extract_rankings(payload, parsed, text)
        cs = extract_citations(payload, parsed, text)
        rankings.extend(rs)
        citations.extend(cs)
        links.extend(extract_links(payload, cs))

    write_csv(output_dir / "conference_rankings.csv", rankings, ["model", "provider", "prompt_id", "run_id", "rank", "acronym", "full_name", "justification"])
    write_csv(output_dir / "citations.csv", citations, ["model", "provider", "prompt_id", "run_id", "title", "authors", "venue", "year", "doi", "arxiv_id", "url"])
    write_csv(output_dir / "source_links.csv", links, ["model", "provider", "prompt_id", "run_id", "url", "domain", "source_type", "claimed_purpose", "validation_status"])
    print(f"parsed {len(rankings)} rankings, {len(citations)} citations, {len(links)} links")


if __name__ == "__main__":
    main()

