"""Explainability and error analysis for grounded QA traces."""

from unireg.analysis.classifier import classify_trace
from unireg.analysis.models import (
    ErrorAnalysisReport,
    ErrorCategory,
    ErrorClassification,
    QATraceRecord,
)
from unireg.analysis.runner import analyze_error_traces

__all__ = [
    "ErrorAnalysisReport",
    "ErrorCategory",
    "ErrorClassification",
    "QATraceRecord",
    "analyze_error_traces",
    "classify_trace",
]
