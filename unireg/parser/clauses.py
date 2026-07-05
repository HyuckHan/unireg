"""Clause parser."""

from __future__ import annotations

from unireg.models import Clause, CleanLine, merge_source_spans
from unireg.parser.ids import clause_id
from unireg.parser.patterns import ClauseSegment, parse_clause_segments


class ClauseParser:
    """Create clause nodes from article body text."""

    def split(self, text: str) -> list[ClauseSegment]:
        return parse_clause_segments(text)

    def create_clause(
        self,
        *,
        article_id: str,
        article_path: list[str],
        line: CleanLine,
        segment: ClauseSegment,
        clause_index: int,
    ) -> Clause:
        fragment = segment.clause_number or _unnumbered_fragment(clause_index)
        return Clause(
            id=clause_id(article_id, fragment),
            path=[*article_path, f"clause:{fragment}"],
            clause_number=segment.clause_number,
            text=segment.text,
            raw_text=segment.raw_text,
            source_span=line.source_span,
        )

    @staticmethod
    def append_to_clause(clause: Clause, line: CleanLine) -> None:
        clause.text = _join_text(clause.text, line.text)
        clause.raw_text = _join_text(clause.raw_text or "", line.text)
        clause.source_span = merge_source_spans(clause.source_span, line.source_span)


def _unnumbered_fragment(clause_index: int) -> str:
    if clause_index == 1:
        return "unnumbered"
    return f"unnumbered-{clause_index}"


def _join_text(existing: str, addition: str) -> str:
    if not existing:
        return addition
    return f"{existing}\n{addition}"
