"""Implicit institutional-bias measurement: derive institution rankings from whose
papers a model cites, and score them against CSRankings ground truths.

For each (model, niche): pool the K sampled answers to the papers prompt, map each
paper's first-author affiliation (OpenAlex-resolved when available, else the model's
own claim) onto a ground-truth institution list, count papers per institution, and
rank institutions by count (ties -> average rank). That derived ranking is compared
against two ground truths:

- GT-niche   (CSRankings for the niche, US top-50): field-specific merit
- GT-overall (CSRankings all areas, US top-50): general fame

The key diagnostic is the comparison of the two MADs: if the citation-derived ranking
sits closer to GT-overall than GT-niche, the model's implicit citation behavior tracks
general fame over niche merit -- the same claim the explicit rank study makes, from an
independent measurement channel.
"""

from __future__ import annotations

import argparse

import pandas as pd
from rapidfuzz import fuzz
from scipy.stats import kendalltau, rankdata, spearmanr

from common import ROOT
from analyze_institutional_bias import DEFAULT_THRESHOLD, normalize_institution

EMPTY_OUTPUTS = {
    "paper_institution_counts.csv": ["model", "niche", "gt", "institution_normalized", "paper_count", "derived_rank", "baseline_rank_avg", "rank_deviation"],
    "paper_institution_rankings.csv": ["model", "niche", "run_id", "institution_normalized", "count", "sample_rank"],
    "paper_bias_metrics.csv": ["model", "niche", "gt", "n_papers_usable", "n_institutions_matched", "coverage", "mad", "spearman", "kendall", "tier_agreement"],
    "paper_bias_summary.csv": ["model", "niche", "n_samples", "n_papers", "resolved_rate", "not_found_rate", "us_share", "mad_vs_niche", "mad_vs_overall", "fame_gap", "tier_agreement_niche", "affiliation_self_report_agreement"],
    "explicit_vs_implicit.csv": ["model", "niche", "explicit_mad", "implicit_mad_vs_niche", "implicit_mad_vs_overall"],
    "unresolved_papers.csv": ["model", "prompt_id", "run_id", "title", "claimed_affiliation", "resolved_status"],
    "baseline_provenance.csv": ["niche", "n_institutions", "retrieved_date", "source_url"],
}


def write_empty(output_dir, reason: str) -> None:
    for name, fields in EMPTY_OUTPUTS.items():
        pd.DataFrame(columns=fields).to_csv(output_dir / name, index=False)
    print(f"{reason} -- wrote empty paper-institution tables.")


def derived_ranking(counts: pd.Series) -> pd.Series:
    """Rank institutions by paper count, most-cited first; ties get average ranks."""
    return pd.Series(rankdata(-counts.values, method="average"), index=counts.index)


def tier_of(rank: float, boundaries: list[int]) -> int:
    for i, b in enumerate(boundaries):
        if rank <= b:
            return i + 1
    return len(boundaries) + 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Score citation-derived institution rankings against CSRankings ground truths.")
    parser.add_argument("--affiliations", default="data/parsed/paper_affiliations.csv")
    parser.add_argument("--institutions", default="data/institutions/master_institution_list.csv")
    parser.add_argument("--prompts", default="data/prompts/prompt_metadata.csv")
    parser.add_argument("--explicit-summary", default="outputs/tables/institutional_bias_summary.csv")
    parser.add_argument("--output", default="outputs/tables")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--tiers", default="10,25", help="Tier boundaries on baseline rank, e.g. '10,25' -> tiers 1-10 / 11-25 / 26+.")
    args = parser.parse_args()

    output_dir = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    tier_bounds = [int(x) for x in args.tiers.split(",")]

    institutions = pd.read_csv(ROOT / args.institutions)
    institutions["baseline_rank_avg"] = institutions.groupby("niche")["metric_value"].transform(
        lambda s: rankdata(-s, method="average")
    )
    provenance = (
        institutions.groupby("niche")
        .agg(n_institutions=("institution", "count"), retrieved_date=("retrieved_date", "first"), source_url=("source_url", "first"))
        .reset_index()
    )
    provenance.to_csv(output_dir / "baseline_provenance.csv", index=False)

    aff_path = ROOT / args.affiliations
    if not aff_path.exists():
        write_empty(output_dir, "No paper_affiliations.csv found. Run resolve_affiliations.py first.")
        return
    papers = pd.read_csv(aff_path)
    if papers.empty:
        write_empty(output_dir, "paper_affiliations.csv is empty. Collect the papers prompts first.")
        return

    prompts = pd.read_csv(ROOT / args.prompts)
    prompts = prompts[prompts.get("family", "") == "papers"] if "family" in prompts.columns else prompts
    niche_map = prompts.set_index("prompt_id")["niche"].dropna().to_dict()
    papers["niche"] = papers["prompt_id"].map(niche_map)
    papers = papers[papers["niche"].notna()]
    if papers.empty:
        write_empty(output_dir, "No paper rows map to a papers-family prompt in prompt_metadata.csv.")
        return

    for col in ("claimed_affiliation", "oa_institution", "resolved_status", "oa_country"):
        if col not in papers.columns:
            papers[col] = ""
        papers[col] = papers[col].fillna("")

    # Affiliation choice: OpenAlex when resolved; the model's own claim otherwise.
    papers["affiliation"] = papers.apply(
        lambda r: r["oa_institution"] if r["resolved_status"] == "resolved" and r["oa_institution"] else r["claimed_affiliation"],
        axis=1,
    )
    papers["affiliation_source"] = papers.apply(
        lambda r: "openalex" if r["resolved_status"] == "resolved" and r["oa_institution"] else ("llm_claimed" if r["claimed_affiliation"] else "none"),
        axis=1,
    )

    # Review file: papers OpenAlex could not find/confidently match (hallucination
    # candidates: not_found, low_confidence) plus papers not yet looked up at all
    # (request_error -- a per-title query failure; unresolved_network -- budget/
    # connectivity ran out mid-run). The resolved_status column distinguishes "this
    # paper looks fabricated" from "we just haven't checked it yet" -- only the
    # former belongs in not_found_rate below.
    papers[papers["resolved_status"].isin(["not_found", "low_confidence", "request_error", "unresolved_network"])][
        ["model", "prompt_id", "run_id", "title", "claimed_affiliation", "resolved_status"]
    ].to_csv(output_dir / "unresolved_papers.csv", index=False)

    usable = papers[papers["affiliation"] != ""].copy()

    canonical = {niche: grp["institution"].tolist() for niche, grp in institutions.groupby("niche")}
    baseline_by_niche = {
        niche: grp.set_index("institution")["baseline_rank_avg"] for niche, grp in institutions.groupby("niche")
    }

    # Match every usable affiliation against both ground-truth lists.
    for gt_label, gt_key in [("niche", None), ("overall", "overall")]:
        col = f"match_{gt_label}"
        matches = []
        for _, row in usable.iterrows():
            gt_niche = gt_key or row["niche"]
            matched, _, _ = normalize_institution(row["affiliation"], canonical.get(gt_niche, []), args.threshold)
            matches.append(matched)
        usable[col] = matches

    counts_rows, metric_rows, sample_rank_rows = [], [], []
    for (model, niche), group in usable.groupby(["model", "niche"]):
        n_samples = group["run_id"].nunique()
        for gt_label in ["niche", "overall"]:
            gt_niche = niche if gt_label == "niche" else "overall"
            matched = group[group[f"match_{gt_label}"].notna()]
            if matched.empty:
                continue
            counts = matched.groupby(f"match_{gt_label}").size().sort_values(ascending=False)
            ranks = derived_ranking(counts)
            baseline = baseline_by_niche[gt_niche]
            rows = pd.DataFrame({
                "paper_count": counts,
                "derived_rank": ranks,
                "baseline_rank_avg": [baseline.get(i) for i in counts.index],
            })
            rows["rank_deviation"] = rows["derived_rank"] - rows["baseline_rank_avg"]
            for inst, r in rows.iterrows():
                counts_rows.append({
                    "model": model, "niche": niche, "gt": gt_label, "institution_normalized": inst,
                    "paper_count": int(r["paper_count"]), "derived_rank": r["derived_rank"],
                    "baseline_rank_avg": r["baseline_rank_avg"], "rank_deviation": r["rank_deviation"],
                })
            scored = rows.dropna(subset=["baseline_rank_avg"])
            metric = {
                "model": model, "niche": niche, "gt": gt_label,
                "n_papers_usable": len(group), "n_institutions_matched": len(scored),
                "coverage": len(matched) / len(group) if len(group) else float("nan"),
            }
            if len(scored) >= 2:
                metric.update({
                    "mad": (scored["derived_rank"] - scored["baseline_rank_avg"]).abs().mean(),
                    "spearman": spearmanr(scored["derived_rank"], scored["baseline_rank_avg"]).correlation,
                    "kendall": kendalltau(scored["derived_rank"], scored["baseline_rank_avg"]).correlation,
                    "tier_agreement": (
                        scored.apply(lambda r: tier_of(r["derived_rank"], tier_bounds) == tier_of(r["baseline_rank_avg"], tier_bounds), axis=1).mean()
                    ),
                })
            metric_rows.append(metric)

        # Per-sample rankings (niche GT) for the box-plot visual.
        for run_id, sample in group.groupby("run_id"):
            matched = sample[sample["match_niche"].notna()]
            if matched.empty:
                continue
            counts = matched.groupby("match_niche").size()
            ranks = derived_ranking(counts)
            for inst in counts.index:
                sample_rank_rows.append({
                    "model": model, "niche": niche, "run_id": run_id,
                    "institution_normalized": inst, "count": int(counts[inst]), "sample_rank": ranks[inst],
                })

    pd.DataFrame(counts_rows).to_csv(output_dir / "paper_institution_counts.csv", index=False)
    pd.DataFrame(sample_rank_rows).to_csv(output_dir / "paper_institution_rankings.csv", index=False)
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(output_dir / "paper_bias_metrics.csv", index=False)

    # Self-report validity: among OpenAlex-resolved papers with a non-empty claim,
    # how often does the model's claimed affiliation agree with OpenAlex?
    resolved = papers[(papers["resolved_status"] == "resolved") & (papers["claimed_affiliation"] != "") & (papers["oa_institution"] != "")]
    validity = (
        resolved.assign(agree=resolved.apply(
            lambda r: fuzz.token_sort_ratio(str(r["claimed_affiliation"]).lower(), str(r["oa_institution"]).lower()) >= 80, axis=1))
        .groupby("model")["agree"].mean()
        if not resolved.empty else pd.Series(dtype=float)
    )

    summary_rows = []
    for (model, niche), group in papers.groupby(["model", "niche"]):
        # NB: metrics["gt"] must use bracket access -- `.gt` is pandas' greater-than method.
        m_niche = metrics[(metrics["model"] == model) & (metrics["niche"] == niche) & (metrics["gt"] == "niche")]
        m_overall = metrics[(metrics["model"] == model) & (metrics["niche"] == niche) & (metrics["gt"] == "overall")]
        mad_n = m_niche["mad"].iloc[0] if len(m_niche) and "mad" in m_niche else float("nan")
        mad_o = m_overall["mad"].iloc[0] if len(m_overall) and "mad" in m_overall else float("nan")
        summary_rows.append({
            "model": model, "niche": niche,
            "n_samples": group["run_id"].nunique(),
            "n_papers": len(group),
            "resolved_rate": (group["resolved_status"] == "resolved").mean(),
            "not_found_rate": group["resolved_status"].isin(["not_found", "low_confidence"]).mean(),
            "us_share": (group["oa_country"] == "US").mean(),
            "mad_vs_niche": mad_n,
            "mad_vs_overall": mad_o,
            # fame_gap > 0: citations sit closer to general fame than to niche merit.
            "fame_gap": mad_n - mad_o if pd.notna(mad_n) and pd.notna(mad_o) else float("nan"),
            "tier_agreement_niche": m_niche["tier_agreement"].iloc[0] if len(m_niche) and "tier_agreement" in m_niche else float("nan"),
            "affiliation_self_report_agreement": validity.get(model, float("nan")),
        })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / "paper_bias_summary.csv", index=False)

    # Explicit-vs-implicit contrast: the paper's headline table.
    explicit_path = ROOT / args.explicit_summary
    if explicit_path.exists():
        explicit = pd.read_csv(explicit_path)[["model", "niche", "mean_abs_deviation"]].rename(
            columns={"mean_abs_deviation": "explicit_mad"}
        )
        contrast = explicit.merge(
            summary[["model", "niche", "mad_vs_niche", "mad_vs_overall"]].rename(
                columns={"mad_vs_niche": "implicit_mad_vs_niche", "mad_vs_overall": "implicit_mad_vs_overall"}
            ),
            on=["model", "niche"], how="outer",
        )
        contrast.to_csv(output_dir / "explicit_vs_implicit.csv", index=False)

    print(f"wrote paper-institution tables to {output_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
