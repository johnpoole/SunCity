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

VERB = (r"(?:said|says|saying|replied|exclaimed|cried|answered|asked|continued|observed|remarked|"
        r"responded|added|returned|retorted|shouted|murmured|murmur|whispered|inquired|enquired|"
        r"ejaculated|thundered|began|interrupted|demanded|rejoined|ventured|resumed|"
        r"persisted|urged|repeated|echoed|gasped|sighed|screamed|roared|put in|went on|"
        r"arose|spoke|proceeded|stammer|stammered|sneered|muttered|told|cries|addressed)")

# Speakers the book never names: the crowd, a voice in the hall, a lady at a meeting.
PEOPLE = "PEOPLE"
CROWD = re.compile(r"\b(everybody|everyone|every one|people|persons|crowd|audience|multitude|throats|"
                   r"voices|somebody|some one|someone|a hundred|\w+s\s+were\s+saying|Mrs\.?\s*\(|"
                   r"many more|one to the other|one to another|such (?:sentences|remarks|cries|expressions) as|"
                   r"(?:from|by) a voice|a voice (?:in|at|from|behind|near)|"
                   r"(?:a|an|one|another|some|several|many|two|three|few)\s+(?:\w+\s+){0,2}"
                   r"(?:lady|ladies|gentleman|gentlemen|man|men|woman|women|girl|girls|boy|boys|member|"
                   r"members|person|persons|fellow|stranger|savant|savants|professor|"
                   r"guest|guests|officer|official|citizen|citizens|bystander|bystanders|speaker))\b", re.I)
# A generic noun with "the" after the crowd has spoken is the same unnamed speaker carrying on.
GENERIC = re.compile(r"\b(?:the|this|that)\s+(?:\w+\s+){0,2}(?:lady|gentleman|man|woman|girl|boy|member|"
                     r"voice|speaker|stranger|fellow|reporter|guest|officer|official|person)\b", re.I)
# Words on a page are read by the narrator, not acted.
PRESS = re.compile(r"\b(reporters?|news|gazette|herald|times|journal|papers?|notice|placard|letter|telegram)\b", re.I)
LEAD_END = re.compile(r"[,:]\s*(?:--\s*)*[-.]?\s*$")

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


def who_is(tag, present, recent, chapter, last):
    """Name the speaker a tag points at, or None when the tag says nothing usable."""
    # The clause round the speech verb names the speaker; the rest of the sentence
    # names bystanders: "he frustrated her design, and ..., he exclaimed, --"
    verbs = list(re.finditer(r"\b" + VERB + r"\b", tag))
    if verbs:
        v = verbs[-1]
        clauses = re.split(r"[,;]\s*", tag)
        pos = 0
        clause = tag
        for c in clauses:
            if pos <= v.start() < pos + len(c) + 1:
                clause = c
                break
            pos += len(c) + 2
        for text in (clause, tag):
            who, how = who_in(text, present, recent, chapter, last)
            if who:
                return who, how
        return None, None
    return who_in(tag, present, recent, chapter, last)


def who_in(text, present, recent, chapter, last):
    if PRESS.search(text):
        return "NARRATOR", "press"
    if CROWD.search(text):
        return PEOPLE, "crowd"
    who = named(text, chapter)
    if who:
        return who, "named"
    if last == PEOPLE and GENERIC.search(text):
        return PEOPLE, "crowd"
    who = by_gender(text, present, recent)
    return (who, "gender") if who else (None, None)


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
        depth = paragraph.count("(", 0, m.start()) - paragraph.count(")", 0, m.start())
        out.append(["aside" if depth > 0 else "quote", m.group(0)])
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
            if s[0] == "quote" or s[0] == "aside":
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

        # A cry reported inside a parenthesis is the meeting interrupting, as in a Hansard
        # report: ("Oh, oh!" and cries of "Shame!"). It does not take the floor from the
        # speaker, so it leaves the alternation alone.
        if s["kind"] == "aside":
            result.append({"voice": PEOPLE, "text": s["text"].strip(), "how": "aside"})
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
            speaker, why = who_is(tag, present, recent, chapter, last)
            how = "post-tag-" + why if speaker else None

        if not speaker and same_para_before:
            m = PRE_TAG.search(same_para_before)
            if m:
                speaker, why = who_is(m.group("who"), present, recent, chapter, last)
                how = "pre-tag-" + why if speaker else None

        # The paragraph before ends in a lead-in: "Some few persons cried out, --"
        # or stands alone and names who speaks next: "He continued his address."
        lead = prv if prv and prv["kind"] == "narr" and prv["para"] == s["para"] - 1 else None
        if lead and same_para_before.strip():
            lead = None
        whole = bool(lead) and not any(x["kind"] == "quote" and x["para"] == lead["para"] for x in segs)
        lead_text = " ".join(x["text"] for x in segs if lead and x["para"] == lead["para"]) if whole \
                    else (lead["text"] if lead else "")
        if not speaker and lead:
            tail = re.split(r"(?<!\bMr\.)(?<!\bMrs\.)(?<!\bDr\.)(?<=[.!?])\s+", lead_text.strip())[-1]
            if LEAD_END.search(lead_text) or (whole and re.search(r"\b" + VERB + r"\b", tail)):
                speaker, why = who_is(tail, present, recent, chapter, last)
                how = "lead-in-" + why if speaker else None

        # A whole paragraph of narration about one character introduces that character's speech:
        #   "Then the great Flin Flon arose, calm, dignified and grave. ..."
        if not speaker and whole and named(lead_text, chapter):
            speaker, how = named(lead_text, chapter), "previous-subject"

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
            # The crowd shouts and someone answers in the same paragraph:
            #   "How, how?" arose from a hundred throats. "By descending..."
            if prev and prev["voice"] == PEOPLE and not same_para_before.rstrip().endswith(","):
                prev = None
                if before_last:
                    speaker, how = before_last, "reply"
            if prev:
                speaker, how = prev["voice"], "same-paragraph"

        # After a tagged crowd line the next untagged quote answers it; after an untagged
        # crowd line the crowd is still talking.
        if not speaker and last == PEOPLE:
            last_quote = next((r for r in reversed(result) if r["voice"] != "NARRATOR"), None)
            if last_quote["how"].startswith(("post-tag", "pre-tag")) and before_last:
                speaker, how = before_last, "reply"
            else:
                speaker, how = PEOPLE, "continuation"

        if not speaker and last and len(present) > 1:
            other = before_last if before_last and before_last != last else \
                    next((p for p in present if p != last), None)
            if other:
                speaker, how = other, "alternation"

        # One speaker and no tag: a speech or the crowd carrying on over several paragraphs.
        if not speaker and last:
            speaker, how = last, "continuation"

        # A quotation on the page before anyone in the chapter has spoken is the narrator reading.
        if not speaker:
            speaker, how = "NARRATOR", "quotation"

        result.append({"voice": speaker, "text": s["text"].strip(), "how": how})
        if speaker != "NARRATOR":
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
