# Knowledge Base — Index

Study notes for defending the assignment *"How Frontier AI Models Treat Information Sources in AI-for-Software-Engineering Questions."* This folder distills the project into short, navigable files. It does not replace the submitted report — for the canonical, citable write-up, use `report/main.tex` (and its rendered PDF, `report/UIUC_project_report_by_Ajoy_Dey.pdf`).

## Contents

| File | What's in it |
|---|---|
| [01-project-overview.md](01-project-overview.md) | Title, abstract, project goal, the two study scenarios, the 7 research questions, why the project was chosen |
| [02-methodology-pipeline.md](02-methodology-pipeline.md) | Conference baseline, the 10-prompt battery, model collection setup, and how the `src/` pipeline turns raw responses into tables and figures |
| [03-glossary.md](03-glossary.md) | Plain-language definitions of every metric/term used (Spearman, Kendall tau, Jaccard, CORE rank, source-type taxonomy, hallucination heuristic, etc.) |
| [04-results-and-findings.md](04-results-and-findings.md) | The actual numbers: dataset sizes, ranking-agreement metrics, source-type distribution, domain concentration, link-validation results |
| [05-qa-defense-prep.md](05-qa-defense-prep.md) | Anticipated teacher questions with ready answers — start here before a viva/defense |
| [06-limitations-and-future-work.md](06-limitations-and-future-work.md) | Threats to validity and what a follow-up version should improve |

## Source material this KB was built from

- `AGENTS.md` — the original assignment brief and methodology plan
- `README.md` — setup and run instructions
- `report/main.tex` — the full submitted report (richest source; ACM format)
- `report/project_report.md`, `report/executive_summary.md` — condensed report drafts
- `data/prompts/prompt_set_v1.md`, `data/prompts/prompt_metadata.csv` — the exact prompts used
- `src/*.py` — the collection/parsing/analysis/visualization pipeline

Every number and claim in this knowledge base traces back to one of those files — nothing here is new analysis.
