from __future__ import annotations

from unireg.models import CleanLine, SourceSpan
from unireg.parser import RegulationMetadataNormalizer, RegulationParser


def test_metadata_normalizer_cleans_external_university_title_examples() -> None:
    normalizer = RegulationMetadataNormalizer()

    cases = [
        (
            "학 칙[시행 2026.04.15.] [2026.04.14.,일부개정]",
            "unireg-eval/university_dongduk/학칙.pdf",
            "학칙",
            None,
            None,
        ),
        (
            "동양미래대학교 규정집 제2편 학칙 2-0-1~1",
            "unireg-eval/university_dongyang/학칙.pdf",
            "학칙",
            "동양미래대학교",
            "2-0-1~1",
        ),
        (
            "덕성여자대학교학칙 2-1-1-1",
            "unireg-eval/university_duksung/학칙.pdf",
            "학칙",
            "덕성여자대학교",
            "2-1-1-1",
        ),
        (
            "광운대학교규정 광운대학교학칙[2-0-1]"
            "광운대학교학칙제정1963.03.01.개정2026.04.22.제1장목적",
            "unireg-eval/university_kwangwoon/학칙.pdf",
            "학칙",
            "광운대학교",
            "2-0-1",
        ),
        (
            "서울여자대학교 학칙 ◀ 2-1-1~1 ▶서울여자대학교 학칙",
            "unireg-eval/university_seoulwomen/학칙.pdf",
            "학칙",
            "서울여자대학교",
            "2-1-1~1",
        ),
    ]

    for raw_title, source_file, title, institution, regulation_code in cases:
        line = _line(raw_title)
        metadata = normalizer.normalize(
            source_file=source_file,
            title_line=line,
            lines=[line],
        )

        assert metadata.title == title
        assert metadata.institution == institution
        assert metadata.regulation_code == regulation_code
        assert metadata.raw_title == raw_title
        assert metadata.title_candidates[-1] == title


def test_parser_preserves_raw_title_and_uses_normalized_title() -> None:
    result = RegulationParser().parse_text(
        "\n"
        "광운대학교규정 광운대학교학칙[2-0-1]"
        "광운대학교학칙제정1963.03.01.개정2026.04.22.제1장목적\n"
        "제1조(목적)\n"
        "본문\n",
        source_file="kwangwoon.pdf",
    )

    assert result.document is not None
    regulation = result.document.regulation
    assert regulation.title == "학칙"
    assert regulation.raw_title is not None
    assert regulation.raw_title.startswith("광운대학교규정 광운대학교학칙")
    assert regulation.institution == "광운대학교"
    assert regulation.regulation_code == "2-0-1"
    assert "metadata_title_contains_structure" in {
        diagnostic.code for diagnostic in result.diagnostics
    }


def test_parser_uses_filename_metadata_when_title_line_is_missing() -> None:
    result = RegulationParser().parse_text(
        "",
        source_file="external/서울여자대학교 학칙[2-1-1].pdf",
    )

    assert result.document is not None
    regulation = result.document.regulation
    assert regulation.title == "학칙"
    assert regulation.institution == "서울여자대학교"
    assert regulation.regulation_code == "2-1-1"


def _line(text: str) -> CleanLine:
    return CleanLine(
        text=text,
        line_number=1,
        source_span=SourceSpan(source_file="source.pdf", page_start=1, page_end=1),
    )
