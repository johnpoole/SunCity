"""Render each chapter with a separate voice per character and concatenate the blocks."""
import asyncio, json, pathlib, re, shutil, subprocess, sys, time
import edge_tts

VOICES = {
    "NARRATOR":       "en-GB-RyanNeural",
    "FLIN":           "en-US-ChristopherNeural",
    "YOBMOT":         "en-GB-LibbyNeural",
    "GUBMUH":         "en-US-RogerNeural",
    "MR_YTIDRUSBA":   "en-US-SteffanNeural",
    "MRS_YTIDRUSBA":  "en-US-MichelleNeural",
    "YREKCAUQ":       "en-GB-ThomasNeural",
    "HTURTEHTERAPS":  "en-AU-NatashaNeural",
    "PEOPLE":         "en-US-GuyNeural",
}

NAMES = {
    "NARRATOR":       "Narrator",
    "FLIN":           "Flin Flon",
    "YOBMOT":         "Princess Yobmot",
    "GUBMUH":         "King Gubmuh",
    "MR_YTIDRUSBA":   "Mr. Ytidrusba",
    "MRS_YTIDRUSBA":  "Mrs. Ytidrusba",
    "YREKCAUQ":       "Doctor Yrekcauq",
    "HTURTEHTERAPS":  "Hturtehteraps",
    "PEOPLE":         "The people",
}

WORK = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "build")
OUT = pathlib.Path("audio")


SHOUTED = re.compile(r"\b[A-Z]{2,}\b")


def speakable(text):
    text = re.sub(r"\[[*†‡]\]", "", text)
    text = text.replace(" -- ", ", ").replace("--", ", ")
    text = text.replace("“", "").replace("”", "").replace('"', "")
    # The printer set the opening word of every chapter, and the newspaper headlines,
    # in full capitals. Read aloud those come out as letters: I, N for IN. The book
    # has no real abbreviation in capitals, so every one of them is a word.
    text = SHOUTED.sub(lambda m: m.group(0).capitalize(), text)
    text = re.sub(r"\s+", " ", text).strip()
    # A fragment left holding only punctuation, such as the bracket around a reported
    # cry, has nothing to say and the speech service returns no audio for it.
    return text if re.search(r"[A-Za-z0-9]", text) else ""


def chapter_titles():
    """The titles the page shows, so the voice reads the same words the reader sees."""
    path = pathlib.Path("chapters.json")
    if not path.exists():
        raise SystemExit("synth_cast.py: chapters.json is missing. Run titles.py first.")
    return {c["n"]: c["title"] for c in json.loads(path.read_text(encoding="utf-8"))}


def spoken_heading(titles, n):
    if n not in titles:
        raise SystemExit(f"synth_cast.py: chapters.json has no title for chapter {n}. "
                         f"Run titles.py to rebuild it.")
    return f"Chapter {n}. {titles[n]}."


def blocks_for(chapter, n, titles):
    """Merge consecutive segments sharing a voice into one synthesis block."""
    out = [{"voice": "NARRATOR", "text": spoken_heading(titles, n)}]
    for s in chapter["segments"]:
        t = speakable(s["text"])
        if not t:
            continue
        if out and out[-1]["voice"] == s["voice"]:
            out[-1]["text"] += " " + t
        else:
            out.append({"voice": s["voice"], "text": t})
    return out


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"ffprobe failed on {path}: {r.stderr.strip()}")
    return float(r.stdout.strip())


async def synth_block(text, voice, path):
    for attempt in range(1, 5):
        try:
            comm = edge_tts.Communicate(text, voice)
            cues = []
            with open(path, "wb") as f:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
                        cues.append({"start": chunk["offset"] / 1e7,
                                     "end": (chunk["offset"] + chunk["duration"]) / 1e7,
                                     "text": chunk["text"]})
            if path.stat().st_size < 500:
                raise RuntimeError(f"only {path.stat().st_size} bytes written")
            return cues
        except Exception as e:
            if attempt == 4:
                raise RuntimeError(
                    f"synth_cast.py: voice {voice} failed after 4 attempts on "
                    f"{len(text)} chars -> {path}: {e!r}") from e
            await asyncio.sleep(4 * attempt)


async def build_chapter(n, chapter, titles):
    mp3 = OUT / f"ch{n:02d}.mp3"
    meta = OUT / f"ch{n:02d}.json"
    work = WORK / f"ch{n:02d}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    blocks = blocks_for(chapter, n, titles)
    offset, cues, parts = 0.0, [], []

    for i, b in enumerate(blocks):
        part = work / f"{i:04d}.mp3"
        raw = await synth_block(b["text"], VOICES[b["voice"]], part)
        for c in raw:
            cues.append({"start": round(offset + c["start"], 3),
                         "end": round(offset + c["end"], 3),
                         "text": c["text"], "voice": b["voice"]})
        offset += duration(part)
        parts.append(part)

    listing = work / "list.txt"
    listing.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", str(listing), "-c", "copy", str(mp3)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed for chapter {n}: {r.stderr.strip()}")

    meta.write_text(json.dumps({"chapter": n, "cues": cues}), encoding="utf-8")
    # On Windows ffmpeg can still hold a part file for a moment after it exits. The chapter
    # is already written, so a temp directory that will not delete is reported, not fatal.
    try:
        shutil.rmtree(work)
    except OSError as e:
        print(f"synth_cast.py: chapter {n} built, but the work directory {work} could not be "
              f"removed: {e}. Delete it by hand.", flush=True)
    return len(blocks), duration(mp3)


async def main():
    cast = json.loads(pathlib.Path("cast.json").read_text(encoding="utf-8"))
    titles = chapter_titles()
    OUT.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)
    order = sorted(cast, key=lambda k: int(k))
    total = 0.0
    for k in order:
        n = int(k)
        meta = OUT / f"ch{n:02d}.json"
        if meta.exists() and (OUT / f"ch{n:02d}.mp3").exists():
            total += duration(OUT / f"ch{n:02d}.mp3")
            print(f"ch{n:02d} already built, skip", flush=True)
            continue
        t0 = time.time()
        nb, dur = await build_chapter(n, cast[k], titles)
        total += dur
        print(f"ch{n:02d}  {nb:3d} blocks  {dur/60:5.1f} min  built in {time.time()-t0:5.0f}s",
              flush=True)
    print(f"total runtime {total/3600:.2f} hours")


if __name__ == "__main__":
    asyncio.run(main())
