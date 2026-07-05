"""Phase 1 regulation parser."""

from __future__ import annotations

from pathlib import Path

from unireg.cleaning import DocumentCleaner
from unireg.loaders import PDFLoader
from unireg.models import (
    Chapter,
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
    merge_source_spans,
)
from unireg.parser.articles import ArticleParser
from unireg.parser.chapters import ChapterParser
from unireg.parser.ids import chapter_id, regulation_id


class RegulationParser:
    """Parse a regulation through chapter and article hierarchy."""

    def __init__(
        self,
        *,
        pdf_loader: PDFLoader | None = None,
        cleaner: DocumentCleaner | None = None,
        chapter_parser: ChapterParser | None = None,
        article_parser: ArticleParser | None = None,
    ) -> None:
        self._pdf_loader = pdf_loader or PDFLoader()
        self._cleaner = cleaner or DocumentCleaner()
        self._chapter_parser = chapter_parser or ChapterParser()
        self._article_parser = article_parser or ArticleParser()

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
        title = (
            title_line.text
            if title_line is not None
            else Path(document.source_file).stem
        )
        reg_id = regulation_id(title, document.source_file)
        regulation = Regulation(
            id=reg_id,
            title=title,
            source_file=document.source_file,
            source_span=title_line.source_span if title_line is not None else None,
        )

        current_chapter = None
        current_article = None
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
                    current_article = None
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

                current_article = self._article_parser.create_article(
                    chapter_id=current_chapter.id,
                    chapter_path=current_chapter.path,
                    regulation_title=regulation.title,
                    chapter_title=current_chapter.title,
                    line=line,
                    heading=article_heading,
                )
                current_chapter.articles.append(current_article)
                parsed_line_count += 1
                continue

            if current_article is not None:
                current_article.add_body_line(line)
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
