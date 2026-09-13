import re, json, pathlib
from bs4 import BeautifulSoup

html = pathlib.Path("suncity_raw.html").read_bytes().decode("iso-8859-1")
soup = BeautifulSoup(html, "html.parser")

heads = soup.find_all("h2", id=lambda v: False)
# chapter headings are <h2> containing <a id="chN">
chapter_heads = [h for h in soup.find_all("h2") if h.find("a", id=re.compile(r"^ch\d+$"))]
if not chapter_heads:
    raise SystemExit("extract.py: no chapter <h2> elements with id=chN found in suncity_raw.html")

def clean(s):
    s = s.replace("\u2014", " -- ").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

chapters = []
for i, h in enumerate(chapter_heads):
    title = clean(h.get_text())
    paras = []
    for el in h.next_siblings:
        if getattr(el, "name", None) == "h2" and el.find("a", id=re.compile(r"^ch\d+$")):
            break
        if getattr(el, "name", None) == "h3" and "THE END" in el.get_text().upper():
            break
        if getattr(el, "name", None) == "p":
            if "caption" in (el.get("class") or []):
                continue
            t = clean(el.get_text())
            if t:
                paras.append(t)
    if not paras:
        raise SystemExit(f"extract.py: chapter {i+1} '{title}' yielded zero paragraphs")
    chapters.append({"n": i + 1, "title": title, "paras": paras})

out = pathlib.Path("text")
manifest = []
for c in chapters:
    body = c["title"] + ".\n\n" + "\n\n".join(c["paras"])
    f = out / f"ch{c['n']:02d}.txt"
    f.write_text(body, encoding="utf-8")
    manifest.append({"n": c["n"], "title": c["title"], "chars": len(body),
                     "words": len(body.split()), "text": f.name})

pathlib.Path("manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"{len(chapters)} chapters, {sum(m['words'] for m in manifest)} words")
for m in manifest[:3] + manifest[-2:]:
    print(f"  {m['n']:2d}  {m['words']:6d}w  {m['title']}")
