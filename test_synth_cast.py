"""What gets handed to the speech service, and what the chapter headings become."""
import unittest
import synth_cast as S


class Speakable(unittest.TestCase):
    def test_the_opening_word_of_a_chapter_is_a_word_not_letters(self):
        self.assertEqual(
            S.speakable("IN one of the loneliest parts of the Rocky Mountains"),
            "In one of the loneliest parts of the Rocky Mountains")

    def test_a_headline_in_capitals_becomes_speech(self):
        self.assertEqual(S.speakable("CAPTURE OF A WONDERFUL CREATURE"),
                         "Capture Of A Wonderful Creature")

    def test_a_name_in_capitals_keeps_its_shape(self):
        self.assertEqual(S.speakable("YTIDRUSBA rose to his feet"), "Ytidrusba rose to his feet")

    def test_single_letters_are_left_alone(self):
        self.assertEqual(S.speakable("I saw a man, F.S.E.U.R., pass by"),
                         "I saw a man, F.S.E.U.R., pass by")

    def test_dashes_become_pauses_and_quotes_are_dropped(self):
        self.assertEqual(S.speakable('He said -- "come here" -- and went'),
                         "He said, come here, and went")

    def test_a_fragment_with_nothing_to_say_is_dropped(self):
        self.assertEqual(S.speakable("("), "")
        self.assertEqual(S.speakable("  --  "), "")


TITLES = {1: "The Lake of Mystery", 2: "Flin Flon's Fish"}


class Headings(unittest.TestCase):
    def test_the_voice_reads_the_title_the_page_shows(self):
        self.assertEqual(S.spoken_heading(TITLES, 2), "Chapter 2. Flin Flon's Fish.")

    def test_a_missing_title_stops_the_build(self):
        with self.assertRaises(SystemExit):
            S.spoken_heading(TITLES, 9)


class Blocks(unittest.TestCase):
    def test_consecutive_lines_of_one_voice_become_a_single_block(self):
        chapter = {"segments": [{"voice": "NARRATOR", "text": "He rose."},
                                {"voice": "FLIN", "text": "Good day."},
                                {"voice": "FLIN", "text": "And good night."},
                                {"voice": "NARRATOR", "text": "("}]}
        blocks = S.blocks_for(chapter, 1, TITLES)
        self.assertEqual([b["voice"] for b in blocks], ["NARRATOR", "FLIN"])
        self.assertEqual(blocks[0]["text"], "Chapter 1. The Lake of Mystery. He rose.")
        self.assertEqual(blocks[1]["text"], "Good day. And good night.")


if __name__ == "__main__":
    unittest.main()
