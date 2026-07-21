# Prompt Set V3 — Institutional Bias in AI-for-Niches (US-scoped)

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
