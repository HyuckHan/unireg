"""Core dataclasses for Phase 1 parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

SCHEMA_VERSION = "unireg.regulation.v1"


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
        }


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
class Article:
    """Article-level representation for Phase 1.

    Clause parsing is intentionally not implemented yet, so article body lines
    keep all content below the article heading.
    """

    id: str
    article_number: str
    title: str | None
    path: list[str]
    source_span: SourceSpan | None = None
    body_lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.body_lines)

    def add_body_line(self, line: CleanLine) -> None:
        self.body_lines.append(line.text)
        self.source_span = merge_source_spans(self.source_span, line.source_span)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "article_number": self.article_number,
            "title": self.title,
            "path": self.path,
            "source_span": _source_span_to_dict(self.source_span),
            "body_lines": self.body_lines,
        }


@dataclass(slots=True, kw_only=True)
class Chapter:
    """Chapter containing parsed articles."""

    id: str
    number: str
    title: str | None
    path: list[str]
    source_span: SourceSpan | None = None
    articles: list[Article] = field(default_factory=list)
    intro_lines: list[str] = field(default_factory=list)

    def add_intro_line(self, line: CleanLine) -> None:
        self.intro_lines.append(line.text)
        self.source_span = merge_source_spans(self.source_span, line.source_span)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "path": self.path,
            "source_span": _source_span_to_dict(self.source_span),
            "intro_lines": self.intro_lines,
            "articles": [article.to_dict() for article in self.articles],
        }


@dataclass(slots=True, kw_only=True)
class Regulation:
    """Parsed regulation tree for Phase 1."""

    id: str
    title: str
    source_file: str
    source_span: SourceSpan | None = None
    preamble_lines: list[str] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)

    def add_preamble_line(self, line: CleanLine) -> None:
        self.preamble_lines.append(line.text)
        self.source_span = merge_source_spans(self.source_span, line.source_span)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "source_file": self.source_file,
            "source_span": _source_span_to_dict(self.source_span),
            "preamble_lines": self.preamble_lines,
            "chapters": [chapter.to_dict() for chapter in self.chapters],
        }


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
            "diagnostics": [
                diagnostic.to_dict() for diagnostic in self.diagnostics
            ],
            "stats": self.stats.to_dict(),
        }


def _source_span_to_dict(source_span: SourceSpan | None) -> dict[str, object] | None:
    if source_span is None:
        return None
    return source_span.to_dict()
