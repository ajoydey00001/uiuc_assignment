"""Generate a static block-diagram picture of the institutional-bias pipeline for the README.

This is a documentation utility, not a data-processing stage -- it does not read any
pipeline data and is not wired into run_pipeline.py. Rerun it by hand after changing
the pipeline's shape (new scripts/stages) to keep the picture in sync.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from common import ROOT

COLORS = {
    "source": ("#FFCC80", "#E65100"),
    "baseline": ("#81D4FA", "#01579B"),
    "prompt": ("#F48FB1", "#880E4F"),
    "collect": ("#A5D6A7", "#1B5E20"),
    "parse": ("#FFF59D", "#F57F17"),
    "analyze": ("#B39DDB", "#4527A0"),
    "viz": ("#80CBC4", "#004D40"),
}

BOX_W, BOX_H = 1.9, 0.9


def draw_box(ax, x: float, y: float, label: str, kind: str, w: float = BOX_W, h: float = BOX_H) -> tuple[float, float]:
    fill, edge = COLORS[kind]
    box = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.06,rounding_size=0.12",
        linewidth=2, edgecolor=edge, facecolor=fill, zorder=3,
    )
    ax.add_patch(box)
    ax.text(x, y, label, ha="center", va="center", fontsize=9.5, fontweight="bold", color="#111111", zorder=4, wrap=True)
    return x, y


def arrow(ax, p1, p2, style="-|>", color="#444444", curve: float = 0.0, lw: float = 2.0):
    ax.add_patch(FancyArrowPatch(
        p1, p2, arrowstyle=style, mutation_scale=16, linewidth=lw, color=color,
        connectionstyle=f"arc3,rad={curve}", zorder=2,
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the pipeline block diagram to a PNG.")
    parser.add_argument("--output", default="outputs/figures/pipeline_diagram.png")
    args = parser.parse_args()

    fig, ax = plt.subplots(figsize=(15, 8))
    ax.set_xlim(-1.5, 12.5)
    ax.set_ylim(-0.5, 6.5)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # Lane A (top): CSRankings baseline
    csr = draw_box(ax, -0.5, 5.2, "CSRankings.org\n(live site)", "source")
    scrape = draw_box(ax, 1.9, 5.2, "scrape_csrankings.py", "baseline")
    baseline = draw_box(ax, 4.3, 5.2, "master_institution_\nlist.csv", "baseline")

    # Lane B (middle): prompts + local model collection
    prompts = draw_box(ax, -0.5, 3.2, "prompt_set_v1.md\n(rank + papers families)", "prompt")
    qm = draw_box(ax, 1.9, 3.2, "query_models.py\n--provider ollama", "collect")
    ollama = draw_box(ax, 1.9, 1.7, "Ollama\nqwen2.5:3b", "collect", h=0.8)
    raw = draw_box(ax, 4.3, 3.2, "raw_responses/\n*.json (immutable)", "collect")

    # Lane C (bottom): parse -> analyze -> visualize, wrapped in run_pipeline.py
    parse = draw_box(ax, 6.7, 3.2, "parse_responses.py", "parse")
    parsed = draw_box(ax, 6.7, 1.7, "parsed/*.csv", "parse", h=0.8)
    analyze = draw_box(ax, 9.1, 3.2, "analyze_institutional_\nbias.py", "analyze")
    tables = draw_box(ax, 9.1, 1.7, "outputs/tables/*.csv", "analyze", h=0.8)
    viz = draw_box(ax, 11.5, 3.2, "visualize_results.py", "viz")
    figs = draw_box(ax, 11.5, 1.7, "outputs/figures/\n*.png", "viz", h=0.8)

    # Dashed wrapper around the one-command pipeline stage
    wrapper = Rectangle((5.6, 0.9), 6.9, 3.1, linewidth=2, edgecolor="#555555", facecolor="none", linestyle="--", zorder=1)
    ax.add_patch(wrapper)
    ax.text(9.05, 4.15, "python src/run_pipeline.py   (safe to rerun anytime)", ha="center", va="center",
            fontsize=10, fontstyle="italic", color="#333333")

    # Lane A flow
    arrow(ax, (csr[0] + BOX_W / 2, csr[1]), (scrape[0] - BOX_W / 2, scrape[1]))
    arrow(ax, (scrape[0] + BOX_W / 2, scrape[1]), (baseline[0] - BOX_W / 2, baseline[1]))
    arrow(ax, (baseline[0], baseline[1] - BOX_H / 2), (analyze[0], analyze[1] + BOX_H / 2), curve=-0.15, color="#01579B")

    # Lane B flow
    arrow(ax, (prompts[0] + BOX_W / 2, prompts[1]), (qm[0] - BOX_W / 2, qm[1]))
    arrow(ax, (qm[0], qm[1] - 0.45), (ollama[0], ollama[1] + 0.4), style="<|-|>", color="#1B5E20")
    arrow(ax, (qm[0] + BOX_W / 2, qm[1]), (raw[0] - BOX_W / 2, raw[1]))

    # Lane B -> Lane C handoff
    arrow(ax, (raw[0] + BOX_W / 2, raw[1]), (parse[0] - BOX_W / 2, parse[1]))

    # Lane C internal flow
    arrow(ax, (parse[0], parse[1] - BOX_H / 2), (parsed[0], parsed[1] + 0.4))
    arrow(ax, (parsed[0] + 0.95, parsed[1]), (analyze[0] - BOX_W / 2, analyze[1] - 0.3), curve=-0.1)
    arrow(ax, (analyze[0], analyze[1] - BOX_H / 2), (tables[0], tables[1] + 0.4))
    arrow(ax, (tables[0] + 0.95, tables[1]), (viz[0] - BOX_W / 2, viz[1] - 0.3), curve=-0.1)
    arrow(ax, (viz[0], viz[1] - BOX_H / 2), (figs[0], figs[1] + 0.4))

    # Legend
    legend_items = [
        ("source", "External source"),
        ("baseline", "Baseline data"),
        ("prompt", "Prompts"),
        ("collect", "Collection"),
        ("parse", "Parsing"),
        ("analyze", "Analysis"),
        ("viz", "Visualization"),
    ]
    lx0 = -1.3
    for i, (kind, label) in enumerate(legend_items):
        fill, edge = COLORS[kind]
        lx = lx0 + i * 1.95
        ax.add_patch(Rectangle((lx, 0.05), 0.25, 0.25, facecolor=fill, edgecolor=edge, linewidth=1.5, zorder=3))
        ax.text(lx + 0.35, 0.175, label, ha="left", va="center", fontsize=8.5, color="#222222")

    ax.set_title("Institutional Bias Pipeline", fontsize=16, fontweight="bold", color="#111111", pad=14)

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
