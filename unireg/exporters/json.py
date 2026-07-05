"""JSON exporter for the canonical regulation model."""

from __future__ import annotations

import json
from pathlib import Path

from unireg.models import ParseResult, Regulation, RegulationDocument

ExportableJSON = ParseResult | Regulation | RegulationDocument


class JSONExporter:
    """Export parser output to a stable JSON string or file."""

    def dumps(
        self,
        value: ExportableJSON,
        *,
        indent: int | None = 2,
        ensure_ascii: bool = False,
        trailing_newline: bool = True,
    ) -> str:
        text = json.dumps(
            self.to_dict(value),
            ensure_ascii=ensure_ascii,
            indent=indent,
        )
        if trailing_newline:
            return f"{text}\n"
        return text

    def dump(
        self,
        value: ExportableJSON,
        path: str | Path,
        *,
        indent: int | None = 2,
        ensure_ascii: bool = False,
    ) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            self.dumps(value, indent=indent, ensure_ascii=ensure_ascii),
            encoding="utf-8",
        )

    @staticmethod
    def loads_document(text: str) -> RegulationDocument:
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise TypeError("Expected JSON object for RegulationDocument.")
        return RegulationDocument.from_dict(payload)

    @staticmethod
    def to_dict(value: ExportableJSON) -> dict[str, object]:
        if isinstance(value, ParseResult):
            return value.to_dict()
        if isinstance(value, Regulation):
            return RegulationDocument(regulation=value).to_dict()
        return value.to_dict()
