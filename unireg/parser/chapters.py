"""Chapter heading parser."""

from __future__ import annotations

from unireg.models import Chapter, CleanLine
from unireg.parser.ids import chapter_id
from unireg.parser.patterns import ChapterHeading, parse_chapter_heading


class ChapterParser:
    """Create chapter nodes from chapter heading lines."""

    def match(self, line: CleanLine) -> ChapterHeading | None:
        return parse_chapter_heading(line.text)

    def create_chapter(
        self,
        *,
        regulation_id: str,
        line: CleanLine,
        heading: ChapterHeading,
    ) -> Chapter:
        path = [f"chapter:{heading.number}"]
        return Chapter(
            id=chapter_id(regulation_id, heading.number),
            number=heading.number,
            title=heading.title,
            path=path,
            source_span=line.source_span,
        )
