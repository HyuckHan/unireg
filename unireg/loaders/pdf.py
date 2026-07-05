"""PDF text loading."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import BinaryIO, Protocol

from unireg.models import ExtractedDocument, ExtractedPage


class PDFLoadError(RuntimeError):
    """Raised when a PDF cannot be loaded."""


class PDFDependencyError(PDFLoadError):
    """Raised when the PDF extraction dependency is unavailable."""


class PDFPageLike(Protocol):
    """Protocol for a pypdf-like page object."""

    def extract_text(self) -> str | None:
        """Extract text from a page."""


class PDFReaderLike(Protocol):
    """Protocol for a pypdf-like reader object."""

    pages: Sequence[PDFPageLike]


class PDFReaderFactory(Protocol):
    """Factory for pypdf-like readers."""

    def __call__(self, stream: BinaryIO) -> PDFReaderLike:
        """Create a PDF reader from a binary stream."""


class PDFLoader:
    """Load page-aware text from a PDF file."""

    extraction_method = "pypdf"

    def __init__(self, reader_factory: PDFReaderFactory | None = None) -> None:
        self._reader_factory = reader_factory or self._default_reader_factory

    def load(self, source_file: str | Path) -> ExtractedDocument:
        """Load a PDF file into an extracted document."""

        path = Path(source_file)
        if not path.exists():
            raise PDFLoadError(f"PDF file does not exist: {path}")
        if path.suffix.lower() != ".pdf":
            raise PDFLoadError(f"Unsupported PDF file extension: {path.suffix}")

        try:
            with path.open("rb") as stream:
                reader = self._reader_factory(stream)
                pages = [
                    ExtractedPage(
                        page_number=index,
                        text=page.extract_text() or "",
                    )
                    for index, page in enumerate(reader.pages, start=1)
                ]
        except PDFDependencyError:
            raise
        except OSError as exc:
            raise PDFLoadError(f"Unable to read PDF file: {path}") from exc
        except Exception as exc:
            raise PDFLoadError(f"Unable to extract PDF text: {path}") from exc

        return ExtractedDocument(
            source_file=str(path),
            pages=pages,
            extraction_method=self.extraction_method,
        )

    @staticmethod
    def _default_reader_factory(stream: BinaryIO) -> PDFReaderLike:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise PDFDependencyError(
                "PDF loading requires the 'pypdf' package. Install with "
                "`pip install .[dev]` or `pip install pypdf`."
            ) from exc

        return PdfReader(stream)
