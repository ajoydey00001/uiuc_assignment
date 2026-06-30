from __future__ import annotations

import argparse

import pandas as pd

from common import ROOT


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze source-link and citation behavior.")
    parser.add_argument("--links", default="data/parsed/source_links.csv")
    parser.add_argument("--citations", default="data/parsed/citations.csv")
    parser.add_argument("--prompts", default="data/prompts/prompt_metadata.csv")
    parser.add_argument("--output", default="outputs/tables")
    args = parser.parse_args()

    output_dir = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    links = pd.read_csv(ROOT / args.links)
    citations = pd.read_csv(ROOT / args.citations)
    prompts = pd.read_csv(ROOT / args.prompts)

    if not links.empty:
        links = links.merge(prompts[["prompt_id", "category", "depth", "source_pressure"]], on="prompt_id", how="left")
        source_dist = links.groupby(["model", "prompt_id", "category", "source_type"]).size().reset_index(name="count")
        source_dist.to_csv(output_dir / "source_type_distribution.csv", index=False)
        domain_dist = links.groupby(["model", "domain"]).size().reset_index(name="count").sort_values(["model", "count"], ascending=[True, False])
        domain_dist.to_csv(output_dir / "domain_concentration.csv", index=False)

        overlap_rows = []
        by_model = {model: set(group["url"].dropna()) for model, group in links.groupby("model")}
        for m1, urls1 in by_model.items():
            for m2, urls2 in by_model.items():
                overlap_rows.append({"model_a": m1, "model_b": m2, "jaccard_url_overlap": jaccard(urls1, urls2)})
        pd.DataFrame(overlap_rows).to_csv(output_dir / "citation_overlap_jaccard.csv", index=False)
    else:
        pd.DataFrame(columns=["model", "prompt_id", "category", "source_type", "count"]).to_csv(output_dir / "source_type_distribution.csv", index=False)
        pd.DataFrame(columns=["model", "domain", "count"]).to_csv(output_dir / "domain_concentration.csv", index=False)
        pd.DataFrame(columns=["model_a", "model_b", "jaccard_url_overlap"]).to_csv(output_dir / "citation_overlap_jaccard.csv", index=False)

    if not citations.empty:
        citations["year_num"] = pd.to_numeric(citations["year"], errors="coerce")
        citations.groupby(["model", "year_num"]).size().reset_index(name="count").to_csv(output_dir / "publication_year_distribution.csv", index=False)
        hallucination_candidates = citations[
            citations[["url", "doi", "arxiv_id"]].fillna("").eq("").all(axis=1)
            | citations["title"].fillna("").str.contains("unknown|uncertain|not sure", case=False, regex=True)
        ]
        hallucination_candidates.to_csv(output_dir / "hallucinated_citation_candidates.csv", index=False)
    else:
        pd.DataFrame(columns=["model", "year_num", "count"]).to_csv(output_dir / "publication_year_distribution.csv", index=False)
        pd.DataFrame().to_csv(output_dir / "hallucinated_citation_candidates.csv", index=False)

    print(f"wrote source tables to {output_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

