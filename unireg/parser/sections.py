"""Section heading parser."""

from __future__ import annotations

from unireg.models import CleanLine, Section
from unireg.parser.ids import section_id
from unireg.parser.patterns import SectionHeading, parse_section_heading


class SectionParser:
    """Create section nodes from section heading lines."""

    def match(self, line: CleanLine) -> SectionHeading | None:
        return parse_section_heading(line.text)

    def create_section(
        self,
        *,
        chapter_id: str,
        chapter_path: list[str],
        line: CleanLine,
        heading: SectionHeading,
    ) -> Section:
        path = [*chapter_path, f"section:{heading.number}"]
        return Section(
            id=section_id(chapter_id, heading.number),
            number=heading.number,
            title=heading.title,
            path=path,
            source_span=line.source_span,
        )
