import asyncio, json, pathlib, re, sys, time
import edge_tts

VOICE = "en-GB-RyanNeural"
RATE = "+0%"
ROMAN = re.compile(r"^([IVXLC]+)\.\s*--\s*(.+)$")

def to_speech(text, n):
    lines = text.split("\n")
    head = lines[0].rstrip(".")
    m = ROMAN.match(head)
    if not m:
        raise SystemExit(f"tts.py: chapter {n} heading '{head}' does not match 'ROMAN. -- TITLE'")
    spoken_head = f"Chapter {n}. {m.group(2).title()}."
    body = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):   # editorial footnote
            continue
        line = re.sub(r"\[[*\u2020\u2021]\]", "", line)   # inline footnote markers
        line = line.replace(" -- ", ", ")                  # em dash -> spoken pause
        body.append(line)
    return spoken_head + "\n\n" + "\n\n".join(body)

async def one(n, title, text, mp3, vtt):
    for attempt in range(1, 5):
        try:
            comm = edge_tts.Communicate(text, VOICE, rate=RATE)
            sub = edge_tts.SubMaker()
            with open(mp3, "wb") as f:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                        sub.feed(chunk)
            pathlib.Path(vtt).write_text(sub.get_srt(), encoding="utf-8")
            size = pathlib.Path(mp3).stat().st_size
            if size < 10000:
                raise RuntimeError(f"output only {size} bytes")
            return size
        except Exception as e:
            if attempt == 4:
                raise RuntimeError(
                    f"tts.py: chapter {n} '{title}' failed after 4 attempts writing {mp3}: {e!r}"
                ) from e
            print(f"  ch{n:02d} attempt {attempt} failed ({e!r}); retrying", flush=True)
            await asyncio.sleep(5 * attempt)

async def main(only=None):
    manifest = json.loads(pathlib.Path("manifest.json").read_text(encoding="utf-8"))
    pathlib.Path("audio").mkdir(exist_ok=True)
    for m in manifest:
        n = m["n"]
        if only and n not in only:
            continue
        mp3 = f"audio/ch{n:02d}.mp3"
        vtt = f"audio/ch{n:02d}.srt"
        if pathlib.Path(mp3).exists() and pathlib.Path(mp3).stat().st_size > 10000:
            print(f"ch{n:02d} exists, skip", flush=True)
            continue
        text = to_speech(pathlib.Path("text") / m["text"], n) if False else \
               to_speech((pathlib.Path("text") / m["text"]).read_text(encoding="utf-8"), n)
        t0 = time.time()
        size = await one(n, m["title"], text, mp3, vtt)
        print(f"ch{n:02d} {m['words']:5d}w -> {size/1024:7.0f} KiB  {time.time()-t0:5.1f}s  {m['title']}", flush=True)

if __name__ == "__main__":
    only = set(int(a) for a in sys.argv[1:]) or None
    asyncio.run(main(only))
