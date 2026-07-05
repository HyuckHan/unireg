"""Phase 1 regulation parser."""

from __future__ import annotations

from pathlib import Path

from unireg.cleaning import DocumentCleaner
from unireg.loaders import PDFLoader
from unireg.models import (
    Appendix,
    Article,
    Chapter,
    Clause,
    CleanDocument,
    CleanLine,
    DiagnosticSeverity,
    ExtractedDocument,
    ExtractedPage,
    ParseDiagnostic,
    ParseResult,
    ParseStats,
    Regulation,
    RegulationDocument,
    Section,
    Table,
    merge_source_spans,
)
from unireg.parser.amendments import AmendmentStatusEnricher
from unireg.parser.appendices import AppendixParser
from unireg.parser.articles import ArticleParser
from unireg.parser.chapters import ChapterParser
from unireg.parser.clauses import ClauseParser
from unireg.parser.ids import chapter_id, regulation_id
from unireg.parser.metadata import RegulationMetadataNormalizer
from unireg.parser.patterns import AppendixHeading
from unireg.parser.references import ReferenceIncompletenessEnricher
from unireg.parser.sections import SectionParser
from unireg.parser.tables import TableParser


class RegulationParser:
    """Parse a regulation through chapter and article hierarchy."""

    def __init__(
        self,
        *,
        pdf_loader: PDFLoader | None = None,
        cleaner: DocumentCleaner | None = None,
        chapter_parser: ChapterParser | None = None,
        section_parser: SectionParser | None = None,
        article_parser: ArticleParser | None = None,
        clause_parser: ClauseParser | None = None,
        appendix_parser: AppendixParser | None = None,
        table_parser: TableParser | None = None,
        metadata_normalizer: RegulationMetadataNormalizer | None = None,
        amendment_enricher: AmendmentStatusEnricher | None = None,
        reference_enricher: ReferenceIncompletenessEnricher | None = None,
    ) -> None:
        self._pdf_loader = pdf_loader or PDFLoader()
        self._cleaner = cleaner or DocumentCleaner()
        self._chapter_parser = chapter_parser or ChapterParser()
        self._section_parser = section_parser or SectionParser()
        self._article_parser = article_parser or ArticleParser()
        self._clause_parser = clause_parser or ClauseParser()
        self._appendix_parser = appendix_parser or AppendixParser()
        self._table_parser = table_parser or TableParser()
        self._metadata_normalizer = (
            metadata_normalizer or RegulationMetadataNormalizer()
        )
        self._amendment_enricher = amendment_enricher or AmendmentStatusEnricher()
        self._reference_enricher = (
            reference_enricher or ReferenceIncompletenessEnricher()
        )

    def parse_file(self, source_file: str | Path) -> ParseResult:
        """Parse a source file.

        Phase 1 supports PDF files through `PDFLoader`.
        """

        path = Path(source_file)
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Unsupported source file type: {path.suffix}")
        return self.parse_extracted_document(self._pdf_loader.load(path))

    def parse_text(self, text: str, *, source_file: str = "<text>") -> ParseResult:
        """Parse already extracted text. Useful for tests and fixtures."""

        document = ExtractedDocument(
            source_file=source_file,
            pages=[ExtractedPage(page_number=1, text=text)],
            extraction_method="text",
        )
        return self.parse_extracted_document(document)

    def parse_extracted_document(self, document: ExtractedDocument) -> ParseResult:
        clean_document = self._cleaner.clean(document)
        return self.parse_clean_document(clean_document)

    def parse_clean_document(self, document: CleanDocument) -> ParseResult:
        diagnostics: list[ParseDiagnostic] = []
        title_line = self._find_title_line(document.lines)
        metadata = self._metadata_normalizer.normalize(
            source_file=document.source_file,
            title_line=title_line,
            lines=document.lines,
        )
        reg_id = regulation_id(metadata.title, document.source_file)
        regulation = Regulation(
            id=reg_id,
            title=metadata.title,
            source_file=document.source_file,
            raw_title=metadata.raw_title,
            title_candidates=metadata.title_candidates,
            regulation_code=metadata.regulation_code,
            institution=metadata.institution,
            source_span=title_line.source_span if title_line is not None else None,
        )
        diagnostics.extend(
            ParseDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                code=warning.code,
                message=warning.message,
                source_span=title_line.source_span if title_line is not None else None,
                line_text=metadata.raw_title,
            )
            for warning in metadata.warnings
        )

        current_chapter = None
        current_section = None
        current_article = None
        current_clause = None
        current_appendix: Appendix | None = None
        current_table: Table | None = None
        highest_chapter_number = 0
        parsed_line_count = 0
        unknown_line_count = 0

        for line in document.lines:
            regulation.source_span = merge_source_spans(
                regulation.source_span,
                line.source_span,
            )

            if title_line is not None and line.line_number == title_line.line_number:
                parsed_line_count += 1
                continue

            appendix_heading = self._appendix_parser.match(line)
            if appendix_heading is not None:
                current_appendix = self._create_appendix(
                    regulation_id=regulation.id,
                    line=line,
                    heading=appendix_heading,
                    appendix_index=len(regulation.appendices) + 1,
                )
                regulation.appendices.append(current_appendix)
                current_table = None
                if appendix_heading.creates_table:
                    current_table = self._create_table_for_appendix(
                        appendix=current_appendix,
                        line=line,
                        heading=appendix_heading,
                    )
                    current_appendix.tables.append(current_table)
                current_chapter = None
                current_section = None
                current_article = None
                current_clause = None
                parsed_line_count += 1
                continue

            if current_appendix is not None:
                current_table = self._add_appendix_line(
                    appendix=current_appendix,
                    line=line,
                    current_table=current_table,
                )
                parsed_line_count += 1
                continue

            chapter_heading = self._chapter_parser.match(line)
            if chapter_heading is not None:
                chapter_number = int(chapter_heading.number)
                if chapter_number > highest_chapter_number:
                    highest_chapter_number = chapter_number
                    current_chapter = self._chapter_parser.create_chapter(
                        regulation_id=regulation.id,
                        line=line,
                        heading=chapter_heading,
                    )
                    regulation.chapters.append(current_chapter)
                    current_section = None
                    current_article = None
                    current_clause = None
                    parsed_line_count += 1
                    continue

            section_heading = self._section_parser.match(line)
            if section_heading is not None:
                if current_chapter is None:
                    current_chapter = self._create_implicit_chapter(
                        regulation_id=regulation.id,
                        line=line,
                    )
                    regulation.chapters.append(current_chapter)
                    diagnostics.append(
                        ParseDiagnostic(
                            severity=DiagnosticSeverity.WARNING,
                            code="section_before_chapter",
                            message="Section appeared before any chapter; "
                            "attached it to an implicit chapter.",
                            source_span=line.source_span,
                            line_text=line.text,
                        )
                    )

                current_section = self._section_parser.create_section(
                    chapter_id=current_chapter.id,
                    chapter_path=current_chapter.path,
                    line=line,
                    heading=section_heading,
                )
                current_chapter.sections.append(current_section)
                current_article = None
                current_clause = None
                parsed_line_count += 1
                continue

            article_heading = self._article_parser.match(line)
            if article_heading is not None:
                if current_chapter is None:
                    current_chapter = self._create_implicit_chapter(
                        regulation_id=regulation.id,
                        line=line,
                    )
                    regulation.chapters.append(current_chapter)
                    diagnostics.append(
                        ParseDiagnostic(
                            severity=DiagnosticSeverity.WARNING,
                            code="article_before_chapter",
                            message="Article appeared before any chapter; "
                            "attached it to an implicit chapter.",
                            source_span=line.source_span,
                            line_text=line.text,
                        )
                    )

                parent_id, parent_path = self._article_parent(
                    current_chapter=current_chapter,
                    current_section=current_section,
                )
                current_article = self._article_parser.create_article(
                    parent_id=parent_id,
                    parent_path=parent_path,
                    regulation_title=regulation.title,
                    chapter_title=current_chapter.title,
                    section_title=(
                        current_section.title if current_section is not None else None
                    ),
                    line=line,
                    heading=article_heading,
                )
                if current_section is not None:
                    current_section.articles.append(current_article)
                else:
                    current_chapter.articles.append(current_article)
                if article_heading.body_text is not None:
                    current_clause = self._add_article_line(
                        article=current_article,
                        line=self._line_with_text(line, article_heading.body_text),
                    )
                else:
                    current_clause = None
                parsed_line_count += 1
                continue

            if current_article is not None:
                current_clause = self._add_article_line(
                    article=current_article,
                    line=line,
                    current_clause=current_clause,
                )
                parsed_line_count += 1
                continue

            if current_section is not None:
                current_section.add_intro_line(line)
                parsed_line_count += 1
                continue

            if current_chapter is not None:
                current_chapter.add_intro_line(line)
                parsed_line_count += 1
                continue

            regulation.add_preamble_line(line)
            diagnostics.append(
                ParseDiagnostic(
                    severity=DiagnosticSeverity.INFO,
                    code="preamble_line",
                    message="Line before the first chapter/article was preserved "
                    "as regulation preamble.",
                    source_span=line.source_span,
                    line_text=line.text,
                )
            )
            unknown_line_count += 1

        self._amendment_enricher.enrich(regulation)
        self._reference_enricher.enrich(regulation)
        article_count = len(regulation.all_articles())
        stats = ParseStats(
            line_count=len(document.lines),
            parsed_line_count=parsed_line_count,
            unknown_line_count=unknown_line_count,
            chapter_count=len(regulation.chapters),
            article_count=article_count,
            diagnostic_count=len(diagnostics),
        )
        return ParseResult(
            document=RegulationDocument(regulation=regulation),
            diagnostics=diagnostics,
            stats=stats,
        )

    def _find_title_line(self, lines: list[CleanLine]) -> CleanLine | None:
        for line in lines:
            if self._chapter_parser.match(line) is not None:
                return None
            if self._section_parser.match(line) is not None:
                return None
            if self._article_parser.match(line) is not None:
                return None
            if line.text:
                return line
        return None

    @staticmethod
    def _create_implicit_chapter(
        *,
        regulation_id: str,
        line: CleanLine,
    ) -> Chapter:
        implicit_id = chapter_id(regulation_id, "implicit")
        return Chapter(
            id=implicit_id,
            number="implicit",
            title=None,
            path=["chapter:implicit"],
            source_span=line.source_span,
        )

    @staticmethod
    def _article_parent(
        *,
        current_chapter: Chapter,
        current_section: Section | None,
    ) -> tuple[str, list[str]]:
        if current_section is not None:
            return current_section.id, current_section.path
        return current_chapter.id, current_chapter.path

    def _add_article_line(
        self,
        *,
        article: Article,
        line: CleanLine,
        current_clause: Clause | None = None,
    ) -> Clause | None:
        article.add_body_line(line)

        segments = self._clause_parser.split(line.text)
        has_numbered_segment = any(
            segment.clause_number is not None for segment in segments
        )
        if not has_numbered_segment and current_clause is not None:
            self._clause_parser.append_to_clause(current_clause, line)
            return current_clause

        last_clause = current_clause
        for segment in segments:
            clause = self._clause_parser.create_clause(
                article_id=article.id,
                article_path=article.path,
                line=line,
                segment=segment,
                clause_index=len(article.clauses) + 1,
            )
            article.clauses.append(clause)
            last_clause = clause
        return last_clause

    def _add_appendix_line(
        self,
        *,
        appendix: Appendix,
        line: CleanLine,
        current_table: Table | None,
    ) -> Table | None:
        table_heading = self._table_parser.match(line)
        if table_heading is not None:
            self._appendix_parser.append_to_appendix(appendix, line)
            table = self._table_parser.create_table(
                appendix=appendix,
                line=line,
                heading=table_heading,
                table_index=len(appendix.tables) + 1,
            )
            appendix.tables.append(table)
            return table

        self._appendix_parser.append_to_appendix(appendix, line)
        if current_table is not None:
            self._table_parser.append_to_table(current_table, line)
        return current_table

    @staticmethod
    def _line_with_text(line: CleanLine, text: str) -> CleanLine:
        return CleanLine(
            text=text,
            source_span=line.source_span,
            line_number=line.line_number,
        )

    def _create_appendix(
        self,
        *,
        regulation_id: str,
        line: CleanLine,
        heading: AppendixHeading,
        appendix_index: int,
    ) -> Appendix:
        return self._appendix_parser.create_appendix(
            regulation_id=regulation_id,
            line=line,
            heading=heading,
            appendix_index=appendix_index,
        )

    def _create_table_for_appendix(
        self,
        *,
        appendix: Appendix,
        line: CleanLine,
        heading: AppendixHeading,
    ) -> Table:
        return self._table_parser.create_for_appendix(
            appendix=appendix,
            line=line,
            heading=heading,
            table_index=len(appendix.tables) + 1,
        )
