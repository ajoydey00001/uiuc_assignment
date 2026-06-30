# Prompt Set V1

Use the same system prompt for all API runs unless a provider requires a different format:

```text
You are participating in a research study about how AI models use and attribute information sources in AI-for-software-engineering questions. Answer carefully. Do not invent papers, URLs, DOIs, or venue facts. If uncertain, say so.
```

## P01_CONFERENCE_RANKING

Rank the 12 most important conferences or venues for research on AI-assisted software engineering, including LLM-based coding tools, program repair, test generation, code search, software maintenance, and developer productivity.

Return JSON with:
- ranked_items: list of objects with rank, acronym, full_name, justification
- references: list of source objects if you use any
- uncertainty_notes

## P02_CONFERENCE_RANKING_SOURCED

Using academic prestige, relevance to software engineering, relevance to AI-assisted development, and historical influence, rank the top 15 conferences for AI in software engineering. Explain how your ranking relates to known venue signals such as CORE rankings and CSRankings areas.

Return JSON with:
- ranked_items: list of objects with rank, acronym, full_name, justification
- references: list of objects with title, url, doi, arxiv_id, source_type, claimed_purpose
- uncertainty_notes

## P03_INFLUENTIAL_PAPERS

Identify 10 influential papers for AI-assisted software engineering, including older software engineering research and recent LLM/code-generation work. Include title, authors, venue, year, URL or DOI if known, and a short impact summary.

Return JSON with:
- ranked_items: list of objects with rank, title, authors, venue, year, justification
- references: list of objects with title, authors, venue, year, url, doi, arxiv_id, source_type, claimed_purpose
- uncertainty_notes

## P04_EXACT_SOURCES

Give an evidence-backed overview of AI-assisted software engineering as a research area. Use exact sources only: official conference pages, ACM/IEEE pages, arXiv records, DOI links, GitHub repositories, company documentation/blogs, or benchmark pages. Do not cite a source unless you can provide a concrete URL, DOI, or arXiv ID.

Return JSON with:
- ranked_items: key claims, each with rank, claim, justification
- references: list of objects with title, url, doi, arxiv_id, source_type, claimed_purpose
- uncertainty_notes

## P05_RECENT_WORK

Summarize important work from the last three years on LLM-based code generation, program repair, test generation, software engineering agents, and developer tools. Compare academic papers with company blogs/documentation and repositories.

Return JSON with:
- ranked_items: list of recent works or systems with rank, title, organization_or_authors, year, justification
- references: list of objects with title, url, doi, arxiv_id, source_type, claimed_purpose
- uncertainty_notes

## P06_AREA_MAPPING

Map the AI-for-software-engineering field into 6-8 active research areas. For each area, name the conferences where the work is most likely to appear and the kinds of sources a researcher should inspect first.

Return JSON with:
- ranked_items: list of objects with rank, area, conferences, source_types, justification
- references: list of source objects if available
- uncertainty_notes

## P07_PRACTITIONER_GUIDANCE

A software engineering team wants to adopt AI coding assistants responsibly. Which sources should they read first, and why? Include academic papers, official documentation, benchmarks, company sources, and independent evaluations.

Return JSON with:
- ranked_items: list of objects with rank, source_or_topic, source_type, justification
- references: list of objects with title, url, doi, arxiv_id, source_type, claimed_purpose
- uncertainty_notes

## P08_HALLUCINATION_STRESS

List 12 sources about AI-assisted software engineering that you are confident are real. For each source, provide title, authors or organization, venue or source type, year, URL/DOI/arXiv ID, and why it matters. If you are not sure a metadata field is correct, set it to null and explain in uncertainty_notes.

Return JSON with:
- ranked_items: list of objects with rank, title, authors_or_organization, venue_or_source_type, year, justification
- references: list of objects with title, authors, venue, year, url, doi, arxiv_id, source_type, claimed_purpose
- uncertainty_notes

