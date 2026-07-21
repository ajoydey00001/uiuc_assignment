# Institutional Bias in AI-for-Niches

**Current focus: the implicit (citation-based) study.** Ask a model for the most influential papers in a research niche, resolve who actually wrote each one, and see whether the institutions it ends up crediting track real niche-specific research output or just general academic fame.

Method: ask for the 15 most influential papers in a niche (unconstrained — no scope restriction, since unconstrained citation behavior is the phenomenon) → resolve each paper's **first-author affiliation** via **OpenAlex** (external, verifiable; the model's own claimed affiliation is kept alongside for a self-report accuracy check) → count papers per institution, pooled across samples → derive an institution ranking from those counts (ties allowed) → score that ranking against **two** ground truths: CSRankings for the niche (field merit) and CSRankings all-areas (general fame). If the derived ranking sits closer to the fame ranking (`fame_gap` > 0), the model's citations track fame over merit. Papers OpenAlex can't verify are the hallucination metric.

Sampled: **K answers per prompt at the provider's default temperature** (not 0 — sampling needs real variance). Two niches so far: software engineering (`se`) and computer vision (`vision`); ground truths tracked with scrape dates in `outputs/tables/baseline_provenance.csv`.

*(An earlier explicit study — directly asking a model to rank universities — also exists in this repo and shares the same pipeline; see [Explicit (rank) study](#explicit-rank-study-secondary) at the bottom if you want it. It's not the current focus.)*

## Pipeline Overview

![Institutional Bias Pipeline](outputs/figures/pipeline_diagram.png)

Everything inside the dashed box runs with one command, `python src/run_pipeline.py`, and is always safe to rerun. Only the baseline scrape and the model collection step run separately, when you want new data.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # one-time, needed for the CSRankings scraper
```

**Required for the implicit study**: get a free OpenAlex API key at [openalex.org/settings/api](https://openalex.org/settings/api) (30-second signup) and add it to `.env`:

```text
OPENALEX_API_KEY=your_key_here
```

OpenAlex runs a metered daily budget: effectively $0/day without a key (429s all day), $1/day with one — enough for a few hundred paper lookups. If you and a collaborator are both resolving papers the same day, get **separate keys** — there's no shared free pool.

## Run The Implicit Study

**1. Rebuild the CSRankings baselines** (one-time, or whenever you want fresher data):

```bash
python src/scrape_csrankings.py --niches se,vision,overall --top-n 50
```

`overall` is the all-areas US ranking — the general-fame ground truth. Writes `data/institutions/master_institution_list.csv`. **Verify**: compare the top 5 rows per niche against `https://csrankings.org/#/index?soft&us` (`se`) and `https://csrankings.org/#/index?vision&us` (`vision`) in a browser. The script fails loudly rather than writing a wrong/empty baseline if the site changes.

**2. Collect model responses** on the `papers` prompts, K samples at the provider's default temperature (no `--temperature` flag):

```bash
# local, no API key needed for collection itself
brew install ollama && ollama serve &     # first time only
ollama pull qwen2.5:3b

python src/query_models.py --provider ollama --models qwen2.5:3b \
  --prompt-ids SE_PAPERS,VIS_PAPERS --run-id imp01 --samples 3 --max-tokens 4096
```

`--samples 3` writes `imp01-s1`, `imp01-s2`, `imp01-s3` per prompt — each a genuinely separate sampled answer (verified: back-to-back calls at default temperature produce different papers). Use a higher K (e.g. 5) if you want tighter per-institution counts and can afford the extra OpenAlex lookups.

API models work the same way — swap `--provider anthropic|openai|gemini` and the model name (needs the matching key in `.env`), add `--sleep 2`. Use a distinct `--run-id` per person/batch so files never collide — this matters more here than in the explicit study, since nothing else disambiguates repeated `papers`-prompt collections.

**3. Run the pipeline** (parses raw responses → resolves affiliations via OpenAlex → scores against both ground truths → generates figures):

```bash
python src/run_pipeline.py
```

Safe to rerun any time — `src/resolve_affiliations.py` caches every OpenAlex answer in `data/cache/openalex_cache.json`, so reruns and collaborators' machines never re-spend budget on titles already looked up. If OpenAlex's daily budget runs out mid-run, unresolved titles are marked `unresolved_network`; just rerun `python src/resolve_affiliations.py` after the reset (midnight UTC) to fill the gaps, then `python src/run_pipeline.py` again to re-score.

## Read The Results (in this order)

1. **`outputs/tables/paper_bias_summary.csv`** — the headline table, one row per model × niche: `mad_vs_niche` and `mad_vs_overall` (citation-derived ranking's distance from field merit vs. general fame), **`fame_gap`** (= mad_vs_niche − mad_vs_overall; positive means citations track fame over merit), `resolved_rate` / `not_found_rate` (hallucination rate), `us_share`, `tier_agreement_niche`, and `affiliation_self_report_agreement` (how often the model's claimed affiliation matches OpenAlex). Read conclusions here, not from any single sample.
2. **`outputs/tables/unresolved_papers.csv`** — papers OpenAlex couldn't find or only matched under a dissimilar title (`not_found`, `low_confidence`), plus anything not yet looked up (`request_error`, `unresolved_network`). The `resolved_status` column tells you which — only the first two are real fabrication candidates.
3. **`outputs/tables/paper_institution_counts.csv`** — pooled paper counts, derived rank, and signed deviation per institution, per ground truth (`gt` column: `niche` or `overall`). This is where you see *which* institutions get over/under-credited and by how much.
4. **Figures**: `paper_rank_boxplot_<model>_<niche>.png` (per-sample rank spread — tight boxes mean consistent over-crediting, not noise), `paper_institution_counts_{se,vision}.png` (count bars, one series per model once more than one has data), `model_agreement_heatmap_{se,vision}.png` (appears once ≥2 models have implicit data — Spearman between models' derived rankings).
5. **`outputs/tables/explicit_vs_implicit.csv`** — if you've also run the explicit study, this puts both measures side by side per model × niche.

### Current result (qwen2.5:3b, K=5, both niches)

| | Fabrication rate | Deviation from niche merit | Deviation from fame | `fame_gap` |
|---|---|---|---|---|
| SE | 74% | 20.2 | 14.0 | **+6.2** |
| Vision | 84% | 20.1 | 12.0 | **+8.1** |

Three-quarters to five-sixths of the "influential papers" this model names don't verifiably exist. `fame_gap` is positive in both niches — when the model does attribute a paper to a real institution, that institution is more likely to be famous than actually productive in the niche. Self-reported affiliations agree with OpenAlex only 1 time in 5. This is one small local model — the implicit study has **zero data yet for frontier models** (Claude/GPT-5.4/Gemini); that's the next real step.

## Limitations

- **The system prompt (`DEFAULT_SYSTEM_PROMPT` in `src/query_models.py`) is deliberately a neutral assistant persona** — it never mentions bias, institutions, or that this is a study. Don't add study-disclosure language back in when writing new prompts; telling a model what's being measured changes what you're measuring (demand characteristics).
- **Implicit-study data is qwen-only so far.** Collect Claude/GPT-5.4/Gemini before treating `fame_gap` or the fabrication rate as more than a single-model observation.
- **OpenAlex title-search caveats**: influential papers indexed as reprints can resolve to the reprint's affiliation (e.g. AlexNet's 2017 CACM version lists Google, the 2012 original lists U. Toronto); the resolver prefers the most-cited title-similar hit, which usually but not always picks the canonical version. Generic titles ("Introduction to Software Engineering") can resolve to a real-but-unintended paper. Both effects are noise on individual papers that mostly washes out in institution-level counts; `unresolved_papers.csv` plus a manual spot-check of top-counted papers remains necessary before publishing.
- **OpenAlex query quirks**: titles containing `?` or `*` are stripped before searching — OpenAlex treats those as wildcard operators (even percent-encoded) and returns `400` otherwise. A handful of exotic titles may still fail with `request_error`; check `unresolved_papers.csv`.
- Institution-name fuzzy matching uses `token_sort_ratio` with threshold 87 (`ALIASES`/`normalize_institution` in `src/analyze_institutional_bias.py`, reused by the implicit study) — calibrated against real data where correct matches scored ≥ 88 and wrong ones ≤ 86.2. Check the unmatched/unresolved tables after every new collection before trusting institution-level counts.
- CSRankings measures publication output in top venues; it is a defensible but not unquestionable ground truth for "research standing."

## Reproducibility Checklist

- Keep raw model outputs under `data/raw_responses/` immutable — never hand-edit; recollect with a new `--run-id` instead.
- Regenerate everything under `data/parsed/` and `outputs/` with `python src/run_pipeline.py`; never hand-edit those files.
- Commit `data/cache/openalex_cache.json` along with new paper collections so collaborators' reruns are reproducible without re-hitting the API.
- When adding a prompt, add its row to `data/prompts/prompt_metadata.csv` with `niche`, `variant`, and `family` set — prompts missing from the metadata are ignored by the analysis rather than mis-scored.
- Re-run `src/scrape_csrankings.py` if a baseline is stale — `outputs/tables/baseline_provenance.csv` shows every ground truth's scrape date.

---

## Web-search study (`src/run_websearch_study.py`)

A separate arm asking three models — **with web search enabled** — for `k=20` recent papers per field, then ranking institutions by first-author affiliation. Everything lives under `data/websearch/` and `outputs/websearch/`, so it never mixes with the closed-book data above.

Prompt matrix is **7 fields × 3 phrasings = 21 prompts**: `{SE,VIS,PL,ALGO,ROB,HCI,AI}_PAPERS_{A,B,C}`. The three phrasings separate a stable institutional prior from wording sensitivity — an institution that dominates all three is a robust result; one that appears under a single phrasing is an artifact.

**Setup:** copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `OPENALEX_API_KEY`.

```bash
# 1. Baselines for the five fields the earlier study never covered (one-time)
python src/scrape_csrankings.py --niches pl,algorithms,robotics,hci,ai

# 2. SMOKE TEST FIRST -- 3 calls, confirms web search actually fires
python src/run_websearch_study.py --collect --prompt-ids SE_PAPERS_A --samples 1 --run-id smoke
python src/run_websearch_study.py --verify

# 3. Full collection -- only if the smoke test shows searches > 0
python src/run_websearch_study.py --collect    # 21 prompts x 5 samples x 3 models = 315 calls
python src/run_websearch_study.py --verify
python src/run_websearch_study.py              # parse -> resolve -> analyse -> figures
```

**`--verify` is not optional.** A provider that ignores the web-search tool returns a perfectly normal-looking closed-book answer; `--verify` reads the recorded search provenance (`queries`, `sources`, `search_count`) from every raw response and exits non-zero if any run shows no evidence of retrieval. If it reports `searches: 0`, that data is closed-book wearing a web-search label — do not analyse it.

Key outputs: `outputs/websearch/tables/paper_institution_counts.csv` (derived rank + deviation from CSRankings) and `outputs/websearch/figures/institution_rank_deviation_*.png` (dumbbell: model rank vs CSRankings, sorted by deviation).

Scraping the new baselines preserves niches not named in `--niches`; pass `--replace` only if you deliberately want to rebuild the whole file.

**Interpretation caveat:** with search on, the measurement is *retrieval + model*, not the model's parametric prior. A famous-university skew here may originate in what the search engine surfaces. Report findings as "under web-search-grounded conditions."

---

## Explicit (rank) study (secondary)

Directly ask a model to rank 15 US universities for a niche; score **rank deviation** vs CSRankings. Deterministic (temperature 0), three paraphrases per niche (A/B/C) as the replication unit instead of repeated sampling. Already collected for all 4 models (Claude Sonnet 4.6, GPT-5.4, Gemini 3.1 Pro, qwen2.5:3b) — headline result: every model deviates roughly **twice as much on SE as on vision** (14.2–16.9 vs 6.3–12.0 rank positions; random guessing ≈ 19.0), the same fame-over-merit pattern the implicit study now confirms independently.

To collect more:

```bash
python src/query_models.py --provider ollama --models qwen2.5:3b \
  --prompt-ids SE_RANK_US,SE_RANK_US_B,SE_RANK_US_C,VIS_RANK_US,VIS_RANK_US_B,VIS_RANK_US_C \
  --run-id run01 --temperature 0 --max-tokens 4096
```

Results land in `outputs/tables/institutional_bias_summary.csv` (headline), `institutional_bias_metrics.csv` (per-paraphrase, for stability checks), `institution_mention_comparison.csv` (row-level, signed deviation per institution), `unmatched_institution_mentions.csv`, and `outputs/figures/institution_deviation_bar_chart.png` / `institution_ranking_heatmap_{se,vision}.png`.
