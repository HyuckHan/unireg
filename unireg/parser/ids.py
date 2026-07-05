"""Deterministic identifier helpers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

_UNSAFE_ID_CHARS_RE = re.compile(r"[^a-z0-9가-힣._:-]+")
_DUPLICATE_DASH_RE = re.compile(r"-+")


def regulation_id(title: str, source_file: str) -> str:
    stem = _slugify(Path(source_file).stem) or "regulation"
    digest = hashlib.sha1(f"{source_file}\n{title}".encode()).hexdigest()[:10]
    return f"regulation:{stem}:{digest}"


def chapter_id(parent_id: str, number: str) -> str:
    return f"{parent_id}/chapter:{_slugify(number)}"


def section_id(parent_id: str, number: str) -> str:
    return f"{parent_id}/section:{_slugify(number)}"


def article_id(parent_id: str, article_fragment: str) -> str:
    return f"{parent_id}/article:{_slugify(article_fragment)}"


def clause_id(parent_id: str, clause_fragment: str) -> str:
    return f"{parent_id}/clause:{_slugify(clause_fragment)}"


def item_id(parent_id: str, item_fragment: str) -> str:
    return f"{parent_id}/item:{_slugify(item_fragment)}"


def sub_item_id(parent_id: str, sub_item_fragment: str) -> str:
    return f"{parent_id}/sub-item:{_slugify(sub_item_fragment)}"


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = _UNSAFE_ID_CHARS_RE.sub("-", value)
    value = _DUPLICATE_DASH_RE.sub("-", value)
    return value.strip("-")
