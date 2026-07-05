"""Evaluate UniReg against external university regulation PDF samples."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unireg.citations import CitationGenerator  # noqa: E402
from unireg.loaders import PDFLoader  # noqa: E402
from unireg.models import Article, Regulation, SourceSpan  # noqa: E402
from unireg.parser import RegulationParser  # noqa: E402


@dataclass(frozen=True, slots=True)
class EvalThresholds:
    """Quality thresholds for an external regulation smoke test."""

    min_articles: int
    min_page_coverage: float


@dataclass(frozen=True, slots=True)
class EvalResult:
    """Evaluation summary for one PDF."""

    university: str
    path: Path
    ok: bool
    elapsed_seconds: float
    pdf_pages: int = 0
    structural_pages: int = 0
    structural_page_start: int | None = None
    structural_page_end: int | None = None
    page_coverage: float = 0.0
    title: str = ""
    chapter_count: int = 0
    section_count: int = 0
    article_count: int = 0
    clause_count: int = 0
    item_count: int = 0
    sub_item_count: int = 0
    appendix_count: int = 0
    citation_count: int = 0
    diagnostic_count: int = 0
    error: str = ""


def main() -> int:
    args = _parse_args()
    thresholds = EvalThresholds(
        min_articles=args.min_articles,
        min_page_coverage=args.min_page_coverage,
    )
    pdf_paths = _discover_pdfs(args.eval_dir, args.pattern)
    if args.limit is not None:
        pdf_paths = pdf_paths[: args.limit]

    if not pdf_paths:
        print(
            f"No PDF files found under {args.eval_dir} with pattern {args.pattern}",
            file=sys.stderr,
        )
        return 2

    loader = PDFLoader()
    parser = RegulationParser()
    citation_generator = CitationGenerator()
    results: list[EvalResult] = []

    for index, path in enumerate(pdf_paths, start=1):
        result = evaluate_pdf(
            path=path,
            eval_dir=args.eval_dir,
            loader=loader,
            parser=parser,
            citation_generator=citation_generator,
            thresholds=thresholds,
        )
        results.append(result)
        if not args.quiet:
            print(_format_result(index, len(pdf_paths), result), flush=True)
        if args.fail_fast and not result.ok:
            break

    if args.report is not None:
        _write_report(args.report, results)
        print(f"Wrote report: {args.report}")

    failed = [result for result in results if not result.ok]
    total_time = sum(result.elapsed_seconds for result in results)
    print(
        f"Summary: total={len(results)} ok={len(results) - len(failed)} "
        f"failed={len(failed)} elapsed={total_time:.2f}s"
    )
    return 1 if failed else 0


def evaluate_pdf(
    *,
    path: Path,
    eval_dir: Path,
    loader: PDFLoader,
    parser: RegulationParser,
    citation_generator: CitationGenerator,
    thresholds: EvalThresholds,
) -> EvalResult:
    """Parse and score one external evaluation PDF."""

    started_at = time.perf_counter()
    university = _university_name(path, eval_dir)
    try:
        extracted_document = loader.load(path)
        parse_result = parser.parse_extracted_document(extracted_document)
        pdf_pages = len(extracted_document.pages)
    except Exception as exc:  # pragma: no cover - depends on input PDFs.
        return EvalResult(
            university=university,
            path=path,
            ok=False,
            elapsed_seconds=time.perf_counter() - started_at,
            error=f"{type(exc).__name__}: {exc}",
        )

    elapsed = time.perf_counter() - started_at
    if parse_result.document is None:
        return EvalResult(
            university=university,
            path=path,
            ok=False,
            elapsed_seconds=elapsed,
            pdf_pages=pdf_pages,
            diagnostic_count=len(parse_result.diagnostics),
            error="parser returned no document",
        )

    regulation = parse_result.document.regulation
    counts = _count_nodes(regulation)
    structural_pages = _structural_pages(regulation)
    page_coverage = len(structural_pages) / pdf_pages if pdf_pages else 0.0
    citations = citation_generator.generate(parse_result, include_quotes=False)
    problems = _quality_problems(
        article_count=counts.article_count,
        page_coverage=page_coverage,
        thresholds=thresholds,
    )

    return EvalResult(
        university=university,
        path=path,
        ok=not problems,
        elapsed_seconds=elapsed,
        pdf_pages=pdf_pages,
        structural_pages=len(structural_pages),
        structural_page_start=min(structural_pages) if structural_pages else None,
        structural_page_end=max(structural_pages) if structural_pages else None,
        page_coverage=page_coverage,
        title=regulation.title,
        chapter_count=parse_result.stats.chapter_count,
        section_count=counts.section_count,
        article_count=parse_result.stats.article_count,
        clause_count=counts.clause_count,
        item_count=counts.item_count,
        sub_item_count=counts.sub_item_count,
        appendix_count=counts.appendix_count,
        citation_count=len(citations),
        diagnostic_count=parse_result.stats.diagnostic_count,
        error="; ".join(problems),
    )


@dataclass(frozen=True, slots=True)
class _NodeCounts:
    section_count: int
    article_count: int
    clause_count: int
    item_count: int
    sub_item_count: int
    appendix_count: int


def _count_nodes(regulation: Regulation) -> _NodeCounts:
    articles = regulation.all_articles()
    clauses = [clause for article in articles for clause in article.clauses]
    items = [item for clause in clauses for item in clause.items]
    sub_items = [sub_item for item in items for sub_item in item.sub_items]
    return _NodeCounts(
        section_count=sum(len(chapter.sections) for chapter in regulation.chapters),
        article_count=len(articles),
        clause_count=len(clauses),
        item_count=len(items),
        sub_item_count=len(sub_items),
        appendix_count=len(regulation.appendices),
    )


def _structural_pages(regulation: Regulation) -> set[int]:
    pages: set[int] = set()
    for chapter in regulation.chapters:
        pages.update(_pages_from_span(chapter.source_span))
        for section in chapter.sections:
            pages.update(_pages_from_span(section.source_span))
            for article in section.articles:
                _add_article_pages(article, pages)
        for article in chapter.articles:
            _add_article_pages(article, pages)
    for appendix in regulation.appendices:
        pages.update(_pages_from_span(appendix.source_span))
        for table in appendix.tables:
            pages.update(_pages_from_span(table.source_span))
    return pages


def _add_article_pages(article: Article, pages: set[int]) -> None:
    pages.update(_pages_from_span(article.source_span))
    for clause in article.clauses:
        pages.update(_pages_from_span(clause.source_span))
        for item in clause.items:
            pages.update(_pages_from_span(item.source_span))
            for sub_item in item.sub_items:
                pages.update(_pages_from_span(sub_item.source_span))


def _pages_from_span(source_span: SourceSpan | None) -> set[int]:
    if source_span is None:
        return set()
    if source_span.page_start is None or source_span.page_end is None:
        return set()
    return set(range(source_span.page_start, source_span.page_end + 1))


def _quality_problems(
    *,
    article_count: int,
    page_coverage: float,
    thresholds: EvalThresholds,
) -> list[str]:
    problems: list[str] = []
    if article_count < thresholds.min_articles:
        problems.append(
            f"article_count {article_count} < min_articles {thresholds.min_articles}"
        )
    if page_coverage < thresholds.min_page_coverage:
        problems.append(
            f"page_coverage {page_coverage:.1%} < "
            f"min_page_coverage {thresholds.min_page_coverage:.1%}"
        )
    return problems


def _discover_pdfs(eval_dir: Path, pattern: str) -> list[Path]:
    return sorted(path for path in eval_dir.rglob(pattern) if path.is_file())


def _university_name(path: Path, eval_dir: Path) -> str:
    try:
        relative_path = path.relative_to(eval_dir)
    except ValueError:
        return path.parent.name
    if len(relative_path.parts) > 1:
        return relative_path.parts[0]
    return path.stem


def _format_result(index: int, total: int, result: EvalResult) -> str:
    status = "OK" if result.ok else "FAIL"
    page_range = _page_range_label(result)
    message = (
        f"[{index}/{total}] {status} {result.university} {result.path.name} "
        f"title={result.title!r} articles={result.article_count} "
        f"clauses={result.clause_count} items={result.item_count} "
        f"pages={page_range}/{result.pdf_pages} "
        f"coverage={result.page_coverage:.1%} "
        f"citations={result.citation_count} time={result.elapsed_seconds:.2f}s"
    )
    if result.error:
        message = f"{message} error={result.error}"
    return message


def _page_range_label(result: EvalResult) -> str:
    if result.structural_page_start is None or result.structural_page_end is None:
        return "none"
    if result.structural_page_start == result.structural_page_end:
        return str(result.structural_page_start)
    return f"{result.structural_page_start}-{result.structural_page_end}"


def _write_report(path: Path, results: list[EvalResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "university",
                "path",
                "ok",
                "elapsed_seconds",
                "pdf_pages",
                "structural_pages",
                "structural_page_start",
                "structural_page_end",
                "page_coverage",
                "title",
                "chapter_count",
                "section_count",
                "article_count",
                "clause_count",
                "item_count",
                "sub_item_count",
                "appendix_count",
                "citation_count",
                "diagnostic_count",
                "error",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "university": result.university,
                    "path": str(result.path),
                    "ok": result.ok,
                    "elapsed_seconds": f"{result.elapsed_seconds:.3f}",
                    "pdf_pages": result.pdf_pages,
                    "structural_pages": result.structural_pages,
                    "structural_page_start": result.structural_page_start,
                    "structural_page_end": result.structural_page_end,
                    "page_coverage": f"{result.page_coverage:.3f}",
                    "title": result.title,
                    "chapter_count": result.chapter_count,
                    "section_count": result.section_count,
                    "article_count": result.article_count,
                    "clause_count": result.clause_count,
                    "item_count": result.item_count,
                    "sub_item_count": result.sub_item_count,
                    "appendix_count": result.appendix_count,
                    "citation_count": result.citation_count,
                    "diagnostic_count": result.diagnostic_count,
                    "error": result.error,
                }
            )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate UniReg parser against university folders under unireg-eval."
        )
    )
    parser.add_argument(
        "--eval-dir",
        type=Path,
        default=Path("unireg-eval"),
        help="Directory containing one folder per university.",
    )
    parser.add_argument(
        "--pattern",
        default="*.pdf",
        help="PDF glob pattern searched recursively under eval-dir.",
    )
    parser.add_argument(
        "--min-articles",
        type=int,
        default=20,
        help="Minimum article count expected for a university regulation.",
    )
    parser.add_argument(
        "--min-page-coverage",
        type=float,
        default=0.25,
        help="Minimum structural source-page coverage ratio.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only parse the first N PDFs after sorting.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first failed PDF.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional CSV report path.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print report path and summary.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
