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

## External University Evaluation

Put external university samples under one folder per university:

```text
unireg-eval/
  university_a/
    학칙.pdf
  university_b/
    학칙.pdf
```

Then run:

```bash
.venv/bin/python scripts/check_eval_pdfs.py \
  --eval-dir unireg-eval \
  --report /tmp/unireg-eval-report.csv
```

The evaluation checks parser success, hierarchy counts, citation counts, and
whether parsed structure spans enough PDF pages to catch first-page-only
failures. It also reports normalized title metadata, extracted institution/code
values, and non-fatal title warnings.

## Metadata Normalization

Parser output keeps both normalized and raw title metadata:

```python
from unireg.parser import RegulationParser

result = RegulationParser().parse_file("unireg-eval/university_a/학칙.pdf")
if result.document is None:
    raise RuntimeError("No document parsed")

regulation = result.document.regulation
print(regulation.title)
print(regulation.raw_title)
print(regulation.institution)
print(regulation.regulation_code)
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

## Citations

```python
from unireg.citations import CitationGenerator
from unireg.parser import RegulationParser

result = RegulationParser().parse_file("examples/pdf/sample.pdf")
citations = CitationGenerator().generate(result)

for citation in citations[:5]:
    print(citation.label, citation.source_label)
```

## Search and RAG Projections

```python
from unireg.parser import RegulationParser
from unireg.projections import ProjectionBuilder

result = RegulationParser().parse_file("examples/pdf/sample.pdf")
projection = ProjectionBuilder().build(result)

print(projection.bm25_documents[0].text)
print(projection.vector_documents[0].metadata)
print(projection.graph_edges[0].edge_type)
```
