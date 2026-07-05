"""Core dataclasses for parsed regulation documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import cast

SCHEMA_VERSION = "unireg.regulation.v1"


class NodeType(StrEnum):
    """Type of a legal hierarchy node."""

    REGULATION = "regulation"
    CHAPTER = "chapter"
    SECTION = "section"
    ARTICLE = "article"
    CLAUSE = "clause"
    ITEM = "item"
    SUB_ITEM = "sub_item"
    APPENDIX = "appendix"
    TABLE = "table"


class ProvisionStatus(StrEnum):
    """Legal status of a provision."""

    ACTIVE = "active"
    REPEALED = "repealed"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class AmendmentEventType(StrEnum):
    """Kind of amendment event detected in source text."""

    ENACTED = "enacted"
    AMENDED = "amended"
    INSERTED = "inserted"
    REPEALED = "repealed"
    EFFECTIVE_DATE_CHANGED = "effective_date_changed"


class ReferenceType(StrEnum):
    """Kind of legal reference."""

    EXPLICIT_REFERENCE = "explicit_reference"
    IMPLICIT_REFERENCE = "implicit_reference"
    UNKNOWN_EXTERNAL_RULE = "unknown_external_rule"
    MISSING_INTERNAL_RULE = "missing_internal_rule"
    ADMINISTRATIVE_DISCRETION = "administrative_discretion"


class ReferenceStatus(StrEnum):
    """Resolution status of a legal reference."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    MISSING = "missing"


class IncompletenessType(StrEnum):
    """Reason a node cannot fully answer downstream questions."""

    REQUIRES_MISSING_REGULATION = "requires_missing_regulation"
    NOT_ANSWERABLE_FROM_CORPUS = "not_answerable_from_corpus"
    PARTIAL_EVIDENCE_ONLY = "partial_evidence_only"
    ADMINISTRATIVE_DISCRETION = "administrative_discretion"


class DiagnosticSeverity(StrEnum):
    """Severity level for parser diagnostics."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


@dataclass(slots=True, kw_only=True)
class SourceSpan:
    """Location of text in an extracted source document."""

    source_file: str
    page_start: int | None = None
    page_end: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    extraction_method: str | None = None
    text_hash: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "source_file": self.source_file,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "extraction_method": self.extraction_method,
            "text_hash": self.text_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object] | None) -> SourceSpan | None:
        if data is None:
            return None
        return cls(
            source_file=_required_str(data, "source_file"),
            page_start=_optional_int(data, "page_start"),
            page_end=_optional_int(data, "page_end"),
            line_start=_optional_int(data, "line_start"),
            line_end=_optional_int(data, "line_end"),
            char_start=_optional_int(data, "char_start"),
            char_end=_optional_int(data, "char_end"),
            extraction_method=_optional_str(data, "extraction_method"),
            text_hash=_optional_str(data, "text_hash"),
        )


def merge_source_spans(
    first: SourceSpan | None,
    second: SourceSpan | None,
) -> SourceSpan | None:
    """Return a span covering both inputs."""

    if first is None:
        return second
    if second is None:
        return first

    return SourceSpan(
        source_file=first.source_file,
        page_start=_min_optional(first.page_start, second.page_start),
        page_end=_max_optional(first.page_end, second.page_end),
        line_start=_min_optional(first.line_start, second.line_start),
        line_end=_max_optional(first.line_end, second.line_end),
        char_start=_min_optional(first.char_start, second.char_start),
        char_end=_max_optional(first.char_end, second.char_end),
        extraction_method=first.extraction_method or second.extraction_method,
        text_hash=first.text_hash or second.text_hash,
    )


def _min_optional(first: int | None, second: int | None) -> int | None:
    values = [value for value in (first, second) if value is not None]
    return min(values) if values else None


def _max_optional(first: int | None, second: int | None) -> int | None:
    values = [value for value in (first, second) if value is not None]
    return max(values) if values else None


@dataclass(slots=True, kw_only=True)
class ExtractedPage:
    """Text extracted from a single source page."""

    page_number: int
    text: str


@dataclass(slots=True, kw_only=True)
class ExtractedDocument:
    """Raw text extracted from a source file."""

    source_file: str
    pages: list[ExtractedPage]
    extraction_method: str


@dataclass(slots=True, kw_only=True)
class CleanLine:
    """A normalized line with source provenance."""

    text: str
    source_span: SourceSpan
    line_number: int


@dataclass(slots=True, kw_only=True)
class CleanDocument:
    """Cleaned source text ready for structural parsing."""

    source_file: str
    lines: list[CleanLine]
    extraction_method: str


@dataclass(slots=True, kw_only=True)
class AmendmentEvent:
    """Amendment metadata attached to a regulation or provision."""

    event_type: AmendmentEventType
    date: date | None = None
    raw_text: str = ""
    source_span: SourceSpan | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "event_type": self.event_type.value,
            "date": self.date.isoformat() if self.date is not None else None,
            "raw_text": self.raw_text,
            "source_span": _source_span_to_dict(self.source_span),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AmendmentEvent:
        return cls(
            event_type=AmendmentEventType(_required_str(data, "event_type")),
            date=_optional_date(data, "date"),
            raw_text=_required_str(data, "raw_text"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            note=_optional_str(data, "note"),
        )


@dataclass(slots=True, kw_only=True)
class Reference:
    """Reference from one legal node to another rule or document."""

    id: str
    source_node_id: str
    reference_type: ReferenceType
    status: ReferenceStatus
    raw_text: str
    target_name: str | None = None
    target_type: str | None = None
    target_node_id: str | None = None
    required_document_name: str | None = None
    confidence: float | None = None
    source_span: SourceSpan | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_node_id": self.source_node_id,
            "reference_type": self.reference_type.value,
            "status": self.status.value,
            "raw_text": self.raw_text,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "target_node_id": self.target_node_id,
            "required_document_name": self.required_document_name,
            "confidence": self.confidence,
            "source_span": _source_span_to_dict(self.source_span),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Reference:
        return cls(
            id=_required_str(data, "id"),
            source_node_id=_required_str(data, "source_node_id"),
            reference_type=ReferenceType(_required_str(data, "reference_type")),
            status=ReferenceStatus(_required_str(data, "status")),
            raw_text=_required_str(data, "raw_text"),
            target_name=_optional_str(data, "target_name"),
            target_type=_optional_str(data, "target_type"),
            target_node_id=_optional_str(data, "target_node_id"),
            required_document_name=_optional_str(data, "required_document_name"),
            confidence=_optional_float(data, "confidence"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
        )


@dataclass(slots=True, kw_only=True)
class IncompletenessFlag:
    """Marker showing that a node requires unavailable legal context."""

    id: str
    node_id: str
    flag_type: IncompletenessType
    raw_text: str
    missing_source: str | None = None
    source_span: SourceSpan | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "flag_type": self.flag_type.value,
            "raw_text": self.raw_text,
            "missing_source": self.missing_source,
            "source_span": _source_span_to_dict(self.source_span),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> IncompletenessFlag:
        return cls(
            id=_required_str(data, "id"),
            node_id=_required_str(data, "node_id"),
            flag_type=IncompletenessType(_required_str(data, "flag_type")),
            raw_text=_required_str(data, "raw_text"),
            missing_source=_optional_str(data, "missing_source"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            note=_optional_str(data, "note"),
        )


@dataclass(slots=True, kw_only=True)
class SubItem:
    """Sub-item under an item, commonly marked with Korean letters."""

    id: str
    sub_item_number: str
    path: list[str]
    title: str | None = None
    text: str = ""
    source_span: SourceSpan | None = None
    status: ProvisionStatus = ProvisionStatus.ACTIVE
    raw_text: str | None = None
    references: list[Reference] = field(default_factory=list)
    incompleteness_flags: list[IncompletenessFlag] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "node_type": NodeType.SUB_ITEM.value,
            "sub_item_number": self.sub_item_number,
            "path": self.path,
            "title": self.title,
            "text": self.text,
            "source_span": _source_span_to_dict(self.source_span),
            "status": self.status.value,
            "raw_text": self.raw_text,
            "references": [reference.to_dict() for reference in self.references],
            "incompleteness_flags": [
                flag.to_dict() for flag in self.incompleteness_flags
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> SubItem:
        return cls(
            id=_required_str(data, "id"),
            sub_item_number=_required_str(data, "sub_item_number"),
            path=_str_list(data, "path"),
            title=_optional_str(data, "title"),
            text=_required_str(data, "text"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            status=ProvisionStatus(_required_str(data, "status")),
            raw_text=_optional_str(data, "raw_text"),
            references=[
                Reference.from_dict(item) for item in _dict_list(data, "references")
            ],
            incompleteness_flags=[
                IncompletenessFlag.from_dict(item)
                for item in _dict_list(data, "incompleteness_flags")
            ],
        )


@dataclass(slots=True, kw_only=True)
class Item:
    """Numbered item under a clause."""

    id: str
    item_number: str
    path: list[str]
    title: str | None = None
    text: str = ""
    source_span: SourceSpan | None = None
    status: ProvisionStatus = ProvisionStatus.ACTIVE
    raw_text: str | None = None
    sub_items: list[SubItem] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    incompleteness_flags: list[IncompletenessFlag] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "node_type": NodeType.ITEM.value,
            "item_number": self.item_number,
            "path": self.path,
            "title": self.title,
            "text": self.text,
            "source_span": _source_span_to_dict(self.source_span),
            "status": self.status.value,
            "raw_text": self.raw_text,
            "sub_items": [sub_item.to_dict() for sub_item in self.sub_items],
            "references": [reference.to_dict() for reference in self.references],
            "incompleteness_flags": [
                flag.to_dict() for flag in self.incompleteness_flags
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Item:
        return cls(
            id=_required_str(data, "id"),
            item_number=_required_str(data, "item_number"),
            path=_str_list(data, "path"),
            title=_optional_str(data, "title"),
            text=_required_str(data, "text"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            status=ProvisionStatus(_required_str(data, "status")),
            raw_text=_optional_str(data, "raw_text"),
            sub_items=[
                SubItem.from_dict(item) for item in _dict_list(data, "sub_items")
            ],
            references=[
                Reference.from_dict(item) for item in _dict_list(data, "references")
            ],
            incompleteness_flags=[
                IncompletenessFlag.from_dict(item)
                for item in _dict_list(data, "incompleteness_flags")
            ],
        )


@dataclass(slots=True, kw_only=True)
class Clause:
    """Clause under an article."""

    id: str
    path: list[str]
    clause_number: str | None = None
    title: str | None = None
    text: str = ""
    source_span: SourceSpan | None = None
    status: ProvisionStatus = ProvisionStatus.ACTIVE
    raw_text: str | None = None
    items: list[Item] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    incompleteness_flags: list[IncompletenessFlag] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "node_type": NodeType.CLAUSE.value,
            "clause_number": self.clause_number,
            "path": self.path,
            "title": self.title,
            "text": self.text,
            "source_span": _source_span_to_dict(self.source_span),
            "status": self.status.value,
            "raw_text": self.raw_text,
            "items": [item.to_dict() for item in self.items],
            "references": [reference.to_dict() for reference in self.references],
            "incompleteness_flags": [
                flag.to_dict() for flag in self.incompleteness_flags
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Clause:
        return cls(
            id=_required_str(data, "id"),
            path=_str_list(data, "path"),
            clause_number=_optional_str(data, "clause_number"),
            title=_optional_str(data, "title"),
            text=_required_str(data, "text"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            status=ProvisionStatus(_required_str(data, "status")),
            raw_text=_optional_str(data, "raw_text"),
            items=[Item.from_dict(item) for item in _dict_list(data, "items")],
            references=[
                Reference.from_dict(item) for item in _dict_list(data, "references")
            ],
            incompleteness_flags=[
                IncompletenessFlag.from_dict(item)
                for item in _dict_list(data, "incompleteness_flags")
            ],
        )


@dataclass(slots=True, kw_only=True)
class Article:
    """Article-level representation.

    Article body lines remain available for migration compatibility while
    structured clause nodes are added by the parser.
    """

    id: str
    article_number: str
    title: str | None
    path: list[str]
    source_span: SourceSpan | None = None
    status: ProvisionStatus = ProvisionStatus.ACTIVE
    raw_text: str | None = None
    regulation_title: str | None = None
    chapter_title: str | None = None
    section_title: str | None = None
    amendment_history: list[AmendmentEvent] = field(default_factory=list)
    body_lines: list[str] = field(default_factory=list)
    clauses: list[Clause] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    incompleteness_flags: list[IncompletenessFlag] = field(default_factory=list)

    @property
    def text(self) -> str:
        if self.body_lines:
            return "\n".join(self.body_lines)
        return "\n".join(clause.text for clause in self.clauses if clause.text)

    def add_body_line(self, line: CleanLine) -> None:
        self.body_lines.append(line.text)
        self.source_span = merge_source_spans(self.source_span, line.source_span)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "node_type": NodeType.ARTICLE.value,
            "article_number": self.article_number,
            "title": self.title,
            "path": self.path,
            "source_span": _source_span_to_dict(self.source_span),
            "status": self.status.value,
            "raw_text": self.raw_text,
            "regulation_title": self.regulation_title,
            "chapter_title": self.chapter_title,
            "section_title": self.section_title,
            "amendment_history": [
                amendment.to_dict() for amendment in self.amendment_history
            ],
            "body_lines": self.body_lines,
            "clauses": [clause.to_dict() for clause in self.clauses],
            "references": [reference.to_dict() for reference in self.references],
            "incompleteness_flags": [
                flag.to_dict() for flag in self.incompleteness_flags
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Article:
        return cls(
            id=_required_str(data, "id"),
            article_number=_required_str(data, "article_number"),
            title=_optional_str(data, "title"),
            path=_str_list(data, "path"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            status=ProvisionStatus(_required_str(data, "status")),
            raw_text=_optional_str(data, "raw_text"),
            regulation_title=_optional_str(data, "regulation_title"),
            chapter_title=_optional_str(data, "chapter_title"),
            section_title=_optional_str(data, "section_title"),
            amendment_history=[
                AmendmentEvent.from_dict(item)
                for item in _dict_list(data, "amendment_history")
            ],
            body_lines=_str_list(data, "body_lines"),
            clauses=[Clause.from_dict(item) for item in _dict_list(data, "clauses")],
            references=[
                Reference.from_dict(item) for item in _dict_list(data, "references")
            ],
            incompleteness_flags=[
                IncompletenessFlag.from_dict(item)
                for item in _dict_list(data, "incompleteness_flags")
            ],
        )


@dataclass(slots=True, kw_only=True)
class Section:
    """Optional section under a chapter."""

    id: str
    number: str
    title: str | None
    path: list[str]
    source_span: SourceSpan | None = None
    status: ProvisionStatus = ProvisionStatus.ACTIVE
    raw_text: str | None = None
    intro_lines: list[str] = field(default_factory=list)
    articles: list[Article] = field(default_factory=list)

    def add_intro_line(self, line: CleanLine) -> None:
        self.intro_lines.append(line.text)
        self.source_span = merge_source_spans(self.source_span, line.source_span)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "node_type": NodeType.SECTION.value,
            "number": self.number,
            "title": self.title,
            "path": self.path,
            "source_span": _source_span_to_dict(self.source_span),
            "status": self.status.value,
            "raw_text": self.raw_text,
            "intro_lines": self.intro_lines,
            "articles": [article.to_dict() for article in self.articles],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Section:
        return cls(
            id=_required_str(data, "id"),
            number=_required_str(data, "number"),
            title=_optional_str(data, "title"),
            path=_str_list(data, "path"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            status=ProvisionStatus(_required_str(data, "status")),
            raw_text=_optional_str(data, "raw_text"),
            intro_lines=_str_list(data, "intro_lines"),
            articles=[Article.from_dict(item) for item in _dict_list(data, "articles")],
        )


@dataclass(slots=True, kw_only=True)
class Chapter:
    """Chapter containing direct articles and optional sections."""

    id: str
    number: str
    title: str | None
    path: list[str]
    source_span: SourceSpan | None = None
    status: ProvisionStatus = ProvisionStatus.ACTIVE
    raw_text: str | None = None
    sections: list[Section] = field(default_factory=list)
    articles: list[Article] = field(default_factory=list)
    intro_lines: list[str] = field(default_factory=list)

    def add_intro_line(self, line: CleanLine) -> None:
        self.intro_lines.append(line.text)
        self.source_span = merge_source_spans(self.source_span, line.source_span)

    def all_articles(self) -> list[Article]:
        """Return direct and section-contained articles."""

        section_articles = [
            article for section in self.sections for article in section.articles
        ]
        return [*self.articles, *section_articles]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "node_type": NodeType.CHAPTER.value,
            "number": self.number,
            "title": self.title,
            "path": self.path,
            "source_span": _source_span_to_dict(self.source_span),
            "status": self.status.value,
            "raw_text": self.raw_text,
            "intro_lines": self.intro_lines,
            "sections": [section.to_dict() for section in self.sections],
            "articles": [article.to_dict() for article in self.articles],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Chapter:
        return cls(
            id=_required_str(data, "id"),
            number=_required_str(data, "number"),
            title=_optional_str(data, "title"),
            path=_str_list(data, "path"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            status=ProvisionStatus(_required_str(data, "status")),
            raw_text=_optional_str(data, "raw_text"),
            intro_lines=_str_list(data, "intro_lines"),
            sections=[Section.from_dict(item) for item in _dict_list(data, "sections")],
            articles=[Article.from_dict(item) for item in _dict_list(data, "articles")],
        )


@dataclass(slots=True, kw_only=True)
class Table:
    """Table placeholder preserving raw table-like content."""

    id: str
    path: list[str]
    caption: str | None = None
    text: str = ""
    source_span: SourceSpan | None = None
    status: ProvisionStatus = ProvisionStatus.ACTIVE
    raw_text: str | None = None
    rows: list[list[str]] = field(default_factory=list)

    def add_line(self, line: CleanLine) -> None:
        self.text = _join_text(self.text, line.text)
        self.raw_text = _join_text(self.raw_text or "", line.text)
        self.source_span = merge_source_spans(self.source_span, line.source_span)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "node_type": NodeType.TABLE.value,
            "path": self.path,
            "caption": self.caption,
            "text": self.text,
            "source_span": _source_span_to_dict(self.source_span),
            "status": self.status.value,
            "raw_text": self.raw_text,
            "rows": self.rows,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Table:
        return cls(
            id=_required_str(data, "id"),
            path=_str_list(data, "path"),
            caption=_optional_str(data, "caption"),
            text=_required_str(data, "text"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            status=ProvisionStatus(_required_str(data, "status")),
            raw_text=_optional_str(data, "raw_text"),
            rows=_str_matrix(data, "rows"),
        )


@dataclass(slots=True, kw_only=True)
class Appendix:
    """Appendix placeholder for future appendix parsing."""

    id: str
    path: list[str]
    number: str | None = None
    title: str | None = None
    text: str = ""
    source_span: SourceSpan | None = None
    status: ProvisionStatus = ProvisionStatus.ACTIVE
    raw_text: str | None = None
    tables: list[Table] = field(default_factory=list)

    def add_line(self, line: CleanLine) -> None:
        self.text = _join_text(self.text, line.text)
        self.raw_text = _join_text(self.raw_text or "", line.text)
        self.source_span = merge_source_spans(self.source_span, line.source_span)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "node_type": NodeType.APPENDIX.value,
            "number": self.number,
            "title": self.title,
            "path": self.path,
            "text": self.text,
            "source_span": _source_span_to_dict(self.source_span),
            "status": self.status.value,
            "raw_text": self.raw_text,
            "tables": [table.to_dict() for table in self.tables],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Appendix:
        return cls(
            id=_required_str(data, "id"),
            path=_str_list(data, "path"),
            number=_optional_str(data, "number"),
            title=_optional_str(data, "title"),
            text=_required_str(data, "text"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            status=ProvisionStatus(_required_str(data, "status")),
            raw_text=_optional_str(data, "raw_text"),
            tables=[Table.from_dict(item) for item in _dict_list(data, "tables")],
        )


@dataclass(slots=True, kw_only=True)
class Regulation:
    """Parsed regulation tree."""

    id: str
    title: str
    source_file: str
    raw_title: str | None = None
    title_candidates: list[str] = field(default_factory=list)
    regulation_code: str | None = None
    path: list[str] = field(default_factory=list)
    institution: str | None = None
    effective_date: date | None = None
    amendment_date: date | None = None
    source_span: SourceSpan | None = None
    status: ProvisionStatus = ProvisionStatus.ACTIVE
    amendment_history: list[AmendmentEvent] = field(default_factory=list)
    preamble_lines: list[str] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)
    appendices: list[Appendix] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    incompleteness_flags: list[IncompletenessFlag] = field(default_factory=list)

    def add_preamble_line(self, line: CleanLine) -> None:
        self.preamble_lines.append(line.text)
        self.source_span = merge_source_spans(self.source_span, line.source_span)

    def all_articles(self) -> list[Article]:
        """Return every article in document order for currently modeled nodes."""

        return [
            article for chapter in self.chapters for article in chapter.all_articles()
        ]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "node_type": NodeType.REGULATION.value,
            "title": self.title,
            "source_file": self.source_file,
            "raw_title": self.raw_title,
            "title_candidates": self.title_candidates,
            "regulation_code": self.regulation_code,
            "path": self.path,
            "institution": self.institution,
            "effective_date": (
                self.effective_date.isoformat()
                if self.effective_date is not None
                else None
            ),
            "amendment_date": (
                self.amendment_date.isoformat()
                if self.amendment_date is not None
                else None
            ),
            "source_span": _source_span_to_dict(self.source_span),
            "status": self.status.value,
            "amendment_history": [
                amendment.to_dict() for amendment in self.amendment_history
            ],
            "preamble_lines": self.preamble_lines,
            "chapters": [chapter.to_dict() for chapter in self.chapters],
            "appendices": [appendix.to_dict() for appendix in self.appendices],
            "references": [reference.to_dict() for reference in self.references],
            "incompleteness_flags": [
                flag.to_dict() for flag in self.incompleteness_flags
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Regulation:
        return cls(
            id=_required_str(data, "id"),
            title=_required_str(data, "title"),
            source_file=_required_str(data, "source_file"),
            raw_title=_optional_str(data, "raw_title"),
            title_candidates=_str_list(data, "title_candidates"),
            regulation_code=_optional_str(data, "regulation_code"),
            path=_str_list(data, "path"),
            institution=_optional_str(data, "institution"),
            effective_date=_optional_date(data, "effective_date"),
            amendment_date=_optional_date(data, "amendment_date"),
            source_span=SourceSpan.from_dict(_optional_dict(data, "source_span")),
            status=ProvisionStatus(_required_str(data, "status")),
            amendment_history=[
                AmendmentEvent.from_dict(item)
                for item in _dict_list(data, "amendment_history")
            ],
            preamble_lines=_str_list(data, "preamble_lines"),
            chapters=[Chapter.from_dict(item) for item in _dict_list(data, "chapters")],
            appendices=[
                Appendix.from_dict(item) for item in _dict_list(data, "appendices")
            ],
            references=[
                Reference.from_dict(item) for item in _dict_list(data, "references")
            ],
            incompleteness_flags=[
                IncompletenessFlag.from_dict(item)
                for item in _dict_list(data, "incompleteness_flags")
            ],
        )


@dataclass(slots=True, kw_only=True)
class RegulationDocument:
    """Versioned root object for serialized parser output."""

    regulation: Regulation
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "regulation": self.regulation.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RegulationDocument:
        return cls(
            schema_version=_required_str(data, "schema_version"),
            regulation=Regulation.from_dict(_required_dict(data, "regulation")),
        )


@dataclass(slots=True, kw_only=True)
class ParseDiagnostic:
    """Recoverable parser diagnostic."""

    severity: DiagnosticSeverity
    code: str
    message: str
    source_span: SourceSpan | None = None
    line_text: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "source_span": _source_span_to_dict(self.source_span),
            "line_text": self.line_text,
        }


@dataclass(slots=True, kw_only=True)
class ParseStats:
    """Small parse summary for tests and CLI output."""

    line_count: int
    parsed_line_count: int
    unknown_line_count: int
    chapter_count: int
    article_count: int
    diagnostic_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "line_count": self.line_count,
            "parsed_line_count": self.parsed_line_count,
            "unknown_line_count": self.unknown_line_count,
            "chapter_count": self.chapter_count,
            "article_count": self.article_count,
            "diagnostic_count": self.diagnostic_count,
        }


@dataclass(slots=True, kw_only=True)
class ParseResult:
    """Result returned by parser entry points."""

    document: RegulationDocument | None
    diagnostics: list[ParseDiagnostic]
    stats: ParseStats

    def to_dict(self) -> dict[str, object]:
        return {
            "document": None if self.document is None else self.document.to_dict(),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "stats": self.stats.to_dict(),
        }


def _source_span_to_dict(source_span: SourceSpan | None) -> dict[str, object] | None:
    if source_span is None:
        return None
    return source_span.to_dict()


def _join_text(existing: str, addition: str) -> str:
    if not existing:
        return addition
    return f"{existing}\n{addition}"


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


def _optional_int(data: dict[str, object], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise TypeError(f"Expected '{key}' to be int or None.")
    return value


def _optional_float(data: dict[str, object], key: str) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int | float):
        raise TypeError(f"Expected '{key}' to be float or None.")
    return float(value)


def _optional_date(data: dict[str, object], key: str) -> date | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Expected '{key}' to be ISO date string or None.")
    return date.fromisoformat(value)


def _required_dict(data: dict[str, object], key: str) -> dict[str, object]:
    value = data[key]
    if not isinstance(value, dict):
        raise TypeError(f"Expected '{key}' to be object.")
    return cast(dict[str, object], value)


def _optional_dict(data: dict[str, object], key: str) -> dict[str, object] | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError(f"Expected '{key}' to be object or None.")
    return cast(dict[str, object], value)


def _str_list(data: dict[str, object], key: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise TypeError(f"Expected '{key}' to be list.")
    if not all(isinstance(item, str) for item in value):
        raise TypeError(f"Expected every item in '{key}' to be str.")
    return cast(list[str], value)


def _dict_list(data: dict[str, object], key: str) -> list[dict[str, object]]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise TypeError(f"Expected '{key}' to be list.")
    if not all(isinstance(item, dict) for item in value):
        raise TypeError(f"Expected every item in '{key}' to be object.")
    return cast(list[dict[str, object]], value)


def _str_matrix(data: dict[str, object], key: str) -> list[list[str]]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise TypeError(f"Expected '{key}' to be list.")
    if not all(
        isinstance(row, list) and all(isinstance(item, str) for item in row)
        for row in value
    ):
        raise TypeError(f"Expected every row in '{key}' to be a list of str.")
    return cast(list[list[str]], value)
