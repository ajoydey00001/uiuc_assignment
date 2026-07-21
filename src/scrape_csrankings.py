"""Scrape CSRankings.org top-N US institutions per niche via headless Chromium.

CSRankings computes its institution rankings client-side in JavaScript from raw
per-author DBLP data (adjusted publication counts across venues in an area group);
there is no plain-HTTP endpoint that returns this table, so a static fetch of the
page (confirmed empty SPA shell) cannot be a faithful source. This script drives a
real headless browser, selects the niche's area group and the USA region exactly as
a human visitor would via the UI controls, and reads the resulting rendered table --
avoiding any reimplementation of CSRankings' non-public aggregation algorithm.
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from common import ROOT

# CSRankings' internal area-group checkbox ids, keyed by our study's niche labels.
# "all" is a special keyword in CSRankings' URL router (handleNavigation): it checks
# every area, producing the all-areas ("overall") ranking used as the general-fame
# ground truth alongside the niche-specific ones.
AREA_CODES = {
    "se": "soft",  # Software Engineering group: FSE, ICSE, ASE, ISSTA
    "vision": "vision",  # Computer Vision group: CVPR, ECCV, ICCV
    "overall": "all",  # every area checked -- CSRankings' default all-areas ranking
}

ROW_RE = re.compile(
    r'<td class="rank-cell">(?P<rank>\d+)</td>.*?'
    r"onclick=\"csr\.toggleFaculty\('[^']*'\);\" style=\"cursor:pointer;\"[^>]*>(?P<institution>[^<]+)</span>"
    r'.*?<img title="(?P<country>[^"]+)"[^>]*>'
    r'.*?<td align="right">(?P<count>[\d.]+)</td>'
    r'<td align="right">(?P<faculty>\d+)</td>',
    re.S,
)


def scrape_area(area_code: str, timeout_ms: int = 20000) -> list[dict]:
    """Load csrankings.org filtered to exactly `area_code` + USA, read the rendered table.

    CSRankings' own client-side router (handleNavigation in csrankings.js) reads the
    URL hash `#/index?{area_code}&us` on load: it clears all area checkboxes, checks
    only `area_code`, and sets the region dropdown to "us" -- this is the same
    mechanism a human clicking area checkboxes triggers, just driven via URL instead
    of simulated clicks (which are unreliable here: the checkbox inputs are visually
    hidden/overlaid by a tour widget on first visit, so direct DOM clicks silently
    fail to toggle framework state). Verified empirically: navigating to
    `?soft&us` vs `?vision&us` produces genuinely different top-ranked institutions,
    confirming this is not accidentally returning the "all areas" aggregate.
    """
    url = f"https://csrankings.org/#/index?{area_code}&us"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(2000)
        checked_areas = page.eval_on_selector_all(
            "input[type=checkbox]:checked", "els => els.map(e => e.id)"
        )
        region_text = page.inner_text("#region-selected-text").strip()
        table_html = page.inner_html("#ranking")
        browser.close()

    if area_code == "all":
        # "all" is a router keyword, not a checkbox id -- verify it actually checked
        # (nearly) everything rather than looking for a checkbox literally named "all".
        if len(checked_areas) < 50:
            raise RuntimeError(
                f"URL {url!r} was expected to select every area but only "
                f"{len(checked_areas)} checkboxes are checked. CSRankings' 'all' "
                "keyword handling may have changed -- do not trust this baseline."
            )
    elif area_code not in checked_areas:
        raise RuntimeError(
            f"URL {url!r} did not select area_code={area_code!r} (checked areas: "
            f"{checked_areas!r}). The area code may be wrong or CSRankings' URL "
            "routing behavior changed -- do not trust a baseline scraped like this."
        )
    if region_text != "USA":
        raise RuntimeError(
            f"Expected region 'USA' after navigating to {url!r}, got {region_text!r}."
        )

    rows = [
        {
            "rank": int(m.group("rank")),
            "institution": m.group("institution").strip(),
            "country": m.group("country").strip(),
            "count": float(m.group("count")),
            "faculty": int(m.group("faculty")),
        }
        for m in ROW_RE.finditer(table_html)
    ]
    if not rows:
        raise RuntimeError(
            f"Scraped zero rows for area_code={area_code!r}. CSRankings' DOM structure may "
            "have changed -- inspect the live page manually before trusting this baseline."
        )
    non_us = [r for r in rows if r["country"] != "United States"]
    if non_us:
        raise RuntimeError(
            f"Region filter did not restrict to USA -- got {len(non_us)} non-US rows "
            f"(e.g. {non_us[0]}). The region-filtering behavior may have changed."
        )
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape CSRankings top-N US institutions per niche.")
    parser.add_argument("--niches", default="se,vision")
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--output", default="data/institutions")
    args = parser.parse_args()

    output_dir = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    retrieved_date = datetime.now(timezone.utc).date().isoformat()

    merged_rows: list[dict] = []
    for niche in [n.strip() for n in args.niches.split(",") if n.strip()]:
        if niche not in AREA_CODES:
            raise ValueError(f"Unknown niche {niche!r}; known niches: {sorted(AREA_CODES)}")
        area_code = AREA_CODES[niche]
        print(f"Scraping niche={niche} (csrankings area code={area_code!r}, region=us) ...")
        all_rows = scrape_area(area_code)
        top_rows = all_rows[: args.top_n]
        print(f"  {len(all_rows)} US rows -> keeping top {len(top_rows)}")

        raw_path = output_dir / f"csrankings_{niche}_raw.csv"
        write_csv(
            raw_path,
            [
                {
                    "rank": r["rank"],
                    "institution": r["institution"],
                    "country": r["country"],
                    "count": r["count"],
                    "faculty": r["faculty"],
                }
                for r in all_rows
            ],
            ["rank", "institution", "country", "count", "faculty"],
        )
        print(f"  wrote {raw_path.relative_to(ROOT)} ({len(all_rows)} rows, full US snapshot for this niche)")

        for r in top_rows:
            merged_rows.append(
                {
                    "niche": niche,
                    "rank": r["rank"],
                    "institution": r["institution"],
                    "metric_value": r["count"],
                    "metric_type": "csrankings_adjusted_count",
                    "source_url": f"https://csrankings.org/#/index?{area_code}&us",
                    "retrieved_date": retrieved_date,
                }
            )

    master_path = output_dir / "master_institution_list.csv"
    write_csv(
        master_path,
        merged_rows,
        ["niche", "rank", "institution", "metric_value", "metric_type", "source_url", "retrieved_date"],
    )
    print(f"wrote {master_path.relative_to(ROOT)} ({len(merged_rows)} rows)")


if __name__ == "__main__":
    main()
