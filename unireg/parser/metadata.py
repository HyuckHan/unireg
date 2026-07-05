"""Regulation metadata normalization."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from unireg.models import CleanLine


@dataclass(frozen=True, slots=True)
class MetadataWarning:
    """Non-fatal metadata quality warning."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class RegulationMetadata:
    """Normalized regulation metadata derived from source text."""

    title: str
    raw_title: str
    title_candidates: list[str]
    institution: str | None
    regulation_code: str | None
    warnings: list[MetadataWarning]


_STRUCTURE_MARKER_RE = re.compile(r"제\s*\d+\s*(?:장|조)|부\s*칙")
_INSTITUTION_RE = re.compile(
    r"(?P<institution>[가-힣]+(?:여자대학교|교육대학교|전문대학교|"
    r"전문대학|대학원대학교|대학교|과학기술원))"
)
_REGULATION_CODE_RE = re.compile(
    r"(?:[\[【(<◀]\s*)?"
    r"(?P<code>\d+(?:\s*-\s*\d+)+(?:\s*[~\uFF5E]\s*\d+)?)"
    r"(?:\s*[\]】)>▶])?"
)
_EFFECTIVE_DATE_RE = re.compile(r"\[\s*시행[^\]]*\]")
_BRACKETED_AMENDMENT_RE = re.compile(
    r"\[\s*\d{4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}\.?\s*,?\s*"
    r"(?:일부개정|전부개정|개정|제정)[^\]]*\]"
)
_PARENTHESIZED_REVISION_RE = re.compile(r"\(\s*\d{8}\s*(?:개정|제정)\s*\)")
_TRAILING_REVISION_RE = re.compile(
    r"(?:제정|개정)\s*\d{4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}\.?.*$"
)
_CATALOG_RE = re.compile(r"규정\s*집|제\s*\d+\s*편")
_STANDALONE_REGULATION_RE = re.compile(r"(?<![가-힣])규정(?![가-힣])")
_SPACE_RE = re.compile(r"\s+")


class RegulationMetadataNormalizer:
    """Normalize title, institution, and regulation-code metadata."""

    def normalize(
        self,
        *,
        source_file: str,
        title_line: CleanLine | None,
        lines: list[CleanLine],
    ) -> RegulationMetadata:
        raw_title = (
            title_line.text.strip()
            if title_line is not None and title_line.text.strip()
            else Path(source_file).stem
        )
        institution = _extract_institution(
            texts=[raw_title, *_first_line_texts(lines), Path(source_file).stem],
            source_file=source_file,
        )
        regulation_code = _extract_regulation_code(
            raw_title
        ) or _extract_regulation_code(Path(source_file).stem)

        title_candidates = _title_candidates(
            raw_title=raw_title,
            institution=institution,
        )
        title = title_candidates[-1] if title_candidates else _fallback_title(raw_title)
        warnings = _metadata_warnings(
            raw_title=raw_title,
            title=title,
            regulation_code=regulation_code,
        )

        return RegulationMetadata(
            title=title,
            raw_title=raw_title,
            title_candidates=title_candidates,
            institution=institution,
            regulation_code=regulation_code,
            warnings=warnings,
        )


def _first_line_texts(lines: list[CleanLine]) -> list[str]:
    return [line.text for line in lines[:10] if line.text]


def _extract_institution(*, texts: list[str], source_file: str) -> str | None:
    path = Path(source_file)
    candidates = [*texts, path.parent.name]
    for text in candidates:
        normalized = _normalize_spaces(text)
        match = _INSTITUTION_RE.search(normalized)
        if match is not None:
            return match.group("institution")
    return None


def _extract_regulation_code(text: str) -> str | None:
    match = _REGULATION_CODE_RE.search(text)
    if match is None:
        return None
    return _normalize_code(match.group("code"))


def _normalize_code(code: str) -> str:
    return re.sub(r"\s+", "", code).replace("\uff5e", "~")


def _title_candidates(*, raw_title: str, institution: str | None) -> list[str]:
    candidates = [
        raw_title,
        _strip_structural_tail(raw_title),
        _strip_inline_metadata(raw_title),
        _normalize_title(raw_title, institution=institution),
    ]
    return _dedupe_preserving_order(
        candidate for candidate in candidates if candidate.strip()
    )


def _strip_structural_tail(text: str) -> str:
    match = _STRUCTURE_MARKER_RE.search(text)
    if match is None:
        return _normalize_spaces(text)
    return _normalize_spaces(text[: match.start()])


def _strip_inline_metadata(text: str) -> str:
    cleaned = _strip_structural_tail(text)
    cleaned = _EFFECTIVE_DATE_RE.sub(" ", cleaned)
    cleaned = _BRACKETED_AMENDMENT_RE.sub(" ", cleaned)
    cleaned = _PARENTHESIZED_REVISION_RE.sub(" ", cleaned)
    cleaned = _TRAILING_REVISION_RE.sub(" ", cleaned)
    cleaned = _REGULATION_CODE_RE.sub(" ", cleaned)
    cleaned = cleaned.replace("◀", " ").replace("▶", " ")
    cleaned = cleaned.replace("【", " ").replace("】", " ")
    cleaned = cleaned.replace("[", " ").replace("]", " ")
    return _normalize_known_title_terms(_normalize_spaces(cleaned))


def _normalize_title(text: str, *, institution: str | None) -> str:
    cleaned = _strip_inline_metadata(text)
    cleaned = _CATALOG_RE.sub(" ", cleaned)
    if institution is not None:
        cleaned = cleaned.replace(institution, " ")
        if "학칙" in cleaned:
            cleaned = _STANDALONE_REGULATION_RE.sub(" ", cleaned)
    cleaned = _normalize_known_title_terms(_normalize_spaces(cleaned))
    cleaned = _dedupe_repeated_words(cleaned)
    return cleaned or _fallback_title(text)


def _normalize_known_title_terms(text: str) -> str:
    text = re.sub(r"학\s*칙", "학칙", text)
    text = re.sub(r"시행\s*세칙", "시행세칙", text)
    text = re.sub(r"학사\s*운영\s*규정", "학사운영규정", text)
    text = re.sub(r"학사\s*관리\s*규정", "학사관리규정", text)
    return _normalize_spaces(text)


def _dedupe_repeated_words(text: str) -> str:
    parts = text.split()
    deduped: list[str] = []
    for part in parts:
        if not deduped or deduped[-1] != part:
            deduped.append(part)
    if len(deduped) == 2 and deduped[0] == deduped[1]:
        return deduped[0]
    return " ".join(deduped)


def _fallback_title(text: str) -> str:
    cleaned = _normalize_known_title_terms(_normalize_spaces(text))
    return cleaned or "Untitled regulation"


def _metadata_warnings(
    *,
    raw_title: str,
    title: str,
    regulation_code: str | None,
) -> list[MetadataWarning]:
    warnings: list[MetadataWarning] = []
    normalized_raw = _normalize_spaces(raw_title)
    if len(normalized_raw) > 60:
        warnings.append(
            MetadataWarning(
                code="metadata_title_long",
                message="Raw title candidate is unusually long.",
            )
        )
    if _STRUCTURE_MARKER_RE.search(normalized_raw) is not None:
        warnings.append(
            MetadataWarning(
                code="metadata_title_contains_structure",
                message="Raw title candidate contains a legal structure marker.",
            )
        )
    if _has_inline_metadata(normalized_raw):
        warnings.append(
            MetadataWarning(
                code="metadata_title_contains_inline_metadata",
                message="Raw title candidate contains inline metadata.",
            )
        )
    if regulation_code is not None:
        warnings.append(
            MetadataWarning(
                code="metadata_title_code_extracted",
                message="Regulation code was extracted from title metadata.",
            )
        )
    if title != normalized_raw:
        warnings.append(
            MetadataWarning(
                code="metadata_title_normalized",
                message="Regulation title was normalized from the raw candidate.",
            )
        )
    return _dedupe_warnings(warnings)


def _has_inline_metadata(text: str) -> bool:
    return (
        _EFFECTIVE_DATE_RE.search(text) is not None
        or _BRACKETED_AMENDMENT_RE.search(text) is not None
        or _PARENTHESIZED_REVISION_RE.search(text) is not None
        or _TRAILING_REVISION_RE.search(text) is not None
    )


def _dedupe_warnings(warnings: list[MetadataWarning]) -> list[MetadataWarning]:
    seen: set[str] = set()
    deduped: list[MetadataWarning] = []
    for warning in warnings:
        if warning.code in seen:
            continue
        seen.add(warning.code)
        deduped.append(warning)
    return deduped


def _dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = _normalize_spaces(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _normalize_spaces(text: str) -> str:
    return _SPACE_RE.sub(" ", text).strip()
