"""Citation matching helpers for grounded QA."""

from __future__ import annotations

from pathlib import Path

from unireg.benchmark.models import GoldCitation
from unireg.qa.models import EvidenceItem


def citation_matches(expected: GoldCitation, actual: GoldCitation) -> bool:
    """Return whether `actual` satisfies the expected citation anchor."""

    if expected.node_id is not None:
        return actual.node_id == expected.node_id

    checks = [
        (expected.regulation_title, actual.regulation_title, _normalize_plain),
        (expected.source_file, actual.source_file, _normalize_path),
        (expected.article, actual.article, _normalize_plain),
        (expected.clause, actual.clause, _normalized_clause),
        (expected.item, actual.item, _normalized_item),
        (expected.sub_item, actual.sub_item, _normalized_sub_item),
    ]
    for expected_value, actual_value, normalizer in checks:
        if expected_value is None:
            continue
        if actual_value is None:
            return False
        if normalizer(expected_value) != normalizer(actual_value):
            return False
    return True


def citation_is_supported(
    citation: GoldCitation,
    evidence: list[EvidenceItem],
) -> bool:
    """Return whether a citation is grounded in the provided evidence."""

    return any(citation_matches(citation, item.citation) for item in evidence)


def citation_matches_any(
    citation: GoldCitation,
    expected: list[GoldCitation],
) -> bool:
    return any(citation_matches(gold, citation) for gold in expected)


def dedupe_citations(citations: list[GoldCitation]) -> list[GoldCitation]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[GoldCitation] = []
    for citation in citations:
        key = citation_key(citation)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped


def citation_key(citation: GoldCitation) -> tuple[str, ...]:
    if citation.node_id is not None:
        return ("node", citation.node_id)
    return (
        "legal",
        citation.regulation_title or "",
        citation.article or "",
        _normalized_clause(citation.clause) if citation.clause else "",
        _normalized_item(citation.item) if citation.item else "",
        _normalized_sub_item(citation.sub_item) if citation.sub_item else "",
        _normalize_path(citation.source_file) if citation.source_file else "",
    )


def _normalize_plain(value: str) -> str:
    return value.strip()


def _normalize_path(value: str) -> str:
    return str(Path(value).resolve())


def _normalized_clause(value: str) -> str:
    if value.startswith("제") and value.endswith("항"):
        return value
    return f"제{value}항"


def _normalized_item(value: str) -> str:
    if value.startswith("제") and value.endswith("호"):
        return value
    return f"제{value}호"


def _normalized_sub_item(value: str) -> str:
    if value.endswith("목"):
        return value
    return f"{value}목"
