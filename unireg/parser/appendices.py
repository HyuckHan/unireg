"""Appendix and supplementary provision parser."""

from __future__ import annotations

from unireg.models import Appendix, CleanLine
from unireg.parser.ids import appendix_id
from unireg.parser.patterns import AppendixHeading, parse_appendix_heading


class AppendixParser:
    """Create appendix placeholders from appendix heading lines."""

    def match(self, line: CleanLine) -> AppendixHeading | None:
        return parse_appendix_heading(line.text)

    def create_appendix(
        self,
        *,
        regulation_id: str,
        line: CleanLine,
        heading: AppendixHeading,
        appendix_index: int,
    ) -> Appendix:
        fragment = _appendix_fragment(heading, appendix_index)
        appendix = Appendix(
            id=appendix_id(regulation_id, fragment),
            path=[f"appendix:{fragment}"],
            number=heading.number,
            title=heading.title,
            text=heading.body_text or "",
            raw_text=line.text,
            source_span=line.source_span,
        )
        return appendix

    @staticmethod
    def append_to_appendix(appendix: Appendix, line: CleanLine) -> None:
        appendix.add_line(line)


def _appendix_fragment(heading: AppendixHeading, appendix_index: int) -> str:
    if heading.kind == "supplementary":
        return f"supplementary-{appendix_index}"
    if heading.kind == "annex":
        return f"annex-{heading.number or appendix_index}"
    if heading.kind == "form":
        return f"form-{heading.number or appendix_index}"
    return f"appendix-{appendix_index}"
