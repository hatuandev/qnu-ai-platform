import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

def parse_markdown_semantic_blocks(markdown_text: str, is_first_page: bool, is_last_page: bool):
    """Parse Markdown into structured semantic elements: header, table, signing_left, signing_right, and body blocks."""
    if not markdown_text or not markdown_text.strip():
        return {
            "header": "",
            "table": "",
            "signing_left": "",
            "signing_right": "",
            "body": [],
        }

    raw = markdown_text.strip()
    header_text = ""
    table_text = ""
    signing_left = ""
    signing_right = ""

    # 1. Extract HTML header table on page 1
    if is_first_page:
        m_hdr = re.search(r"<table[^>]*>[\s\S]*?BỘ GIÁO DỤC[\s\S]*?</table>", raw, re.IGNORECASE)
        if m_hdr:
            header_html = m_hdr.group(0)
            # Clean HTML to plain markdown
            clean_hdr = re.sub(r"<[^>]+>", "\n", header_html)
            clean_hdr = re.sub(r"\n\s*\n", "\n", clean_hdr).strip()
            header_text = clean_hdr
            raw = raw[:m_hdr.start()] + "\n" + raw[m_hdr.end():]

    # 2. Extract HTML signing table on closing page
    if is_last_page:
        m_sig = re.search(r"<table[^>]*>[\s\S]*?(?:Nơi nhận|HIỆU TRƯỞNG)[\s\S]*?</table>", raw, re.IGNORECASE)
        if m_sig:
            sig_html = m_sig.group(0)
            # Find td 1 and td 2
            tds = re.findall(r"<td[^>]*>([\s\S]*?)</td>", sig_html, re.IGNORECASE)
            if len(tds) >= 2:
                signing_left = re.sub(r"<[^>]+>", "\n", tds[0]).strip()
                signing_right = re.sub(r"<[^>]+>", "\n", tds[1]).strip()
            else:
                signing_right = re.sub(r"<[^>]+>", "\n", sig_html).strip()
            raw = raw[:m_sig.start()] + "\n" + raw[m_sig.end():]

    # 3. Extract GFM Tables (| ... |)
    table_lines = []
    other_lines = []
    in_tbl = False
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            in_tbl = True
            table_lines.append(s)
        else:
            if in_tbl:
                in_tbl = False
            other_lines.append(line)

    if table_lines:
        table_text = "\n".join(table_lines)

    remaining_raw = "\n".join(other_lines)
    # Remove HTML tags like <br>, <center>, </center>
    remaining_raw = re.sub(r"</?(?:br|center|p|div|span)[^>]*>", "\n", remaining_raw, flags=re.IGNORECASE)

    # Split remaining into paragraphs
    raw_blocks = [b.strip() for b in re.split(r"\n\s*\n", remaining_raw) if b.strip()]
    clean_body = []
    for b in raw_blocks:
        if b.startswith("<!--"):
            continue
        clean_b = re.sub(r"\n+", "\n", b).strip()
        if clean_b:
            clean_body.append(clean_b)

    return {
        "header": header_text,
        "table": table_text,
        "signing_left": signing_left,
        "signing_right": signing_right,
        "body": clean_body,
    }

# Test parsing on TB2302
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import KnowledgeDocument


async def run_test():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == 'doc_64869d87a6f9'))
        doc = res.scalar_one_or_none()
        p_mds = (doc.doc_metadata or {}).get("page_markdowns") or {}

    for p in ("1", "2"):
        md = p_mds.get(p, "")
        parsed = parse_markdown_semantic_blocks(md, is_first_page=(p=="1"), is_last_page=(p=="2"))
        print(f"\n=== Parsed Page {p} Markdown ===")
        print("Header:", repr(parsed["header"][:60]))
        print("Table snippet:", repr(parsed["table"][:80]))
        print("Signing left:", repr(parsed["signing_left"][:40]))
        print("Signing right:", repr(parsed["signing_right"][:40]))
        print(f"Body blocks ({len(parsed['body'])}):")
        for i, b in enumerate(parsed["body"]):
            print(f"  [{i+1}] {b[:50]!r}")

asyncio.run(run_test())
