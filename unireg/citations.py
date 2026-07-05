"""Deterministic citation projection for parsed regulation nodes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from unireg.models import (
    Article,
    Clause,
    Item,
    NodeType,
    ParseResult,
    Regulation,
    RegulationDocument,
    SourceSpan,
    SubItem,
)

CitationRoot = ParseResult | Regulation | RegulationDocument


@dataclass(frozen=True, slots=True, kw_only=True)
class Citation:
    """Citation derived from a legal node and its source span."""

    node_id: str
    node_type: NodeType
    regulation_title: str
    label: str
    source_label: str
    source_span: SourceSpan | None
    quote: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "regulation_title": self.regulation_title,
            "label": self.label,
            "source_label": self.source_label,
            "source_span": (
                None if self.source_span is None else self.source_span.to_dict()
            ),
            "quote": self.quote,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Citation:
        return cls(
            node_id=_required_str(data, "node_id"),
            node_type=NodeType(_required_str(data, "node_type")),
            regulation_title=_required_str(data, "regulation_title"),
            label=_required_str(data, "label"),
            source_label=_required_str(data, "source_label"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            quote=_optional_str(data, "quote"),
        )


class CitationGenerator:
    """Generate deterministic citations from the parsed hierarchy."""

    def generate(
        self, value: CitationRoot, *, include_quotes: bool = True
    ) -> list[Citation]:
        regulation = _regulation_from_root(value)
        citations: list[Citation] = []
        for article in regulation.all_articles():
            citations.append(
                self.article(regulation, article, include_quote=include_quotes)
            )
            for clause in article.clauses:
                citations.append(
                    self.clause(
                        regulation,
                        article,
                        clause,
                        include_quote=include_quotes,
                    )
                )
                for item in clause.items:
                    citations.append(
                        self.item(
                            regulation,
                            article,
                            clause,
                            item,
                            include_quote=include_quotes,
                        )
                    )
                    for sub_item in item.sub_items:
                        citations.append(
                            self.sub_item(
                                regulation,
                                article,
                                clause,
                                item,
                                sub_item,
                                include_quote=include_quotes,
                            )
                        )
        return citations

    def article(
        self,
        regulation: Regulation,
        article: Article,
        *,
        include_quote: bool = True,
    ) -> Citation:
        return _citation(
            node_id=article.id,
            node_type=NodeType.ARTICLE,
            regulation=regulation,
            label=_article_label(regulation, article),
            source_span=article.source_span,
            quote=article.text if include_quote else None,
        )

    def clause(
        self,
        regulation: Regulation,
        article: Article,
        clause: Clause,
        *,
        include_quote: bool = True,
    ) -> Citation:
        return _citation(
            node_id=clause.id,
            node_type=NodeType.CLAUSE,
            regulation=regulation,
            label=_clause_label(regulation, article, clause),
            source_span=clause.source_span,
            quote=clause.text if include_quote else None,
        )

    def item(
        self,
        regulation: Regulation,
        article: Article,
        clause: Clause,
        item: Item,
        *,
        include_quote: bool = True,
    ) -> Citation:
        label = f"{_clause_label(regulation, article, clause)}, 제{item.item_number}호"
        return _citation(
            node_id=item.id,
            node_type=NodeType.ITEM,
            regulation=regulation,
            label=label,
            source_span=item.source_span,
            quote=item.text if include_quote else None,
        )

    def sub_item(
        self,
        regulation: Regulation,
        article: Article,
        clause: Clause,
        item: Item,
        sub_item: SubItem,
        *,
        include_quote: bool = True,
    ) -> Citation:
        item_label = (
            f"{_clause_label(regulation, article, clause)}, 제{item.item_number}호"
        )
        return _citation(
            node_id=sub_item.id,
            node_type=NodeType.SUB_ITEM,
            regulation=regulation,
            label=f"{item_label}, {sub_item.sub_item_number}목",
            source_span=sub_item.source_span,
            quote=sub_item.text if include_quote else None,
        )


def _regulation_from_root(value: CitationRoot) -> Regulation:
    if isinstance(value, ParseResult):
        if value.document is None:
            raise ValueError("Cannot cite ParseResult without a document.")
        return value.document.regulation
    if isinstance(value, RegulationDocument):
        return value.regulation
    return value


def _citation(
    *,
    node_id: str,
    node_type: NodeType,
    regulation: Regulation,
    label: str,
    source_span: SourceSpan | None,
    quote: str | None,
) -> Citation:
    normalized_quote = quote.strip() if quote is not None and quote.strip() else None
    return Citation(
        node_id=node_id,
        node_type=node_type,
        regulation_title=regulation.title,
        label=label,
        source_label=_source_label(source_span),
        source_span=source_span,
        quote=normalized_quote,
    )


def _article_label(regulation: Regulation, article: Article) -> str:
    return f"{regulation.title}, {article.article_number}{_title_suffix(article.title)}"


def _clause_label(regulation: Regulation, article: Article, clause: Clause) -> str:
    if clause.clause_number is None:
        return f"{_article_label(regulation, article)}, 본문"
    return f"{_article_label(regulation, article)}, 제{clause.clause_number}항"


def _title_suffix(title: str | None) -> str:
    if title:
        return f"({title})"
    return ""


def _source_label(source_span: SourceSpan | None) -> str:
    if source_span is None:
        return "source unavailable"

    source_file = Path(source_span.source_file).name
    if source_span.page_start is not None and source_span.page_end is not None:
        if source_span.page_start == source_span.page_end:
            return f"{source_file} p.{source_span.page_start}"
        return f"{source_file} pp.{source_span.page_start}-{source_span.page_end}"
    if source_span.line_start is not None and source_span.line_end is not None:
        if source_span.line_start == source_span.line_end:
            return f"{source_file} line {source_span.line_start}"
        return f"{source_file} lines {source_span.line_start}-{source_span.line_end}"
    return source_file


def _required_str(data: dict[str, object], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise TypeError(f"Expected '{key}' to be str.")
    return value


def _optional_str(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Expected '{key}' to be str or None.")
    return value


def _optional_dict(data: dict[str, object], key: str) -> dict[str, object] | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError(f"Expected '{key}' to be object or None.")
    return value
