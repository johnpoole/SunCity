# The Sunless City

J. E. Preston Muddock, 1905. Thirty-six chapters read aloud in the browser, with
the text scrolling under the voice and a picture above it that follows the story.

Open `index.html` over HTTP. It will not work from the file system because the
page fetches JSON.

    python -m http.server 8000

## The picture

Chapters 1 and 2 are drawn as a page from a Sunday colour supplement of the year
the book came out. That was the year Winsor McCay started Little Nemo in
Slumberland in the New York Herald, and Little Nemo is the model: a boy who falls
each night into a fantastic underground kingdom, against a grocer who sinks in a
copper fish into a lost city under a lake. Same shape of story, same year, same
city.

What that means on the canvas:

- **Black ink and flat colour.** Every shape is a filled colour with a heavy
  black line over it. No gradients, no soft edges, no shading.
- **Off register.** The colour is drawn a few pixels away from the black line, as
  the printing plates were.
- **Laid paper.** A cream ground with a faint speck in it, not white.
- **A caption strip** under each panel carrying the scene's own words, and a
  **speech balloon** over whoever is talking.

Everything is drawn with canvas primitives in `index.html`. There are no images
and no drawing library. The palette is the `INK` object; `inkShape` is the one
call that fills a path and then inks it.

The remaining thirty-four chapters still use the older renderer, a 96 by 54
canvas of coloured blocks scaled up. Chapters move over to the comic one at a
time, and the two renderers live side by side until they are all done.

### When the picture changes

The panel changes when the scene changes, or every fifteen seconds of the
reading, whichever comes first.

Fifteen seconds is `BEAT_SECONDS`. A scene that runs eleven minutes would
otherwise hold one drawing for eleven minutes, so each scene owns a run of
panels and the run repeats:

    beat = floor((now - scene start) / BEAT_SECONDS) % beats.length

`INK_BEATS` holds those runs, keyed by chapter number and then by the position
of the scene in `scenes.json`. Chapter 1 has eighteen panels across four scenes.
A chapter in `INK_BEATS` gets the comic; a chapter that is not there gets the old
canvas. A scene with no panels throws, naming the chapter and the scene, rather
than drawing nothing.

## How a chapter is built

Five steps, each its own script, each writing a file the next one reads.

| Step | Script | Writes |
|---|---|---|
| Split the source into chapters | `extract.py` | `text/chNN.txt`, `manifest.json` |
| Title the chapters | `titles.py` | `chapters.json` |
| Name the speaker of every line | `attribute.py` | `cast.json` |
| Read it aloud, one voice per speaker | `synth_cast.py` | `audio/chNN.mp3`, `audio/chNN.json` |
| Say what the picture shows | hand-written | `scenes.json` |

`tts.py` is the earlier reader that used one voice for the whole book.
`synth_cast.py` replaced it and is the one that builds what ships.

`audio/chNN.json` is the timing file. It holds one cue per phrase with a start, an
end, the words, and the speaker. The page highlights the text from it, and the
picture reads the speaker from it to decide whose balloon to open.

`scenes.json` marks where each scene begins, by cue number, with a note that
becomes the caption. Rebuilding the audio moves the cue numbers, so the markers
have to be re-pointed at the phrase they used to sit on.

### Who is speaking

`attribute.py` decides, in this order, and records which rule it used in the
`how` field so a wrong answer can be traced:

1. A tag after the quote, `said Flin`.
2. A tag before it.
3. A following sentence with a pronoun in it.
4. The sentence that leads into the quote, `Some few persons cried out, --`.
5. A whole paragraph of narration about one character, before the quote.
6. The subject of the paragraph, for the first quote in it.
7. The speaker of the previous quote in the same paragraph.
8. The other party, answering.
9. The same speaker, carrying on.

Unnamed crowds go to a speaker called `PEOPLE`, with its own voice and colour.
Words quoted from a newspaper go to the narrator. A cry reported inside a
parenthesis, the way a Hansard report does it, is the meeting interrupting and
does not take the floor from whoever is speaking.

There is deliberately **no fallback to the chapter's main character**. There used
to be, and it gave Flin Flon a hundred and twenty lines he never says, including
every line in chapter 2.

`python -m unittest test_attribute` covers the rules against the shapes of
paragraph the book actually uses.

### Rebuilding after a change to the speakers

`synth_cast.py` skips a chapter that already has both its `.mp3` and its `.json`.
So to rebuild, delete the pair for the chapters whose voices changed, run it
again, then re-point the scene markers at the cues carrying the same words. The
whole book is about nine hours of audio and takes roughly an hour to build.

## Deploying

The site is `sunlesscity.johnpoole.ca`, served by nginx in Docker on the house
server, out of `~/suncity`.

    git push origin main
    ssh basement 'cd ~/suncity && git pull --ff-only && docker compose build && docker compose up -d'

Confirm from the server, never from inside the house, because the router has no
hairpin NAT:

    ssh basement 'cd ~/suncity && git rev-parse --short HEAD && docker compose ps'

## Layout

    index.html        the whole reader: player, script, and both renderers
    chapters.json     chapter numbers and titles for the contents list
    scenes.json       scene markers and their captions, per chapter
    cast.json         every line with its speaker and the rule that named them
    manifest.json     chapter files and word counts
    text/             the chapters as plain text
    audio/            one mp3 and one cue file per chapter
    suncity_raw.html  the source the text came from
