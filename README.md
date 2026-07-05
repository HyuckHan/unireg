# UniReg

UniReg is an open-source parser and knowledge platform for university regulations.

Its primary goal is to transform university regulations (PDF/HWP) into structured knowledge that can be searched, linked, and queried by Large Language Models.

## Features

- Parse university regulations from PDF/HWP
- Extract hierarchy
    - Chapter
    - Section (optional)
    - Article
    - Clause
    - Item
- Preserve amendment history
- Export Markdown
- Export JSON
- Build knowledge graph
- Support RAG
- Citation-aware answers

## Project Stages

1. Regulation Parser
2. Structured Data Model
3. Search Engine
4. RAG
5. Web UI
6. Obsidian Export

## Philosophy

LLM should never invent regulations.

Every answer must be grounded by the original regulation.

## PDF Corpus Smoke Test

Copy regulation PDFs into `examples/pdf`, then run:

```bash
.venv/bin/python scripts/check_pdfs.py --pdf-dir examples/pdf
```

To save a CSV report:

```bash
.venv/bin/python scripts/check_pdfs.py \
  --pdf-dir examples/pdf \
  --report /tmp/unireg-pdf-report.csv \
  --quiet
```

The full corpus pytest is opt-in so normal tests stay fast:

```bash
UNIREG_RUN_PDF_CORPUS=1 .venv/bin/python -m pytest tests/test_pdf_corpus.py
```

## Export

```python
from unireg.exporters import JSONExporter, MarkdownExporter
from unireg.parser import RegulationParser

result = RegulationParser().parse_file("examples/pdf/sample.pdf")
if result.document is None:
    raise RuntimeError("No document parsed")

JSONExporter().dump(result.document, "out/regulation.json")
MarkdownExporter().dump(result.document, "out/regulation.md")
```
