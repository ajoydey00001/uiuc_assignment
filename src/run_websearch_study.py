"""Web-search arm of the implicit institutional-bias study.

Asks each model for the 15 most influential SE papers *with web search enabled*,
repeatedly, then ranks institutions by how often they appear as the first author's
affiliation. If a model favours famous universities, those institutions dominate the
derived ranking regardless of their actual SE publication output in CSRankings.

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
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = "data/websearch/raw_responses"
PARSED_DIR = "data/websearch/parsed"
TABLE_DIR = "outputs/websearch/tables"
FIGURE_DIR = "outputs/websearch/figures"


def run(args: list[str]) -> None:
    print("+", " ".join(args))
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def collect(anthropic_model: str, gemini_model: str, prompt_ids: str, run_id: str, samples: int, sleep: float) -> None:
    for provider, model in (("anthropic", anthropic_model), ("gemini", gemini_model)):
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
    parser.add_argument("--anthropic-model", default="claude-sonnet-4-6")
    parser.add_argument("--gemini-model", default="gemini-3.1-pro-preview")
    parser.add_argument("--prompt-ids", default="SE_PAPERS")
    parser.add_argument("--run-id", default="web01")
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=2.0, help="Seconds between calls; web search is rate-limited.")
    args = parser.parse_args()

    raw_dir = ROOT / RAW_DIR

    if args.collect:
        collect(args.anthropic_model, args.gemini_model, args.prompt_ids, args.run_id, args.samples, args.sleep)

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
