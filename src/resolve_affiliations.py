"""Resolve first-author institutional affiliations for LLM-cited papers via OpenAlex.

For each unique paper title in data/parsed/paper_mentions.csv, query the OpenAlex API
and record the top hit's first-author institution. The model's own claimed affiliation
is kept alongside: the two columns disagree exactly where the model's self-report is
wrong (a validity result), and titles OpenAlex cannot find at all are hallucination
candidates.

OpenAlex now runs a credit-budget system: $1/day free usage WITH an api_key vs
$0.01/day without (effectively unusable without one). Get a free key at
https://openalex.org/settings/api and set OPENALEX_API_KEY in .env.

Responses are cached in data/cache/openalex_cache.json so reruns and partner machines
never re-hit the API for known titles. If the daily budget/network is unavailable the
stage writes what it can from cache, marks the rest unresolved_network, and exits 0 --
the pipeline must keep working with a partially- or un-resolved budget.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time

import pandas as pd
import requests
from dotenv import load_dotenv
from rapidfuzz import fuzz

from common import ROOT

OPENALEX_URL = "https://api.openalex.org/works"
MAILTO = "ajoyakash84@gmail.com"  # kept alongside api_key; harmless, some endpoints still read it


def cache_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def lookup_openalex(title: str, session: requests.Session, api_key: str | None) -> dict:
    """Return {status, oa_title, oa_first_author, oa_institution, oa_country, oa_year, oa_id}.

    Strategy: fetch the top 5 search hits, keep only those whose title actually
    matches the query (token_sort_ratio >= 90 -- OpenAlex "search" is fuzzy and
    happily returns similarly-titled different papers), then take the MOST-CITED
    matching hit that has a first-author institution. Canonical originals out-cite
    both reprints and same-title doppelgangers. A hit that matches no title closely
    is returned as low_confidence and treated downstream as unusable.

    `?`/`*` are stripped before searching: OpenAlex's `search` parameter treats them
    as wildcard operators even when percent-encoded, and rejects them with a 400
    unless using the separate `search.exact` syntax -- many real paper titles end in
    a literal `?` (survey/question-style titles), so stripping (rather than erroring
    or switching search modes) keeps those queries working; the token_sort_ratio
    post-filter below doesn't care about the missing punctuation.
    """
    query = re.sub(r"[?*]", "", title).strip()
    params = {"search": query, "per-page": 5, "mailto": MAILTO}
    if api_key:
        params["api_key"] = api_key
    resp = session.get(OPENALEX_URL, params=params, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        return {"status": "not_found"}

    def first_author_institution(work: dict) -> dict:
        authorships = work.get("authorships") or []
        first = next((a for a in authorships if a.get("author_position") == "first"), authorships[0] if authorships else None)
        institutions = (first or {}).get("institutions") or []
        inst = institutions[0] if institutions else {}
        return {
            "author": ((first or {}).get("author") or {}).get("display_name") or "",
            "institution": inst.get("display_name") or "",
            "country": inst.get("country_code") or "",
        }

    query_norm = cache_key(title)
    similar = [w for w in results if fuzz.token_sort_ratio(query_norm, cache_key(w.get("title") or "")) >= 90]
    if similar:
        pool, base_status = similar, "resolved"
    else:
        pool, base_status = results[:1], "low_confidence"

    pool = sorted(pool, key=lambda w: w.get("cited_by_count") or 0, reverse=True)
    work, fa = pool[0], first_author_institution(pool[0])
    for w in pool:
        candidate = first_author_institution(w)
        if candidate["institution"]:
            work, fa = w, candidate
            break
    status = base_status if fa["institution"] else "no_affiliation"
    return {
        "status": status,
        "oa_title": work.get("title") or "",
        "oa_first_author": fa["author"],
        "oa_institution": fa["institution"],
        "oa_country": fa["country"],
        "oa_year": work.get("publication_year") or "",
        "oa_id": work.get("id") or "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve paper first-author affiliations via OpenAlex.")
    parser.add_argument("--papers", default="data/parsed/paper_mentions.csv")
    parser.add_argument("--output", default="data/parsed/paper_affiliations.csv")
    parser.add_argument("--cache", default="data/cache/openalex_cache.json")
    parser.add_argument("--sleep", type=float, default=0.15, help="Seconds between API calls (polite pool).")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("OPENALEX_API_KEY")
    if not api_key:
        print(
            "OPENALEX_API_KEY not set -- OpenAlex's free-without-a-key budget is "
            "$0.01/day (effectively nothing). Get a free key at "
            "https://openalex.org/settings/api and add OPENALEX_API_KEY to .env "
            "for the $1/day budget. Continuing with cache only."
        )

    papers_path = ROOT / args.papers
    output_path = ROOT / args.output
    cache_path = ROOT / args.cache
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if not papers_path.exists():
        pd.DataFrame().to_csv(output_path, index=False)
        print("no paper_mentions.csv yet -- wrote empty paper_affiliations.csv")
        return
    papers = pd.read_csv(papers_path)
    if papers.empty:
        papers.assign(resolved_status=[]).to_csv(output_path, index=False)
        print("paper_mentions.csv is empty -- wrote empty paper_affiliations.csv")
        return

    cache: dict[str, dict] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    session = requests.Session()
    # Check remaining daily budget once upfront (per OpenAlex's documented
    # /rate-limit endpoint) rather than discovering it title-by-title after
    # burning through retries -- a $0-budget day should fail fast with one
    # clear message, not 4 retries times however many titles are unresolved.
    network_ok = True
    if api_key:
        try:
            rl = session.get("https://api.openalex.org/rate-limit", params={"api_key": api_key}, timeout=15)
            rl.raise_for_status()
            remaining = rl.json().get("rate_limit", {}).get("daily_remaining_usd")
            if remaining is not None and remaining <= 0:
                print("OpenAlex daily budget is $0 remaining (resets midnight UTC) -- continuing with cache only.")
                network_ok = False
            else:
                print(f"OpenAlex daily budget remaining: ${remaining}")
        except requests.RequestException as exc:
            print(f"Could not check OpenAlex budget ({exc}); will attempt lookups and back off if needed.")

    looked_up = 0
    for title in papers["title"].dropna().unique():
        key = cache_key(title)
        if not key or key in cache:
            continue
        if not network_ok:
            continue
        for attempt in range(4):
            try:
                cache[key] = lookup_openalex(title, session, api_key)
                looked_up += 1
                time.sleep(args.sleep)
                break
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                # 429/5xx are transient -- back off and retry this title.
                if status in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(10 * (attempt + 1))
                    continue
                # Any other HTTP error (e.g. 400 -- a malformed query for this
                # specific title) is a per-title failure, not evidence OpenAlex is
                # down. Skip only this title and keep processing the rest of the
                # batch; a single bad title must never abort everything else, which
                # is exactly what happened before this fix (one 400 stalled 73
                # already-authenticated, budget-available lookups).
                print(f"  skipping {title[:70]!r}: HTTP {status}")
                cache[key] = {"status": "request_error"}
                break
            except requests.RequestException as exc:
                # Genuine connectivity failure (DNS/timeout/connection refused) --
                # this really does affect every subsequent request, so stop the
                # batch; unresolved titles stay out of the cache so a later online
                # rerun fills them.
                print(f"OpenAlex unreachable ({exc}); continuing offline with cache only.")
                network_ok = False
                break

    cache_path.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")

    def annotate(row):
        entry = cache.get(cache_key(row["title"]))
        if entry is None:
            return pd.Series({"resolved_status": "unresolved_network", "oa_title": "", "oa_first_author": "",
                              "oa_institution": "", "oa_country": "", "oa_year": "", "oa_id": ""})
        return pd.Series({
            "resolved_status": entry.get("status", "not_found"),
            "oa_title": entry.get("oa_title", ""),
            "oa_first_author": entry.get("oa_first_author", ""),
            "oa_institution": entry.get("oa_institution", ""),
            "oa_country": entry.get("oa_country", ""),
            "oa_year": entry.get("oa_year", ""),
            "oa_id": entry.get("oa_id", ""),
        })

    out = pd.concat([papers, papers.apply(annotate, axis=1)], axis=1)
    out.to_csv(output_path, index=False)
    counts = out["resolved_status"].value_counts().to_dict()
    print(f"wrote {output_path.relative_to(ROOT)} ({len(out)} rows, {looked_up} new lookups, status: {counts})")


if __name__ == "__main__":
    main()
