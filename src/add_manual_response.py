from __future__ import annotations

import argparse
from pathlib import Path

from common import ROOT, read_prompt_text
from query_models import DEFAULT_SYSTEM_PROMPT, write_record


def main() -> None:
    parser = argparse.ArgumentParser(description="Save a manually collected chat transcript as raw model data.")
    parser.add_argument("--provider", required=True, help="Example: openai_web, claude_web, copilot_chat")
    parser.add_argument("--model", required=True, help="Example: ChatGPT free, Claude Sonnet web, GitHub Copilot Chat")
    parser.add_argument("--prompt-id", required=True)
    parser.add_argument("--run-id", default="manual01")
    parser.add_argument("--response-file", required=True, help="Plain text file containing the model answer.")
    parser.add_argument("--prompt-set", default="data/prompts/prompt_set_v1.md")
    parser.add_argument("--output", default="data/raw_responses")
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args()

    response_text = Path(args.response_file).read_text(encoding="utf-8")
    user_prompt = read_prompt_text(ROOT / args.prompt_set, args.prompt_id)
    path = write_record(
        ROOT / args.output,
        args.provider,
        args.model,
        args.prompt_id,
        args.run_id,
        DEFAULT_SYSTEM_PROMPT,
        user_prompt,
        args.temperature,
        response_text,
        {"manual_collection": True, "response_file": args.response_file},
    )
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

