"""Knowledge normalization package — Canonical Document Model, Table Reconstruction, and Quality Gate."""

from app.modules.knowledge.normalization.markdown_renderer import (
    render_canonical_document_markdown,
    render_canonical_table_markdown,
)
from app.modules.knowledge.normalization.models import (
    BlockType,
    CanonicalBlock,
    CanonicalCell,
    CanonicalDocument,
    CanonicalRow,
    CanonicalTable,
    QualityIssue,
    SourceSpan,
)
from app.modules.knowledge.normalization.quality_gate import (
    DataQualityGate,
    DocumentQualityReport,
)
from app.modules.knowledge.normalization.record_normalizer import (
    AdmissionProgramRecord,
    AdmissionsRecordNormalizer,
    CertificateConversionRecord,
    HistoricalAdmissionRecord,
    ImplementationPlanRecordNormalizer,
    ImplementationTaskRecord,
)
from app.modules.knowledge.normalization.table_reconstructor import (
    reconstruct_multi_page_tables,
    table_schema_key,
)
from app.modules.knowledge.normalization.text_normalizer import (
    join_wrapped_paragraph_lines,
    normalize_encoding,
    normalize_whitespace,
)

__all__ = [
    "AdmissionProgramRecord",
    "AdmissionsRecordNormalizer",
    "BlockType",
    "CanonicalBlock",
    "CanonicalCell",
    "CanonicalDocument",
    "CanonicalRow",
    "CanonicalTable",
    "CertificateConversionRecord",
    "DataQualityGate",
    "DocumentQualityReport",
    "HistoricalAdmissionRecord",
    "ImplementationPlanRecordNormalizer",
    "ImplementationTaskRecord",
    "QualityIssue",
    "SourceSpan",
    "join_wrapped_paragraph_lines",
    "normalize_encoding",
    "normalize_whitespace",
    "reconstruct_multi_page_tables",
    "render_canonical_document_markdown",
    "render_canonical_table_markdown",
    "table_schema_key",
]
