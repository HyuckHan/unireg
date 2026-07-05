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


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None
