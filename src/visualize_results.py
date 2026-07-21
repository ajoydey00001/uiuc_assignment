from __future__ import annotations

import argparse
import os

os.environ.setdefault("MPLCONFIGDIR", str(__import__("pathlib").Path(__file__).resolve().parents[1] / ".matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from common import ROOT, safe_model_name


def save_empty(path, title: str) -> None:
    plt.figure(figsize=(8, 4))
    plt.text(0.5, 0.5, "No data yet", ha="center", va="center", fontsize=16)
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate figures for ranking and source analyses.")
    parser.add_argument("--tables", default="outputs/tables")
    parser.add_argument("--figures", default="outputs/figures")
    args = parser.parse_args()

    table_dir = ROOT / args.tables
    figure_dir = ROOT / args.figures
    figure_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    ranking_matrix_path = table_dir / "ranking_matrix.csv"
    if ranking_matrix_path.exists():
        ranking = pd.read_csv(ranking_matrix_path, index_col=0)
        if not ranking.empty:
            plt.figure(figsize=(10, max(6, len(ranking) * 0.28)))
            sns.heatmap(ranking.drop(columns=["baseline_rank"], errors="ignore"), annot=True, fmt=".1f", cmap="viridis_r", cbar_kws={"label": "Rank"})
            plt.title("Conference Ranking Heatmap")
            plt.ylabel("Conference")
            plt.tight_layout()
            plt.savefig(figure_dir / "conference_ranking_heatmap.png", dpi=160)
            plt.close()
        else:
            save_empty(figure_dir / "conference_ranking_heatmap.png", "Conference Ranking Heatmap")

    source_path = table_dir / "source_type_distribution.csv"
    if source_path.exists():
        source = pd.read_csv(source_path)
        if not source.empty:
            plt.figure(figsize=(11, 6))
            agg = source.groupby(["model", "source_type"])["count"].sum().reset_index()
            sns.barplot(data=agg, x="source_type", y="count", hue="model")
            plt.xticks(rotation=35, ha="right")
            plt.title("Source Type Distribution")
            plt.tight_layout()
            plt.savefig(figure_dir / "source_type_bar_chart.png", dpi=160)
            plt.close()
        else:
            save_empty(figure_dir / "source_type_bar_chart.png", "Source Type Distribution")

    overlap_path = table_dir / "citation_overlap_jaccard.csv"
    if overlap_path.exists():
        overlap = pd.read_csv(overlap_path)
        if not overlap.empty:
            matrix = overlap.pivot(index="model_a", columns="model_b", values="jaccard_url_overlap")
            plt.figure(figsize=(8, 6))
            sns.heatmap(matrix, annot=True, vmin=0, vmax=1, cmap="mako")
            plt.title("Citation URL Overlap")
            plt.tight_layout()
            plt.savefig(figure_dir / "citation_overlap_heatmap.png", dpi=160)
            plt.close()
        else:
            save_empty(figure_dir / "citation_overlap_heatmap.png", "Citation URL Overlap")

    years_path = table_dir / "publication_year_distribution.csv"
    if years_path.exists():
        years = pd.read_csv(years_path)
        years = years.dropna(subset=["year_num"]) if not years.empty else years
        if not years.empty:
            plt.figure(figsize=(10, 5))
            sns.barplot(data=years, x="year_num", y="count", hue="model")
            plt.xticks(rotation=45, ha="right")
            plt.title("Publication Year Distribution")
            plt.tight_layout()
            plt.savefig(figure_dir / "publication_year_distribution.png", dpi=160)
            plt.close()
        else:
            save_empty(figure_dir / "publication_year_distribution.png", "Publication Year Distribution")

    ranking_matrix_path = table_dir / "institution_ranking_matrix.csv"
    if ranking_matrix_path.exists():
        inst_ranking = pd.read_csv(ranking_matrix_path)
        for niche in sorted(inst_ranking["niche"].dropna().unique()) if not inst_ranking.empty else []:
            niche_df = inst_ranking[inst_ranking["niche"] == niche].set_index("institution_normalized")
            model_cols = [c for c in niche_df.columns if c not in {"niche", "baseline_rank"}]
            heat = niche_df[model_cols].dropna(how="all")
            fig_path = figure_dir / f"institution_ranking_heatmap_{niche}.png"
            if not heat.empty:
                plt.figure(figsize=(10, max(6, len(heat) * 0.28)))
                sns.heatmap(heat, annot=True, fmt=".1f", cmap="viridis_r", cbar_kws={"label": "Rank"})
                plt.title(f"Institution Ranking Heatmap ({niche})")
                plt.ylabel("Institution")
                plt.tight_layout()
                plt.savefig(fig_path, dpi=160)
                plt.close()
            else:
                save_empty(fig_path, f"Institution Ranking Heatmap ({niche})")
        if inst_ranking.empty:
            save_empty(figure_dir / "institution_ranking_heatmap_se.png", "Institution Ranking Heatmap (se)")
            save_empty(figure_dir / "institution_ranking_heatmap_vision.png", "Institution Ranking Heatmap (vision)")

    summary_path = table_dir / "institutional_bias_summary.csv"
    if summary_path.exists():
        summary = pd.read_csv(summary_path)
        if not summary.empty and summary["mean_abs_deviation"].notna().any():
            plt.figure(figsize=(10, 6))
            sns.barplot(data=summary, x="model", y="mean_abs_deviation", hue="niche")
            plt.ylabel("Mean absolute rank deviation vs CSRankings")
            plt.title("Institutional Bias: Rank Deviation by Model (mean across paraphrases)")
            plt.xticks(rotation=20, ha="right")
            plt.tight_layout()
            plt.savefig(figure_dir / "institution_deviation_bar_chart.png", dpi=160)
            plt.close()
        else:
            save_empty(figure_dir / "institution_deviation_bar_chart.png", "Institutional Bias: Rank Deviation by Model")

    # --- Implicit (papers) study figures ---

    rankings_path = table_dir / "paper_institution_rankings.csv"
    if rankings_path.exists():
        sample_ranks = pd.read_csv(rankings_path)
        if not sample_ranks.empty:
            for (model, niche), grp in sample_ranks.groupby(["model", "niche"]):
                totals = grp.groupby("institution_normalized")["count"].sum().sort_values(ascending=False)
                top = totals.head(15).index.tolist()
                sub = grp[grp["institution_normalized"].isin(top)]
                plt.figure(figsize=(12, 6))
                sns.boxplot(data=sub, x="institution_normalized", y="sample_rank", order=top, color="#7fb8b1")
                sns.stripplot(data=sub, x="institution_normalized", y="sample_rank", order=top, color="#333333", size=4, alpha=0.7)
                plt.xticks(rotation=40, ha="right")
                plt.gca().invert_yaxis()
                plt.ylabel("Rank within sample (1 = most cited)")
                plt.xlabel("Institution")
                plt.title(f"Per-sample citation-derived ranks — {model} ({niche})")
                plt.tight_layout()
                plt.savefig(figure_dir / f"paper_rank_boxplot_{safe_model_name(model)}_{niche}.png", dpi=160)
                plt.close()

    counts_path = table_dir / "paper_institution_counts.csv"
    if counts_path.exists():
        counts = pd.read_csv(counts_path)
        counts = counts[counts["gt"] == "niche"] if not counts.empty else counts
        if not counts.empty:
            for niche, grp in counts.groupby("niche"):
                order = grp.groupby("institution_normalized")["paper_count"].sum().sort_values(ascending=False).head(15).index.tolist()
                sub = grp[grp["institution_normalized"].isin(order)]
                plt.figure(figsize=(12, 6))
                sns.barplot(data=sub, x="institution_normalized", y="paper_count", hue="model", order=order)
                plt.xticks(rotation=40, ha="right")
                plt.ylabel("Papers attributed (pooled over samples)")
                plt.xlabel("Institution")
                plt.title(f"Citation-derived institution counts ({niche})")
                plt.tight_layout()
                plt.savefig(figure_dir / f"paper_institution_counts_{niche}.png", dpi=160)
                plt.close()

            for niche, grp in counts.groupby("niche"):
                pivot = grp.pivot_table(index="institution_normalized", columns="model", values="derived_rank")
                models = list(pivot.columns)
                if len(models) >= 2:
                    corr = pd.DataFrame(index=models, columns=models, dtype=float)
                    for a in models:
                        for b in models:
                            both = pd.concat([pivot[a], pivot[b]], axis=1, keys=["a", "b"]).dropna()
                            corr.loc[a, b] = both["a"].corr(both["b"], method="spearman") if len(both) >= 3 else float("nan")
                    plt.figure(figsize=(8, 6))
                    sns.heatmap(corr.astype(float), annot=True, vmin=-1, vmax=1, cmap="vlag", center=0)
                    plt.title(f"Model agreement on citation-derived rankings ({niche})")
                    plt.tight_layout()
                    plt.savefig(figure_dir / f"model_agreement_heatmap_{niche}.png", dpi=160)
                    plt.close()

    # --- Explicit (US-university ranking) boxplots, grouped by prompt ---
    # One figure per niche, faceted left-to-right by prompt paraphrase (variant
    # A/B/C). Within each facet, one box per institution shows the distribution of
    # ranks the models assigned it under that prompt; the red diamond is the
    # CSRankings baseline. This makes prompt-sensitivity of the institutional
    # hierarchy directly visible -- an institution whose box jumps between facets
    # is ranked inconsistently depending on how the question is phrased.
    mention_path = table_dir / "institution_mention_comparison.csv"
    for niche in ("se", "vision"):
        fig_path = figure_dir / f"explicit_rank_boxplot_{niche}.png"
        mentions = pd.read_csv(mention_path) if mention_path.exists() else pd.DataFrame()
        if mentions.empty or "niche" not in mentions.columns:
            save_empty(fig_path, f"Explicit US-university ranks by prompt ({niche})")
            continue
        nm = mentions[mentions["niche"] == niche].copy()
        nm["rank"] = pd.to_numeric(nm["rank"], errors="coerce")
        nm["baseline_rank_avg"] = pd.to_numeric(nm.get("baseline_rank_avg"), errors="coerce")
        nm = nm.dropna(subset=["rank", "institution_normalized"])
        if nm.empty:
            save_empty(fig_path, f"Explicit US-university ranks by prompt ({niche})")
            continue

        # Consistent institution order across facets: most-mentioned institutions
        # first, then ordered by overall mean rank (best rank on the left).
        by_inst = nm.groupby("institution_normalized")
        top = (
            by_inst["rank"].agg(["count", "mean"]).sort_values(["count", "mean"], ascending=[False, True])
            .head(12).sort_values("mean").index.tolist()
        )
        sub = nm[nm["institution_normalized"].isin(top)]
        variants = sorted(sub["variant"].dropna().unique(), key=str)
        if not variants:
            save_empty(fig_path, f"Explicit US-university ranks by prompt ({niche})")
            continue

        baseline = sub.groupby("institution_normalized")["baseline_rank_avg"].first()
        fig, axes = plt.subplots(1, len(variants), figsize=(max(7, 4.2 * len(variants)), 7), sharey=True, squeeze=False)
        for ax, variant in zip(axes[0], variants):
            vdf = sub[sub["variant"] == variant]
            prompt_id = vdf["prompt_id"].iloc[0] if not vdf.empty else f"variant {variant}"
            sns.boxplot(data=vdf, x="institution_normalized", y="rank", order=top, color="#7fb8b1", showfliers=False, ax=ax)
            sns.stripplot(data=vdf, x="institution_normalized", y="rank", order=top, hue="model", dodge=False, size=5, alpha=0.8, ax=ax)
            base_y = [baseline.get(inst) for inst in top]
            ax.scatter(range(len(top)), base_y, marker="D", color="#c0392b", s=42, zorder=5, label="CSRankings baseline")
            ax.set_title(f"{prompt_id}\n(variant {variant})", fontsize=10)
            ax.set_xlabel("")
            ax.set_ylabel("Rank (1 = top)" if ax is axes[0][0] else "")
            ax.tick_params(axis="x", labelrotation=45)
            for lbl in ax.get_xticklabels():
                lbl.set_ha("right")
            legend = ax.get_legend()
            if legend is not None:
                legend.remove()
        axes[0][0].invert_yaxis()
        handles, labels = axes[0][-1].get_legend_handles_labels()
        if handles:
            fig.legend(handles, labels, loc="lower center", ncol=min(6, len(labels)), frameon=False, bbox_to_anchor=(0.5, -0.02))
        fig.suptitle(f"US-university rank by prompt paraphrase — {niche} (box = across models, diamond = CSRankings)", fontsize=12)
        fig.tight_layout(rect=(0, 0.04, 1, 0.97))
        fig.savefig(fig_path, dpi=160, bbox_inches="tight")
        plt.close(fig)

    try:
        shown = figure_dir.relative_to(ROOT)
    except ValueError:
        shown = figure_dir
    print(f"wrote figures to {shown}")


if __name__ == "__main__":
    main()
