# AI Model Source Behavior in AI-for-Software-Engineering Questions

This repository contains a reproducible research workflow for studying how frontier AI models rank venues and cite sources when answering AI-for-software-engineering questions.

The study focuses on two behaviors:

1. Source impact understanding: which conferences and papers models treat as important, and whether those rankings align with baseline signals such as CORE-style ranks and CSRankings areas.
2. Source retrieval and attribution: which links, papers, blogs, documentation pages, repositories, and company sources models cite.

## What Is Included

- A cleaned conference baseline: `data/conferences/master_conference_list.csv`
- CORE/CSRankings comparison notes: `data/conferences/core_raw.csv`, `data/conferences/csrankings_raw.csv`
- Eight prompts with metadata: `data/prompts/prompt_set_v1.md`, `data/prompts/prompt_metadata.csv`
- Gemini API collection script: `src/query_models.py`
- Manual transcript import script for ChatGPT, Claude, Copilot, or other web-only models: `src/add_manual_response.py`
- Parsers and analysis scripts: `src/parse_responses.py`, `src/analyze_rankings.py`, `src/analyze_sources.py`
- Figure generation: `src/visualize_results.py`
- A one-command pipeline: `src/run_pipeline.py`
- Demo raw responses so the pipeline works immediately before you collect real responses.

The demo responses are labeled with `provider=demo` and `model=demo_gemini_like`. Replace or supplement them with real model runs before submitting final results.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.11 is recommended. Newer local Python builds may work, but scientific packages are usually easiest to install on Python 3.11 or 3.12.

For Gemini API collection, create a local `.env` file:

```text
GEMINI_API_KEY=your_key_here
```

Do not commit `.env`.

## Run The Demo Pipeline

```bash
python src/run_pipeline.py
```

This regenerates:

- `data/parsed/conference_rankings.csv`
- `data/parsed/citations.csv`
- `data/parsed/source_links.csv`
- `outputs/tables/model_ranking_comparison.csv`
- `outputs/tables/ranking_metrics.csv`
- `outputs/tables/source_type_distribution.csv`
- `outputs/tables/domain_concentration.csv`
- `outputs/figures/conference_ranking_heatmap.png`
- `outputs/figures/source_type_bar_chart.png`
- `outputs/figures/citation_overlap_heatmap.png`
- `outputs/figures/publication_year_distribution.png`

Optionally validate extracted URLs:

```bash
python src/validate_links.py
```

## Collect Gemini Responses

Run all prompts with Gemini:

```bash
python src/query_models.py --provider gemini --models gemini-1.5-flash --run-id run01
```

Run only selected prompts:

```bash
python src/query_models.py --provider gemini --models gemini-1.5-flash --prompt-ids P01_CONFERENCE_RANKING,P04_EXACT_SOURCES --run-id run01
```

After collection:

```bash
python src/run_pipeline.py
```

## Add Manual Responses From Free Chat Interfaces

For ChatGPT, Claude, Copilot Chat, Grok, DeepSeek web chat, or any system without a usable research API:

1. Open `data/prompts/prompt_set_v1.md`.
2. Copy one prompt exactly.
3. Run it in the web interface.
4. Save the model answer as a local text file, for example `outputs/chat_history/chatgpt_P01_manual01.txt`.
5. Import it:

```bash
python src/add_manual_response.py \
  --provider openai_web \
  --model "ChatGPT free web" \
  --prompt-id P01_CONFERENCE_RANKING \
  --run-id manual01 \
  --response-file outputs/chat_history/chatgpt_P01_manual01.txt
```

Then rerun:

```bash
python src/run_pipeline.py
```

If you collect screenshots or share links, store them in `outputs/chat_history/` and mention them in the report.

## Suggested Real Collection Plan

Use at least one deterministic Gemini API run for all prompts. For models without APIs, manually collect at least:

- ChatGPT: `P01_CONFERENCE_RANKING`, `P04_EXACT_SOURCES`, `P08_HALLUCINATION_STRESS`
- Claude: same three prompts if available
- GitHub Copilot Chat: `P07_PRACTITIONER_GUIDANCE` and `P08_HALLUCINATION_STRESS`
- Any other free model: `P01_CONFERENCE_RANKING` and `P04_EXACT_SOURCES`

This gives enough data to compare rankings, source types, and hallucination risk without requiring paid access to every provider.

## Important Limitations

- The included CORE and CSRankings files are comparison baselines, not absolute truth.
- The baseline venue metadata should be rechecked against the latest CORE portal and CSRankings before final submission.
- Web interfaces may use hidden system prompts, browsing, personalization, or changing model versions.
- Some APIs do not support perfectly deterministic decoding.
- A citation can look plausible but still be false; this project flags candidates but manual validation remains necessary.
- Demo data is only for testing the pipeline and must not be presented as empirical model behavior.

## Reproducibility Checklist

- Install dependencies from `requirements.txt`.
- Keep raw model outputs under `data/raw_responses/`.
- Never edit raw responses after collection.
- Regenerate parsed data and outputs with `python src/run_pipeline.py`.
- Document model names, dates, prompts, run IDs, API settings, and manual collection notes.
- In the final report, separate demo/test runs from real study results.
