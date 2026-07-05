from __future__ import annotations

from pathlib import Path

from scripts.check_eval_pdfs import (
    EvalResult,
    EvalThresholds,
    _page_range_label,
    _pages_from_span,
    _quality_problems,
    _university_name,
)
from unireg.models import SourceSpan


def test_pages_from_span_returns_inclusive_page_range() -> None:
    span = SourceSpan(source_file="source.pdf", page_start=2, page_end=4)

    assert _pages_from_span(span) == {2, 3, 4}


def test_pages_from_span_ignores_missing_page_coordinates() -> None:
    span = SourceSpan(source_file="source.pdf", page_start=2, page_end=None)

    assert _pages_from_span(span) == set()


def test_university_name_uses_first_directory_under_eval_root() -> None:
    path = Path("unireg-eval/university_a/학칙.pdf")

    assert _university_name(path, Path("unireg-eval")) == "university_a"


def test_quality_problems_check_articles_and_page_coverage() -> None:
    thresholds = EvalThresholds(min_articles=20, min_page_coverage=0.25)

    problems = _quality_problems(
        article_count=1,
        page_coverage=0.1,
        thresholds=thresholds,
    )

    assert problems == [
        "article_count 1 < min_articles 20",
        "page_coverage 10.0% < min_page_coverage 25.0%",
    ]


def test_page_range_label_formats_missing_single_and_range() -> None:
    assert (
        _page_range_label(
            EvalResult(
                university="u",
                path=Path("a.pdf"),
                ok=True,
                elapsed_seconds=0.0,
            )
        )
        == "none"
    )
    assert (
        _page_range_label(
            EvalResult(
                university="u",
                path=Path("a.pdf"),
                ok=True,
                elapsed_seconds=0.0,
                structural_page_start=3,
                structural_page_end=3,
            )
        )
        == "3"
    )
    assert (
        _page_range_label(
            EvalResult(
                university="u",
                path=Path("a.pdf"),
                ok=True,
                elapsed_seconds=0.0,
                structural_page_start=3,
                structural_page_end=5,
            )
        )
        == "3-5"
    )
