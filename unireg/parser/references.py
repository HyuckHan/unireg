"""Reference and incompleteness enrichment."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from unireg.models import (
    Article,
    Clause,
    IncompletenessFlag,
    IncompletenessType,
    Item,
    Reference,
    ReferenceStatus,
    ReferenceType,
    Regulation,
    SourceSpan,
)
from unireg.parser.ids import incompleteness_flag_id, reference_id
from unireg.parser.patterns import parse_item_segments

_SENTENCE_RE = re.compile(r"[^.\n。!?]+[.\n。!?]?")


@dataclass(frozen=True, slots=True, kw_only=True)
class _ReferenceRule:
    pattern: re.Pattern[str]
    reference_type: ReferenceType
    status: ReferenceStatus
    flag_type: IncompletenessType
    target_name: str | None = None
    target_type: str | None = None
    required_document_name: str | None = None
    missing_source: str | None = None
    confidence: float = 0.9
    note: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class _ReferenceMatch:
    raw_text: str
    rule: _ReferenceRule


@dataclass(frozen=True, slots=True, kw_only=True)
class _TextNode:
    id: str
    text: str
    source_span: SourceSpan | None
    references: list[Reference]
    incompleteness_flags: list[IncompletenessFlag]


_RULES = [
    _ReferenceRule(
        pattern=re.compile(r"시행\s*세칙(?:에|으로)?\s*(?:따른다|정한다)"),
        reference_type=ReferenceType.MISSING_INTERNAL_RULE,
        status=ReferenceStatus.MISSING,
        flag_type=IncompletenessType.REQUIRES_MISSING_REGULATION,
        target_name="시행세칙",
        target_type="regulation",
        required_document_name="시행세칙",
        missing_source="시행세칙",
        confidence=0.95,
    ),
    _ReferenceRule(
        pattern=re.compile(r"별도\s*(?:의\s*)?규정(?:에)?\s*따른다"),
        reference_type=ReferenceType.MISSING_INTERNAL_RULE,
        status=ReferenceStatus.MISSING,
        flag_type=IncompletenessType.REQUIRES_MISSING_REGULATION,
        target_name="별도 규정",
        target_type="regulation",
        required_document_name="별도 규정",
        missing_source="별도 규정",
        confidence=0.9,
    ),
    _ReferenceRule(
        pattern=re.compile(r"총장(?:이|은|가)?\s*따로\s*정한다"),
        reference_type=ReferenceType.ADMINISTRATIVE_DISCRETION,
        status=ReferenceStatus.UNRESOLVED,
        flag_type=IncompletenessType.ADMINISTRATIVE_DISCRETION,
        target_name="총장",
        target_type="authority",
        confidence=0.95,
        note="Delegated to administrative discretion.",
    ),
    _ReferenceRule(
        pattern=re.compile(r"세부\s*사항(?:은|는)?[^.\n。!?]*따로\s*정한다"),
        reference_type=ReferenceType.IMPLICIT_REFERENCE,
        status=ReferenceStatus.UNRESOLVED,
        flag_type=IncompletenessType.REQUIRES_MISSING_REGULATION,
        confidence=0.85,
        note="References an unspecified separate rule or decision.",
    ),
]


class ReferenceIncompletenessEnricher:
    """Attach unresolved references and incompleteness flags to legal nodes."""

    def enrich(self, regulation: Regulation) -> Regulation:
        for node in _iter_text_nodes(regulation):
            matches = list(_detect_references(node.text))
            existing = {
                (reference.raw_text, reference.reference_type)
                for reference in node.references
            }
            for match in matches:
                key = (match.raw_text, match.rule.reference_type)
                if key in existing:
                    continue
                offset = len(node.references) + 1
                node.references.append(_create_reference(node, match, offset))
                node.incompleteness_flags.append(
                    _create_incompleteness_flag(node, match, offset)
                )
                existing.add(key)
        return regulation


def _iter_text_nodes(regulation: Regulation) -> Iterable[_TextNode]:
    for article in regulation.all_articles():
        if article.clauses:
            for clause in article.clauses:
                yield from _iter_clause_nodes(clause)
        elif article.text:
            yield _article_node(article)


def _iter_clause_nodes(clause: Clause) -> Iterable[_TextNode]:
    if clause.items:
        prefix = _clause_prefix(clause.text)
        if prefix:
            yield _TextNode(
                id=clause.id,
                text=prefix,
                source_span=clause.source_span,
                references=clause.references,
                incompleteness_flags=clause.incompleteness_flags,
            )
        for item in clause.items:
            yield from _iter_item_nodes(item)
        return

    if clause.text:
        yield _TextNode(
            id=clause.id,
            text=clause.text,
            source_span=clause.source_span,
            references=clause.references,
            incompleteness_flags=clause.incompleteness_flags,
        )


def _iter_item_nodes(item: Item) -> Iterable[_TextNode]:
    if item.text:
        yield _TextNode(
            id=item.id,
            text=item.text,
            source_span=item.source_span,
            references=item.references,
            incompleteness_flags=item.incompleteness_flags,
        )
    for sub_item in item.sub_items:
        if sub_item.text:
            yield _TextNode(
                id=sub_item.id,
                text=sub_item.text,
                source_span=sub_item.source_span,
                references=sub_item.references,
                incompleteness_flags=sub_item.incompleteness_flags,
            )


def _article_node(article: Article) -> _TextNode:
    return _TextNode(
        id=article.id,
        text=article.text,
        source_span=article.source_span,
        references=article.references,
        incompleteness_flags=article.incompleteness_flags,
    )


def _clause_prefix(text: str) -> str:
    segments = parse_item_segments(text)
    if not segments:
        return text

    prefix_parts = [segment.text for segment in segments if segment.item_number is None]
    return " ".join(part for part in prefix_parts if part).strip()


def _detect_references(text: str) -> Iterable[_ReferenceMatch]:
    seen: set[str] = set()
    for sentence in _iter_sentences(text):
        for rule in _RULES:
            if rule.pattern.search(sentence) is None:
                continue
            if sentence in seen:
                break
            seen.add(sentence)
            yield _ReferenceMatch(raw_text=sentence, rule=rule)
            break


def _iter_sentences(text: str) -> Iterable[str]:
    for match in _SENTENCE_RE.finditer(text):
        sentence = match.group(0).strip()
        if sentence:
            yield sentence


def _create_reference(
    node: _TextNode,
    match: _ReferenceMatch,
    index: int,
) -> Reference:
    rule = match.rule
    return Reference(
        id=reference_id(node.id, index, match.raw_text),
        source_node_id=node.id,
        reference_type=rule.reference_type,
        status=rule.status,
        raw_text=match.raw_text,
        target_name=rule.target_name,
        target_type=rule.target_type,
        required_document_name=rule.required_document_name,
        confidence=rule.confidence,
        source_span=node.source_span,
    )


def _create_incompleteness_flag(
    node: _TextNode,
    match: _ReferenceMatch,
    index: int,
) -> IncompletenessFlag:
    rule = match.rule
    return IncompletenessFlag(
        id=incompleteness_flag_id(node.id, index, match.raw_text),
        node_id=node.id,
        flag_type=rule.flag_type,
        raw_text=match.raw_text,
        missing_source=rule.missing_source,
        source_span=node.source_span,
        note=rule.note,
    )
