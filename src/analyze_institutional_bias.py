"""Measure institutional bias: how far model rankings of US universities deviate
from their CSRankings niche-specific research standing.

Design: prompts are US-university-scoped to match the baseline's sampling frame
exactly, so every institution a model names is scoreable. The headline metric is
rank deviation -- the absolute difference between where a model ranks a university
and where CSRankings ranks it by actual publication output in that niche. Larger
deviation = the model's picture of the field is further from measured reality.

Baseline ranks are tie-aware: CSRankings displays tied ranks (two universities can
both be #6), so scoring uses average ranks recomputed from the continuous
adjusted-count score (metric_value), not the displayed rank.
"""

from __future__ import annotations

import argparse
import re

import pandas as pd
from rapidfuzz import fuzz
from rapidfuzz import process as rf_process
from rapidfuzz import utils as rf_utils
from scipy.stats import kendalltau, rankdata, spearmanr

from common import ROOT

# Exact-match fast path for abbreviation <-> full-name pairs that pure character-
# similarity fuzzy scoring cannot bridge. Grow this from what shows up in
# unmatched_institution_mentions.csv after each collection.
ALIASES = {
    "MIT": "Massachusetts Inst. of Technology",
    "Massachusetts Institute of Technology": "Massachusetts Inst. of Technology",
    "Massachusetts Institute of Technology (MIT)": "Massachusetts Inst. of Technology",
    "MIT CSAIL": "Massachusetts Inst. of Technology",
    "MIT Computer Science & Artificial Intelligence Laboratory (CSAIL)": "Massachusetts Inst. of Technology",
    "CMU": "Carnegie Mellon University",
    "UIUC": "Univ. of Illinois at Urbana-Champaign",
    "University of Illinois Urbana-Champaign": "Univ. of Illinois at Urbana-Champaign",
    "University of Illinois at Urbana-Champaign": "Univ. of Illinois at Urbana-Champaign",
    "UC Berkeley": "Univ. of California - Berkeley",
    "Berkeley": "Univ. of California - Berkeley",
    "University of California, Berkeley": "Univ. of California - Berkeley",
    "UCSD": "Univ. of California - San Diego",
    "UC San Diego": "Univ. of California - San Diego",
    "University of California, San Diego": "Univ. of California - San Diego",
    "UCLA": "Univ. of California - Los Angeles",
    "University of California, Los Angeles": "Univ. of California - Los Angeles",
    "UC Irvine": "Univ. of California - Irvine",
    "University of California, Irvine": "Univ. of California - Irvine",
    "Georgia Tech": "Georgia Institute of Technology",
    "UMass Amherst": "Univ. of Massachusetts Amherst",
    "University of Massachusetts Amherst": "Univ. of Massachusetts Amherst",
    "University of Maryland": "Univ. of Maryland - College Park",
    "University of Maryland, College Park": "Univ. of Maryland - College Park",
    "UT Austin": "University of Texas at Austin",
    "Stanford": "Stanford University",
    "Caltech": "California Institute of Technology",
    "University of Michigan, Ann Arbor": "University of Michigan",
    "University of Michigan at Ann Arbor": "University of Michigan",
    "University of Michigan Ann Arbor": "University of Michigan",
    "University of Wisconsin-Madison": "Univ. of Wisconsin - Madison",
    "University of Wisconsin, Madison": "Univ. of Wisconsin - Madison",
}

# Calibrated against observed score margins in the real multi-model data: every
# confirmed-correct fuzzy match scored >= 88.0 (e.g. UIUC-variant 88.0, UCSD 90.3),
# while every confirmed-wrong match scored <= 86.2 (e.g. "California Institute of
# Technology" -> "Georgia Institute of Technology" at 86.2, via the shared
# "Institute of Technology" tokens). 87 splits the two populations.
DEFAULT_THRESHOLD = 87.0


def normalize_institution(
    raw_name: str, canonical_names: list[str], threshold: float = DEFAULT_THRESHOLD
) -> tuple[str | None, str, float]:
    """Returns (matched_canonical_name_or_None, best_candidate_seen, match_score).

    Alias lookup first (on both the raw name and the name with any parenthetical
    acronym stripped, e.g. "... (UCLA)"), then rapidfuzz best-match against the
    niche's canonical list. A best_candidate is always returned (even below
    threshold) so unmatched rows can be reviewed against their closest guess.

    Scorer choice matters: WRatio without preprocessing produced catastrophic
    false matches just above threshold ("Stanford University" -> "North Carolina
    State University" at 85.5; several "(UIUC)/(UCSD)/(UCLA)"-suffixed names ->
    "Carnegie Mellon University"). token_sort_ratio over punctuation/case-
    normalized text with the parenthetical stripped is far better behaved:
    correct variants score 88+, wrong universities score <80.
    """
    raw_name = (raw_name or "").strip()
    if not raw_name or not canonical_names:
        return None, "", 0.0
    stripped = re.sub(r"\s*\([^)]*\)", "", raw_name).strip()
    for name in (raw_name, stripped):
        alias_target = ALIASES.get(name)
        if alias_target and alias_target in canonical_names:
            return alias_target, alias_target, 100.0
        if name in canonical_names:
            return name, name, 100.0
    match = rf_process.extractOne(
        stripped, canonical_names, scorer=fuzz.token_sort_ratio, processor=rf_utils.default_process
    )
    if match is None:
        return None, "", 0.0
    candidate, score, _ = match
    if score >= threshold:
        return candidate, candidate, score
    return None, candidate, score


def top_k_overlap(a: pd.Series, b: pd.Series, k: int) -> float:
    left = set(a.nsmallest(k).index)
    right = set(b.nsmallest(k).index)
    return len(left & right) / k if k else 0.0


EMPTY_OUTPUTS = {
    "unmatched_institution_mentions.csv": ["model", "prompt_id", "run_id", "niche", "institution_raw", "best_match_candidate", "match_score"],
    "institution_mention_comparison.csv": ["model", "provider", "prompt_id", "run_id", "niche", "variant", "rank", "institution_raw", "institution_normalized", "match_score", "baseline_rank", "baseline_rank_avg", "rank_deviation", "abs_deviation"],
    "institutional_bias_metrics.csv": ["model", "prompt_id", "run_id", "niche", "variant", "n_listed", "n_matched", "match_rate", "sum_abs_deviation", "mean_abs_deviation", "spearman_vs_baseline", "kendall_vs_baseline", "top5_overlap_vs_baseline"],
    "institutional_bias_summary.csv": ["model", "niche", "n_rankings", "mean_abs_deviation", "std_abs_deviation", "mean_spearman", "mean_kendall", "mean_top5_overlap", "mean_match_rate"],
    "institution_ranking_matrix.csv": ["niche", "institution_normalized", "baseline_rank"],
}


def write_empty(output_dir, reason: str) -> None:
    for name, fieldnames in EMPTY_OUTPUTS.items():
        pd.DataFrame(columns=fieldnames).to_csv(output_dir / name, index=False)
    print(f"{reason} -- wrote empty institutional-bias tables.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score model US-university rankings against the CSRankings niche baseline.")
    parser.add_argument("--institution-mentions", default="data/parsed/institution_mentions.csv")
    parser.add_argument("--institutions", default="data/institutions/master_institution_list.csv")
    parser.add_argument("--prompts", default="data/prompts/prompt_metadata.csv")
    parser.add_argument("--output", default="outputs/tables")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()

    mentions = pd.read_csv(ROOT / args.institution_mentions)
    institutions = pd.read_csv(ROOT / args.institutions)
    prompts = pd.read_csv(ROOT / args.prompts)
    output_dir = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    if mentions.empty:
        write_empty(output_dir, "No institution mentions found. Run query_models.py + parse_responses.py first.")
        return

    # Only prompts registered in the metadata (with a niche) are scored; responses
    # from older prompt sets still on disk are ignored rather than mis-scored. The
    # papers (implicit) family is scored by analyze_paper_institutions.py, not here.
    if "family" in prompts.columns:
        prompts = prompts[prompts["family"] == "rank"]
    meta = prompts.set_index("prompt_id")[["niche", "variant"]]
    scored = mentions.merge(meta, left_on="prompt_id", right_index=True, how="inner")
    if scored.empty:
        write_empty(output_dir, "No mentions matched a prompt_id in prompt_metadata.csv.")
        return

    # Tie-aware baseline: CSRankings displays tied ranks, so recompute average
    # ranks from the continuous adjusted-count score per niche.
    institutions = institutions.copy()
    institutions["baseline_rank_avg"] = institutions.groupby("niche")["metric_value"].transform(
        lambda s: rankdata(-s, method="average")
    )
    canonical_by_niche = {
        niche: group["institution"].tolist() for niche, group in institutions.groupby("niche")
    }

    matched_names, best_candidates, scores = [], [], []
    for _, row in scored.iterrows():
        canonical_names = canonical_by_niche.get(row["niche"], [])
        matched, candidate, score = normalize_institution(row["institution_raw"], canonical_names, args.threshold)
        matched_names.append(matched)
        best_candidates.append(candidate)
        scores.append(score)
    scored["institution_normalized"] = matched_names
    scored["match_score"] = scores
    scored["best_match_candidate"] = best_candidates

    # US-scoped prompts should match almost everything; whatever doesn't (a US
    # university outside the niche top-50, or a name needing a new alias) is
    # flagged for review, never silently dropped.
    unmatched = scored[scored["institution_normalized"].isna()]
    unmatched[["model", "prompt_id", "run_id", "niche", "institution_raw", "best_match_candidate", "match_score"]].to_csv(
        output_dir / "unmatched_institution_mentions.csv", index=False
    )

    matched = scored[scored["institution_normalized"].notna()].copy()
    baseline = institutions.rename(columns={"institution": "institution_normalized", "rank": "baseline_rank"})
    matched = matched.merge(
        baseline[["niche", "institution_normalized", "baseline_rank", "baseline_rank_avg"]],
        on=["niche", "institution_normalized"],
        how="left",
    )
    matched["rank"] = pd.to_numeric(matched["rank"], errors="coerce")
    matched["rank_deviation"] = matched["rank"] - matched["baseline_rank_avg"]
    matched["abs_deviation"] = matched["rank_deviation"].abs()
    matched[[
        "model", "provider", "prompt_id", "run_id", "niche", "variant", "rank", "institution_raw",
        "institution_normalized", "match_score", "baseline_rank", "baseline_rank_avg", "rank_deviation", "abs_deviation",
    ]].to_csv(output_dir / "institution_mention_comparison.csv", index=False)

    # Per-ranking metrics: one row per (model, prompt, run, niche). The headline
    # number is mean_abs_deviation -- how many rank positions, on average, the
    # model's placement of a university differs from its CSRankings standing.
    listed_counts = scored.groupby(["model", "prompt_id", "run_id", "niche"]).size()
    metric_rows = []
    for (model, prompt_id, run_id, niche, variant), group in matched.groupby(
        ["model", "prompt_id", "run_id", "niche", "variant"]
    ):
        group = group.dropna(subset=["rank", "baseline_rank_avg"])
        n_listed = int(listed_counts.get((model, prompt_id, run_id, niche), len(group)))
        row = {
            "model": model,
            "prompt_id": prompt_id,
            "run_id": run_id,
            "niche": niche,
            "variant": variant,
            "n_listed": n_listed,
            "n_matched": len(group),
            "match_rate": len(group) / n_listed if n_listed else float("nan"),
        }
        if len(group) >= 2:
            model_rank = group.set_index("institution_normalized")["rank"]
            baseline_rank = group.set_index("institution_normalized")["baseline_rank_avg"]
            row.update({
                "sum_abs_deviation": group["abs_deviation"].sum(),
                "mean_abs_deviation": group["abs_deviation"].mean(),
                "spearman_vs_baseline": spearmanr(model_rank, baseline_rank).correlation,
                "kendall_vs_baseline": kendalltau(model_rank, baseline_rank).correlation,
                "top5_overlap_vs_baseline": top_k_overlap(model_rank, baseline_rank, min(5, len(group))),
            })
        metric_rows.append(row)
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(output_dir / "institutional_bias_metrics.csv", index=False)

    # Model x niche summary across paraphrases and runs: conclusions should be
    # read here, not from any single prompt (wording swings single rankings).
    summary = (
        metrics.groupby(["model", "niche"])
        .agg(
            n_rankings=("prompt_id", "count"),
            mean_abs_deviation=("mean_abs_deviation", "mean"),
            std_abs_deviation=("mean_abs_deviation", "std"),
            mean_spearman=("spearman_vs_baseline", "mean"),
            mean_kendall=("kendall_vs_baseline", "mean"),
            mean_top5_overlap=("top5_overlap_vs_baseline", "mean"),
            mean_match_rate=("match_rate", "mean"),
        )
        .reset_index()
    )
    summary.to_csv(output_dir / "institutional_bias_summary.csv", index=False)

    pivot = matched.pivot_table(index=["niche", "institution_normalized"], columns="model", values="rank", aggfunc="mean")
    baseline_lookup = institutions.set_index(["niche", "institution"])["rank"]
    pivot["baseline_rank"] = pivot.index.map(baseline_lookup)
    pivot.sort_values(["baseline_rank"]).sort_index(level="niche", sort_remaining=False).to_csv(
        output_dir / "institution_ranking_matrix.csv"
    )

    print(f"wrote institutional bias tables to {output_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
