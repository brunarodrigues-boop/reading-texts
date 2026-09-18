#!/usr/bin/env python3
"""Refresh the embedded DATA block in index.html from the MobyMax primer CSV.

    python3 build.py "<path to Primer Course CSV>"

Only the `const DATA = {...};` line is rewritten; every other byte of
index.html — the whole UI — is left untouched, and the script asserts that
before writing. Entries keep CSV row order, which is what the page renders,
and lessons with no passage yet are kept with an empty `texts` list so the
sidebar still lists them.
"""
import csv, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "index.html")
PATTERN = re.compile(r'(const DATA = )(\{.*?\})(;\n)', re.S)
TEXT_COLS = ("Text Problem set 1", "Text Problem set 2")


def build(csv_path):
    rows = list(csv.DictReader(io.open(csv_path, encoding="utf-8-sig")))
    data = {}
    for r in rows:
        grade = (r.get("Grade") or "").strip()
        if not grade:
            continue
        texts = [(r.get(c) or "").strip() for c in TEXT_COLS]
        data.setdefault(grade, []).append({
            "unit":   (r.get("Unit") or "").strip(),
            "topic":  (r.get("Topic") or "").strip(),
            "lesson": (r.get("Lesson") or "").strip(),
            "texts":  [t for t in texts if t],
        })
    return data


def main(csv_path):
    page = io.open(PAGE, encoding="utf-8").read()
    m = PATTERN.search(page)
    if not m:
        sys.exit("could not find the DATA block in index.html")

    before = json.loads(m.group(2))
    data = build(csv_path)

    # Never silently drop a passage the page is already serving.
    lost = []
    for g, items in before.items():
        new = {(i["unit"], i["topic"], i["lesson"]): i for i in data.get(g, [])}
        for it in items:
            k = (it["unit"], it["topic"], it["lesson"])
            if it["texts"] and len(new.get(k, {}).get("texts", [])) < len(it["texts"]):
                lost.append(f"G{g} · {it['lesson']}")
    if lost:
        print("REFUSING TO WRITE — these lessons would lose text:")
        for l in lost[:20]:
            print("   ", l)
        sys.exit(1)

    blob = json.dumps(data, ensure_ascii=False)
    out = page[:m.start()] + m.group(1) + blob + m.group(3) + page[m.end():]

    # Everything outside the DATA block must be byte-identical.
    assert page[:m.start()] == out[:m.start()], "content before DATA changed"
    assert page[m.end():] == out[len(out) - len(page[m.end():]):], "content after DATA changed"

    io.open(PAGE, "w", encoding="utf-8").write(out)

    n_old = sum(len(i["texts"]) for v in before.values() for i in v)
    n_new = sum(len(i["texts"]) for v in data.values() for i in v)
    print(f"wrote {PAGE}")
    print(f"  passages {n_old} -> {n_new}  (+{n_new - n_old})")
    for g in sorted(data, key=lambda x: int(x) if x.isdigit() else 99):
        items = data[g]
        t = sum(len(i["texts"]) for i in items)
        print(f"    grade {g}: {len(items):3d} lessons, {t:3d} passages")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
