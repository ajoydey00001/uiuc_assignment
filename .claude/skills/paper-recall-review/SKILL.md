---
name: paper-recall-review
description: Peer-review an LLM's "list influential papers" response (SE_PAPERS/VIS_PAPERS-style prompts) for fabrication and recency/institutional bias. Use when the user asks to review, peer-review, fact-check, or "check for bugs/old papers" in a raw_responses JSON from this project's implicit-bias study, or wants a summary artifact of implicit-bias findings.
---

# Paper-recall peer review

This project studies whether LLMs show implicit institutional/temporal bias when
asked to recall influential papers (as opposed to when asked directly to rank
institutions). A raw response to a papers-listing prompt (`SE_PAPERS`, `VIS_PAPERS`,
or similar `*_PAPERS` / `*_influential_papers` prompt_id) needs a specific kind of
review that differs from ordinary code review: it's a factual audit against the
scholarly record, not a style or correctness check.

## What to do, in order

1. **Read the raw response file directly** — don't trust summary CSVs alone.
   `response_text` is often fenced in ```json and may have malformed JSON (stray
   quote types, trailing commas from small models). Parse leniently; if a model
   or field breaks, fall back to regex extraction rather than giving up on the row
   (this mirrors `src/common.py`'s `load_json_lenient` philosophy in this repo).

2. **Cross-reference `resolved_status` before trusting anything.** If
   `data/parsed/paper_affiliations.csv` (or an equivalent `outputs_*/tables/paper_bias_summary.csv`
   / `unresolved_papers.csv`) exists for this model/prompt/run, check it first.
   Rows marked `low_confidence` or `not_found` mean the fuzzy OpenAlex match found
   the *nearest* real paper, not the *correct* one — never report `oa_institution`
   or `oa_title` from those rows as ground truth. A `resolved_rate` of 0% for a
   given model/niche is itself the finding (nothing to verify), not a data gap to
   patch over.

3. **Verify every paper in the list against real scholarly knowledge** (use
   WebSearch if available and the claim is uncertain from memory). For each
   paper, classify it as one of:
   - **verified** — title, authors, year, venue, and affiliation-at-the-time all check out.
   - **caveat** — real paper, but a minor genuinely-ambiguous detail (the model
     itself often flags these in `uncertainty_notes` — that's honest hedging, not a defect).
   - **misattributed / fabricated title** — the most insidious failure mode seen
     in this project: a **real author, real venue, real year, and correct
     affiliation**, but an **invented title** grafted on. This survives a casual
     fact-check because every field except the one needing a primary-source
     lookup is correct. Don't stop verifying at "the author and venue are real."
   - **fabricated outright** — placeholder-pattern names (repeating surnames
     across "different" authors like Smith/Brown/Green/White), invented venues,
     nonsense affiliations. Common from small (<7B) models; treat the whole
     response as a hallucination-floor data point, not a peer sample.

4. **Compute recency stats relative to the current date, not the training
   cutoff.** Mean/median year, % published in the last decade, most recent year
   cited. Critically: **compare against another niche/domain in the same
   dataset if one exists** (e.g. this project runs both an `SE_*` and `VIS_*`
   track). A recency gap that shows up in one domain but not the other is much
   stronger evidence of domain-specific bias than a recency gap alone — it rules
   out "citation-accrual lag" (which would depress recent papers everywhere) as
   the explanation.

5. **Give the PhD-level verdict explicitly.** State whether the pattern is
   defensible (real methodological reason) or a bias artifact, and say why in
   one sentence citing the cross-domain contrast or the fabrication mechanics —
   don't just describe the numbers and stop short of a judgment.

6. **Delegate the heavy lifting to subagents when there's more than one file or
   more than one axis to check.** The pattern that works well: one subagent does
   deep paper-by-paper verification of a single sample response; a second
   subagent aggregates recency/resolution stats across every model × niche ×
   run in the corpus (reading raw JSON directly if the relevant `outputs/tables/*.csv`
   is empty or stale — check for that before trusting a summary table exists).
   Run them in parallel and in the foreground when their output feeds a synthesis
   step that follows immediately (e.g. building a report/artifact).

7. **If asked for a shareable summary**, build it as an Artifact — load
   `artifact-design` and `dataviz` first. Lead with the cross-domain contrast
   chart (it's the strongest single piece of evidence), follow with the
   resolution-rate chart, then the paper-by-paper case-study table with
   good/warning/critical status pills, then institutional-bias explicit-vs-implicit
   numbers, then the PhD verdict as a callout, then a methodology/limitations
   footer naming exact sample sizes — small n (3-5 runs) per cell is common in
   this project and should be stated, not hidden.

## Things not to do

- Don't take `claimed_affiliation` as ground truth for institutional-bias
  scoring — it's the model's own claim, which is what's under test. Ground
  truth is OpenAlex (or another external source), and only on rows that
  actually resolved with confidence.
- Don't compare a fabrication-heavy small model's numbers against frontier
  models on equal footing in a headline stat — frame it as the floor.
- Don't average away a single-cell inversion (e.g. one model/niche pair that
  contradicts the overall trend) into a summary statistic — name it.
