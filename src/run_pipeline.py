from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str]) -> None:
    print("+", " ".join(args))
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main() -> None:
    run(["src/parse_responses.py", "--input", "data/raw_responses", "--output", "data/parsed"])
    run(["src/analyze_rankings.py", "--input", "data/parsed/conference_rankings.csv"])
    run(["src/analyze_sources.py", "--links", "data/parsed/source_links.csv", "--citations", "data/parsed/citations.csv"])
    run(["src/visualize_results.py"])


if __name__ == "__main__":
    main()

