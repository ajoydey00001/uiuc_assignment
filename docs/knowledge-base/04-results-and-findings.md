# 04 — Results and Findings

All numbers below are from `report/main.tex` (the final pipeline run) — see [03-glossary.md](03-glossary.md) for what each metric means.

## Parsed dataset size

From 30 raw API response files:

- **205** parsed ranking rows → `data/parsed/conference_rankings.csv`
- **86** parsed citation rows → `data/parsed/citations.csv`
- **86** extracted source-link rows → `data/parsed/source_links.csv`
- **86** validated source-link rows → `data/parsed/source_links_validated.csv`

## RQ1–RQ2: Conference ranking behavior

Ranking prompts generally placed **ICSE, FSE, ASE, ISSTA, and MSR** near the top — expected, since these are central SE/testing/mining-software-repositories venues. AI-specific venues (ICLR, NeurIPS, ICML) also appeared, especially when models connected AI-for-SE to LLM/code-model research.

Selected ranking-agreement metrics:

| Model | Prompt | Matched | Spearman | Kendall | Top-5 overlap | Mean abs. diff. |
|---|---|---|---|---|---|---|
| Gemma 4 31B | P01 ranking | 8 | 0.643 | 0.571 | 0.60 | 4.25 |
| Gemma 4 31B | P02 sourced ranking | 11 | 0.536 | 0.455 | 0.60 | 5.73 |
| Nemotron 3 Ultra | P01 ranking | 9 | 0.700 | 0.611 | 0.60 | 3.11 |
| Nemotron 3 Ultra | P02 sourced ranking | 15 | 0.682 | 0.581 | 0.80 | 6.00 |
| Nemotron 3 Ultra | P09 lower-rank check | 19 | 0.788 | 0.708 | **1.00** | 5.53 |
| GPT-OSS 120B | P02 sourced ranking | 9 | **1.000** | **1.000** | 1.00 | 2.67 |

Strongest agreement: GPT-OSS on the sourced-ranking prompt (perfect agreement on 9 matched venues) and Nemotron on the lower-rank-venue prompt (perfect top-5 overlap, best Spearman/Kendall).

## RQ3: Source-type preference

Aggregate source-type distribution across all 86 extracted links:

| Source type | Count |
|---|---|
| arXiv | 48 |
| unknown | 19 |
| conference page | 6 |
| GitHub repository | 6 |
| academic paper | 4 |
| personal blog | 2 |
| company blog | 1 |

**arXiv dominates** (48/86) — when asked for exact sources, models prefer accessible preprint links over ACM/IEEE pages or older records. The 19 `unknown` links were mostly ranking sites or general project pages not covered by the first-version classifier.

## RQ4: Domain concentration

`arxiv.org` was the top domain overall. Gemma's top domains: `arxiv.org`, `github.com`, `csrankings.org`, `portal.core.edu.au`, `owasp.org`, `huggingface.co`. Nemotron's top domains: `arxiv.org`, `conf.researchr.org`, `docs.github.com`, `doi.org`, `github.blog`, `github.com`.

Evidence for a **self-organization/ecosystem citation bias is limited** in this dataset — some GitHub/GitHub-docs links appeared, but models did not overwhelmingly cite their own provider ecosystem. A larger balanced dataset would be needed to make a strong claim either way.

## RQ5–RQ6: Recency and prompt sensitivity

Recent LLM/code-generation work (Codex-style code generation, SWE-bench-style agent benchmarks) appeared frequently, showing a **recency pull** toward LLM-era research. But older, established SE venues (ICSE, FSE, ASE, ISSTA, MSR) still dominated ranking prompts — recency bias didn't crowd out foundational venues.

**Prompt sensitivity was visible**: ranking prompts emphasized conferences/prestige; exact-source prompts produced many arXiv/GitHub/web links; the lower-rank-venue prompt (P09) changed the answer surface entirely, surfacing specialized venues (ICPC, ICST, COMPSAC, SAC) that shallower prompts tend to omit. This supports the idea that shallow prompts reinforce common top-venue answers, while deeper, source-pressured prompts expose richer/more diverse source choices.

## RQ7: Link validity and hallucination risk

Automated validation of all 86 extracted links:

- **72 valid**
- **12 dead**
- **2 unverifiable**

Dead/unverifiable links are a warning signal for hallucinated or stale URLs — but validation failure can also mean redirects, bot-blocking, or temporary outages, so it's treated as a first-pass filter, not final proof (see [03-glossary.md](03-glossary.md#link-validation-validate_linkspy)).

## Figures (`outputs/figures/`)

| File | Shows |
|---|---|
| `conference_ranking_heatmap.png` | Model-assigned rank per venue, heatmapped (lower = higher-ranked) |
| `source_type_bar_chart.png` | Source-type counts by model and prompt |
| `citation_overlap_heatmap.png` | Pairwise Jaccard URL overlap between models |
| `publication_year_distribution.png` | Extracted citation counts by publication year |
