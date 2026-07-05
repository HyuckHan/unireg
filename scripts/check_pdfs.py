"""Parse every PDF in a directory and report smoke-test results."""

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

from unireg.parser import RegulationParser  # noqa: E402


@dataclass(frozen=True, slots=True)
class PDFCheckResult:
    path: Path
    ok: bool
    elapsed_seconds: float
    chapter_count: int = 0
    article_count: int = 0
    appendix_count: int = 0
    diagnostic_count: int = 0
    error: str = ""


def main() -> int:
    args = _parse_args()
    pdf_dir = args.pdf_dir
    pdf_paths = sorted(pdf_dir.rglob("*.pdf"))
    if args.limit is not None:
        pdf_paths = pdf_paths[: args.limit]

    if not pdf_paths:
        print(f"No PDF files found under {pdf_dir}", file=sys.stderr)
        return 2

    parser = RegulationParser()
    results: list[PDFCheckResult] = []

    for index, path in enumerate(pdf_paths, start=1):
        result = _check_pdf(parser, path)
        results.append(result)
        status = "OK" if result.ok else "FAIL"
        message = (
            f"[{index}/{len(pdf_paths)}] {status} {path} "
            f"articles={result.article_count} appendices={result.appendix_count} "
            f"time={result.elapsed_seconds:.2f}s"
        )
        if result.error:
            message = f"{message} error={result.error}"
        if not args.quiet:
            print(message, flush=True)
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


def _check_pdf(parser: RegulationParser, path: Path) -> PDFCheckResult:
    started_at = time.perf_counter()
    try:
        result = parser.parse_file(path)
    except Exception as exc:  # pragma: no cover - exercised by corrupt PDFs.
        return PDFCheckResult(
            path=path,
            ok=False,
            elapsed_seconds=time.perf_counter() - started_at,
            error=f"{type(exc).__name__}: {exc}",
        )

    elapsed = time.perf_counter() - started_at
    if result.document is None:
        return PDFCheckResult(
            path=path,
            ok=False,
            elapsed_seconds=elapsed,
            diagnostic_count=len(result.diagnostics),
            error="parser returned no document",
        )

    regulation = result.document.regulation
    return PDFCheckResult(
        path=path,
        ok=True,
        elapsed_seconds=elapsed,
        chapter_count=result.stats.chapter_count,
        article_count=result.stats.article_count,
        appendix_count=len(regulation.appendices),
        diagnostic_count=result.stats.diagnostic_count,
    )


def _write_report(path: Path, results: list[PDFCheckResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "path",
                "ok",
                "elapsed_seconds",
                "chapter_count",
                "article_count",
                "appendix_count",
                "diagnostic_count",
                "error",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "path": str(result.path),
                    "ok": result.ok,
                    "elapsed_seconds": f"{result.elapsed_seconds:.3f}",
                    "chapter_count": result.chapter_count,
                    "article_count": result.article_count,
                    "appendix_count": result.appendix_count,
                    "diagnostic_count": result.diagnostic_count,
                    "error": result.error,
                }
            )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test UniReg parser against a directory of PDFs."
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path("examples/pdf"),
        help="Directory containing PDF files. Defaults to examples/pdf.",
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
