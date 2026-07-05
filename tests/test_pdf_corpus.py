from __future__ import annotations

import os
from pathlib import Path

import pytest

from unireg.parser import RegulationParser

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = PROJECT_ROOT / "examples/pdf"


@pytest.mark.corpus
def test_examples_pdf_corpus_smoke() -> None:
    if os.environ.get("UNIREG_RUN_PDF_CORPUS") != "1":
        pytest.skip("Set UNIREG_RUN_PDF_CORPUS=1 to parse every PDF fixture.")

    pdf_paths = sorted(PDF_DIR.rglob("*.pdf"))
    assert pdf_paths, f"No PDFs found under {PDF_DIR}"

    parser = RegulationParser()
    failures: list[str] = []
    for path in pdf_paths:
        try:
            result = parser.parse_file(path)
        except Exception as exc:  # pragma: no cover - reports corpus-specific input.
            failures.append(f"{path}: {type(exc).__name__}: {exc}")
            continue

        if result.document is None:
            failures.append(f"{path}: parser returned no document")

    assert not failures, "\n".join(failures)
