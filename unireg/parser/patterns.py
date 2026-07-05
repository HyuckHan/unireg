"""Regex patterns for Korean regulation structure."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class ChapterHeading:
    number: str
    title: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionHeading:
    number: str
    title: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ArticleHeading:
    article_number: str
    id_fragment: str
    title: str | None
    body_text: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ClauseSegment:
    clause_number: str | None
    text: str
    raw_text: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ItemSegment:
    item_number: str | None
    text: str
    raw_text: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SubItemSegment:
    sub_item_number: str
    text: str
    raw_text: str


_CLAUSE_MARKERS = {
    "①": "1",
    "②": "2",
    "③": "3",
    "④": "4",
    "⑤": "5",
    "⑥": "6",
    "⑦": "7",
    "⑧": "8",
    "⑨": "9",
    "⑩": "10",
    "⑪": "11",
    "⑫": "12",
    "⑬": "13",
    "⑭": "14",
    "⑮": "15",
    "⑯": "16",
    "⑰": "17",
    "⑱": "18",
    "⑲": "19",
    "⑳": "20",
}
_CLAUSE_MARKER_RE = re.compile(f"[{''.join(_CLAUSE_MARKERS)}]")
_ITEM_MARKER_RE = re.compile(r"(?<![\d.])(?P<number>[1-9]\d?)\.\s*")
_SUB_ITEM_MARKER_RE = re.compile(r"(?<![가-힣A-Za-z0-9.])(?P<number>[가-하])\.\s*")
_CHAPTER_RE = re.compile(r"^제\s*(?P<number>\d+)\s*장\s*(?P<title>.*)$")
_SECTION_RE = re.compile(r"^제\s*(?P<number>\d+)\s*절\s*(?P<title>.*)$")
_ARTICLE_RE = re.compile(
    r"^제\s*(?P<base>\d+)\s*조"
    r"(?:\s*의\s*(?P<sub>\d+))?"
    r"\s*(?:\((?P<title>[^)]*)\))?"
    r"\s*(?P<body>.*)$"
)


def parse_chapter_heading(text: str) -> ChapterHeading | None:
    match = _CHAPTER_RE.match(text)
    if match is None:
        return None

    title = _empty_to_none(match.group("title"))
    return ChapterHeading(number=match.group("number"), title=title)


def parse_section_heading(text: str) -> SectionHeading | None:
    match = _SECTION_RE.match(text)
    if match is None:
        return None

    title = _empty_to_none(match.group("title"))
    return SectionHeading(number=match.group("number"), title=title)


def parse_article_heading(text: str) -> ArticleHeading | None:
    match = _ARTICLE_RE.match(text)
    if match is None:
        return None

    base = match.group("base")
    sub = match.group("sub")
    title = _empty_to_none(match.group("title"))
    body_text = _empty_to_none(match.group("body"))

    article_number = f"제{base}조"
    id_fragment = base
    if sub is not None:
        article_number = f"{article_number}의{sub}"
        id_fragment = f"{base}-{sub}"

    return ArticleHeading(
        article_number=article_number,
        id_fragment=id_fragment,
        title=title,
        body_text=body_text,
    )


def parse_clause_segments(text: str) -> list[ClauseSegment]:
    matches = list(_CLAUSE_MARKER_RE.finditer(text))
    if not matches:
        stripped = text.strip()
        return (
            [ClauseSegment(clause_number=None, text=stripped, raw_text=stripped)]
            if stripped
            else []
        )

    segments: list[ClauseSegment] = []
    first_match = matches[0]
    prefix = text[: first_match.start()].strip()
    if prefix:
        segments.append(ClauseSegment(clause_number=None, text=prefix, raw_text=prefix))

    for index, match in enumerate(matches):
        next_start = (
            matches[index + 1].start() if index + 1 < len(matches) else len(text)
        )
        raw_text = text[match.start() : next_start].strip()
        marker = match.group(0)
        body = raw_text[len(marker) :].strip()
        segments.append(
            ClauseSegment(
                clause_number=_CLAUSE_MARKERS[marker],
                text=body,
                raw_text=raw_text,
            )
        )

    return segments


def parse_item_segments(text: str) -> list[ItemSegment]:
    matches = list(_ITEM_MARKER_RE.finditer(text))
    if not matches:
        return []

    segments: list[ItemSegment] = []
    first_match = matches[0]
    prefix = text[: first_match.start()].strip()
    if prefix:
        segments.append(ItemSegment(item_number=None, text=prefix, raw_text=prefix))

    for index, match in enumerate(matches):
        next_start = (
            matches[index + 1].start() if index + 1 < len(matches) else len(text)
        )
        raw_text = text[match.start() : next_start].strip()
        number = match.group("number")
        body = raw_text[match.end() - match.start() :].strip()
        segments.append(ItemSegment(item_number=number, text=body, raw_text=raw_text))

    return segments


def parse_sub_item_segments(text: str) -> list[SubItemSegment]:
    matches = list(_SUB_ITEM_MARKER_RE.finditer(text))
    if not matches:
        return []

    segments: list[SubItemSegment] = []
    for index, match in enumerate(matches):
        next_start = (
            matches[index + 1].start() if index + 1 < len(matches) else len(text)
        )
        raw_text = text[match.start() : next_start].strip()
        number = match.group("number")
        body = raw_text[match.end() - match.start() :].strip()
        segments.append(
            SubItemSegment(
                sub_item_number=number,
                text=body,
                raw_text=raw_text,
            )
        )

    return segments


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None
