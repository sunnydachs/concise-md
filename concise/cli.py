"""Command-line interface for concise-md."""

from __future__ import annotations

import argparse
import json
import sys

from .core import concise as condense
from .core import extract_code, extract_conclusion, extract_verify, parse_sections
def _read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as stream:
        return stream.read()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Condense verbose Markdown into a learning-friendly format.")
    parser.add_argument("file", help="Markdown file, or '-' for stdin")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--language", choices=("auto", "en", "ja"), default="auto", help="output language")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    text = _read_input(args.file)
    output = condense(text, language=args.language)
    if args.json:
        sections = parse_sections(text)
        payload = {
            "input_lines": len(text.splitlines()),
            "output_lines": len(output.splitlines()),
            "conclusion": extract_conclusion(sections),
            "code_blocks": extract_code(sections),
            "verify": extract_verify(sections, bool(extract_code(sections)), args.language),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(output, end="" if output.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
