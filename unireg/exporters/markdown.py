"""Markdown exporter for parsed regulation hierarchy."""

from __future__ import annotations

from pathlib import Path

from unireg.models import (
    Appendix,
    Article,
    Chapter,
    Clause,
    IncompletenessFlag,
    Item,
    ParseResult,
    Reference,
    Regulation,
    RegulationDocument,
    Section,
    SubItem,
    Table,
)
from unireg.parser.patterns import parse_item_segments

ExportableMarkdown = ParseResult | Regulation | RegulationDocument


class MarkdownExporter:
    """Export the canonical hierarchy to deterministic Markdown."""

    def dumps(self, value: ExportableMarkdown, *, trailing_newline: bool = True) -> str:
        regulation = _regulation_from_exportable(value)
        lines: list[str] = []
        _append_heading(lines, 1, regulation.title)
        _append_metadata(lines, regulation)

        if regulation.preamble_lines:
            _append_heading(lines, 2, "Preamble")
            _append_paragraph(lines, "\n".join(regulation.preamble_lines))

        for chapter in regulation.chapters:
            _append_chapter(lines, chapter)

        if regulation.appendices:
            _append_heading(lines, 2, "Appendices")
            for appendix in regulation.appendices:
                _append_appendix(lines, appendix)

        text = "\n".join(lines).rstrip()
        if trailing_newline:
            return f"{text}\n"
        return text

    def dump(self, value: ExportableMarkdown, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.dumps(value), encoding="utf-8")


def _regulation_from_exportable(value: ExportableMarkdown) -> Regulation:
    if isinstance(value, ParseResult):
        if value.document is None:
            raise ValueError("Cannot export ParseResult without a document.")
        return value.document.regulation
    if isinstance(value, RegulationDocument):
        return value.regulation
    return value


def _append_metadata(lines: list[str], regulation: Regulation) -> None:
    metadata = [f"- Source file: {regulation.source_file}"]
    if regulation.effective_date is not None:
        metadata.append(f"- Effective date: {regulation.effective_date.isoformat()}")
    if regulation.amendment_date is not None:
        metadata.append(f"- Amendment date: {regulation.amendment_date.isoformat()}")

    if lines and lines[-1] != "":
        lines.append("")
    lines.extend(metadata)
    lines.append("")


def _append_chapter(lines: list[str], chapter: Chapter) -> None:
    _append_heading(lines, 2, _numbered_title(f"제{chapter.number}장", chapter.title))
    for intro_line in chapter.intro_lines:
        _append_paragraph(lines, intro_line)
    for article in chapter.articles:
        _append_article(lines, article, level=3)
    for section in chapter.sections:
        _append_section(lines, section)


def _append_section(lines: list[str], section: Section) -> None:
    _append_heading(lines, 3, _numbered_title(f"제{section.number}절", section.title))
    for intro_line in section.intro_lines:
        _append_paragraph(lines, intro_line)
    for article in section.articles:
        _append_article(lines, article, level=4)


def _append_article(lines: list[str], article: Article, *, level: int) -> None:
    title = _numbered_title(article.article_number, article.title)
    _append_heading(lines, level, title)
    if article.clauses:
        for clause in article.clauses:
            _append_clause(lines, clause)
    elif article.text:
        _append_paragraph(lines, article.text)
    _append_reference_notes(lines, article.references, article.incompleteness_flags)


def _append_clause(lines: list[str], clause: Clause) -> None:
    prefix = _clause_prefix(clause)
    if clause.clause_number is None:
        if prefix:
            _append_paragraph(lines, prefix)
    else:
        lines.append(_bullet(0, f"제{clause.clause_number}항", prefix))

    for item in clause.items:
        _append_item(lines, item)
    _append_reference_notes(lines, clause.references, clause.incompleteness_flags)


def _append_item(lines: list[str], item: Item) -> None:
    lines.append(_bullet(1, f"제{item.item_number}호", item.text))
    for sub_item in item.sub_items:
        _append_sub_item(lines, sub_item)
    _append_reference_notes(lines, item.references, item.incompleteness_flags)


def _append_sub_item(lines: list[str], sub_item: SubItem) -> None:
    lines.append(_bullet(2, f"{sub_item.sub_item_number}목", sub_item.text))
    _append_reference_notes(lines, sub_item.references, sub_item.incompleteness_flags)


def _append_appendix(lines: list[str], appendix: Appendix) -> None:
    _append_heading(lines, 3, appendix.title or "Appendix")
    if appendix.text and not appendix.tables:
        _append_paragraph(lines, appendix.text)
    for table in appendix.tables:
        _append_table(lines, table)


def _append_table(lines: list[str], table: Table) -> None:
    _append_heading(lines, 4, f"Table: {table.caption or 'Table'}")
    if table.text:
        _append_paragraph(lines, table.text)


def _append_reference_notes(
    lines: list[str],
    references: list[Reference],
    incompleteness_flags: list[IncompletenessFlag],
) -> None:
    if (references or incompleteness_flags) and lines and lines[-1] != "":
        lines.append("")
    for reference in references:
        status = f"{reference.reference_type.value}/{reference.status.value}"
        target = (
            f" target={reference.required_document_name}"
            if reference.required_document_name is not None
            else ""
        )
        lines.append(f"> Reference ({status}{target}): {reference.raw_text}")
    for flag in incompleteness_flags:
        missing = (
            f" missing={flag.missing_source}" if flag.missing_source is not None else ""
        )
        lines.append(f"> Incomplete ({flag.flag_type.value}{missing}): {flag.raw_text}")


def _append_heading(lines: list[str], level: int, title: str) -> None:
    if lines and lines[-1] != "":
        lines.append("")
    lines.append(f"{'#' * level} {title}")
    lines.append("")


def _append_paragraph(lines: list[str], text: str) -> None:
    if lines and lines[-1] != "":
        lines.append("")
    lines.extend(text.splitlines())
    lines.append("")


def _numbered_title(number: str, title: str | None) -> str:
    if title:
        return f"{number} {title}"
    return number


def _clause_prefix(clause: Clause) -> str:
    if not clause.items:
        return clause.text
    prefixes = [
        segment.text
        for segment in parse_item_segments(clause.text)
        if segment.item_number is None
    ]
    return " ".join(prefix for prefix in prefixes if prefix).strip()


def _bullet(depth: int, marker: str, text: str) -> str:
    indent = "  " * depth
    if text:
        return f"{indent}- {marker} {text}"
    return f"{indent}- {marker}"
