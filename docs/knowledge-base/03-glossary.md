# 03 — Glossary

Plain-language definitions for every term a teacher might ask you to explain, tied to how it's actually used in this project.

## Baseline signals

**CORE rank** — A venue-quality category (A\*, A, B, C) from the CORE conference ranking portal. In this project, mapped to a numeric `core_score` (A\*=1, A=2, B=3, C=4, unranked=5) so it can be correlated against model ranks. It measures *prestige category*, not publication volume.

**CSRankings area** — A research-area label from CSRankings, which ranks institutions/researchers by publication counts in top venues per area. It's *area-based and count-oriented*, unlike CORE's category-based approach — the two baselines measure genuinely different things, which is why the report treats them as comparison signals rather than one absolute ground truth.

**`baseline_rank`** — A single pragmatic rank (1–30) assigned to each venue in `master_conference_list.csv`, used as the "expected" order to compare model rankings against.

## Ranking-agreement metrics (`analyze_rankings.py`)

**Spearman correlation** — Measures how well two rankings agree in *order* (rank correlation), from -1 (perfectly reversed) to +1 (perfectly matched). Used to compare a model's venue ranking against the baseline rank and against the numeric CORE score.

**Kendall tau** — Another rank-correlation measure, based on the fraction of pairwise orderings that agree between two rankings, also -1 to +1. More conservative/robust to outliers than Spearman; reported alongside it for a fuller picture.

**Top-k overlap** — Of the model's top-k ranked venues and the baseline's top-k venues, what fraction overlap (0 to 1). E.g. top-5 overlap of 0.60 means 3 of the model's top 5 venues also appear in the baseline's top 5.

**Mean absolute rank difference** — Average of `|model_rank − baseline_rank|` across matched venues. Lower is better; it's in the same units as rank position, so a value of 3 means venues are, on average, 3 positions off from baseline.

## Source-behavior metrics (`analyze_sources.py`)

**Jaccard similarity** — `|A ∩ B| / |A ∪ B|` for two sets of cited URLs. Used to measure how much two models' cited sources overlap (0 = no shared URLs, 1 = identical sets).

**Source-type taxonomy** — Every extracted URL is classified by domain into one of: `arxiv`, `academic_paper` (doi.org, dl.acm.org, ieeexplore.ieee.org), `conference_page`, `journal_page`, `company_blog` (openai.com, anthropic.com, deepmind.google, microsoft.com, research.google), `personal_blog`, `documentation` (docs.github.com, ai.google.dev, developers.google.com), `github_repository`, `news`, `benchmark_or_dataset`, or `unknown` (domain doesn't match any known pattern — see `classify_url()` in `parse_responses.py`).

**Domain concentration** — A count of citations grouped by `(model, domain)`, used to see which specific websites a model leans on most.

**Publication-year distribution** — Citation counts grouped by extracted `year`, used to look for recency bias (RQ5).

**Hallucination candidate** — A parsing heuristic, *not* a proof of hallucination: a citation row is flagged if it has no URL, DOI, *and* no arXiv ID, or if its title contains words like "unknown", "uncertain", "not sure". It's a first-pass filter to prioritize manual review, not a hallucination detector.

## Link validation (`validate_links.py`)

**`validation_status`** — One of four labels assigned by live HTTP check:
- `valid` — HTTP status 200–399
- `dead_link` — HTTP 404 or 5xx
- `ambiguous` — any other status code
- `unverifiable` — the request failed entirely (timeout, DNS failure, blocked, or the URL field was empty)

A `dead_link` or `unverifiable` result is a *warning signal*, not final proof of hallucination — it can also mean a temporary outage, a redirect the script didn't follow, or bot-blocking by the target site.

## Prompt/response contract

**Structured JSON contract** — Most prompts ask for JSON with three top-level fields: `ranked_items` (the ranked list itself), `references` (source objects with title/url/doi/arxiv_id/source_type), and `uncertainty_notes` (free text where the model flags anything it's not sure about). This structure is what makes automated parsing possible; when a model doesn't comply, `parse_responses.py` falls back to regex extraction from the raw text.

**`temperature=0`** — The target decoding setting for all API collection, chosen to make responses as close to deterministic/reproducible as the provider allows (not all APIs guarantee true determinism even at temperature 0).
