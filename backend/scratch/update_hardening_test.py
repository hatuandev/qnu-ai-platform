from pathlib import Path

p = Path("tests/test_publishing_v2_hardening.py")
c = p.read_text(encoding="utf-8")
old = "    db.get.side_effect = [binding, target_rev, col, old_rev]"
new = """    db.get.side_effect = lambda model, ident: {
        "rev_old": old_rev,
        "rev_new": target_rev,
        "bind_1": binding,
        "col_1": col,
    }.get(ident)"""

if old in c:
    p.write_text(c.replace(old, new), encoding="utf-8")
    print("UPDATED LF")
elif old.replace("\n", "\r\n") in c:
    p.write_text(c.replace(old.replace("\n", "\r\n"), new.replace("\n", "\r\n")), encoding="utf-8")
    print("UPDATED CRLF")
else:
    print("NOT FOUND")
