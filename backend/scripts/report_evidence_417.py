"""Readable independent-review worksheet, not an automatic accuracy/Ragas score."""

import argparse
import json
from collections import Counter
from pathlib import Path

from app.modules.rag.evidence_validation import validate_decision_integrity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="storage/admissions_eval417_stable.json")
    parser.add_argument("--output", default="../docs/nhat_ky/2026-10-13_phien_417_doi_soat_82_cau.md")
    args = parser.parse_args()
    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in report["cases"]}
    statuses = Counter(r.get("response", {}).get("status") or
        ("http_error" if r.get("http") else "transport_error") for r in report["results"])
    decisions = Counter((r.get("response", {}).get("answer_decision") or {}).get("status", "none") for r in report["results"])
    models = Counter(f"{u['provider']}/{u['model']}" for r in report["results"] for u in r.get("served_models", []))
    checks = []
    for item in report["results"]:
        response = item.get("response", {})
        decision = response.get("answer_decision") or {}
        if decision.get("status") in {"supported", "partial"}:
            checks.append({"id": item["id"], "valid": validate_decision_integrity(
                decision, response.get("answer", ""), response.get("citations") or [])})
    responses_received = sum(bool(r.get("http")) for r in report["results"])
    routes = report.get("routes") or sorted({r["route"] for r in report["results"]})
    expected_runs = len(cases) * len(routes)
    summary = {"attempted": len(report["results"]), "responses_received": responses_received,
        "expected_runs": expected_runs, "expected_questions": len(cases), "routes": routes,
        "runtime_statuses": dict(statuses),
        "decisions": dict(decisions), "served_model_calls": dict(models), "integrity_checks": checks,
        "configuration_unchanged": report.get("configuration_unchanged"),
        "publication_unchanged": report.get("publication_unchanged"), "code_unchanged": report.get("code_unchanged"),
        "interruption_reason": report.get("interruption_reason"),
        "note": "Transport/HTTP failures are infrastructure results, not factual answer grades. Runtime status and integrity are not independent accuracy or Ragas scores."}
    Path("storage/evidence417_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Phiên417 — Đối soát câu hỏi độc lập", "",
             f"Đã thử {len(report['results'])}/{expected_runs} lượt cho {len(cases)} câu qua {', '.join(routes)}; nhận {responses_received} phản hồi HTTP (kể cả lỗi). Lỗi kết nối không phải đáp án sai.", "",
             "Đáp án tham chiếu chỉ để chấm, không đưa vào prompt/evidence. Status supported/answered không tự chứng minh đáp án đúng. Không công bố Ragas từ bảng này.", "",
             f"Runtime: {dict(statuses)}. Quyết định: {dict(decisions)}.", "",
             f"Kiểm tra digest/revision/quote/numeric: {sum(c['valid'] for c in checks)}/{len(checks)} quyết định supported/partial đạt contract; chưa thay thế kiểm chứng ngữ nghĩa.", "",
             f"Config/publication/code không đổi: {summary['configuration_unchanged']}/{summary['publication_unchanged']}/{summary['code_unchanged']}.", ""]
    for item in report["results"]:
        response = item.get("response", {})
        case = cases[item["id"]]
        decision = response.get("answer_decision") or {}
        lines += [f"## Câu {item['id']}: {case['question']}", "", "Tham chiếu: " + case["expected_answer"], "",
                  "Thực tế: " + (response.get("answer") or item.get("error") or response.get("detail") or "Không có câu trả lời"), "",
                  f"Status: {response.get('status')}; decision: {decision.get('status')}; reason: {decision.get('reason')}; error: {response.get('error_code')}; thời gian: {item['elapsed_seconds']}s.", ""]
        refs = {(c.get("title"), c.get("page_number"), c.get("source_revision_id")) for c in response.get("citations", [])}
        lines += ["Nguồn: " + "; ".join(f"{title}, trang {page}, {revision}" for title, page, revision in sorted(refs, key=str)), "",
                  "Mô hình thực: " + ", ".join(sorted({f"{u['provider']}/{u['model']} (fallback={u['fallback']})" for u in item.get("served_models", [])})), ""]
    Path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k != "integrity_checks"}, ensure_ascii=True))


if __name__ == "__main__":
    main()
