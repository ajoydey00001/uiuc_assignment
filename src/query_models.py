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


DEFAULT_SYSTEM_PROMPT = (
    "You are participating in a research study about how AI models use and "
    "attribute information sources in AI-for-software-engineering questions. "
    "Answer carefully. Do not invent papers, URLs, DOIs, or venue facts. If "
    "uncertain, say so."
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


def query_gemini(model: str, system_prompt: str, user_prompt: str, temperature: float) -> tuple[str, dict[str, Any]]:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise SystemExit("Install dependencies first: pip install -r requirements.txt") from exc

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY or GOOGLE_API_KEY in your environment or .env file.")

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_prompt,
        response_mime_type="application/json",
    )
    response = client.models.generate_content(model=model, contents=user_prompt, config=config)
    params = {"temperature": temperature, "response_mime_type": "application/json"}
    return response.text or "", params


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
    else:
        raise ValueError(provider)
    if not api_key:
        raise SystemExit(f"Missing API key for provider {provider}")

    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
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
        "temperature": temperature,
        "max_tokens": max_tokens,
        "base_url": base_url,
        "usage": data.get("usage", {}),
    }
    return text, params


def main() -> None:
    parser = argparse.ArgumentParser(description="Query supported model APIs and save raw responses.")
    parser.add_argument("--prompts", default="data/prompts/prompt_metadata.csv")
    parser.add_argument("--prompt-set", default="data/prompts/prompt_set_v1.md")
    parser.add_argument("--output", default="data/raw_responses")
    parser.add_argument("--provider", choices=["gemini", "nvidia", "openai", "openrouter"], default="gemini")
    parser.add_argument("--models", default="gemini-1.5-flash")
    parser.add_argument("--prompt-ids", default="all", help="Comma-separated prompt ids or 'all'.")
    parser.add_argument("--run-id", default="run01")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between API calls.")
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    args = parser.parse_args()

    load_dotenv()
    metadata = read_prompt_metadata(ROOT / args.prompts)
    wanted = {p.strip() for p in args.prompt_ids.split(",")} if args.prompt_ids != "all" else None
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    for row in metadata:
        prompt_id = row["prompt_id"]
        if wanted and prompt_id not in wanted:
            continue
        user_prompt = read_prompt_text(ROOT / args.prompt_set, prompt_id)
        for model in models:
            last_error: Exception | None = None
            for attempt in range(args.retries + 1):
                try:
                    if args.provider == "gemini":
                        response_text, params = query_gemini(model, args.system_prompt, user_prompt, args.temperature)
                    elif args.provider in {"nvidia", "openai", "openrouter"}:
                        response_text, params = query_openai_compatible(args.provider, model, args.system_prompt, user_prompt, args.temperature, args.max_tokens)
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
                        params = {"collection_error": str(exc), "temperature": args.temperature, "max_tokens": args.max_tokens}
            path = write_record(
                ROOT / args.output,
                args.provider,
                model,
                prompt_id,
                args.run_id,
                args.system_prompt,
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
