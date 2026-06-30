# AGENTS.md

## Project Goal

Design and execute a reproducible research study on how frontier AI models treat information sources in AI-for-software-engineering questions.

The project should compare models across two main scenarios:

1. **Source impact understanding**
   - How models rank academic venues, papers, and source types.
   - Whether rankings align with established signals such as CORE rankings and CSRankings.

2. **Source retrieval and attribution behavior**
   - Which exact links, papers, blogs, repositories, company pages, and other sources models cite.
   - How source choices change when questions vary in depth, specificity, and recency.

The expected deliverables may include code, datasets, prompts, raw model transcripts, parsed results, tables, figures, and a written report.

## Research Questions

Use these as the backbone of the study:

1. Which conferences do frontier models consider most important for AI in software engineering?
2. Do model-generated conference rankings correlate with CORE and CSRankings?
3. Do models prefer academic sources, company blogs, documentation, arXiv papers, GitHub repositories, news articles, or general web pages?
4. Do models cite sources from their own organizations or ecosystem more often than competing sources?
5. Do models over-prioritize recent LLM/code-generation work compared with older, established software engineering research?
6. Do shallow prompts produce more web/blog sources while deeper prompts produce more academic citations?
7. Which models hallucinate papers, venues, URLs, or DOIs more often?

## Recommended Repository Structure

Create this structure as the project grows:

```text
.
├── AGENTS.md
├── README.md
├── requirements.txt
├── data/
│   ├── conferences/
│   │   ├── core_raw.csv
│   │   ├── csrankings_raw.csv
│   │   └── master_conference_list.csv
│   ├── prompts/
│   │   ├── prompt_set_v1.md
│   │   └── prompt_metadata.csv
│   ├── raw_responses/
│   │   └── <model>/<prompt_id>_<run_id>.json
│   └── parsed/
│       ├── conference_rankings.csv
│       ├── citations.csv
│       └── source_links.csv
├── src/
│   ├── collect_conferences.py
│   ├── query_models.py
│   ├── parse_responses.py
│   ├── analyze_rankings.py
│   ├── analyze_sources.py
│   └── visualize_results.py
├── notebooks/
│   ├── 01_conference_data.ipynb
│   ├── 02_ranking_analysis.ipynb
│   └── 03_source_analysis.ipynb
├── outputs/
│   ├── figures/
│   ├── tables/
│   └── chat_history/
└── report/
    ├── executive_summary.md
    ├── project_report.md
    └── references.bib
```

## Phase 1: Build Conference Dataset

Start with a master list of 25-30 venues connected to software engineering, programming languages, formal methods, AI, and AI-assisted development.

Minimum columns:

```text
conference,acronym,full_name,field,core_rank,csrankings_area,notes
```

Initial candidate venues:

```text
ICSE,FSE/ESEC-FSE,ASE,ISSTA,MSR,ICSME,SANER,RE,MODELS,
PLDI,OOPSLA,POPL,ECOOP,CAV,TACAS,FM,VMCAI,
NeurIPS,ICML,ICLR,AAAI,IJCAI,KDD,WWW,CHI,UIST
```

Use CORE and CSRankings as comparison baselines. Keep raw collected files separate from the cleaned master list.

## Phase 2: Prompt Design

Use a prompt battery that varies depth and source pressure. Store every prompt with a stable `prompt_id`.

Suggested prompt categories:

1. **Conference ranking**
   - Ask the model to rank top venues for AI-assisted software engineering.

2. **Influential papers**
   - Ask for influential papers with title, authors, venue, year, and impact summary.

3. **Exact source disclosure**
   - Ask for URLs, DOIs, arXiv links, or official pages used to support the answer.

4. **Recent work**
   - Ask about LLM-based code generation, program repair, testing, or developer tools in the last three years.

5. **Area mapping**
   - Ask which research areas are active and which conferences dominate each area.

6. **Practitioner guidance**
   - Ask which sources a software engineering team should read before adopting AI tools.

Use structured-output instructions whenever possible:

```text
Return your answer as JSON with these fields:
- ranked_items
- justification
- references
- uncertainty_notes
```

If JSON fails, save the raw response and parse later with a robust fallback parser.

## Phase 3: Model Querying

Target models may include:

```text
OpenAI GPT models
Anthropic Claude models
Google Gemini models
DeepSeek models
Qwen models
Grok or other web-only models, if accessible
```

For each model and prompt:

1. Run at least one deterministic query where possible.
2. Prefer temperature `0` or the closest available equivalent.
3. Save raw response text exactly as returned.
4. Save metadata:
   - model name
   - provider
   - date and time
   - prompt id
   - run id
   - temperature
   - system prompt
   - user prompt
   - API parameters

If using web interfaces, save transcripts, screenshots, share links, and timestamps.

## Phase 4: Parsing And Validation

Extract at least three datasets:

1. **Conference rankings**
   - `model`, `prompt_id`, `run_id`, `rank`, `acronym`, `full_name`, `justification`

2. **Citations**
   - `model`, `prompt_id`, `run_id`, `title`, `authors`, `venue`, `year`, `doi`, `arxiv_id`, `url`

3. **Source links**
   - `model`, `prompt_id`, `run_id`, `url`, `domain`, `source_type`, `claimed_purpose`

Recommended source types:

```text
academic_paper
conference_page
journal_page
arxiv
company_blog
personal_blog
documentation
github_repository
news
benchmark_or_dataset
unknown
```

Validate links where possible. Mark sources as:

```text
valid
dead_link
unverifiable
hallucinated
ambiguous
```

## Phase 5: Analysis

For rankings:

1. Compare model rankings against CORE and CSRankings.
2. Compute Spearman correlation, Kendall tau, top-k overlap, and mean absolute rank difference.
3. Identify venues each model over-ranks or under-ranks.
4. Compare agreement between models.

For sources:

1. Count source types by model and prompt category.
2. Measure citation overlap between models using Jaccard similarity.
3. Analyze domain concentration, such as `openai.com`, `deepmind.google`, `anthropic.com`, `arxiv.org`, `acm.org`, and `ieee.org`.
4. Track publication years to study recency bias.
5. Mark hallucinated or unverifiable citations.

For prompt sensitivity:

1. Compare shallow versus deep prompts.
2. Compare ranking prompts versus source-disclosure prompts.
3. If repeated runs exist, measure stability within the same model.

## Phase 6: Expected Outputs

Produce:

1. A cleaned `master_conference_list.csv`.
2. A prompt set with metadata.
3. Raw model responses.
4. Parsed rankings and citations.
5. Tables:
   - model ranking comparison
   - ranking correlation matrix
   - source type distribution
   - hallucinated citation report
6. Figures:
   - conference ranking heatmap
   - source type bar chart
   - citation overlap heatmap
   - publication year distribution
7. A short final report explaining method, results, limitations, and future work.

## Coding Standards

Use Python for data collection, parsing, and analysis.

Preferred practices:

1. Keep raw data immutable.
2. Write parsed or cleaned outputs to separate files.
3. Use `pandas` for tabular data.
4. Use `pydantic` or dataclasses for structured records if the codebase becomes complex.
5. Use deterministic filenames containing model, prompt id, and run id.
6. Do not store API keys in the repository.
7. Use `.env` for local secrets and add `.env` to `.gitignore`.
8. Make scripts runnable from the repository root.

Example command style:

```bash
python src/query_models.py --prompts data/prompts/prompt_metadata.csv --models openai,claude
python src/parse_responses.py --input data/raw_responses --output data/parsed
python src/analyze_rankings.py --input data/parsed/conference_rankings.csv
```

## Reproducibility Checklist

Before submitting, ensure the project includes:

1. Clear instructions in `README.md`.
2. Dependency list in `requirements.txt`.
3. Raw prompts and raw responses.
4. Parsed data files.
5. Scripts or notebooks that regenerate tables and figures.
6. Notes about unavailable APIs or manual collection steps.
7. A limitations section describing model access, date of collection, and validation gaps.

## Suggested Timeline

```text
Day 1: Build conference list and baseline metadata.
Day 2: Write prompt set and test on one model manually.
Day 3: Implement query scripts or manual transcript workflow.
Day 4: Collect responses from all available models.
Day 5: Parse rankings, citations, and URLs.
Day 6: Validate links and classify source types.
Day 7: Run ranking and source analysis.
Day 8: Generate figures and tables.
Day 9: Write report.
Day 10: Polish, verify reproducibility, and submit.
```

## Important Limitations To Document

Document these explicitly rather than hiding them:

1. Model knowledge cutoffs may differ.
2. Some models may have browsing enabled while others do not.
3. Web interfaces may change responses based on personalization or hidden system prompts.
4. Some APIs do not support true deterministic decoding.
5. Models may provide plausible but false citations.
6. CORE and CSRankings measure different kinds of prestige and should not be treated as absolute truth.

## First Concrete Tasks

Start with these files:

1. `README.md` with the research objective and reproduction notes.
2. `data/conferences/master_conference_list.csv` with 25-30 venues.
3. `data/prompts/prompt_set_v1.md` with 6-8 prompts.
4. `src/parse_responses.py` with basic extraction logic.
5. `src/analyze_rankings.py` with initial ranking comparison metrics.

Keep the first version simple and reproducible. Add sophistication only after the basic pipeline works end to end.
