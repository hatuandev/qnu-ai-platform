import os
import re
from pathlib import Path

backend_dir = Path("backend/app")
frontend_dir = Path("frontend/src")

def safe_read(p: Path) -> str:
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        try:
            with open(p, "rb") as f:
                return f.read().decode("utf-8", errors="ignore")
        except Exception:
            return ""

print("=== 1. BACKEND ARCHITECTURE & FILE SIZES ===")
large_files = []
total_py_files = 0
total_py_lines = 0

for p in backend_dir.rglob("*.py"):
    if "__pycache__" in p.parts:
        continue
    content = safe_read(p)
    if not content:
        continue
    lines = len(content.splitlines())
    total_py_files += 1
    total_py_lines += lines
    if lines > 600:
        large_files.append((lines, str(p.relative_to(Path(".")))))

large_files.sort(key=lambda x: x[0], reverse=True)
print(f"Total Python Files: {total_py_files} files, {total_py_lines:,} lines of code")
print(f"Files > 600 lines ({len(large_files)} files):")
for lines, fpath in large_files[:15]:
    print(f"  {lines:4d} lines: {fpath}")

print("\n=== 2. ZERO HARDCODED MODELS SCAN ===")
suspicious_model_hits = []
hardcoded_patterns = [
    r'["\'](gemini-[\w\.-]+)["\']',
    r'["\'](gpt-4o[\w\.-]*)["\']',
]
for p in backend_dir.rglob("*.py"):
    if "__pycache__" in p.parts or "test" in p.name:
        continue
    txt = safe_read(p)
    if not txt:
        continue
    for pat in hardcoded_patterns:
        matches = re.findall(pat, txt)
        if matches and "model_catalog_service" not in p.name and "seeder" not in p.name:
            rel = str(p.relative_to(Path(".")))
            suspicious_model_hits.append((rel, matches[:3]))

print(f"Model string occurrences outside catalog/seeder: {len(suspicious_model_hits)}")
for fpath, m in suspicious_model_hits[:10]:
    print(f"  {fpath}: {m}")

print("\n=== 3. ZERO MOJIBAKE & UTF-8 INTEGRITY SCAN ===")
mojibake_hits = []
mojibake_pattern = re.compile(r"[\ufffd]|\?oAn|\?cc|Quyt\s*<nh|B~\s*GIA\?O")
all_source_files = (
    list(backend_dir.rglob("*.py"))
    + list(frontend_dir.rglob("*.tsx"))
    + list(frontend_dir.rglob("*.ts"))
)
for p in all_source_files:
    if "__pycache__" in p.parts or "node_modules" in p.parts:
        continue
    content = safe_read(p)
    if content and mojibake_pattern.search(content):
        mojibake_hits.append(str(p.relative_to(Path("."))))

print(f"Mojibake / Corrupted text files found: {len(mojibake_hits)}")
for h in mojibake_hits:
    print(f"  {h}")

print("\n=== 4. FRONTEND STRUCTURE & COMPONENT REUSE ===")
ui_components = list((frontend_dir / "components" / "ui").glob("*.tsx"))
admin_components = list((frontend_dir / "components" / "admin").glob("*.tsx"))
ai_components = list((frontend_dir / "components" / "ai").glob("*.tsx"))
pages = list((frontend_dir / "pages").glob("*.tsx")) + list((frontend_dir / "pages").glob("**/*.tsx"))

total_ts_files = 0
total_ts_lines = 0
for p in frontend_dir.rglob("*.[jt]s*"):
    if "node_modules" in p.parts:
        continue
    c = safe_read(p)
    if c:
        total_ts_files += 1
        total_ts_lines += len(c.splitlines())

print(f"Frontend Totals: {total_ts_files} TypeScript files, {total_ts_lines:,} lines of code")
print(f"Component Hierarchy:")
print(f"  Level 1 (UI Primitives @/components/ui): {len(ui_components)} components")
print(f"  Level 2 (Admin Helpers @/components/admin): {len(admin_components)} components")
print(f"  Level 3 (AI Suite @/components/ai): {len(ai_components)} components")
print(f"  Pages count: {len(pages)} pages")

# Check for raw input type=checkbox / radio in pages
raw_input_hits = []
raw_input_pat = re.compile(r'<input\s+[^>]*type=[\'"](checkbox|radio)[\'"]')
for p in pages:
    txt = safe_read(p)
    if txt and raw_input_pat.search(txt):
        raw_input_hits.append(str(p.relative_to(Path("."))))

print(f"Pages with raw native <input type=checkbox/radio>: {len(raw_input_hits)}")
for h in raw_input_hits:
    print(f"  {h}")

# Check for emojis in pages and admin components
emoji_pattern = re.compile(r"[\U0001F300-\U0001F9FF]|[\u2600-\u26FF]|[\u2700-\u27BF]")
emoji_hits = []
for p in pages + admin_components:
    txt = safe_read(p)
    if txt and emoji_pattern.search(txt):
        emoji_hits.append(str(p.relative_to(Path("."))))

print(f"Pages/Admin components with character emojis (should use Lucide icons): {len(emoji_hits)}")
for h in emoji_hits[:5]:
    print(f"  {h}")

print("\n=== 5. RFC 7807 & EXCEPTION SAFETY SCAN ===")
bare_except_hits = []
bare_except_pat = re.compile(r"except\s*:\s*(?:pass|continue)")
for p in backend_dir.rglob("*.py"):
    if "__pycache__" in p.parts:
        continue
    txt = safe_read(p)
    if txt and bare_except_pat.search(txt):
        bare_except_hits.append(str(p.relative_to(Path("."))))

print(f"Backend files with bare 'except: pass/continue' (anti-pattern): {len(bare_except_hits)}")
for h in bare_except_hits:
    print(f"  {h}")
