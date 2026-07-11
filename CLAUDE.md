# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

A reproducible research study (UIUC assignment) on how frontier AI models treat information sources when answering AI-for-software-engineering questions. It studies two behaviors:

1. **Source impact understanding** — how models rank academic venues/papers, and whether those rankings align with CORE rankings and CSRankings.
2. **Source retrieval and attribution** — which exact links, papers, blogs, repos, and company pages models cite, and how that varies with prompt depth/specificity.

`AGENTS.md` contains the original detailed research plan (research questions, phases, coding standards, timeline) — read it for the full methodology behind the pipeline described below.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Secrets live in `.env` (gitignored, never commit): `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `NVIDIA_API_KEY`/`nvidia_api_key`, `OPENAI_API_KEY`. `query_models.py` loads `.env` via `python-dotenv`.

## Common Commands

Run the full pipeline (parse → analyze rankings → analyze sources → generate figures), always from repo root:

```bash
python src/run_pipeline.py
```

Individual pipeline stages (each is independently runnable and takes `--input`/`--output` style flags — see each script's `argparse` block for the full set):

```bash
python src/parse_responses.py --input data/raw_responses --output data/parsed
python src/analyze_rankings.py --input data/parsed/conference_rankings.csv
python src/analyze_sources.py --links data/parsed/source_links.csv --citations data/parsed/citations.csv
python src/visualize_results.py
python src/validate_links.py   # optional: HTTP-checks URLs in source_links.csv
```

Collect new model responses (writes raw JSON, does not touch parsed data):

```bash
python src/query_models.py --provider gemini --models gemini-1.5-flash --run-id run01
python src/query_models.py --provider openrouter --models google/gemma-4-31b-it:free,openai/gpt-oss-120b:free,nvidia/nemotron-3-ultra-550b-a55b:free --run-id final01 --temperature 0 --max-tokens 4096 --sleep 2
python src/query_models.py --provider gemini --models gemini-1.5-flash --prompt-ids P01_CONFERENCE_RANKING,P04_EXACT_SOURCES --run-id run01
```

Import a manually-collected transcript (for web-only chat UIs with no API, e.g. ChatGPT/Claude/Copilot Chat):

```bash
python src/add_manual_response.py --provider openai_web --model "ChatGPT free web" --prompt-id P01_CONFERENCE_RANKING --run-id manual01 --response-file outputs/chat_history/chatgpt_P01_manual01.txt
```

After any collection (API or manual), rerun `python src/run_pipeline.py` to regenerate parsed data/tables/figures.

There is no test suite, linter, or build step in this repo — correctness is verified by running the pipeline and inspecting the CSVs/figures it produces.

## Architecture

This is a linear data pipeline, not an application. Data flows one direction through `data/` and `outputs/`, and every stage is a standalone script under `src/` that can be re-run independently as long as its inputs exist.

```
data/prompts/prompt_set_v1.md + prompt_metadata.csv   (prompt bank, keyed by prompt_id)
        │
        ▼  src/query_models.py (API)  or  src/add_manual_response.py (manual transcript import)
data/raw_responses/<safe_model_name>/<prompt_id>_<run_id>.json   (immutable — never hand-edit)
        │
        ▼  src/parse_responses.py
data/parsed/{conference_rankings,citations,source_links}.csv
        │
        ├──▼ src/analyze_rankings.py  (uses data/conferences/master_conference_list.csv as baseline)
        │      outputs/tables/{model_ranking_comparison,ranking_metrics,ranking_matrix}.csv
        │
        ├──▼ src/analyze_sources.py
        │      outputs/tables/{source_type_distribution,domain_concentration,citation_overlap_jaccard,
        │                       publication_year_distribution,hallucinated_citation_candidates}.csv
        │
        └──▼ src/visualize_results.py  (reads the tables above)
               outputs/figures/*.png

src/validate_links.py (optional, separate branch): data/parsed/source_links.csv → data/parsed/source_links_validated.csv
```

Key conventions to preserve when touching this pipeline:

- **Raw data is immutable.** `data/raw_responses/**/*.json` files are never edited after collection; each holds full metadata (provider, model, prompt_id, run_id, timestamp, temperature, system/user prompt, API params, raw `response_text`) via `write_record()` in `src/query_models.py`, which is reused by `src/add_manual_response.py` for manual imports.
- **`src/common.py`** is the shared module: `ROOT` (repo root, resolved from file location — all scripts read/write paths relative to this), `read_prompt_text()` (extracts a prompt body from `prompt_set_v1.md` by `## {prompt_id}` heading), `safe_model_name()` (sanitizes model names for directory names), `load_json_lenient()` (best-effort JSON extraction from a possibly markdown-fenced or truncated LLM response).
- **Parsing is defense-in-depth.** `parse_responses.py` first tries to read structured JSON (`ranked_items`, `references` fields) via `load_json_lenient()`; if that yields nothing it falls back to regex extraction from raw text (`RANK_RE` for numbered rankings, `URL_RE`/`DOI_RE`/`ARXIV_RE` for citations). Any new response format should extend both paths, not just the structured one, since model output is inconsistent across providers/free-tier routes.
- **Model/prompt identity keys.** Every parsed/analysis table is keyed by `(model, prompt_id, run_id)`; conference identity is normalized through `normalize_acronym()` in `analyze_rankings.py` before joining against the baseline list (handles aliases like `ESEC-FSE` → `FSE`).
- **Baseline comparison data** lives in `data/conferences/master_conference_list.csv` (`baseline_rank`, `core_rank`, `csrankings_area` columns) — this is the ground truth `analyze_rankings.py` correlates model rankings against (Spearman, Kendall tau, top-k overlap, mean abs rank diff).
- Scripts are meant to be run from the repo root (`cwd=ROOT` in `run_pipeline.py`); all default `--input`/`--output` args are relative paths.

## Report

`report/` contains the write-up: `main.tex` (ACM format, uses `acmart.cls`), `project_report.md`/`executive_summary.md` (markdown drafts), `references.bib`, and a prebuilt `report/UIUC_project_report_by_Ajoy_Dey.pdf`. Figures embedded in the report are copied into `report/figures/` from `outputs/figures/`.
