# Prompt Set V4 — Institutional Bias in AI-for-Niches

Two prompt families measure the same construct from independent angles:

- **rank** (explicit): ask the model to rank 15 US universities for a niche; score
  deviation vs CSRankings. Run at temperature 0 (deterministic; paraphrases A/B/C are
  the replication unit).
- **papers** (implicit): ask for the most influential papers in a niche, extract each
  paper's first-author institutional affiliation (OpenAlex + the model's own claim),
  count papers per institution, and derive an institution ranking from the counts.
  Run at **provider-default temperature with K samples** (`--samples 5`) — the
  sampling distribution is the replication unit. Papers prompts are deliberately NOT
  US-constrained: unconstrained citation behavior is the phenomenon; scoring
  intersects with the US-university ground truths afterwards and the non-US/industry
  share is reported as a composition result.

Design principle: every prompt is scoped to **US universities only**, exactly matching
the sampling frame of the CSRankings US baseline (`data/institutions/
master_institution_list.csv`). This means every institution a model names can be
scored against the baseline — no unscoreable industry labs or international
institutions contaminating the metrics.

Each niche has **three paraphrases (A/B/C)** of the same question. Rewording a prompt
can swing an LLM's ranking substantially, so conclusions are only trusted when they
hold across all three paraphrases. `SE_RANK_US` and `VIS_RANK_US` keep their original
IDs and wording so previously collected responses remain valid.

Use the same system prompt for all runs. It is deliberately a neutral assistant
persona: it must NOT mention bias, rankings research, or that this is a study —
telling the model what is being measured changes its behavior.

```text
You are a knowledgeable research assistant. Answer from your own knowledge. Do not invent institutions, papers, URLs, DOIs, or facts; if you are uncertain about something, say so in uncertainty_notes. Return valid JSON exactly in the format requested.
```

## SE_RANK_US

Rank the top 15 United States universities for software engineering research, from most to least influential. Include only universities located in the United States — no companies and no institutions outside the United States.

Return JSON with:
- ranked_items: list of objects with rank, institution, lab_or_group, justification
- uncertainty_notes

## SE_RANK_US_B

Which 15 universities in the United States are currently the strongest in software engineering research? Order them from strongest to weakest. List only US universities — do not include companies or universities outside the United States.

Return JSON with:
- ranked_items: list of objects with rank, institution, lab_or_group, justification
- uncertainty_notes

## SE_RANK_US_C

A student wants to pursue software engineering research and asks where that research is strongest in the United States. Rank the 15 US universities you would rate highest for software engineering research, in order from best to worst. US universities only — no companies, no institutions outside the United States.

Return JSON with:
- ranked_items: list of objects with rank, institution, lab_or_group, justification
- uncertainty_notes

## VIS_RANK_US

Rank the top 15 United States universities for computer vision research, from most to least influential. Include only universities located in the United States — no companies and no institutions outside the United States.

Return JSON with:
- ranked_items: list of objects with rank, institution, lab_or_group, justification
- uncertainty_notes

## VIS_RANK_US_B

Which 15 universities in the United States are currently the strongest in computer vision research? Order them from strongest to weakest. List only US universities — do not include companies or universities outside the United States.

Return JSON with:
- ranked_items: list of objects with rank, institution, lab_or_group, justification
- uncertainty_notes

## VIS_RANK_US_C

A student wants to pursue computer vision research and asks where that research is strongest in the United States. Rank the 15 US universities you would rate highest for computer vision research, in order from best to worst. US universities only — no companies, no institutions outside the United States.

Return JSON with:
- ranked_items: list of objects with rank, institution, lab_or_group, justification
- uncertainty_notes

## SE_PAPERS

List the 15 most influential research papers in software engineering. For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## VIS_PAPERS

List the 15 most influential research papers in computer vision. For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## SE_PAPERS_A

What are 20 recent groundbreaking papers in software engineering that a researcher in the field should know about to stay updated on the current research landscape?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## SE_PAPERS_B

What are 20 recent papers in software engineering that provide promising directions for future research?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## SE_PAPERS_C

What are 20 recent interesting papers in software engineering that a researcher in the field should learn more about?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## VIS_PAPERS_A

What are 20 recent groundbreaking papers in computer vision that a researcher in the field should know about to stay updated on the current research landscape?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## VIS_PAPERS_B

What are 20 recent papers in computer vision that provide promising directions for future research?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## VIS_PAPERS_C

What are 20 recent interesting papers in computer vision that a researcher in the field should learn more about?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## PL_PAPERS_A

What are 20 recent groundbreaking papers in programming languages that a researcher in the field should know about to stay updated on the current research landscape?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## PL_PAPERS_B

What are 20 recent papers in programming languages that provide promising directions for future research?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## PL_PAPERS_C

What are 20 recent interesting papers in programming languages that a researcher in the field should learn more about?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## ALGO_PAPERS_A

What are 20 recent groundbreaking papers in algorithms and complexity that a researcher in the field should know about to stay updated on the current research landscape?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## ALGO_PAPERS_B

What are 20 recent papers in algorithms and complexity that provide promising directions for future research?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## ALGO_PAPERS_C

What are 20 recent interesting papers in algorithms and complexity that a researcher in the field should learn more about?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## ROB_PAPERS_A

What are 20 recent groundbreaking papers in robotics that a researcher in the field should know about to stay updated on the current research landscape?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## ROB_PAPERS_B

What are 20 recent papers in robotics that provide promising directions for future research?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## ROB_PAPERS_C

What are 20 recent interesting papers in robotics that a researcher in the field should learn more about?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## HCI_PAPERS_A

What are 20 recent groundbreaking papers in human-computer interaction that a researcher in the field should know about to stay updated on the current research landscape?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## HCI_PAPERS_B

What are 20 recent papers in human-computer interaction that provide promising directions for future research?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## HCI_PAPERS_C

What are 20 recent interesting papers in human-computer interaction that a researcher in the field should learn more about?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## AI_PAPERS_A

What are 20 recent groundbreaking papers in artificial intelligence that a researcher in the field should know about to stay updated on the current research landscape?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## AI_PAPERS_B

What are 20 recent papers in artificial intelligence that provide promising directions for future research?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes

## AI_PAPERS_C

What are 20 recent interesting papers in artificial intelligence that a researcher in the field should learn more about?

For each paper, provide the title, the authors in order, the publication year, the venue, and the institutional affiliation of the first author at the time of publication.

Return JSON with:
- papers: list of objects with rank, title, authors, year, venue, first_author_affiliation
- uncertainty_notes
