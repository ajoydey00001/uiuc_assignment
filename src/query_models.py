from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from common import ROOT, read_prompt_metadata, read_prompt_text, safe_model_name


# Deliberately a neutral assistant persona: it must not mention bias, source
# attribution, or that this is a study -- telling the model what is being measured
# changes its behavior (demand characteristics).
DEFAULT_SYSTEM_PROMPT = (
    "You are a knowledgeable research assistant. Answer from your own knowledge. "
    "Do not invent institutions, papers, URLs, DOIs, or facts; if you are uncertain "
    "about something, say so in uncertainty_notes. Return valid JSON exactly in the "
    "format requested."
)

# The closed-book prompt above tells the model to answer from its own knowledge,
# which actively suppresses the behaviour the web-search arm is trying to measure.
# This variant permits retrieval while keeping the same anti-fabrication and
# uncertainty-reporting clauses, so the only deliberate difference between arms is
# whether the model may look things up.
WEB_SEARCH_SYSTEM_PROMPT = (
    "You are a knowledgeable research assistant with access to web search. Search the "
    "web to verify the papers you list and the institutional affiliation of each first "
    "author at the time of publication. Do not invent institutions, papers, URLs, DOIs, "
    "or facts; if you are uncertain about something after searching, say so in "
    "uncertainty_notes. Return valid JSON exactly in the format requested."
)


def write_record(
    output_root: Path,
    provider: str,
    model: str,
    prompt_id: str,
    run_id: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    response_text: str,
    params: dict[str, Any],
) -> Path:
    model_dir = output_root / safe_model_name(model)
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / f"{prompt_id}_{run_id}.json"
    payload = {
        "provider": provider,
        "model": model,
        "prompt_id": prompt_id,
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "temperature": temperature,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "api_parameters": params,
        "response_text": response_text,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def query_gemini(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float | None,
    web_search: bool = False,
) -> tuple[str, dict[str, Any]]:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise SystemExit("Install dependencies first: pip install -r requirements.txt") from exc

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY or GOOGLE_API_KEY in your environment or .env file.")

    client = genai.Client(api_key=api_key)
    config_kwargs: dict[str, Any] = {"system_instruction": system_prompt}
    if web_search:
        # Search grounding and JSON mode are mutually exclusive on pre-Gemini-3 models
        # (HTTP 400 "Search Grounding can't be used with JSON/YAML/XML mode"), and SDK
        # support is inconsistent even where the API allows it. Omitting the mime type
        # is safe: common.load_json_lenient() strips ```json fences and salvages
        # partial JSON, which is the same path every non-Gemini provider already uses.
        config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    else:
        config_kwargs["response_mime_type"] = "application/json"
    if temperature is not None:
        config_kwargs["temperature"] = temperature
    config = types.GenerateContentConfig(**config_kwargs)
    response = client.models.generate_content(model=model, contents=user_prompt, config=config)

    params: dict[str, Any] = {
        "temperature": temperature if temperature is not None else "provider_default",
        "response_mime_type": None if web_search else "application/json",
        "web_search_enabled": web_search,
    }
    if web_search:
        # Provenance: proof the tool actually fired, plus which sources were consulted.
        # An empty/absent grounding_metadata means the model answered closed-book
        # despite the tool being offered -- that invalidates the run, so record it.
        params["web_search"] = _gemini_grounding_provenance(response)
    return response.text or "", params


def _gemini_grounding_provenance(response: Any) -> dict[str, Any]:
    """Pull search queries and retrieved source URLs out of a grounded Gemini response."""
    queries: list[str] = []
    sources: list[dict[str, str]] = []
    for candidate in getattr(response, "candidates", None) or []:
        meta = getattr(candidate, "grounding_metadata", None)
        if meta is None:
            continue
        queries.extend(getattr(meta, "web_search_queries", None) or [])
        for chunk in getattr(meta, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            if web is not None:
                sources.append({"title": getattr(web, "title", "") or "", "uri": getattr(web, "uri", "") or ""})
    return {"queries": queries, "sources": sources, "search_count": len(queries)}


def query_anthropic(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    web_search: bool = False,
    max_searches: int = 5,
) -> tuple[str, dict[str, Any]]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY in your environment or .env file.")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")

    url = f"{base_url.rstrip('/')}/messages"
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if web_search:
        # Server-side tool: Anthropic runs the searches and feeds results back to the
        # model within the same request, so no client-side tool loop is needed.
        payload["tools"] = [{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": max_searches,
        }]
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    response = requests.post(url, headers=headers, json=payload, timeout=300 if web_search else 180)
    if response.status_code >= 400:
        raise RuntimeError(f"anthropic request failed for {model}: HTTP {response.status_code} {response.text[:500]}")
    data = response.json()
    blocks = data.get("content") or []
    # A grounded response interleaves server_tool_use / web_search_tool_result blocks
    # with the text blocks; joining only the text blocks yields the answer unchanged.
    text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
    params = {
        "temperature": temperature if temperature is not None else "provider_default",
        "max_tokens": max_tokens,
        "base_url": base_url,
        "usage": data.get("usage", {}),
        "stop_reason": data.get("stop_reason"),
        "web_search_enabled": web_search,
    }
    if web_search:
        params["web_search"] = _anthropic_search_provenance(blocks)
    return text, params


def _anthropic_search_provenance(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Pull issued queries and returned source URLs out of a grounded Anthropic response."""
    queries: list[str] = []
    sources: list[dict[str, str]] = []
    for block in blocks:
        if block.get("type") == "server_tool_use" and block.get("name") == "web_search":
            query = (block.get("input") or {}).get("query")
            if query:
                queries.append(query)
        elif block.get("type") == "web_search_tool_result":
            content = block.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("url"):
                        sources.append({"title": item.get("title", "") or "", "uri": item["url"]})
    return {"queries": queries, "sources": sources, "search_count": len(queries)}


def query_openai_compatible(
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> tuple[str, dict[str, Any]]:
    if provider == "nvidia":
        api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("nvidia_api_key")
        base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    elif provider == "openrouter":
        if model.startswith("google/"):
            model_key = os.getenv("GEMINI_API_KEY")
        elif model.startswith("openai/"):
            model_key = os.getenv("OPENAI_API_KEY")
        elif model.startswith("nvidia/"):
            model_key = os.getenv("nvidia_api_key") or os.getenv("NVIDIA_API_KEY")
        else:
            model_key = None
        api_key = model_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("nvidia_api_key")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    elif provider == "ollama":
        # Ollama serves an OpenAI-compatible API locally and ignores the API key,
        # but the guard below requires a non-empty value.
        api_key = os.getenv("OLLAMA_API_KEY", "ollama-local")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    elif provider == "litellm":
        # LiteLLM proxy also serves an OpenAI-compatible API; it routes to whatever
        # backend (e.g. Anthropic) is configured on the proxy side. Point
        # LITELLM_BASE_URL/LITELLM_API_KEY at your running proxy instance.
        api_key = os.getenv("LITELLM_API_KEY")
        base_url = os.getenv("LITELLM_BASE_URL", "http://localhost:4000/v1")
    else:
        raise ValueError(provider)
    if not api_key:
        raise SystemExit(f"Missing API key for provider {provider}")

    url = f"{base_url.rstrip('/')}/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost/ai-source-study",
        "X-Title": "AI Source Study",
    }
    response = requests.post(url, headers=headers, json=payload, timeout=180)
    if response.status_code >= 400:
        raise RuntimeError(f"{provider} request failed for {model}: HTTP {response.status_code} {response.text[:500]}")
    data = response.json()
    if "choices" not in data or not data["choices"]:
        raise RuntimeError(f"{provider} returned no choices for {model}: {json.dumps(data)[:500]}")
    text = data["choices"][0]["message"].get("content") or ""
    params = {
        "temperature": temperature if temperature is not None else "provider_default",
        "max_tokens": max_tokens,
        "base_url": base_url,
        "usage": data.get("usage", {}),
        "web_search_enabled": False,
    }
    return text, params


def main() -> None:
    parser = argparse.ArgumentParser(description="Query supported model APIs and save raw responses.")
    parser.add_argument("--prompts", default="data/prompts/prompt_metadata.csv")
    parser.add_argument("--prompt-set", default="data/prompts/prompt_set_v1.md")
    parser.add_argument("--output", default="data/raw_responses")
    parser.add_argument("--provider", choices=["gemini", "nvidia", "openai", "openrouter", "ollama", "anthropic", "litellm"], default="gemini")
    parser.add_argument("--models", default="gemini-1.5-flash")
    parser.add_argument("--prompt-ids", default="all", help="Comma-separated prompt ids or 'all'.")
    parser.add_argument("--run-id", default="run01")
    parser.add_argument(
        "--temperature", type=float, default=None,
        help="Sampling temperature. Omit to use the provider's default (needed for sampled/K-answer collection); pass 0 for deterministic runs.",
    )
    parser.add_argument(
        "--samples", type=int, default=1,
        help="Answers to collect per prompt. With N>1, files are written as <run-id>-s1..-sN; use with default temperature, not 0.",
    )
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between API calls.")
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--system-prompt", default=None, help="Overrides the automatic closed-book / web-search system prompt.")
    parser.add_argument(
        "--web-search",
        action="store_true",
        help="Enable provider-native web search (anthropic, gemini). Changes what is measured: responses become retrieval-grounded rather than closed-book.",
    )
    parser.add_argument("--max-searches", type=int, default=5, help="Max web searches per request (anthropic).")
    args = parser.parse_args()

    load_dotenv()

    # Web search is provider-native; there is no local search backend for ollama and
    # the OpenAI-compatible path needs a pinned *-search-preview model, so silently
    # dropping the flag would produce closed-book data labelled as grounded.
    if args.web_search and args.provider not in {"anthropic", "gemini"}:
        raise SystemExit(
            f"--web-search is not supported for provider '{args.provider}'. "
            "Supported: anthropic (web_search_20250305 tool), gemini (google_search grounding). "
            "Local ollama models have no search backend."
        )
    system_prompt = args.system_prompt or (WEB_SEARCH_SYSTEM_PROMPT if args.web_search else DEFAULT_SYSTEM_PROMPT)

    metadata = read_prompt_metadata(ROOT / args.prompts)
    wanted = {p.strip() for p in args.prompt_ids.split(",")} if args.prompt_ids != "all" else None
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    # With --samples N>1, each sample gets its own run_id suffix (-s1..-sN) so the
    # raw-file naming scheme and parser stay untouched: a sample is just a run.
    run_ids = [args.run_id] if args.samples <= 1 else [f"{args.run_id}-s{k}" for k in range(1, args.samples + 1)]

    for row in metadata:
        prompt_id = row["prompt_id"]
        if wanted and prompt_id not in wanted:
            continue
        user_prompt = read_prompt_text(ROOT / args.prompt_set, prompt_id)
        for model in models:
            for run_id in run_ids:
                last_error: Exception | None = None
                for attempt in range(args.retries + 1):
                    try:
                        if args.provider == "gemini":
                            response_text, params = query_gemini(model, system_prompt, user_prompt, args.temperature, args.web_search)
                        elif args.provider == "anthropic":
                            response_text, params = query_anthropic(
                                model, system_prompt, user_prompt, args.temperature, args.max_tokens,
                                args.web_search, args.max_searches,
                            )
                        elif args.provider in {"nvidia", "openai", "openrouter", "ollama", "litellm"}:
                            response_text, params = query_openai_compatible(args.provider, model, system_prompt, user_prompt, args.temperature, args.max_tokens)
                        else:
                            raise ValueError(args.provider)
                        break
                    except Exception as exc:
                        last_error = exc
                        if attempt < args.retries:
                            time.sleep(max(2.0, args.sleep))
                        else:
                            if not args.continue_on_error:
                                raise
                            response_text = json.dumps({
                                "ranked_items": [],
                                "references": [],
                                "uncertainty_notes": f"API collection failed: {exc}",
                            })
                            params = {
                                "collection_error": str(exc),
                                "temperature": args.temperature,
                                "max_tokens": args.max_tokens,
                                "web_search_enabled": args.web_search,
                            }
                path = write_record(
                    ROOT / args.output,
                    args.provider,
                    model,
                    prompt_id,
                    run_id,
                    system_prompt,
                    user_prompt,
                    args.temperature,
                    response_text,
                    params,
                )
                print(f"wrote {path.relative_to(ROOT)}")
                if args.sleep:
                    time.sleep(args.sleep)


if __name__ == "__main__":
    main()
