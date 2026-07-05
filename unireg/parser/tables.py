"""Table placeholder parser."""

from __future__ import annotations

from unireg.models import Appendix, CleanLine, Table
from unireg.parser.ids import table_id
from unireg.parser.patterns import AppendixHeading, TableHeading, parse_table_heading


class TableParser:
    """Create table placeholders without attempting full table extraction."""

    def match(self, line: CleanLine) -> TableHeading | None:
        return parse_table_heading(line.text)

    def create_for_appendix(
        self,
        *,
        appendix: Appendix,
        line: CleanLine,
        heading: AppendixHeading,
        table_index: int,
    ) -> Table:
        fragment = _table_fragment(heading.number, table_index)
        table = Table(
            id=table_id(appendix.id, fragment),
            path=[*appendix.path, f"table:{fragment}"],
            caption=heading.title,
            text=heading.body_text or "",
            raw_text=line.text,
            source_span=line.source_span,
        )
        return table

    def create_table(
        self,
        *,
        appendix: Appendix,
        line: CleanLine,
        heading: TableHeading,
        table_index: int,
    ) -> Table:
        fragment = _table_fragment(heading.number, table_index)
        table = Table(
            id=table_id(appendix.id, fragment),
            path=[*appendix.path, f"table:{fragment}"],
            caption=heading.caption,
            text=heading.body_text or "",
            raw_text=line.text,
            source_span=line.source_span,
        )
        return table

    @staticmethod
    def append_to_table(table: Table, line: CleanLine) -> None:
        table.add_line(line)


def _table_fragment(number: str | None, table_index: int) -> str:
    return number or str(table_index)
