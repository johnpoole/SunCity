"""Split each chapter into narration and dialogue segments and name the speaker of each line."""
import json, pathlib, re

# gender resolves tags that carry no proper name, such as `said the lady`.
CAST = {
    "FLIN":           {"gender": "m", "pattern": r"\bFlin\b|\bFlonatin\b|\bFlon\b|\bJosiah\b"},
    "MR_YTIDRUSBA":   {"gender": "m", "pattern": r"\bMr\.?\s+Ytidrusba\b"},
    "MRS_YTIDRUSBA":  {"gender": "f", "pattern": r"\bMrs\.?\s+Ytidrusba\b"},
    "YOBMOT":         {"gender": "f", "pattern": r"\bYobmot\b|\bPrincess\b|\bHer Royal Highness\b"},
    "GUBMUH":         {"gender": "m", "pattern": r"\bGubmuh\b|\bKing\b|\bHis Majesty\b"},
    "YREKCAUQ":       {"gender": "m", "pattern": r"\bYrekcauq\b|\bDoctor\b|\bDr\.?\b"},
    "HTURTEHTERAPS":  {"gender": "f", "pattern": r"\bHturtehteraps\b"},
}
for c in CAST.values():
    c["re"] = re.compile(c["pattern"])

# A bare "Ytidrusba" is the husband early on and the wife from chapter 25.
BARE_YTIDRUSBA = re.compile(r"\bYtidrusba\b")
YTIDRUSBA_SWITCH_CHAPTER = 25

FEMALE = re.compile(r"\b(she|her|herself|lady|ladies|princess|queen|woman|madam|mrs|girl|dame)\b", re.I)
MALE = re.compile(r"\b(he|him|his|himself|gentleman|man|sir|mr|king|doctor|fellow|stranger)\b", re.I)

VERB = (r"(?:said|says|replied|exclaimed|cried|answered|asked|continued|observed|remarked|"
        r"responded|added|returned|retorted|shouted|murmured|whispered|inquired|enquired|"
        r"ejaculated|thundered|began|interrupted|demanded|rejoined|ventured|resumed|"
        r"persisted|urged|repeated|echoed|gasped|sighed|screamed|roared|put in|went on)")

POST_TAG = re.compile(r"^\s*[,.!?;:]?\s*(?:" + VERB + r"\s+(?P<a>[^.,;!?]{0,40})"
                      r"|(?P<b>[^.,;!?]{0,40}?)\s+" + VERB + r"\b)")
PRE_TAG = re.compile(r"(?P<who>[^.!?]{0,60})\b" + VERB + r"\b[^\"“]{0,30}$")
SPLIT_TAG = re.compile(r"\b" + VERB + r"\b[^.!?]*,\s*$")
PRONOUN_NEAR = re.compile(r"^[^.!?]{0,45}?\b(she|he|her|his|him)\b", re.I)
QUOTE = re.compile(r"“[^”]*”|\"[^\"]*\"")
INTERJECTION = re.compile(r"^[\"“]\s*(?:Oh|Ah|Well|Yes|No|Nay|Sir|Madam|Pray|Come|Why|"
                          r"What|How|Good|Dear|Alas|Hush|Stop|Hold|By)\b", re.I)


def named(text, chapter):
    hits = [k for k, c in CAST.items() if c["re"].search(text)]
    if not hits and BARE_YTIDRUSBA.search(text):
        hits = ["MRS_YTIDRUSBA" if chapter >= YTIDRUSBA_SWITCH_CHAPTER else "MR_YTIDRUSBA"]
    return hits[0] if len(hits) == 1 else None


def by_gender(text, present, recent):
    if FEMALE.search(text):
        want = "f"
    elif MALE.search(text):
        want = "m"
    else:
        return None
    for who in recent:
        if who in present and CAST[who]["gender"] == want:
            return who
    for who in present:
        if CAST[who]["gender"] == want:
            return who
    return None


def is_speech(quote, before, after, speech_earlier_in_para):
    """True when a quoted span is spoken aloud, false when it is a phrase inside a sentence."""
    inner = quote.strip("\"“”").strip()
    if not inner:
        return False
    if not (inner[0].isupper() or INTERJECTION.match(quote)):
        # A lowercase opening is speech only as the tail of a split quote:
        #   "Really, madam," answered Flin, "you need some information..."
        return bool(speech_earlier_in_para and SPLIT_TAG.search(before))
    if POST_TAG.match(after) or PRE_TAG.search(before):
        return True
    if before.strip() and not re.search(r"[.!?:;,—-]\s*$", before):
        return False
    return len(inner.split()) >= 4 or inner[-1] in ".!?"


def split_paragraph(paragraph):
    out, pos = [], 0
    for m in QUOTE.finditer(paragraph):
        if m.start() > pos:
            out.append(["narr", paragraph[pos:m.start()]])
        out.append(["quote", m.group(0)])
        pos = m.end()
    if pos < len(paragraph):
        out.append(["narr", paragraph[pos:]])
    return [s for s in out if s[1].strip()]


def build_segments(paragraphs):
    """Flatten the chapter into segments tagged with their paragraph index."""
    segs = []
    for pi, para in enumerate(paragraphs):
        parts = split_paragraph(para)
        speech_earlier = False
        for i, s in enumerate(parts):
            if s[0] == "quote":
                before = parts[i - 1][1] if i and parts[i - 1][0] == "narr" else ""
                after = parts[i + 1][1] if i + 1 < len(parts) and parts[i + 1][0] == "narr" else ""
                if not is_speech(s[1], before, after, speech_earlier):
                    s[0] = "narr"
                else:
                    speech_earlier = True
            segs.append({"kind": s[0], "text": s[1], "para": pi})
    return segs


def attribute_chapter(paragraphs, present, chapter):
    segs = build_segments(paragraphs)
    default = present[0] if present else "NARRATOR"
    recent, last, before_last = [], None, None

    # narration around each segment, and the first quote of each paragraph
    first_quote_in_para = {}
    for i, s in enumerate(segs):
        if s["kind"] == "quote" and s["para"] not in first_quote_in_para:
            first_quote_in_para[s["para"]] = i

    para_subject = {}
    for pi in set(s["para"] for s in segs):
        narr = " ".join(s["text"] for s in segs if s["para"] == pi and s["kind"] == "narr")
        para_subject[pi] = named(narr, chapter)

    result = []
    for i, s in enumerate(segs):
        if s["kind"] == "narr":
            result.append({"voice": "NARRATOR", "text": s["text"].strip(), "how": "narration"})
            continue

        nxt = segs[i + 1] if i + 1 < len(segs) else None
        prv = segs[i - 1] if i else None
        same_para_after = nxt["text"] if nxt and nxt["kind"] == "narr" and nxt["para"] == s["para"] else ""
        same_para_before = prv["text"] if prv and prv["kind"] == "narr" and prv["para"] == s["para"] else ""
        any_after = nxt["text"] if nxt and nxt["kind"] == "narr" else ""

        speaker = how = None

        m = POST_TAG.match(same_para_after)
        if m:
            tag = (m.group("a") or "") + " " + (m.group("b") or "")
            speaker = named(tag, chapter)
            how = "post-tag" if speaker else None
            if not speaker:
                speaker = by_gender(tag, present, recent)
                how = "post-tag-gender" if speaker else None

        if not speaker and same_para_before:
            m = PRE_TAG.search(same_para_before)
            if m:
                speaker = named(m.group("who"), chapter)
                how = "pre-tag" if speaker else None
                if not speaker:
                    speaker = by_gender(m.group("who"), present, recent)
                    how = "pre-tag-gender" if speaker else None

        # a following sentence like "Then she checked herself, and added:" names the speaker
        if not speaker and any_after:
            m = PRONOUN_NEAR.match(any_after.strip())
            if m:
                speaker = by_gender(m.group(1), present, recent)
                how = "following-pronoun" if speaker else None

        if not speaker and para_subject.get(s["para"]) and first_quote_in_para.get(s["para"]) == i:
            speaker, how = para_subject[s["para"]], "paragraph-subject"

        if not speaker and first_quote_in_para.get(s["para"]) != i:
            prev = next((r for r in reversed(result) if r["voice"] != "NARRATOR"), None)
            if prev:
                speaker, how = prev["voice"], "same-paragraph"

        if not speaker and last and len(present) > 1:
            other = before_last if before_last and before_last != last else \
                    next((p for p in present if p != last), None)
            if other:
                speaker, how = other, "alternation"

        if not speaker:
            speaker, how = default, "default"

        result.append({"voice": speaker, "text": s["text"].strip(), "how": how})
        before_last, last = last, speaker
        recent = [speaker] + [r for r in recent if r != speaker]

    return result


def main():
    manifest = json.loads(pathlib.Path("manifest.json").read_text(encoding="utf-8"))
    out, stats = {}, {}
    for m in manifest:
        n = m["n"]
        raw = (pathlib.Path("text") / m["text"]).read_text(encoding="utf-8")
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        heading, paragraphs = lines[0], lines[1:]
        paragraphs = [p for p in paragraphs if not (p.startswith("[") and p.endswith("]"))]

        counts = {k: len(c["re"].findall(raw)) for k, c in CAST.items()}
        key = "MRS_YTIDRUSBA" if n >= YTIDRUSBA_SWITCH_CHAPTER else "MR_YTIDRUSBA"
        counts[key] = max(counts[key], len(BARE_YTIDRUSBA.findall(raw)))
        present = [k for k, v in sorted(counts.items(), key=lambda x: -x[1]) if v >= 3]

        segs = attribute_chapter(paragraphs, present, n)
        out[n] = {"heading": heading, "present": present, "segments": segs}
        for s in segs:
            if s["voice"] != "NARRATOR":
                stats[s["how"]] = stats.get(s["how"], 0) + 1

    pathlib.Path("cast.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    spoken = sum(stats.values())
    print(f"{spoken} spoken lines across {len(out)} chapters")
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {v:5d}  {v*100/spoken:5.1f}%  {k}")

    voices = {}
    for c in out.values():
        for s in c["segments"]:
            if s["voice"] != "NARRATOR":
                voices[s["voice"]] = voices.get(s["voice"], 0) + 1
    print("\nlines per character:")
    for k, v in sorted(voices.items(), key=lambda x: -x[1]):
        print(f"  {v:5d}  {k}")


if __name__ == "__main__":
    main()
