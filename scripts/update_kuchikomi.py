#!/usr/bin/env python3
"""
Validate and manage kuchikomi.json content for GitHub Actions.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KUCHIKOMI_PATH = REPO_ROOT / "kuchikomi.json"
PROGRAMS_PATH = REPO_ROOT / "programs.json"
VALID_SENTIMENTS = {"positive", "negative", "mixed"}


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse error in {path}: {exc}") from exc


def normalize_text(text: str) -> str:
    return text.strip().replace("\r\n", "\n")


def find_program_titles() -> set[str]:
    programs = load_json(PROGRAMS_PATH)
    if not isinstance(programs, dict):
        raise ValueError("programs.json must be a JSON object")
    entries = programs.get("programs")
    if not isinstance(entries, list):
        raise ValueError("programs.json must contain a 'programs' array")
    titles = {p["title"] for p in entries if isinstance(p, dict) and "title" in p}
    return titles


def validate_entry(entry: object, program_titles: set[str], index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(entry, dict):
        return [f"entry[{index}] must be an object"]

    title = entry.get("title")
    sentiment = entry.get("sentiment")
    text = entry.get("text")

    if not isinstance(title, str) or not title.strip():
        errors.append(f"entry[{index}].title must be a non-empty string")
    elif title not in program_titles:
        errors.append(f"entry[{index}].title '{title}' is not found in programs.json")

    if sentiment not in VALID_SENTIMENTS:
        errors.append(
            f"entry[{index}].sentiment must be one of {sorted(VALID_SENTIMENTS)}, got {sentiment!r}"
        )

    if not isinstance(text, str) or not text.strip():
        errors.append(f"entry[{index}].text must be a non-empty string")
    else:
        normalized = normalize_text(text)
        if len(normalized) < 20 or len(normalized) > 80:
            errors.append(
                f"entry[{index}].text length should be 20〜80 characters, got {len(normalized)}"
            )


    return errors


def validate_kuchikomi(path: Path, strict_titles: bool = True) -> None:
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError("kuchikomi.json must be a JSON array")

    program_titles = find_program_titles()
    seen_titles: set[str] = set()
    errors: list[str] = []

    for index, entry in enumerate(data):
        entry_errors = validate_entry(entry, program_titles, index)
        errors.extend(entry_errors)
        if isinstance(entry, dict):
            title = entry.get("title")
            if isinstance(title, str) and title.strip():
                if title in seen_titles:
                    errors.append(f"duplicate title found: {title!r}")
                seen_titles.add(title)

    if errors:
        raise ValueError("\n".join(errors))


def format_kuchikomi(path: Path) -> None:
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError("kuchikomi.json must be a JSON array")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate or format kuchikomi.json")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate kuchikomi.json and exit with error on invalid content",
    )
    parser.add_argument(
        "--format",
        action="store_true",
        help="Rewrite kuchikomi.json with canonical JSON formatting",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.validate:
        validate_kuchikomi(KUCHIKOMI_PATH)
        print("✅ kuchikomi.json validation passed")
        return 0

    if args.format:
        format_kuchikomi(KUCHIKOMI_PATH)
        print("✅ kuchikomi.json formatted")
        return 0

    print("Nothing to do. Use --validate or --format.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
