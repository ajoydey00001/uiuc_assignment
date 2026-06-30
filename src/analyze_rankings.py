from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from scipy.stats import kendalltau, spearmanr

from common import ROOT


CORE_SCORE = {"A*": 1, "A": 2, "B": 3, "C": 4}


def normalize_acronym(value: str) -> str:
    value = str(value or "").upper().strip()
    aliases = {"ESEC-FSE": "FSE", "FSE/ESEC-FSE": "FSE", "NEURIPS": "NEURIPS"}
    return aliases.get(value, value)


def top_k_overlap(a: pd.Series, b: pd.Series, k: int) -> float:
    left = set(a.nsmallest(k).index)
    right = set(b.nsmallest(k).index)
    return len(left & right) / k if k else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare model venue rankings with baseline rankings.")
    parser.add_argument("--input", default="data/parsed/conference_rankings.csv")
    parser.add_argument("--conferences", default="data/conferences/master_conference_list.csv")
    parser.add_argument("--output", default="outputs/tables")
    args = parser.parse_args()

    rankings = pd.read_csv(ROOT / args.input)
    conferences = pd.read_csv(ROOT / args.conferences)
    output_dir = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    if rankings.empty:
        raise SystemExit("No rankings found. Run parse_responses.py after collecting model responses.")

    rankings["acronym_norm"] = rankings["acronym"].map(normalize_acronym)
    conferences["acronym_norm"] = conferences["acronym"].map(normalize_acronym)
    conferences["core_score"] = conferences["core_rank"].map(CORE_SCORE).fillna(5)

    merged = rankings.merge(
        conferences[["acronym_norm", "full_name", "field", "core_rank", "core_score", "csrankings_area", "baseline_rank"]],
        on="acronym_norm",
        how="left",
        suffixes=("_model", "_baseline"),
    )
    merged["rank"] = pd.to_numeric(merged["rank"], errors="coerce")
    merged["rank_difference_vs_baseline"] = merged["rank"] - merged["baseline_rank"]
    merged.to_csv(output_dir / "model_ranking_comparison.csv", index=False)

    metric_rows = []
    for (model, prompt_id, run_id), group in merged.dropna(subset=["baseline_rank", "rank"]).groupby(["model", "prompt_id", "run_id"]):
        if len(group) < 2:
            continue
        model_rank = group.set_index("acronym_norm")["rank"]
        baseline_rank = group.set_index("acronym_norm")["baseline_rank"]
        core_score = group.set_index("acronym_norm")["core_score"]
        metric_rows.append({
            "model": model,
            "prompt_id": prompt_id,
            "run_id": run_id,
            "n_matched": len(group),
            "spearman_vs_baseline": spearmanr(model_rank, baseline_rank).correlation,
            "kendall_vs_baseline": kendalltau(model_rank, baseline_rank).correlation,
            "spearman_vs_core_score": spearmanr(model_rank, core_score).correlation,
            "top5_overlap_vs_baseline": top_k_overlap(model_rank, baseline_rank, min(5, len(group))),
            "mean_abs_rank_difference": (model_rank - baseline_rank).abs().mean(),
        })

    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(output_dir / "ranking_metrics.csv", index=False)

    pivot = merged.pivot_table(index="acronym_norm", columns="model", values="rank", aggfunc="mean")
    pivot["baseline_rank"] = conferences.set_index("acronym_norm")["baseline_rank"]
    pivot.sort_values("baseline_rank").to_csv(output_dir / "ranking_matrix.csv")

    print(f"wrote ranking tables to {output_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

