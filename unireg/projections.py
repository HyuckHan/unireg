"""Downstream search, vector, and graph projections."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import cast

from unireg.citations import Citation, CitationGenerator
from unireg.models import (
    Appendix,
    Article,
    Chapter,
    Clause,
    IncompletenessFlag,
    Item,
    NodeType,
    ParseResult,
    ProvisionStatus,
    Reference,
    ReferenceStatus,
    Regulation,
    RegulationDocument,
    Section,
    SourceSpan,
    SubItem,
    Table,
)

ProjectionRoot = ParseResult | Regulation | RegulationDocument


class GraphEdgeType(StrEnum):
    """Supported graph edge types for projected regulation graphs."""

    CONTAINS = "contains"
    REFERS_TO = "refers_to"
    MISSING_REFERENCE = "missing_reference"
    UNRESOLVED_REFERENCE = "unresolved_reference"


@dataclass(frozen=True, slots=True, kw_only=True)
class BM25Document:
    """Keyword-search document derived from a citeable legal node."""

    document_id: str
    node_id: str
    node_type: NodeType
    title: str
    text: str
    citation_label: str
    source_label: str
    source_span: SourceSpan | None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "title": self.title,
            "text": self.text,
            "citation_label": self.citation_label,
            "source_label": self.source_label,
            "source_span": (
                None if self.source_span is None else self.source_span.to_dict()
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> BM25Document:
        return cls(
            document_id=_required_str(data, "document_id"),
            node_id=_required_str(data, "node_id"),
            node_type=NodeType(_required_str(data, "node_type")),
            title=_required_str(data, "title"),
            text=_required_str(data, "text"),
            citation_label=_required_str(data, "citation_label"),
            source_label=_required_str(data, "source_label"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            metadata=_str_dict(data, "metadata"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class VectorDocument:
    """Vector-DB-ready text chunk derived from a citeable legal node."""

    chunk_id: str
    node_id: str
    node_type: NodeType
    text: str
    citation_label: str
    source_label: str
    source_span: SourceSpan | None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "text": self.text,
            "citation_label": self.citation_label,
            "source_label": self.source_label,
            "source_span": (
                None if self.source_span is None else self.source_span.to_dict()
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> VectorDocument:
        return cls(
            chunk_id=_required_str(data, "chunk_id"),
            node_id=_required_str(data, "node_id"),
            node_type=NodeType(_required_str(data, "node_type")),
            text=_required_str(data, "text"),
            citation_label=_required_str(data, "citation_label"),
            source_label=_required_str(data, "source_label"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            metadata=_str_dict(data, "metadata"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphNode:
    """Graph node projection for legal hierarchy and references."""

    node_id: str
    node_type: NodeType
    label: str
    properties: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "label": self.label,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> GraphNode:
        return cls(
            node_id=_required_str(data, "node_id"),
            node_type=NodeType(_required_str(data, "node_type")),
            label=_required_str(data, "label"),
            properties=_object_dict(data, "properties"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphEdge:
    """Graph edge projection for hierarchy and legal references."""

    edge_id: str
    edge_type: GraphEdgeType
    source_node_id: str
    target_node_id: str | None
    properties: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "edge_id": self.edge_id,
            "edge_type": self.edge_type.value,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> GraphEdge:
        return cls(
            edge_id=_required_str(data, "edge_id"),
            edge_type=GraphEdgeType(_required_str(data, "edge_type")),
            source_node_id=_required_str(data, "source_node_id"),
            target_node_id=_optional_str(data, "target_node_id"),
            properties=_object_dict(data, "properties"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectionSet:
    """Complete downstream projection set for one regulation."""

    bm25_documents: list[BM25Document]
    vector_documents: list[VectorDocument]
    graph_nodes: list[GraphNode]
    graph_edges: list[GraphEdge]

    def to_dict(self) -> dict[str, object]:
        return {
            "bm25_documents": [document.to_dict() for document in self.bm25_documents],
            "vector_documents": [
                document.to_dict() for document in self.vector_documents
            ],
            "graph_nodes": [node.to_dict() for node in self.graph_nodes],
            "graph_edges": [edge.to_dict() for edge in self.graph_edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ProjectionSet:
        return cls(
            bm25_documents=[
                BM25Document.from_dict(item)
                for item in _dict_list(data, "bm25_documents")
            ],
            vector_documents=[
                VectorDocument.from_dict(item)
                for item in _dict_list(data, "vector_documents")
            ],
            graph_nodes=[
                GraphNode.from_dict(item) for item in _dict_list(data, "graph_nodes")
            ],
            graph_edges=[
                GraphEdge.from_dict(item) for item in _dict_list(data, "graph_edges")
            ],
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _ProjectionNode:
    node_id: str
    node_type: NodeType
    label: str
    text: str
    source_span: SourceSpan | None
    status: ProvisionStatus
    references: list[Reference]
    incompleteness_flags: list[IncompletenessFlag]
    metadata: dict[str, str]


class ProjectionBuilder:
    """Build deterministic search, vector, and graph projections."""

    def __init__(self, citation_generator: CitationGenerator | None = None) -> None:
        self._citation_generator = citation_generator or CitationGenerator()

    def build(self, value: ProjectionRoot) -> ProjectionSet:
        regulation = _regulation_from_root(value)
        state = _ProjectionState(regulation=regulation)
        self._add_regulation(state)
        return ProjectionSet(
            bm25_documents=state.bm25_documents,
            vector_documents=state.vector_documents,
            graph_nodes=state.graph_nodes,
            graph_edges=state.graph_edges,
        )

    def _add_regulation(self, state: _ProjectionState) -> None:
        regulation = state.regulation
        state.add_graph_node(
            node_id=regulation.id,
            node_type=NodeType.REGULATION,
            label=regulation.title,
            properties={
                **_regulation_metadata(regulation),
                "status": regulation.status.value,
            },
        )

        for index, chapter in enumerate(regulation.chapters, start=1):
            self._add_chapter(state, chapter, index=index)
        for index, appendix in enumerate(regulation.appendices, start=1):
            self._add_appendix(state, appendix, index=index)

    def _add_chapter(
        self,
        state: _ProjectionState,
        chapter: Chapter,
        *,
        index: int,
    ) -> None:
        metadata = {
            **_regulation_metadata(state.regulation),
            "chapter_number": chapter.number,
        }
        if chapter.title is not None:
            metadata["chapter_title"] = chapter.title
        label = _numbered_label(f"제{chapter.number}장", chapter.title)
        state.add_graph_node(
            node_id=chapter.id,
            node_type=NodeType.CHAPTER,
            label=label,
            properties={**metadata, "status": chapter.status.value},
        )
        state.add_hierarchy_edge(
            source_node_id=state.regulation.id,
            target_node_id=chapter.id,
            index=index,
        )

        for article_index, article in enumerate(chapter.articles, start=1):
            self._add_article(
                state,
                article,
                parent_node_id=chapter.id,
                base_metadata=metadata,
                index=article_index,
            )
        for section_index, section in enumerate(chapter.sections, start=1):
            self._add_section(
                state,
                section,
                parent_node_id=chapter.id,
                base_metadata=metadata,
                index=section_index,
            )

    def _add_section(
        self,
        state: _ProjectionState,
        section: Section,
        *,
        parent_node_id: str,
        base_metadata: dict[str, str],
        index: int,
    ) -> None:
        metadata = {
            **base_metadata,
            "section_number": section.number,
        }
        if section.title is not None:
            metadata["section_title"] = section.title
        label = _numbered_label(f"제{section.number}절", section.title)
        state.add_graph_node(
            node_id=section.id,
            node_type=NodeType.SECTION,
            label=label,
            properties={**metadata, "status": section.status.value},
        )
        state.add_hierarchy_edge(
            source_node_id=parent_node_id,
            target_node_id=section.id,
            index=index,
        )

        for article_index, article in enumerate(section.articles, start=1):
            self._add_article(
                state,
                article,
                parent_node_id=section.id,
                base_metadata=metadata,
                index=article_index,
            )

    def _add_article(
        self,
        state: _ProjectionState,
        article: Article,
        *,
        parent_node_id: str,
        base_metadata: dict[str, str],
        index: int,
    ) -> None:
        citation = self._citation_generator.article(
            state.regulation, article, include_quote=False
        )
        hierarchy_metadata = {
            **base_metadata,
            "article_number": article.article_number,
        }
        if article.title is not None:
            hierarchy_metadata["article_title"] = article.title
        metadata = {
            **hierarchy_metadata,
            **_node_metadata(
                article.status,
                article.references,
                article.incompleteness_flags,
            ),
        }
        node = _ProjectionNode(
            node_id=article.id,
            node_type=NodeType.ARTICLE,
            label=citation.label,
            text=article.text,
            source_span=article.source_span,
            status=article.status,
            references=article.references,
            incompleteness_flags=article.incompleteness_flags,
            metadata=metadata,
        )
        state.add_projected_node(node, citation)
        state.add_hierarchy_edge(
            source_node_id=parent_node_id,
            target_node_id=article.id,
            index=index,
        )

        for clause_index, clause in enumerate(article.clauses, start=1):
            self._add_clause(
                state,
                article,
                clause,
                parent_node_id=article.id,
                base_metadata=hierarchy_metadata,
                index=clause_index,
            )

    def _add_clause(
        self,
        state: _ProjectionState,
        article: Article,
        clause: Clause,
        *,
        parent_node_id: str,
        base_metadata: dict[str, str],
        index: int,
    ) -> None:
        citation = self._citation_generator.clause(
            state.regulation, article, clause, include_quote=False
        )
        hierarchy_metadata = {**base_metadata}
        if clause.clause_number is not None:
            hierarchy_metadata["clause_number"] = clause.clause_number
        metadata = {
            **hierarchy_metadata,
            **_node_metadata(
                clause.status,
                clause.references,
                clause.incompleteness_flags,
            ),
        }
        node = _ProjectionNode(
            node_id=clause.id,
            node_type=NodeType.CLAUSE,
            label=citation.label,
            text=clause.text,
            source_span=clause.source_span,
            status=clause.status,
            references=clause.references,
            incompleteness_flags=clause.incompleteness_flags,
            metadata=metadata,
        )
        state.add_projected_node(node, citation)
        state.add_hierarchy_edge(
            source_node_id=parent_node_id,
            target_node_id=clause.id,
            index=index,
        )

        for item_index, item in enumerate(clause.items, start=1):
            self._add_item(
                state,
                article,
                clause,
                item,
                parent_node_id=clause.id,
                base_metadata=hierarchy_metadata,
                index=item_index,
            )

    def _add_item(
        self,
        state: _ProjectionState,
        article: Article,
        clause: Clause,
        item: Item,
        *,
        parent_node_id: str,
        base_metadata: dict[str, str],
        index: int,
    ) -> None:
        citation = self._citation_generator.item(
            state.regulation, article, clause, item, include_quote=False
        )
        hierarchy_metadata = {
            **base_metadata,
            "item_number": item.item_number,
        }
        metadata = {
            **hierarchy_metadata,
            **_node_metadata(
                item.status,
                item.references,
                item.incompleteness_flags,
            ),
        }
        node = _ProjectionNode(
            node_id=item.id,
            node_type=NodeType.ITEM,
            label=citation.label,
            text=item.text,
            source_span=item.source_span,
            status=item.status,
            references=item.references,
            incompleteness_flags=item.incompleteness_flags,
            metadata=metadata,
        )
        state.add_projected_node(node, citation)
        state.add_hierarchy_edge(
            source_node_id=parent_node_id,
            target_node_id=item.id,
            index=index,
        )

        for sub_item_index, sub_item in enumerate(item.sub_items, start=1):
            self._add_sub_item(
                state,
                article,
                clause,
                item,
                sub_item,
                parent_node_id=item.id,
                base_metadata=hierarchy_metadata,
                index=sub_item_index,
            )

    def _add_sub_item(
        self,
        state: _ProjectionState,
        article: Article,
        clause: Clause,
        item: Item,
        sub_item: SubItem,
        *,
        parent_node_id: str,
        base_metadata: dict[str, str],
        index: int,
    ) -> None:
        citation = self._citation_generator.sub_item(
            state.regulation,
            article,
            clause,
            item,
            sub_item,
            include_quote=False,
        )
        metadata = {
            **base_metadata,
            "sub_item_number": sub_item.sub_item_number,
            **_node_metadata(
                sub_item.status,
                sub_item.references,
                sub_item.incompleteness_flags,
            ),
        }
        node = _ProjectionNode(
            node_id=sub_item.id,
            node_type=NodeType.SUB_ITEM,
            label=citation.label,
            text=sub_item.text,
            source_span=sub_item.source_span,
            status=sub_item.status,
            references=sub_item.references,
            incompleteness_flags=sub_item.incompleteness_flags,
            metadata=metadata,
        )
        state.add_projected_node(node, citation)
        state.add_hierarchy_edge(
            source_node_id=parent_node_id,
            target_node_id=sub_item.id,
            index=index,
        )

    def _add_appendix(
        self,
        state: _ProjectionState,
        appendix: Appendix,
        *,
        index: int,
    ) -> None:
        hierarchy_metadata = {**_regulation_metadata(state.regulation)}
        if appendix.number is not None:
            hierarchy_metadata["appendix_number"] = appendix.number
        metadata = {
            **hierarchy_metadata,
            **_node_metadata(
                appendix.status,
                references=[],
                incompleteness_flags=[],
            ),
        }
        label = appendix.title or "Appendix"
        node = _ProjectionNode(
            node_id=appendix.id,
            node_type=NodeType.APPENDIX,
            label=label,
            text=appendix.text,
            source_span=appendix.source_span,
            status=appendix.status,
            references=[],
            incompleteness_flags=[],
            metadata=metadata,
        )
        state.add_projected_node(node, _citation_from_node(node))
        state.add_hierarchy_edge(
            source_node_id=state.regulation.id,
            target_node_id=appendix.id,
            index=index,
        )

        for table_index, table in enumerate(appendix.tables, start=1):
            self._add_table(
                state,
                table,
                parent_node_id=appendix.id,
                base_metadata=hierarchy_metadata,
                index=table_index,
            )

    def _add_table(
        self,
        state: _ProjectionState,
        table: Table,
        *,
        parent_node_id: str,
        base_metadata: dict[str, str],
        index: int,
    ) -> None:
        metadata = {
            **base_metadata,
            **_node_metadata(
                table.status,
                references=[],
                incompleteness_flags=[],
            ),
        }
        label = table.caption or "Table"
        node = _ProjectionNode(
            node_id=table.id,
            node_type=NodeType.TABLE,
            label=label,
            text=table.text,
            source_span=table.source_span,
            status=table.status,
            references=[],
            incompleteness_flags=[],
            metadata=metadata,
        )
        state.add_projected_node(node, _citation_from_node(node))
        state.add_hierarchy_edge(
            source_node_id=parent_node_id,
            target_node_id=table.id,
            index=index,
        )


@dataclass(slots=True)
class _ProjectionState:
    regulation: Regulation
    bm25_documents: list[BM25Document] = field(default_factory=list)
    vector_documents: list[VectorDocument] = field(default_factory=list)
    graph_nodes: list[GraphNode] = field(default_factory=list)
    graph_edges: list[GraphEdge] = field(default_factory=list)

    def add_projected_node(self, node: _ProjectionNode, citation: Citation) -> None:
        self.add_graph_node(
            node_id=node.node_id,
            node_type=node.node_type,
            label=node.label,
            properties={
                **node.metadata,
                "status": node.status.value,
                "text": node.text,
                "citation_label": citation.label,
                "source_label": citation.source_label,
                **_source_span_properties(node.source_span),
            },
        )
        self._add_reference_edges(node)

        text = _projection_text(node.label, node.text)
        if not text:
            return
        metadata = {
            **node.metadata,
            "citation_label": citation.label,
            "source_label": citation.source_label,
        }
        self.bm25_documents.append(
            BM25Document(
                document_id=f"bm25:{node.node_id}",
                node_id=node.node_id,
                node_type=node.node_type,
                title=node.label,
                text=text,
                citation_label=citation.label,
                source_label=citation.source_label,
                source_span=node.source_span,
                metadata=metadata,
            )
        )
        self.vector_documents.append(
            VectorDocument(
                chunk_id=f"vector:{node.node_id}",
                node_id=node.node_id,
                node_type=node.node_type,
                text=text,
                citation_label=citation.label,
                source_label=citation.source_label,
                source_span=node.source_span,
                metadata=metadata,
            )
        )

    def add_graph_node(
        self,
        *,
        node_id: str,
        node_type: NodeType,
        label: str,
        properties: dict[str, object],
    ) -> None:
        self.graph_nodes.append(
            GraphNode(
                node_id=node_id,
                node_type=node_type,
                label=label,
                properties=properties,
            )
        )

    def add_hierarchy_edge(
        self,
        *,
        source_node_id: str,
        target_node_id: str,
        index: int,
    ) -> None:
        self.graph_edges.append(
            GraphEdge(
                edge_id=_edge_id(
                    source_node_id,
                    GraphEdgeType.CONTAINS,
                    target_node_id,
                    str(index),
                ),
                edge_type=GraphEdgeType.CONTAINS,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                properties={"order": index},
            )
        )

    def _add_reference_edges(self, node: _ProjectionNode) -> None:
        for index, reference in enumerate(node.references, start=1):
            edge_type = _reference_edge_type(reference)
            self.graph_edges.append(
                GraphEdge(
                    edge_id=_edge_id(
                        node.node_id,
                        edge_type,
                        reference.target_node_id,
                        reference.id or str(index),
                    ),
                    edge_type=edge_type,
                    source_node_id=node.node_id,
                    target_node_id=reference.target_node_id,
                    properties=_reference_properties(reference),
                )
            )


def _regulation_from_root(value: ProjectionRoot) -> Regulation:
    if isinstance(value, ParseResult):
        if value.document is None:
            raise ValueError("Cannot project ParseResult without a document.")
        return value.document.regulation
    if isinstance(value, RegulationDocument):
        return value.regulation
    return value


def _regulation_metadata(regulation: Regulation) -> dict[str, str]:
    metadata = {
        "regulation_id": regulation.id,
        "regulation_title": regulation.title,
        "source_file": regulation.source_file,
    }
    if regulation.raw_title is not None:
        metadata["raw_title"] = regulation.raw_title
    if regulation.institution is not None:
        metadata["institution"] = regulation.institution
    if regulation.regulation_code is not None:
        metadata["regulation_code"] = regulation.regulation_code
    if regulation.effective_date is not None:
        metadata["effective_date"] = regulation.effective_date.isoformat()
    if regulation.amendment_date is not None:
        metadata["amendment_date"] = regulation.amendment_date.isoformat()
    return metadata


def _node_metadata(
    status: ProvisionStatus,
    references: list[Reference],
    incompleteness_flags: list[IncompletenessFlag],
) -> dict[str, str]:
    metadata = {"provision_status": status.value}
    reference_types = sorted(
        {reference.reference_type.value for reference in references}
    )
    reference_statuses = sorted({reference.status.value for reference in references})
    required_documents = sorted(
        {
            reference.required_document_name
            for reference in references
            if reference.required_document_name is not None
        }
    )
    incompleteness_types = sorted(
        {flag.flag_type.value for flag in incompleteness_flags}
    )
    missing_sources = sorted(
        {
            flag.missing_source
            for flag in incompleteness_flags
            if flag.missing_source is not None
        }
    )
    _add_joined(metadata, "reference_types", reference_types)
    _add_joined(metadata, "reference_statuses", reference_statuses)
    _add_joined(metadata, "required_documents", required_documents)
    _add_joined(metadata, "incompleteness_types", incompleteness_types)
    _add_joined(metadata, "missing_sources", missing_sources)
    return metadata


def _source_span_properties(source_span: SourceSpan | None) -> dict[str, object]:
    if source_span is None:
        return {}
    return {
        key: value for key, value in source_span.to_dict().items() if value is not None
    }


def _reference_edge_type(reference: Reference) -> GraphEdgeType:
    if reference.target_node_id is not None:
        return GraphEdgeType.REFERS_TO
    if (
        reference.status == ReferenceStatus.MISSING
        or reference.required_document_name is not None
    ):
        return GraphEdgeType.MISSING_REFERENCE
    return GraphEdgeType.UNRESOLVED_REFERENCE


def _reference_properties(reference: Reference) -> dict[str, object]:
    properties: dict[str, object] = {
        "reference_id": reference.id,
        "reference_type": reference.reference_type.value,
        "status": reference.status.value,
        "raw_text": reference.raw_text,
    }
    if reference.target_name is not None:
        properties["target_name"] = reference.target_name
    if reference.target_type is not None:
        properties["target_type"] = reference.target_type
    if reference.required_document_name is not None:
        properties["required_document_name"] = reference.required_document_name
    if reference.confidence is not None:
        properties["confidence"] = reference.confidence
    if reference.source_span is not None:
        properties.update(_source_span_properties(reference.source_span))
    return properties


def _citation_from_node(node: _ProjectionNode) -> Citation:
    return Citation(
        node_id=node.node_id,
        node_type=node.node_type,
        regulation_title=node.metadata["regulation_title"],
        label=node.label,
        source_label=_source_label(node.source_span),
        source_span=node.source_span,
        quote=None,
    )


def _source_label(source_span: SourceSpan | None) -> str:
    if source_span is None:
        return "source unavailable"
    source_file = Path(source_span.source_file).name
    if source_span.page_start is not None and source_span.page_end is not None:
        if source_span.page_start == source_span.page_end:
            return f"{source_file} p.{source_span.page_start}"
        return f"{source_file} pp.{source_span.page_start}-{source_span.page_end}"
    return source_file


def _projection_text(label: str, text: str) -> str:
    normalized_text = text.strip()
    if normalized_text:
        return f"{label}\n{normalized_text}"
    return label.strip()


def _numbered_label(number: str, title: str | None) -> str:
    if title:
        return f"{number} {title}"
    return number


def _add_joined(
    metadata: dict[str, str],
    key: str,
    values: list[str],
) -> None:
    if values:
        metadata[key] = "|".join(values)


def _edge_id(
    source_node_id: str,
    edge_type: GraphEdgeType,
    target_node_id: str | None,
    salt: str,
) -> str:
    digest = hashlib.sha1(
        "\n".join(
            [source_node_id, edge_type.value, target_node_id or "", salt]
        ).encode()
    ).hexdigest()[:12]
    return f"edge:{digest}"


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
    return cast(dict[str, object], value)


def _object_dict(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise TypeError(f"Expected '{key}' to be object.")
    return cast(dict[str, object], value)


def _str_dict(data: dict[str, object], key: str) -> dict[str, str]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise TypeError(f"Expected '{key}' to be object.")
    if not all(isinstance(item_key, str) for item_key in value):
        raise TypeError(f"Expected every key in '{key}' to be str.")
    if not all(isinstance(item_value, str) for item_value in value.values()):
        raise TypeError(f"Expected every value in '{key}' to be str.")
    return cast(dict[str, str], value)


def _dict_list(data: dict[str, object], key: str) -> list[dict[str, object]]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise TypeError(f"Expected '{key}' to be list.")
    if not all(isinstance(item, dict) for item in value):
        raise TypeError(f"Expected every item in '{key}' to be object.")
    return cast(list[dict[str, object]], value)
