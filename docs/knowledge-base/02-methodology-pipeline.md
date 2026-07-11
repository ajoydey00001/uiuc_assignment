# 02 — Methodology and Pipeline

## 1. Conference baseline

`data/conferences/master_conference_list.csv` — 30 venues, columns: `conference, acronym, full_name, field, core_rank, csrankings_area, baseline_rank`. Grouped into:

- **Software engineering venues:** ICSE, FSE/ESEC-FSE, ASE, ISSTA, MSR, ICSME, SANER, RE, MODELS, ICPC, ICST, COMPSAC, SAC
- **Programming-language / formal-methods venues:** PLDI, OOPSLA, POPL, ECOOP, CAV, TACAS, FM, VMCAI
- **Adjacent AI / data / web / HCI venues:** NeurIPS, ICML, ICLR, AAAI, IJCAI, KDD, WWW, CHI, UIST

Lower-rank/specialized venues (COMPSAC, ICST, SAC) were **deliberately included** to test whether models only repeat the most prestigious venues or can also recognize specialized sources useful for practical AI-for-SE questions. CORE and CSRankings are used as *comparison signals, not ground truth* — CORE ranks venues into categories (A*/A/B/C), CSRankings is area/publication-count oriented, so they measure different things.

## 2. Prompt battery (10 prompts)

Stored in `data/prompts/prompt_set_v1.md`, metadata in `data/prompts/prompt_metadata.csv`. All prompts share one system prompt instructing the model not to invent papers/URLs/DOIs/venue facts and to flag uncertainty. Most request structured JSON with `ranked_items`, `references`, `uncertainty_notes`.

| Prompt ID | Category | Depth | Source pressure | What it asks |
|---|---|---|---|---|
| P01_CONFERENCE_RANKING | conference_ranking | shallow | low | Rank the 12 most important venues for AI-assisted SE |
| P02_CONFERENCE_RANKING_SOURCED | conference_ranking | deep | high | Rank top 15 venues and relate the ranking to CORE/CSRankings |
| P03_INFLUENTIAL_PAPERS | influential_papers | deep | medium | List 10 influential papers (old SE + recent LLM work) with metadata |
| P04_EXACT_SOURCES | exact_source_disclosure | deep | high | Evidence-backed overview using only sources with a concrete URL/DOI/arXiv ID |
| P05_RECENT_WORK | recent_work | medium | high | Summarize the last 3 years of LLM code-gen/repair/testing/agent work |
| P06_AREA_MAPPING | area_mapping | deep | medium | Map the field into 6–8 active research areas and their venues/source types |
| P07_PRACTITIONER_GUIDANCE | practitioner_guidance | shallow | medium | Which sources should a team read before adopting AI coding assistants |
| P08_HALLUCINATION_STRESS | hallucination_validation | deep | high | List 12 sources the model is *confident* are real; null out uncertain fields |
| P09_LOW_RANK_VENUE_CHECK | conference_ranking | deep | medium | Rank 15 venues including deliberately lower-rank/specialized ones |
| P10_SOURCE_VALIDATION_AUDIT | exact_source_disclosure | deep | high | 12 sources labeled by source type, preferring independently checkable ones |

## 3. Model collection

Final collection used **3 OpenRouter free-tier models**: `google/gemma-4-31b-it:free`, `openai/gpt-oss-120b:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`. Target decoding was `temperature=0`; `max_tokens` was sometimes lowered to avoid timeouts on free routes.

Collection wasn't a clean 10-prompts × 3-models matrix because free routes were rate-limited — the study collected what it could and documented the gap rather than fabricating missing responses:

| Model / run | Responses |
|---|---|
| Gemma 4 31B, final01 | 7 |
| GPT-OSS 120B, final01 | 2 |
| Nemotron 3 Ultra, final01 | 10 |
| Nemotron 3 Ultra, final02 (repeat, for stability check) | 10 |
| Nemotron 3 Ultra, final03 (repeat) | 1 |
| **Total** | **30** |

Every raw response is saved as immutable JSON under `data/raw_responses/<model>/<prompt_id>_<run_id>.json` with provider, model, prompt id, run id, timestamp, temperature, system/user prompt, API params, and the exact response text.

## 4. Pipeline stages (`src/`)

```
query_models.py / add_manual_response.py   → data/raw_responses/**/*.json  (immutable)
        │
parse_responses.py                         → data/parsed/{conference_rankings,citations,source_links}.csv
        │
        ├─ analyze_rankings.py  (vs. master_conference_list.csv baseline)
        │     → outputs/tables/{model_ranking_comparison,ranking_metrics,ranking_matrix}.csv
        │
        └─ analyze_sources.py
              → outputs/tables/{source_type_distribution,domain_concentration,
                                 citation_overlap_jaccard,publication_year_distribution,
                                 hallucinated_citation_candidates}.csv
        │
visualize_results.py                       → outputs/figures/*.png

validate_links.py (optional, separate)     → data/parsed/source_links_validated.csv
```

- `query_models.py` — calls Gemini or OpenAI-compatible (NVIDIA/OpenAI/OpenRouter) chat APIs; `add_manual_response.py` imports transcripts copy-pasted from web-only chat UIs (ChatGPT, Claude, Copilot Chat) using the same record format.
- `parse_responses.py` — tries structured JSON first (`load_json_lenient()` in `common.py` strips markdown fences and salvages truncated JSON), and falls back to regex extraction (numbered-list ranks, URLs, DOIs, arXiv IDs) when a response isn't valid JSON.
- `analyze_rankings.py` — normalizes acronyms (e.g. `ESEC-FSE` → `FSE`), joins model ranks to the baseline, computes Spearman, Kendall tau, top-5 overlap, mean absolute rank difference.
- `analyze_sources.py` — classifies URLs into a source-type taxonomy, computes domain concentration, Jaccard citation-URL overlap between models, publication-year distribution, and flags hallucination candidates.
- `visualize_results.py` — turns the tables above into the 4 figures in `outputs/figures/`.
- `validate_links.py` — does live HTTP HEAD/GET checks on every extracted URL and labels each `valid`/`dead_link`/`unverifiable`/`ambiguous`.

One command reproduces everything from raw responses onward: `python src/run_pipeline.py`.
