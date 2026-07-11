# 01 — Project Overview

## Title and framing

**How Frontier AI Models Treat Information Sources in AI-for-Software-Engineering Questions**
Author: Ajoy Dey, Bangladesh University of Engineering and Technology.

## Abstract (from `report/main.tex`)

AI-assisted software engineering is now discussed through many kinds of sources: software engineering conferences, programming-language venues, arXiv papers, benchmarks, company blogs, documentation, GitHub repositories, and practitioner reports. This project studies how frontier and open-weight AI models treat those sources when asked questions about AI in software engineering. The study is a reproducible, prompt-based experiment with:

- a 30-venue conference baseline,
- 10 prompts,
- 30 raw model responses (collected from OpenRouter free routes for Gemma 4 31B, GPT-OSS 120B, and Nemotron 3 Ultra),
- parsers for rankings and citations, and
- analysis scripts for ranking agreement, source-type distribution, domain concentration, and link validation.

## Project goal (from `AGENTS.md`)

Design and execute a reproducible research study on how frontier AI models treat information sources in AI-for-software-engineering questions, comparing models across **two scenarios**:

1. **Source impact understanding** — how models rank academic venues, papers, and source types, and whether those rankings align with established signals such as CORE rankings and CSRankings.
2. **Source retrieval and attribution behavior** — which exact links, papers, blogs, repositories, company pages, and other sources models cite, and how source choices change as questions vary in depth, specificity, and recency.

## The 7 research questions

| # | Question | Why it matters |
|---|---|---|
| RQ1 | Which conferences do frontier models consider most important for AI in software engineering? | Establishes the baseline "what do models say" signal before comparing to anything external. |
| RQ2 | Do model-generated conference rankings correlate with CORE-style ranks and CSRankings areas? | Tests whether model judgment tracks an established prestige signal, or diverges from it. |
| RQ3 | Do models prefer academic sources, company blogs, documentation, arXiv papers, GitHub repositories, news, or general web pages? | Reveals whether models default to convenient/accessible sources over authoritative ones. |
| RQ4 | Do models cite sources from their own organization/ecosystem more often than competing sources? | Tests for a self-promotion or ecosystem bias in source selection. |
| RQ5 | Do models over-prioritize recent LLM/code-generation work over older, established SE research? | Tests for a recency bias that could crowd out foundational work. |
| RQ6 | Do shallow prompts produce more web/blog sources while deeper prompts produce more academic citations? | Tests whether prompt design itself shapes source quality, not just the model. |
| RQ7 | Which models hallucinate papers, venues, URLs, or DOIs more often? | Directly measures reliability — the practical risk of trusting a model's citations. |

## Why this project (personal motivation, from the report's Introduction)

The author's day-to-day software work with AI involves moving between academic sources (for durable research ideas) and industrial sources (for practical implementation details, APIs, benchmarks, deployment guidance). That made the question personally relevant: as AI assistants become part of software engineering work, it matters whether they value established research, whether they over-rely on recent web material, and whether they cite exact sources reliably.

The deliverable is not just the report — it's a **reproducible research package**: prompts, raw responses, parsing scripts, analysis scripts, figures, tables, and documented limitations, all runnable from the repo root.
