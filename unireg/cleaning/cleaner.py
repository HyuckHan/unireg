"""Conservative text cleaner for extracted regulations."""

from __future__ import annotations

import re
from itertools import pairwise

from unireg.models import CleanDocument, CleanLine, ExtractedDocument, SourceSpan

_WHITESPACE_RE = re.compile(r"[ \t\u00a0]+")
_PAGE_HEADER_TEMPLATE = (
    r"^[가-힣A-Za-z][가-힣A-Za-z\s]{{0,20}}\s+\d+(?:-\d+)+~{page_number}"
)
_STRUCTURAL_MARKER_RE = re.compile(
    r"(?=제\s*\d+\s*장\b|제\s*\d+\s*절\b|제\s*\d+\s*조(?:\s*의\s*\d+)?\s*\()"
)


class DocumentCleaner:
    """Normalize extracted text while preserving source spans."""

    def clean(self, document: ExtractedDocument) -> CleanDocument:
        lines: list[CleanLine] = []
        output_line_number = 1

        for page in document.pages:
            for page_line_number, raw_line in enumerate(
                page.text.splitlines(),
                start=1,
            ):
                normalized = self.normalize_line(raw_line)
                normalized = self.strip_page_header(
                    normalized,
                    page_number=page.page_number,
                )
                if not normalized:
                    continue

                for segment in self.split_structural_segments(normalized):
                    lines.append(
                        CleanLine(
                            text=segment,
                            source_span=SourceSpan(
                                source_file=document.source_file,
                                page_start=page.page_number,
                                page_end=page.page_number,
                                line_start=page_line_number,
                                line_end=page_line_number,
                                extraction_method=document.extraction_method,
                            ),
                            line_number=output_line_number,
                        )
                    )
                    output_line_number += 1

        return CleanDocument(
            source_file=document.source_file,
            lines=lines,
            extraction_method=document.extraction_method,
        )

    @staticmethod
    def normalize_line(line: str) -> str:
        """Normalize a single line without making structural guesses."""

        normalized = _normalize_fullwidth_ascii(line)
        normalized = _WHITESPACE_RE.sub(" ", normalized)
        return normalized.strip()

    @staticmethod
    def strip_page_header(line: str, *, page_number: int) -> str:
        """Strip repeated page headers while preserving body text after them."""

        pattern = re.compile(_PAGE_HEADER_TEMPLATE.format(page_number=page_number))
        return pattern.sub("", line, count=1).strip()

    @staticmethod
    def split_structural_segments(line: str) -> list[str]:
        """Split PDF-extracted lines before chapter and article headings."""

        marker_positions = [
            match.start() for match in _STRUCTURAL_MARKER_RE.finditer(line)
        ]
        if not marker_positions:
            return [line]

        positions = [0]
        positions.extend(position for position in marker_positions if position != 0)
        positions.append(len(line))

        segments: list[str] = []
        for start, end in pairwise(positions):
            segment = line[start:end].strip()
            if segment:
                segments.append(segment)
        return segments


def _normalize_fullwidth_ascii(value: str) -> str:
    chars: list[str] = []
    for char in value:
        codepoint = ord(char)
        if codepoint == 0x3000:
            chars.append(" ")
        elif 0xFF01 <= codepoint <= 0xFF5E:
            chars.append(chr(codepoint - 0xFEE0))
        else:
            chars.append(char)
    return "".join(chars)
