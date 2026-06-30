from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import requests

from common import ROOT


def validate_url(url: str, timeout: float) -> tuple[str, int | None]:
    if not isinstance(url, str) or not url.strip():
        return "unverifiable", None
    try:
        response = requests.head(url, allow_redirects=True, timeout=timeout, headers={"User-Agent": "ai-source-study/1.0"})
        if response.status_code in {403, 405}:
            response = requests.get(url, allow_redirects=True, timeout=timeout, headers={"User-Agent": "ai-source-study/1.0"}, stream=True)
        status = response.status_code
    except requests.RequestException:
        return "unverifiable", None

    if 200 <= status < 400:
        return "valid", status
    if status == 404 or status >= 500:
        return "dead_link", status
    return "ambiguous", status


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate URLs in parsed source_links.csv.")
    parser.add_argument("--input", default="data/parsed/source_links.csv")
    parser.add_argument("--output", default="data/parsed/source_links_validated.csv")
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    path = ROOT / args.input
    links = pd.read_csv(path)
    if links.empty:
        links.to_csv(ROOT / args.output, index=False)
        print("no links to validate")
        return

    statuses = links["url"].apply(lambda url: validate_url(url, args.timeout))
    links["validation_status"] = [status for status, _ in statuses]
    links["http_status"] = [code for _, code in statuses]
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    links.to_csv(out, index=False)
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

