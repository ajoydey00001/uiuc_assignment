# Executive Summary

This project studies how AI models answer questions about AI-assisted software engineering, with attention to two behaviors: how they rank research venues and which sources they cite.

The repository now contains a reproducible first version of the study pipeline:

- a 30-venue conference baseline spanning software engineering, programming languages, formal methods, AI, data mining, HCI, and lower-rank software engineering venues;
- ten structured prompts that vary depth and source pressure;
- scripts for Gemini API collection and manual collection from free web interfaces;
- parsers for rankings, citations, and URLs;
- ranking and source-analysis scripts; and
- tables and figures that can be regenerated from raw responses.

The final run contains 30 raw API response files from OpenRouter free routes: Gemma 4 31B, GPT-OSS 120B, and Nemotron 3 Ultra. OpenRouter rate limits prevented a perfectly balanced 10-prompt run for every model, so repeated Nemotron runs were added for stability analysis.

The parser extracted 205 ranking rows, 86 citation rows, and 86 source-link rows. Link validation marked 72 links valid, 12 dead, and 2 unverifiable.

Main observable pattern: the ranking prompts usually placed ICSE, FSE, ASE, ISSTA, and MSR near the top, while the source-heavy prompts cited many arXiv and repository/documentation links. The low-rank prompt helped include specialized venues such as ICPC, ICST, COMPSAC, and SAC.
