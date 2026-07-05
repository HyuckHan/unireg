from __future__ import annotations

from unireg.parser.patterns import parse_section_heading


def test_parse_section_heading() -> None:
    heading = parse_section_heading("제1절 통칙")

    assert heading is not None
    assert heading.number == "1"
    assert heading.title == "통칙"


def test_parse_section_heading_ignores_non_section() -> None:
    assert parse_section_heading("제1조(목적)") is None
