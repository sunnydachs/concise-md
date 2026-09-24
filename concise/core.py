"""Rule-based Markdown condenser.

The engine is deliberately deterministic and stdlib-only. It preserves code
blocks verbatim while selecting a short conclusion and verification guidance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable


HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
SENTENCE_SPLIT = re.compile(r"(?<=[。.!?])\s+")
JAPANESE_CHARS = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")

CONCLUSION_MARKERS = (
    "tl;dr",
    "in short",
    "bottom line",
    "to summarize",
    "summary:",
    "the standard approach",
    "結論",
    "要するに",
    "まとめ",
    "つまり",
    "標準",
    "標準的",
)
VERIFY_MARKERS = (
    "verify",
    "expect",
    "run it",
    "run the",
    "check",
    "confirm",
    "test",
    "検証",
    "確認",
    "実行",
    "テスト",
    "動作",
)
ANTIPATTERN_MARKERS = ("don't", "do not", "bad", "wrong", "avoid", "しない", "失敗")
MAX_CODE_BLOCKS = 3
MAX_CODE_LINES = 25
SHORT_INPUT_LINES = 10
MAX_SENTENCE_CHARS = 220


@dataclass
class Section:
    """A heading-delimited Markdown section."""

    title: str
    paras: list[str] = field(default_factory=list)
    code: list[str] = field(default_factory=list)


def parse_sections(text: str) -> list[Section]:
    """Split Markdown into sections, preserving fenced code exactly."""

    sections: list[Section] = []
    current = Section("(intro)")
    in_code = False
    code_buf: list[str] = []

    for line in text.splitlines():
        if line.strip().startswith("```"):
            if in_code:
                current.code.append("\n".join(code_buf))
                code_buf = []
            in_code = not in_code
            continue
        if in_code:
            code_buf.append(line)
            continue
        match = HEADING.match(line)
        if match:
            if current.paras or current.code:
                sections.append(current)
            current = Section(match.group(2).strip())
            continue
        if line.strip():
            current.paras.append(line.strip())
        elif current.paras:
            current.paras = [" ".join(current.paras)]

    if in_code and code_buf:
        current.code.append("\n".join(code_buf))
    if current.paras:
        current.paras = [" ".join(current.paras)]
    if current.paras or current.code:
        sections.append(current)
    return sections


def _has_marker(text: str, markers: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in SENTENCE_SPLIT.split(text) if sentence.strip()]


def _clip_sentence(sentence: str) -> str:
    if len(sentence) <= MAX_SENTENCE_CHARS:
        return sentence
    cut = sentence[:MAX_SENTENCE_CHARS]
    for separator in ("。", ". "):
        position = cut.rfind(separator)
        if position > MAX_SENTENCE_CHARS // 2:
            return cut[: position + (1 if separator == "。" else 0)].rstrip()
    return cut.rstrip() + "…"


def _is_japanese(text: str) -> bool:
    prose = "\n".join(line for line in text.splitlines() if not line.strip().startswith("```"))
    chars = [char for char in prose if char.isalpha()]
    return bool(chars) and len(JAPANESE_CHARS.findall(prose)) / len(chars) >= 0.29


def extract_conclusion(sections: Iterable[Section]) -> list[str]:
    """Return a marker sentence, otherwise the first prose sentence."""

    section_list = list(sections)
    for section in section_list:
        for paragraph in section.paras:
            for sentence in _sentences(paragraph):
                if _has_marker(sentence, CONCLUSION_MARKERS):
                    return [_clip_sentence(sentence)]
    if not section_list or not section_list[0].paras:
        return []
    return [_clip_sentence(_sentences(section_list[0].paras[0])[0])]


def extract_verify(sections: Iterable[Section], has_code: bool, language: str) -> list[str]:
    """Prefer a verification heading, then marker sentences, then a default."""

    section_list = list(sections)
    for section in section_list:
        if _has_marker(section.title, VERIFY_MARKERS):
            found = [_clip_sentence(sentence) for sentence in _sentences(" ".join(section.paras))]
            if found:
                return found[:3]
    found: list[str] = []
    for section in section_list:
        for paragraph in section.paras:
            for sentence in _sentences(paragraph):
                if _has_marker(sentence, VERIFY_MARKERS) and sentence not in found:
                    found.append(_clip_sentence(sentence))
                    if len(found) == 3:
                        return found
    if found:
        return found
    if has_code:
        return ["上記コードを実行して出力を確認してください"] if language == "ja" else ["Run the code above and check the output."]
    return ["内容を実際の環境で確認してください"] if language == "ja" else ["Verify the content in your actual environment."]


def _is_antipattern(block: str) -> bool:
    first_line = block.splitlines()[0].lower() if block.splitlines() else ""
    return _has_marker(first_line, ANTIPATTERN_MARKERS)


def extract_code(sections: Iterable[Section]) -> list[str]:
    """Select up to three unique blocks, deferring anti-pattern examples."""

    blocks: list[str] = []
    deferred: list[str] = []
    seen: set[str] = set()
    for section in sections:
        for block in section.code:
            if block in seen:
                continue
            seen.add(block)
            (deferred if _is_antipattern(block) else blocks).append(block)
    ordered = (blocks + deferred)[:MAX_CODE_BLOCKS]
    trimmed: list[str] = []
    for block in ordered:
        lines = block.splitlines()
        if len(lines) > MAX_CODE_LINES:
            dropped = len(lines) - MAX_CODE_LINES
            lines = lines[:MAX_CODE_LINES] + [f"… (省略: {dropped}行)"]
        trimmed.append("\n".join(lines))
    return trimmed


def _prose_lines(text: str) -> int:
    in_code = False
    count = 0
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code and line.strip():
            count += 1
    return count


def _code_count(sections: Iterable[Section]) -> int:
    return sum(len(section.code) for section in sections)


def concise(text: str, language: str = "auto") -> str:
    """Restructure verbose Markdown into conclusion, code, and verification."""

    if not text.strip():
        return "(入力が空です)"
    sections = parse_sections(text)
    prose = _prose_lines(text)
    if prose < SHORT_INPUT_LINES and _code_count(sections) <= 1:
        return text.rstrip() + "\n"
    is_japanese = _is_japanese(text)
    selected_language = language if language != "auto" else ("ja" if is_japanese else "en")
    conclusion = extract_conclusion(sections)
    code_blocks = extract_code(sections)
    verify = extract_verify(sections, bool(code_blocks), selected_language)
    if selected_language == "ja":
        headings = ("## 結論", "## 最小コード", "## 検証方法")
    else:
        headings = ("## Conclusion", "## Minimal code", "## How to verify")
    lines = [headings[0], ""]
    lines += [f"- {item}" for item in conclusion]
    if code_blocks:
        lines += ["", headings[1], ""]
        for block in code_blocks:
            lines += ["```", block, "```", ""]
    lines += [headings[2], ""]
    lines += [f"- {item}" for item in verify]
    return "\n".join(lines) + "\n"


__all__ = [
    "ANTIPATTERN_MARKERS",
    "CONCLUSION_MARKERS",
    "MAX_CODE_BLOCKS",
    "MAX_CODE_LINES",
    "SHORT_INPUT_LINES",
    "Section",
    "VERIFY_MARKERS",
    "concise",
    "extract_code",
    "extract_conclusion",
    "extract_verify",
    "parse_sections",
]
