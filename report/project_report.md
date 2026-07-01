# Project Report: AI Model Source Behavior in AI-for-Software-Engineering Questions

## 1. Objective

This study evaluates how AI models treat information sources when asked about AI-assisted software engineering. It compares model behavior across venue ranking, paper/source citation, recent-work summaries, area mapping, and practitioner guidance prompts.

## 2. Research Questions

1. Which conferences do frontier models consider most important for AI in software engineering?
2. Do model-generated conference rankings correlate with CORE-style ranks and CSRankings areas?
3. Do models prefer academic sources, company blogs, documentation, arXiv papers, GitHub repositories, news articles, or general web pages?
4. Do models cite sources from their own organizations or ecosystem more often than competing sources?
5. Do models over-prioritize recent LLM/code-generation work compared with older software engineering research?
6. Do shallow prompts produce more web/blog sources while deeper prompts produce more academic citations?
7. Which models hallucinate papers, venues, URLs, or DOIs more often?

## 3. Data And Prompts

The conference baseline is stored in `data/conferences/master_conference_list.csv`. It includes 30 venues: software engineering venues such as ICSE, FSE, ASE, ISSTA, MSR, ICSME, SANER, RE, MODELS, ICPC, ICST, COMPSAC, and SAC; programming-language and formal-methods venues such as PLDI, OOPSLA, POPL, CAV, TACAS, FM, and VMCAI; and related AI/HCI/data venues such as NeurIPS, ICML, ICLR, AAAI, IJCAI, KDD, WWW, CHI, and UIST.

The prompt battery has 10 prompts and is stored in `data/prompts/prompt_set_v1.md`, with metadata in `data/prompts/prompt_metadata.csv`. Prompt `P09_LOW_RANK_VENUE_CHECK` was added to test whether models include lower-rank and specialized venues when explicitly asked.

## 4. Model Collection Method

Gemini responses can be collected with:

```bash
python src/query_models.py --provider gemini --models gemini-1.5-flash --run-id run01
```

The final API collection for this version used OpenRouter free endpoints for three models:

- `google/gemma-4-31b-it:free`
- `openai/gpt-oss-120b:free`
- `nvidia/nemotron-3-ultra-550b-a55b:free`

The command was:

```bash
python src/query_models.py --provider openrouter --models google/gemma-4-31b-it:free,openai/gpt-oss-120b:free,nvidia/nemotron-3-ultra-550b-a55b:free --run-id final01 --temperature 0 --max-tokens 4096 --sleep 2
```

Because free routes were rate-limited, the final 30 raw responses were collected as:

- Gemma 4 31B: 7 prompt responses, `final01`
- GPT-OSS 120B: 2 prompt responses, `final01`
- Nemotron 3 Ultra: 10 prompt responses, `final01`
- Nemotron 3 Ultra: 10 repeated prompt responses, `final02`
- Nemotron 3 Ultra: 1 additional repeated response, `final03`

This makes the dataset large enough for a final run while also supporting a small stability check for Nemotron.

Manual responses from web interfaces can be imported with:

```bash
python src/add_manual_response.py --provider openai_web --model "ChatGPT free web" --prompt-id P01_CONFERENCE_RANKING --run-id manual01 --response-file outputs/chat_history/chatgpt_P01_manual01.txt
```

All raw responses are stored under `data/raw_responses/` with model, prompt, run, timestamp, prompt text, parameters, and exact response text.

## 5. Parsing And Analysis

The parser extracts:

- conference rankings into `data/parsed/conference_rankings.csv`;
- citations into `data/parsed/citations.csv`; and
- source links into `data/parsed/source_links.csv`.

Run the full pipeline:

```bash
python src/run_pipeline.py
```

The ranking analysis computes Spearman correlation, Kendall tau, top-k overlap, and mean absolute rank difference against the baseline. The source analysis computes source-type distributions, domain concentration, citation overlap, publication-year distribution, and hallucination candidates. Extracted URLs were validated with `src/validate_links.py`.

## 6. Results

The final pipeline run produced:

- 30 raw API response files in `data/raw_responses/`
- 205 parsed ranking rows in `data/parsed/conference_rankings.csv`
- 86 parsed citation rows in `data/parsed/citations.csv`
- 86 extracted source links in `data/parsed/source_links.csv`
- 86 validated source links in `data/parsed/source_links_validated.csv`
- model/run collection counts in `outputs/tables/collection_summary.csv`

Ranking prompts generally placed ICSE, FSE, ASE, ISSTA, and MSR near the top. The source-heavy prompts produced many arXiv references and some GitHub, company, documentation, conference, and ranking-site links.

Selected ranking metrics from `outputs/tables/ranking_metrics.csv`:

- Gemma `P01_CONFERENCE_RANKING`: Spearman 0.643 vs baseline, top-5 overlap 0.60
- Nemotron `P01_CONFERENCE_RANKING` final01: Spearman 0.700 vs baseline, top-5 overlap 0.60
- Nemotron `P02_CONFERENCE_RANKING_SOURCED` final01: Spearman 0.682 vs baseline, top-5 overlap 0.80
- Nemotron `P09_LOW_RANK_VENUE_CHECK` final02: Spearman 0.788 vs baseline, top-5 overlap 1.00
- GPT-OSS `P02_CONFERENCE_RANKING_SOURCED`: Spearman 1.000 on the 9 matched venues extracted from that response

Source validation results from `data/parsed/source_links_validated.csv`:

- Valid links: 72
- Dead links: 12
- Unverifiable links: 2

Generated figures:

- `outputs/figures/conference_ranking_heatmap.png`
- `outputs/figures/source_type_bar_chart.png`
- `outputs/figures/citation_overlap_heatmap.png`
- `outputs/figures/publication_year_distribution.png`

## 7. Limitations

Model knowledge cutoffs differ. OpenRouter free routes were rate-limited during collection, so the dataset is not a perfectly balanced 10-prompts-by-3-models matrix. Some responses were collected with smaller `max_tokens` values to reduce timeout and rate-limit failures. CORE and CSRankings are useful comparison signals but do not measure the same thing and should not be treated as absolute ground truth. Automated link validation can mark a source dead or unverifiable because of temporary network failures, access restrictions, redirects, or generated false URLs, so suspicious items should be checked manually before making strong claims.

## 8. Future Work

Future versions should add richer citation verification against Crossref, Semantic Scholar, or OpenAlex; collect balanced runs after free-route rate limits reset; add more repeated runs per model; and run statistical tests for prompt sensitivity.
