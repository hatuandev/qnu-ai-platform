#!/usr/bin/env python3
"""Compare two RAG benchmark run result files and generate a diff report.

Usage:
    python compare_runs.py <run_A.json> <run_B.json> [--markdown] [--output <report.md>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_run_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy tệp kết quả benchmark: {file_path}")
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise TypeError(f"Dữ liệu trong {file_path} không phải là JSON object.")
        return data
    except Exception as exc:
        raise ValueError(f"Lỗi đọc tệp {file_path}: {exc}") from exc


def compare_runs(run_a: dict[str, Any], run_b: dict[str, Any]) -> dict[str, Any]:
    """Calculate comparative metrics between baseline Run A and candidate Run B."""
    score_a = float(run_a.get("total_score", 0))
    score_b = float(run_b.get("total_score", 0))
    max_a = float(run_a.get("max_score", 48))
    max_b = float(run_b.get("max_score", 48))

    pass_rate_a = (
        float(run_a.get("pass_rate", 0))
        if "pass_rate" in run_a
        else (round((score_a / max_a * 100), 2) if max_a > 0 else 0.0)
    )
    pass_rate_b = (
        float(run_b.get("pass_rate", 0))
        if "pass_rate" in run_b
        else (round((score_b / max_b * 100), 2) if max_b > 0 else 0.0)
    )

    score_delta = round(score_b - score_a, 2)
    pass_rate_delta = round(pass_rate_b - pass_rate_a, 2)

    # 1. Violations comparison
    viols_a = run_a.get("violation_counts") or {}
    viols_b = run_b.get("violation_counts") or {}
    all_violation_keys = sorted(set(viols_a.keys()) | set(viols_b.keys()))
    violations_comparison = []
    for k in all_violation_keys:
        cnt_a = int(viols_a.get(k, 0))
        cnt_b = int(viols_b.get(k, 0))
        violations_comparison.append(
            {
                "violation": k,
                "count_a": cnt_a,
                "count_b": cnt_b,
                "delta": cnt_b - cnt_a,
            }
        )

    # 2. Group comparison
    groups_a = run_a.get("scores_by_group") or {}
    groups_b = run_b.get("scores_by_group") or {}
    all_group_keys = sorted(set(groups_a.keys()) | set(groups_b.keys()))
    groups_comparison = []
    for grp in all_group_keys:
        ga = groups_a.get(grp) or {}
        gb = groups_b.get(grp) or {}

        g_score_a = float(ga.get("score", 0))
        g_max_a = float(ga.get("max", 8))
        g_rate_a = (
            float(ga.get("pass_rate", 0))
            if "pass_rate" in ga
            else (round(g_score_a / g_max_a * 100, 1) if g_max_a > 0 else 0.0)
        )

        g_score_b = float(gb.get("score", 0))
        g_max_b = float(gb.get("max", 8))
        g_rate_b = (
            float(gb.get("pass_rate", 0))
            if "pass_rate" in gb
            else (round(g_score_b / g_max_b * 100, 1) if g_max_b > 0 else 0.0)
        )

        groups_comparison.append(
            {
                "group": grp,
                "score_a": g_score_a,
                "max_a": g_max_a,
                "rate_a": g_rate_a,
                "score_b": g_score_b,
                "max_b": g_max_b,
                "rate_b": g_rate_b,
                "delta_score": round(g_score_b - g_score_a, 2),
                "delta_rate": round(g_rate_b - g_rate_a, 1),
            }
        )

    # 3. Question-level deltas
    results_a = {r.get("id"): r for r in (run_a.get("results") or []) if r.get("id")}
    results_b = {r.get("id"): r for r in (run_b.get("results") or []) if r.get("id")}
    all_q_ids = sorted(set(results_a.keys()) | set(results_b.keys()))

    question_deltas = []
    regressions_count = 0
    improvements_count = 0

    for q_id in all_q_ids:
        ra = results_a.get(q_id) or {}
        rb = results_b.get(q_id) or {}

        v_a = ra.get("verdict", "N/A")
        v_b = rb.get("verdict", "N/A")
        s_a = float(ra.get("score", 0))
        s_b = float(rb.get("score", 0))

        if v_a != v_b or s_a != s_b:
            if s_b < s_a:
                status = "REGRESSED"
                regressions_count += 1
            elif s_b > s_a:
                status = "IMPROVED"
                improvements_count += 1
            else:
                status = "CHANGED"

            question_deltas.append(
                {
                    "id": q_id,
                    "group": rb.get("group") or ra.get("group") or "unknown",
                    "verdict_a": v_a,
                    "verdict_b": v_b,
                    "score_a": s_a,
                    "score_b": s_b,
                    "delta": round(s_b - s_a, 2),
                    "status": status,
                    "note": rb.get("notes") or ra.get("notes") or "",
                }
            )

    return {
        "run_a": {
            "run_id": run_a.get("run_id", "Run A"),
            "model": run_a.get("model", "unknown"),
            "timestamp": run_a.get("timestamp", ""),
            "total_score": score_a,
            "max_score": max_a,
            "pass_rate": pass_rate_a,
        },
        "run_b": {
            "run_id": run_b.get("run_id", "Run B"),
            "model": run_b.get("model", "unknown"),
            "timestamp": run_b.get("timestamp", ""),
            "total_score": score_b,
            "max_score": max_b,
            "pass_rate": pass_rate_b,
        },
        "score_delta": score_delta,
        "pass_rate_delta": pass_rate_delta,
        "regressions_count": regressions_count,
        "improvements_count": improvements_count,
        "violations_comparison": violations_comparison,
        "groups_comparison": groups_comparison,
        "question_deltas": question_deltas,
    }


def format_markdown_report(diff: dict[str, Any]) -> str:
    ra = diff["run_a"]
    rb = diff["run_b"]
    score_delta_str = (
        f"+{diff['score_delta']}" if diff["score_delta"] > 0 else f"{diff['score_delta']}"
    )
    rate_delta_str = (
        f"+{diff['pass_rate_delta']}%"
        if diff["pass_rate_delta"] > 0
        else f"{diff['pass_rate_delta']}%"
    )

    lines = [
        "# Báo cáo Đối chiếu Kết quả Benchmark RAG (Markdown & Excel)",
        "",
        "## 1. Tổng quan Lần chạy",
        "",
        "| Tiêu chí | Lần chạy A (Baseline) | Lần chạy B (Candidate) | Chênh lệch (Delta) |",
        "| :--- | :--- | :--- | :--- |",
        f"| **Mã Run ID** | `{ra['run_id']}` | `{rb['run_id']}` | - |",
        f"| **Mô hình / Phiên bản** | {ra['model']} | {rb['model']} | - |",
        f"| **Thời điểm chạy** | {ra['timestamp'] or 'N/A'} | {rb['timestamp'] or 'N/A'} | - |",
        f"| **Tổng điểm đạt được** | **{ra['total_score']} / {ra['max_score']}** | **{rb['total_score']} / {rb['max_score']}** | **{score_delta_str} điểm** |",
        f"| **Tỷ lệ đạt chuẩn (% Pass)** | **{ra['pass_rate']}%** | **{rb['pass_rate']}%** | **{rate_delta_str}** |",
        f"| **Số câu cải thiện (Improved)** | - | {diff['improvements_count']} câu | +{diff['improvements_count']} |",
        f"| **Số câu bị thoái lui (Regressed)** | - | {diff['regressions_count']} câu | {diff['regressions_count']} |",
        "",
        "## 2. Điểm số theo Nhóm Đánh giá (Scores by Group)",
        "",
        "| Nhóm kiểm thử | Điểm Run A | Tỷ lệ A | Điểm Run B | Tỷ lệ B | Chênh lệch |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]

    for g in diff["groups_comparison"]:
        g_delta_str = (
            f"+{g['delta_score']}" if g["delta_score"] > 0 else f"{g['delta_score']}"
        )
        lines.append(
            f"| `{g['group']}` | {g['score_a']}/{g['max_a']} | {g['rate_a']}% | "
            f"{g['score_b']}/{g['max_b']} | {g['rate_b']}% | **{g_delta_str}** |"
        )

    lines.extend([
        "",
        "## 3. Thống kê Vi phạm Quy tắc (Violation Counts)",
        "",
    ])

    if not diff["violations_comparison"]:
        lines.append("*Không ghi nhận vi phạm quy tắc trong cả hai lần chạy.*")
    else:
        lines.extend([
            "| Loại vi phạm | Run A | Run B | Chênh lệch |",
            "| :--- | :---: | :---: | :---: |",
        ])
        for v in diff["violations_comparison"]:
            v_delta_str = (
                f"+{v['delta']}" if v["delta"] > 0 else f"{v['delta']}"
            )
            lines.append(
                f"| `{v['violation']}` | {v['count_a']} | {v['count_b']} | {v_delta_str} |"
            )

    lines.extend([
        "",
        "## 4. Chi tiết các Câu hỏi có Thay đổi Kết quả (Verdict / Score Deltas)",
        "",
    ])

    if not diff["question_deltas"]:
        lines.append("✅ **100% câu hỏi giữ nguyên kết quả đánh giá giữa hai lần chạy.**")
    else:
        lines.extend([
            "| Mã câu | Nhóm | Đánh giá Run A | Đánh giá Run B | Điểm A -> B | Trạng thái | Ghi chú |",
            "| :---: | :--- | :---: | :---: | :---: | :---: | :--- |",
        ])
        for q in diff["question_deltas"]:
            status_icon = (
                "🟢 IMPROVED"
                if q["status"] == "IMPROVED"
                else ("🔴 REGRESSED" if q["status"] == "REGRESSED" else "🟡 CHANGED")
            )
            q_delta_str = f"+{q['delta']}" if q["delta"] > 0 else f"{q['delta']}"
            lines.append(
                f"| **{q['id']}** | `{q['group']}` | {q['verdict_a']} | {q['verdict_b']} | "
                f"{q['score_a']} -> {q['score_b']} ({q_delta_str}) | {status_icon} | {q['note']} |"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Đối chiếu kết quả giữa hai lần chạy Benchmark RAG."
    )
    parser.add_argument("run_a", help="Đường dẫn file kết quả Baseline (Run A)")
    parser.add_argument("run_b", help="Đường dẫn file kết quả Candidate (Run B)")
    parser.add_argument(
        "--markdown", action="store_true", help="Xuất báo cáo định dạng Markdown"
    )
    parser.add_argument(
        "--output", "-o", help="Đường dẫn file để ghi báo cáo (tùy chọn)"
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Trả về mã thoát khác 0 (exit 1) nếu có bất kỳ câu hỏi nào bị thoái lui (regressed).",
    )

    args = parser.parse_args()

    try:
        run_a = load_run_file(args.run_a)
        run_b = load_run_file(args.run_b)
        diff = compare_runs(run_a, run_b)
        report = format_markdown_report(diff)

        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(report, encoding="utf-8")
            print(f"Đã xuất báo cáo đối chiếu ra: {out_path}")
        else:
            print(report)

        if args.fail_on_regression and diff["regressions_count"] > 0:
            sys.stderr.write(
                f"\n[CẢNH BÁO] Phát hiện {diff['regressions_count']} câu hỏi bị thoái lui (regression)!\n"
            )
            return 1

        return 0
    except Exception as exc:
        sys.stderr.write(f"Lỗi: {exc}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
