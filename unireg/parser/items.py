"""Item and sub-item parser."""

from __future__ import annotations

from unireg.models import Clause, CleanLine, Item, SubItem, merge_source_spans
from unireg.parser.ids import item_id, sub_item_id
from unireg.parser.patterns import (
    ItemSegment,
    SubItemSegment,
    parse_item_segments,
    parse_sub_item_segments,
)


class ItemParser:
    """Create item and sub-item nodes under clauses."""

    def add_items_from_text(self, clause: Clause, line: CleanLine, text: str) -> None:
        segments = parse_item_segments(text)
        numbered_segments = [
            segment for segment in segments if segment.item_number is not None
        ]
        if not numbered_segments:
            return

        for segment in numbered_segments:
            item = self.create_item(
                clause=clause,
                line=line,
                segment=segment,
            )
            clause.items.append(item)

    def append_continuation(self, clause: Clause, line: CleanLine) -> None:
        segments = parse_item_segments(line.text)
        numbered_segments = [
            segment for segment in segments if segment.item_number is not None
        ]
        if numbered_segments:
            for segment in numbered_segments:
                clause.items.append(
                    self.create_item(
                        clause=clause,
                        line=line,
                        segment=segment,
                    )
                )
            return

        if not clause.items:
            return

        last_item = clause.items[-1]
        if last_item.sub_items:
            self.append_to_sub_item(last_item.sub_items[-1], line)
        else:
            self.append_to_item(last_item, line)

    def create_item(
        self,
        *,
        clause: Clause,
        line: CleanLine,
        segment: ItemSegment,
    ) -> Item:
        if segment.item_number is None:
            raise ValueError("Cannot create an Item from an unnumbered segment.")

        item = Item(
            id=item_id(clause.id, segment.item_number),
            item_number=segment.item_number,
            path=[*clause.path, f"item:{segment.item_number}"],
            text=segment.text,
            raw_text=segment.raw_text,
            source_span=line.source_span,
        )
        self._populate_sub_items(item=item, line=line, text=segment.text)
        return item

    @staticmethod
    def append_to_item(item: Item, line: CleanLine) -> None:
        item.text = _join_text(item.text, line.text)
        item.raw_text = _join_text(item.raw_text or "", line.text)
        item.source_span = merge_source_spans(item.source_span, line.source_span)

    @staticmethod
    def append_to_sub_item(sub_item: SubItem, line: CleanLine) -> None:
        sub_item.text = _join_text(sub_item.text, line.text)
        sub_item.raw_text = _join_text(sub_item.raw_text or "", line.text)
        sub_item.source_span = merge_source_spans(
            sub_item.source_span,
            line.source_span,
        )

    def _populate_sub_items(self, *, item: Item, line: CleanLine, text: str) -> None:
        segments = parse_sub_item_segments(text)
        if not segments:
            return

        first_start = text.find(f"{segments[0].sub_item_number}.")
        if first_start > 0:
            item.text = text[:first_start].strip()
        else:
            item.text = ""

        for segment in segments:
            item.sub_items.append(
                self.create_sub_item(
                    item=item,
                    line=line,
                    segment=segment,
                )
            )

    @staticmethod
    def create_sub_item(
        *,
        item: Item,
        line: CleanLine,
        segment: SubItemSegment,
    ) -> SubItem:
        return SubItem(
            id=sub_item_id(item.id, segment.sub_item_number),
            sub_item_number=segment.sub_item_number,
            path=[*item.path, f"sub-item:{segment.sub_item_number}"],
            text=segment.text,
            raw_text=segment.raw_text,
            source_span=line.source_span,
        )


def _join_text(existing: str, addition: str) -> str:
    if not existing:
        return addition
    return f"{existing}\n{addition}"
