"""Speaker attribution on the shapes of paragraph the book uses."""
import unittest
import attribute as A

PRESENT = ["FLIN", "YOBMOT"]


def voices(paragraphs, present=PRESENT, chapter=2):
    return [(s["voice"], s["text"]) for s in A.attribute_chapter(paragraphs, present, chapter)
            if s["voice"] != "NARRATOR" or s["how"] != "narration"]


class LeadIns(unittest.TestCase):
    def test_crowd_lead_in_and_the_lines_after_it(self):
        out = voices([
            "Everybody exclaimed to everybody else, --",
            '"Is it not wonderful?"',
            '"How strange to be sure!"',
        ])
        self.assertEqual([v for v, _ in out], ["PEOPLE", "PEOPLE"])

    def test_unnamed_girl_is_the_people(self):
        out = voices([
            "And one beautiful girl of about nineteen summers was heard to murmur, --",
            '"Wal, I guess that licks creation, it does."',
        ])
        self.assertEqual(out[0][0], "PEOPLE")

    def test_reporter_is_read_by_the_narrator(self):
        out = voices([
            "They produced an effect that is indescribable, though one of the reporters spoke of it --",
            '"As a scene of exquisite loveliness."',
        ])
        self.assertEqual(out[0][0], "NARRATOR")

    def test_named_lead_in_across_paragraphs(self):
        out = voices([
            "Then the great Flin Flon arose, calm, dignified and grave. He placed his umbrella on the table.",
            '"Mr President, learned Fellows, and ladies and gentlemen, I have the honour of appearing."',
            '"In dealing with the subject in hand it will be necessary for me to digress somewhat."',
        ], present=["FLIN"])
        self.assertEqual([v for v, _ in out], ["FLIN", "FLIN"])

    def test_pronoun_clause_beats_bystander(self):
        out = voices([
            "She tried to draw him towards her, but he frustrated her design, and he exclaimed, --",
            '"Your Highness, I am really surprised at you."',
        ])
        self.assertEqual(out[0][0], "FLIN")


class Asides(unittest.TestCase):
    def test_cry_reported_in_a_parenthesis_is_the_meeting(self):
        out = voices([
            "Her Highness rose and said, --",
            '"I oppose the application." ("Oh, oh!" and cries of "Shame!")',
            '"I have made a study of the whole race of chariot-drivers."',
        ], present=["YOBMOT"])
        self.assertEqual([v for v, _ in out], ["YOBMOT", "PEOPLE", "PEOPLE", "YOBMOT"])


class Replies(unittest.TestCase):
    def test_answer_to_a_tagged_crowd_line(self):
        out = voices([
            "Flin Flon arose and said, --",
            '"I intend to descend into the lake."',
            '"Impossible! impossible!" cried the audience.',
            '"Nothing is impossible to the resolute and energetic man of science."',
        ], present=["FLIN"])
        self.assertEqual([v for v, _ in out], ["FLIN", "PEOPLE", "FLIN"])

    def test_answer_to_the_crowd_in_the_same_paragraph(self):
        out = voices([
            "Flin Flon arose and said, --",
            '"I am prepared to brave that opposition."',
            '"How, how?" arose from a hundred throats. "By descending to the bottom of Lake Avernus."',
        ], present=["FLIN"])
        self.assertEqual([v for v, _ in out], ["FLIN", "PEOPLE", "FLIN"])


class NoGuessing(unittest.TestCase):
    def test_quotation_before_anyone_speaks_is_the_narrator(self):
        out = voices(["He was born to do great deeds.", '"Down the ringing grooves of time."'])
        self.assertEqual(out[0][0], "NARRATOR")

    def test_every_line_records_the_rule_that_placed_it(self):
        out = A.attribute_chapter([
            "Flin Flon arose and said, --",
            '"I intend to descend into the lake."',
            '"And I shall come back."',
            "The seven plagues of Egypt must have been nice by comparison.",
            '"Send me to Parliament,"',
        ], ["FLIN"], 25)
        hows = [s["how"] for s in out if s["voice"] != "NARRATOR"]
        self.assertEqual(hows, ["lead-in-named", "continuation", "continuation"])
        self.assertNotIn("default", [s["how"] for s in out])


if __name__ == "__main__":
    unittest.main()
