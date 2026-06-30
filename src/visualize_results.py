from __future__ import annotations

import argparse
import os

os.environ.setdefault("MPLCONFIGDIR", str(__import__("pathlib").Path(__file__).resolve().parents[1] / ".matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from common import ROOT


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

    print(f"wrote figures to {figure_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
