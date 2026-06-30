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

The conference baseline is stored in `data/conferences/master_conference_list.csv`. It includes software engineering venues such as ICSE, FSE, ASE, ISSTA, MSR, ICSME, SANER, RE, and MODELS; programming-language and formal-methods venues such as PLDI, OOPSLA, POPL, CAV, TACAS, and FM; and related AI/HCI/data venues such as NeurIPS, ICML, ICLR, AAAI, IJCAI, KDD, WWW, CHI, and UIST.

The prompt battery is stored in `data/prompts/prompt_set_v1.md`, with metadata in `data/prompts/prompt_metadata.csv`.

## 4. Model Collection Method

Gemini responses can be collected with:

```bash
python src/query_models.py --provider gemini --models gemini-1.5-flash --run-id run01
```

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

The ranking analysis computes Spearman correlation, Kendall tau, top-k overlap, and mean absolute rank difference against the baseline. The source analysis computes source-type distributions, domain concentration, citation overlap, publication-year distribution, and hallucination candidates.

## 6. Current Results

The repository includes demo data so the pipeline can be tested immediately. These rows are labeled `provider=demo` and `model=demo_gemini_like`.

Before final submission, replace or supplement demo data with real collected responses. Then update this section using the generated tables:

- `outputs/tables/ranking_metrics.csv`
- `outputs/tables/model_ranking_comparison.csv`
- `outputs/tables/source_type_distribution.csv`
- `outputs/tables/domain_concentration.csv`
- `outputs/tables/hallucinated_citation_candidates.csv`

Suggested figures:

- `outputs/figures/conference_ranking_heatmap.png`
- `outputs/figures/source_type_bar_chart.png`
- `outputs/figures/citation_overlap_heatmap.png`
- `outputs/figures/publication_year_distribution.png`

## 7. Limitations

Model knowledge cutoffs differ. Web interfaces may browse or personalize results. Some providers do not offer deterministic decoding. Manual transcript collection is less controlled than API collection but is necessary for free or closed interfaces. CORE and CSRankings are useful comparison signals but do not measure the same thing and should not be treated as absolute ground truth. Some citations require manual validation because plausible metadata can still be hallucinated.

## 8. Future Work

Future versions should add automated link validation, richer citation verification against Crossref/Semantic Scholar/OpenAlex, repeated runs per model, and statistical tests for prompt sensitivity.

