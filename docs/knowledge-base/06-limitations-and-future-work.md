# 06 — Limitations and Future Work

From `report/main.tex` ("Threats to Validity") and `report/project_report.md` ("Future Work").

## Threats to validity

**API availability.** The strongest threat. OpenRouter free-route rate limits meant Gemma and GPT-OSS could not be collected for all 10 prompts in the experiment window. Missing responses were never fabricated — the gap is documented, and repeated Nemotron runs were collected instead to at least support a stability check.

**Baseline validity.** CORE and CSRankings are useful comparison signals but measure different things (prestige category vs. area/publication volume). A venue can be specialized and useful even if it isn't top-ranked on either baseline — so "disagreement with baseline" isn't automatically "the model is wrong."

**Parsing validity.** `parse_responses.py` handles structured JSON plus a text-extraction fallback, but model responses are messy in practice. Some venue names or citations may be missed or normalized imperfectly (e.g. acronym variants not covered by `normalize_acronym()`).

**Link validation.** Automated URL validation (`validate_links.py`) can fail for reasons unrelated to hallucination: temporary network problems, redirects the script doesn't follow, bot-blocking, or publisher access restrictions. Manual checking is still necessary for high-stakes claims.

**Model versioning.** Free API routes may swap underlying models or providers over time without notice. Raw responses are stored with timestamps precisely so the *actually observed* data is preserved even if a route's behavior later changes.

## Future work

- Collect balanced runs once free-route rate limits reset, aiming for the original 10-prompts × 3-models design
- Add richer citation verification against Crossref, Semantic Scholar, or OpenAlex (rather than relying only on live HTTP link checks)
- Add more repeated runs per model to support real statistical stability analysis
- Run formal statistical tests for prompt sensitivity (currently qualitative/descriptive)
- Compare API responses against web-interface (chat UI) responses from tools everyday engineers actually use, since API behavior may not match what a practitioner experiences in ChatGPT/Claude/Copilot Chat
