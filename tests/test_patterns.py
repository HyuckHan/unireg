from __future__ import annotations

from unireg.parser.patterns import parse_clause_segments, parse_section_heading


def test_parse_section_heading() -> None:
    heading = parse_section_heading("제1절 통칙")

    assert heading is not None
    assert heading.number == "1"
    assert heading.title == "통칙"


def test_parse_section_heading_ignores_non_section() -> None:
    assert parse_section_heading("제1조(목적)") is None


def test_parse_clause_segments_splits_circled_markers() -> None:
    segments = parse_clause_segments("① 첫째 조항② 둘째 조항")

    assert [segment.clause_number for segment in segments] == ["1", "2"]
    assert [segment.text for segment in segments] == ["첫째 조항", "둘째 조항"]
    assert [segment.raw_text for segment in segments] == [
        "① 첫째 조항",
        "② 둘째 조항",
    ]


def test_parse_clause_segments_preserves_unnumbered_prefix() -> None:
    segments = parse_clause_segments("본문 머리말 ① 첫째 조항")

    assert [segment.clause_number for segment in segments] == [None, "1"]
    assert [segment.text for segment in segments] == ["본문 머리말", "첫째 조항"]
