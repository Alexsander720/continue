"""Golden values read by hand from the four .info sidecars (not copied from reader output)."""
from pathlib import Path
import unittest
from reader import read

HERE = Path(__file__).resolve().parent / "stages"


class ReaderTests(unittest.TestCase):
    def test_stage_days(self):
        expected = {"stage1_day110.info": 110, "stage2_day111.info": 111,
                    "stage3_day113.info": 113, "stage4_day114.info": 114}
        for name, day in expected.items():
            card = read(HERE / name)
            self.assertEqual(card["progress"]["day"], day, name)
            self.assertEqual(card["facts"], [{"id": "day", "icon": "day", "value": str(day)}])
            self.assertIn("day", card["proven"])
            self.assertEqual(card["fact_sources"]["day"], "day")

    def test_saved_at_is_parsed_and_increases(self):
        times = [read(HERE / n)["progress"]["saved_at"] for n in sorted(HERE.glob("stage*.info"))]
        self.assertTrue(all(isinstance(t, float) for t in times))
        self.assertEqual(times, sorted(times))

    def test_constant_fields_stay_hidden(self):
        card = read(HERE / "stage4_day114.info")
        self.assertEqual(card["progress"]["village_rep"], 17)
        for field in ("graveyard_quality", "church_quality", "village_rep", "town_citizens"):
            self.assertIn(field, card["unproven"])
            self.assertNotIn(field, card["proven"])
        self.assertIsNone(card["place"])

    def test_directory_picks_newest_info(self):
        card = read(HERE)
        self.assertEqual(card["progress"]["day"], 114)

    def test_missing_input_displays_nothing(self):
        card = read(HERE / "does_not_exist.info")
        self.assertEqual(card["facts"], [])
        self.assertEqual(card["proven"], [])


if __name__ == "__main__":
    unittest.main()
