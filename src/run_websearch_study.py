"""Web-search arm of the implicit institutional-bias study.

Asks each model, *with web search enabled*, for k=20 recent papers in a field, then
ranks institutions by how often they appear as the first author's affiliation. If a
model favours famous universities, those institutions dominate the derived ranking
regardless of their actual publication output in CSRankings.

The prompt matrix is 7 fields x 3 question phrasings (21 prompts):

    fields    se, vision, pl, algorithms, robotics, hci, ai
    phrasings A "recent groundbreaking papers ... to stay updated"
              B "recent papers ... promising directions for future research"
              C "recent interesting papers ... should learn more about"

Three phrasings of the same underlying request separate a stable institutional prior
from wording sensitivity: an institution that dominates all three is a robust result,
one that appears under a single phrasing is an artifact of that wording.

This arm is kept in its own directory tree so it never mixes with the closed-book
data collected earlier:

    data/websearch/raw_responses/   data/websearch/parsed/
    outputs/websearch/tables/       outputs/websearch/figures/

Typical use -- collect fresh responses, then analyse:

    python src/run_websearch_study.py --collect

Analyse whatever has already been collected (no API calls, no cost):

    python src/run_websearch_study.py

Web search is provider-native and only works for anthropic and gemini; local ollama
models have no search backend. Requires ANTHROPIC_API_KEY / GEMINI_API_KEY in .env.

IMPORTANT: after collecting, verify that search actually fired -- see --verify. A
provider that ignores the tool returns a perfectly normal-looking closed-book answer,
which would silently invalidate the whole arm.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = "data/websearch/raw_responses"
PARSED_DIR = "data/websearch/parsed"
TABLE_DIR = "outputs/websearch/tables"
FIGURE_DIR = "outputs/websearch/figures"

# 7 fields x 3 question phrasings, k=20 papers each. Field prefixes match the niche
# codes in data/prompts/prompt_metadata.csv and the CSRankings area codes in
# scrape_csrankings.AREA_CODES, so every niche has a baseline to be scored against.
FIELD_PREFIXES = ["SE", "VIS", "PL", "ALGO", "ROB", "HCI", "AI"]
ALL_PAPER_PROMPTS = ",".join(
    f"{prefix}_PAPERS_{variant}" for prefix in FIELD_PREFIXES for variant in ("A", "B", "C")
)


def run(args: list[str]) -> None:
    print("+", " ".join(args))
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


KEY_FOR_PROVIDER = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def check_keys(providers: list[tuple[str, str]]) -> None:
    """Fail before collection starts if a provider's key is missing.

    Without this the run dies partway through, after already spending calls on the
    providers that did have keys, leaving a half-collected and unusable matrix.
    """
    load_dotenv(ROOT / ".env")
    missing = [
        (provider, KEY_FOR_PROVIDER[provider])
        for provider, _ in providers
        if provider in KEY_FOR_PROVIDER and not os.getenv(KEY_FOR_PROVIDER[provider])
    ]
    if missing:
        lines = "\n".join(f"    {key}   (needed for {provider})" for provider, key in missing)
        raise SystemExit(
            f"Missing API key(s) in {ROOT / '.env'}:\n{lines}\n\n"
            "Add them to .env, or skip that provider, e.g.:\n"
            "    python src/run_websearch_study.py --collect --anthropic-model ''"
        )


def check_baselines(prompt_ids: str) -> None:
    """Warn about niches with no CSRankings baseline to be scored against.

    Without a baseline row the derived ranking for that niche has nothing to compare
    to, so the analysis silently produces no deviation numbers for it.
    """
    meta_path = ROOT / "data/prompts/prompt_metadata.csv"
    baseline_path = ROOT / "data/institutions/master_institution_list.csv"
    if not meta_path.exists() or not baseline_path.exists():
        return
    with meta_path.open(encoding="utf-8", newline="") as f:
        wanted = {p.strip() for p in prompt_ids.split(",")}
        niches = {r["niche"] for r in csv.DictReader(f) if r["prompt_id"] in wanted}
    with baseline_path.open(encoding="utf-8", newline="") as f:
        have = {r["niche"] for r in csv.DictReader(f)}
    missing = sorted(niches - have)
    if missing:
        print(f"\nWARNING: no CSRankings baseline for niche(s): {', '.join(missing)}")
        print("Those fields will produce rankings with nothing to score against. Fix with:")
        print(f"    python src/scrape_csrankings.py --niches {','.join(missing)}\n")


def collect(providers: list[tuple[str, str]], prompt_ids: str, run_id: str, samples: int, sleep: float) -> None:
    n_prompts = len([p for p in prompt_ids.split(",") if p.strip()])
    n_calls = n_prompts * samples * len(providers)
    print(f"\nCollecting ~{n_calls} web-search responses "
          f"({n_prompts} prompts x {samples} samples x {len(providers)} models).")
    print("Web-search calls are slow and billed per search; Ctrl-C now to abort.\n")

    for provider, model in providers:
        if not model:
            continue
        run([
            "src/query_models.py",
            "--provider", provider,
            "--models", model,
            "--prompt-ids", prompt_ids,
            "--run-id", run_id,
            "--samples", str(samples),
            "--web-search",
            "--output", RAW_DIR,
            "--sleep", str(sleep),
            "--continue-on-error",
        ])


def verify(raw_dir: Path) -> int:
    """Report, per raw response, whether web search actually fired.

    Returns the number of files that were collected closed-book despite the flag --
    a non-zero count means those runs are not valid web-search data.
    """
    files = sorted(raw_dir.rglob("*.json"))
    if not files:
        print(f"no raw responses under {raw_dir.relative_to(ROOT)} -- run with --collect first")
        return 0
    ungrounded = 0
    print(f"\n{'file':<52} {'searches':>9}  {'sources':>7}")
    print("-" * 72)
    for path in files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"{path.name:<52} {'UNREADABLE':>9}")
            ungrounded += 1
            continue
        params = record.get("api_parameters") or {}
        search = params.get("web_search") or {}
        n_queries = search.get("search_count", 0)
        n_sources = len(search.get("sources") or [])
        label = f"{path.parent.name}/{path.name}"
        print(f"{label:<52} {n_queries:>9}  {n_sources:>7}")
        if not params.get("web_search_enabled") or n_queries == 0:
            ungrounded += 1
    print("-" * 72)
    if ungrounded:
        print(f"WARNING: {ungrounded}/{len(files)} responses show no evidence of web search.")
        print("Those runs are closed-book and must not be reported as web-search data.")
    else:
        print(f"All {len(files)} responses show evidence of web search.")
    return ungrounded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--collect", action="store_true", help="Query the models first (costs API credits).")
    parser.add_argument("--verify", action="store_true", help="Only check whether web search fired; no analysis.")
    parser.add_argument("--anthropic-model", default="claude-sonnet-4-6", help="Empty string to skip this provider.")
    parser.add_argument("--gemini-model", default="gemini-3.1-pro-preview", help="Empty string to skip this provider.")
    parser.add_argument("--openai-model", default="gpt-5.4", help="Empty string to skip this provider.")
    parser.add_argument(
        "--prompt-ids",
        default=ALL_PAPER_PROMPTS,
        help="Comma-separated prompt ids. Defaults to the full 7-field x 3-variant matrix.",
    )
    parser.add_argument("--run-id", default="web01")
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=2.0, help="Seconds between calls; web search is rate-limited.")
    args = parser.parse_args()

    raw_dir = ROOT / RAW_DIR

    if args.collect:
        providers = [
            ("anthropic", args.anthropic_model),
            ("gemini", args.gemini_model),
            ("openai", args.openai_model),
        ]
        providers = [(p, m) for p, m in providers if m]
        check_keys(providers)
        check_baselines(args.prompt_ids)
        collect(providers, args.prompt_ids, args.run_id, args.samples, args.sleep)

    if args.verify:
        raise SystemExit(1 if verify(raw_dir) else 0)

    if not raw_dir.exists() or not any(raw_dir.rglob("*.json")):
        raise SystemExit(
            f"No responses in {RAW_DIR}. Collect them first:\n"
            f"    python src/run_websearch_study.py --collect"
        )

    run(["src/parse_responses.py", "--input", RAW_DIR, "--output", PARSED_DIR])
    run(["src/resolve_affiliations.py",
         "--papers", f"{PARSED_DIR}/paper_mentions.csv",
         "--output", f"{PARSED_DIR}/paper_affiliations.csv"])
    # No explicit-ranking arm in this study, so point --explicit-summary at a path that
    # does not exist; analyze_paper_institutions skips the contrast table when absent.
    run(["src/analyze_paper_institutions.py",
         "--affiliations", f"{PARSED_DIR}/paper_affiliations.csv",
         "--explicit-summary", f"{TABLE_DIR}/institutional_bias_summary.csv",
         "--output", TABLE_DIR])
    run(["src/visualize_results.py", "--tables", TABLE_DIR, "--figures", FIGURE_DIR])

    print("\nDone. Key outputs:")
    print(f"  {TABLE_DIR}/paper_institution_counts.csv    institution ranking + deviation from CSRankings")
    print(f"  {FIGURE_DIR}/institution_rank_deviation_*.png  model rank vs CSRankings (dumbbell)")
    print(f"  {FIGURE_DIR}/paper_rank_boxplot_*.png          rank stability across samples")
    print("\nCheck that web search actually fired:")
    print("  python src/run_websearch_study.py --verify")


if __name__ == "__main__":
    main()
