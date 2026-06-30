# Executive Summary

This project studies how AI models answer questions about AI-assisted software engineering, with attention to two behaviors: how they rank research venues and which sources they cite.

The repository now contains a reproducible first version of the study pipeline:

- a 29-venue conference baseline spanning software engineering, programming languages, formal methods, AI, data mining, systems, and HCI;
- eight structured prompts that vary depth and source pressure;
- scripts for Gemini API collection and manual collection from free web interfaces;
- parsers for rankings, citations, and URLs;
- ranking and source-analysis scripts; and
- tables and figures that can be regenerated from raw responses.

The included demo responses are only pipeline tests. Real conclusions should be written after collecting actual Gemini, Copilot Chat, ChatGPT/Claude/free web model responses and rerunning the analysis.

Expected final findings should discuss:

1. Which venues models rank highest for AI-for-software-engineering.
2. Whether those rankings align with the conference baseline.
3. Whether models prefer academic papers, arXiv, company blogs, documentation, GitHub repositories, or general pages.
4. Whether source choices change between shallow and deeper prompts.
5. Which citations or links appear hallucinated, ambiguous, or unverifiable.

