"""Offline paired context measurement, optionally pinning the baseline app copy."""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--app-path", type=Path, default=ROOT / "backend")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.app_path.resolve()))
import app
from app.modules.knowledge.normalization.qnu_markdown import QnuStructuredDocument
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.services.semantic_annotations import INSTRUCTION
from app.modules.knowledge.services.semantic_binding import ModelSemanticProposal
from app.modules.knowledge.services.semantic_context import (
    ContextBuilder,
    SemanticContextPolicy,
    context_bytes,
)

assert Path(app.__file__).resolve().parent == (args.app_path / "app").resolve()
pair = ROOT / "backend/storage/rag544-offline"
document = QnuStructuredDocument.model_validate_json((pair / "standard.json").read_bytes())
reference = json.loads((pair / "projection.json").read_text(encoding="utf-8"))["qnu_input"]
_, artifact = project_document(document, reference, {})
system_bytes = len((INSTRUCTION + json.dumps(ModelSemanticProposal.model_json_schema(), ensure_ascii=False)).encode())
times = []
for _ in range(3):
    start = time.perf_counter()
    builder = ContextBuilder(artifact, document, SemanticContextPolicy(max_packet_bytes=48000-system_bytes))
    packets = builder.packets()
    times.append((time.perf_counter()-start)*1000)
report = {"fixture_sha256": document.source.sha256, "system_bytes": system_bytes, "packets": len(packets),
    "packet_payload_bytes": [context_bytes(p) for p in packets], "unexamined": sorted(set(builder.unexamined)),
    "minimum_request_utf8_bytes": sum(context_bytes(p)+system_bytes for p in packets),
    "build_ms_samples": times, "build_ms_median": statistics.median(times),
    "provider_calls": 0, "tokens": "NOT_MEASURED", "scope": "whole synthetic document; offline only"}
args.output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8", newline="\n")
print(json.dumps({k: v for k, v in report.items() if k != "packet_payload_bytes"}))
