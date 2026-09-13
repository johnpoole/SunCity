import json, pathlib, re

ROMAN = re.compile(r"^([IVXLC]+)\.\s*--\s*(.+)$")
SMALL = {"a","an","and","as","at","but","by","for","in","of","on","or","the","to","up","with","from"}

def cap(word):
    # keep interior apostrophes lowercase: FLON'S -> Flon's
    parts = word.split("'")
    return "'".join([parts[0].capitalize()] + [p.lower() for p in parts[1:]])

def titlecase(s):
    words = s.lower().split()
    out = []
    for i, w in enumerate(words):
        if w in SMALL and 0 < i < len(words) - 1:
            out.append(w)
        else:
            out.append(cap(w))
    return " ".join(out)

m = json.loads(pathlib.Path("manifest.json").read_text(encoding="utf-8"))
chapters = []
for c in m:
    g = ROMAN.match(c["title"])
    if not g:
        raise SystemExit(f"titles.py: chapter {c['n']} title '{c['title']}' does not match 'ROMAN. -- TITLE'")
    chapters.append({"n": c["n"], "title": titlecase(g.group(2)), "words": c["words"]})

pathlib.Path("chapters.json").write_text(json.dumps(chapters, indent=1), encoding="utf-8")
for c in chapters:
    print(f"{c['n']:2d}. {c['title']}")
