# 05 — Q&A Defense Prep

Likely questions and ready answers, each traceable to a specific section of `report/main.tex`. Read [03-glossary.md](03-glossary.md) first if a term below is unfamiliar.

---

**Q: Why did you use free OpenRouter models instead of paid APIs?**
A: Budget/access constraints of a course project. OpenRouter's free routes gave access to three real, different model families (Gemma 4 31B, GPT-OSS 120B, Nemotron 3 Ultra) without cost. The tradeoff — documented explicitly as a limitation — was rate-limiting, which prevented a perfectly balanced collection.

**Q: Why isn't the dataset a balanced 10-prompts × 3-models matrix?**
A: OpenRouter free-route rate limits: Gemma and GPT-OSS were intermittently throttled, Nemotron was slower but reliable. Rather than fabricate missing responses to fill the matrix, I collected what was actually available (30 real responses: Gemma 7, GPT-OSS 2, Nemotron 10+10+1) and used the repeated Nemotron runs as a small stability check. This is documented as a threat to validity, not hidden.

**Q: What's the difference between CORE and CSRankings, and why use either as a baseline?**
A: CORE assigns venues a prestige *category* (A\*/A/B/C). CSRankings ranks by publication *volume* in an *area*. They measure different things, so neither is absolute ground truth — I use `baseline_rank` (derived pragmatically from both) purely as a comparison instrument to see whether model rankings are *reasonable*, not to grade models against a single "correct" answer.

**Q: How do you know a citation is hallucinated versus just unverifiable?**
A: I don't claim certainty — I use two independent, weaker signals instead of one strong claim. `analyze_sources.py` flags a "hallucination candidate" if a citation has no URL/DOI/arXiv ID, or its title contains hedge words. Separately, `validate_links.py` does a live HTTP check and labels each URL `valid`/`dead_link`/`unverifiable`/`ambiguous`. Both are first-pass filters meant to prioritize manual review — a dead link could be a hallucinated URL, but could also be a redirect, outage, or bot-blocked page.

**Q: Why does arXiv dominate the source links (48 of 86)?**
A: When prompts pressure the model for *exact*, checkable sources, models gravitate toward whatever's easiest to link to reliably — arXiv preprints are open-access, stably URLed, and heavily represented in the models' training data for AI/ML-adjacent topics. Paywalled ACM/IEEE pages are harder for a model to cite confidently with a working link.

**Q: Is there evidence models favor their own company's sources (self-ecosystem bias)?**
A: Only weak evidence in this dataset — some GitHub/GitHub-docs links appear, but no model overwhelmingly cited its own provider's ecosystem. I'm explicit in the report that this is inconclusive with only 3 models and 86 links; a larger, balanced dataset would be needed to make a real claim about RQ4.

**Q: Did you find a recency bias toward LLM-era work?**
A: Partially. Recent LLM/code-generation papers (Codex-style generation, SWE-bench-style benchmarks) appeared often, but older, foundational SE venues (ICSE, FSE, ASE, ISSTA, MSR) still dominated the *ranking* prompts. So there's a recency pull in citations, but it didn't crowd out established venues in rankings.

**Q: Does prompt design actually change model behavior, or is it just the model?**
A: Prompt design clearly matters. The same underlying model gave different answer *shapes* depending on the prompt: shallow ranking prompts (P01) reinforced obvious top venues, while the deliberately source-pressured lower-rank prompt (P09) surfaced specialized venues (ICPC, ICST, COMPSAC, SAC) that P01-style prompts tend to omit. That's direct evidence for RQ6.

**Q: What's the single biggest limitation of this study?**
A: API availability/rate-limiting on free routes — it's the root cause of the unbalanced dataset and is the first item under Threats to Validity. Everything downstream (sample size per model, statistical confidence) is constrained by it.

**Q: Is the study reproducible? How would someone rerun it?**
A: Yes — raw responses are stored immutably with full metadata, and `python src/run_pipeline.py` regenerates every parsed CSV, table, and figure from those raw files in one command. New collection is a separate, explicit step (`src/query_models.py` or `src/add_manual_response.py`) that never overwrites existing raw data.

**Q: What would you change with more time or budget?**
A: Paid/stable API access for a truly balanced 10×3 matrix; richer citation verification against Crossref/Semantic Scholar/OpenAlex instead of just live-link checks; more repeated runs per model for real stability statistics; and a comparison between API responses and web-chat-UI responses (since many practitioners use the chat UI, not the API).

**Q: How do the ranking metrics (Spearman/Kendall/top-5 overlap) actually differ, and why report all three?**
A: Spearman and Kendall both measure rank agreement but weight disagreements differently (Kendall is more robust to a few large swaps); top-5 overlap is a simpler, more intuitive "did the model get the obvious top venues right" measure. Reporting all three avoids over-relying on one metric that might flatter or penalize a model for reasons unrelated to actual ranking quality.
