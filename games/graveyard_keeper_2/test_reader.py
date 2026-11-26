"""Golden values read by hand from the eight stage folders (not copied from reader output)."""
from pathlib import Path
import unittest
from reader import read

HERE = Path(__file__).resolve().parent / "stages"
# (day, graveyardQuality, churchQuality) typed from each JSON file by eye; happiness is the
# value the player read from the HUD thumbs-up counter at that point (0, 3, 0, 5, 10 of 20).
GOLDEN = {
    "stage1_day110": (110, 28, 36, 0),
    "stage2_day111": (111, 28, 36, 3),
    "stage3_day113": (113, 28, 36, 3),
    "stage4_day114": (114, 28, 36, 0),
    "stage5_day116": (116, 23, 36, 5),
    "stage6_day117": (117, 23, 36, 5),
    "stage7_day117": (117, 23, 29, 5),
    "stage8_day117": (117, 23, 29, 10),
}


class ReaderTests(unittest.TestCase):
    def test_stage_values_and_facts(self):
        for name, (day, graveyard, church, happiness) in GOLDEN.items():
            card = read(HERE / name)
            self.assertEqual(card["progress"]["day"], day, name)
            self.assertEqual(card["progress"]["graveyard_quality"], graveyard, name)
            self.assertEqual(card["progress"]["church_quality"], church, name)
            self.assertEqual(card["progress"]["happiness"], happiness, name)
            self.assertEqual(card["facts"], [
                {"id": "day", "icon": "day", "value": str(day)},
                {"id": "graveyard_quality", "icon": "graveyard_quality", "value": str(graveyard)},
                {"id": "church_quality", "icon": "church_quality", "value": str(church)},
                {"id": "happiness", "icon": "happiness", "value": str(happiness)},
            ], name)
            for field in ("day", "graveyard_quality", "church_quality", "happiness"):
                self.assertIn(field, card["proven"])
                self.assertEqual(card["fact_sources"][field], field)

    def test_quality_fields_declare_nonmonotonic(self):
        card = read(HERE / "stage8_day117")
        for field in ("graveyard_quality", "church_quality", "happiness"):
            self.assertTrue(card["nonmonotonic"][field].strip())
        self.assertNotIn("day", card["nonmonotonic"])

    def test_saved_at_is_parsed_and_increases(self):
        times = [read(HERE / n)["progress"]["saved_at"] for n in sorted(HERE.glob("stage*"))]
        self.assertTrue(all(isinstance(t, float) for t in times))
        self.assertEqual(times, sorted(times))

    def test_unverified_fields_stay_hidden(self):
        card = read(HERE / "stage8_day117")
        self.assertEqual(card["progress"]["village_rep"], 17)  # HUD reputation moved 0 -> 10 while this stayed 17: not the HUD value
        self.assertEqual(card["progress"]["town_citizens"], 20)
        for field in ("village_rep", "town_citizens"):
            self.assertIn(field, card["unproven"])
            self.assertNotIn(field, card["proven"])
        self.assertIsNone(card["place"])

    def test_directory_picks_newest_info(self):
        card = read(HERE)
        self.assertEqual(card["progress"]["day"], 117)
        self.assertEqual(card["progress"]["church_quality"], 29)
        self.assertEqual(card["progress"]["happiness"], 10)

    def test_info_without_dat_hides_happiness(self):
        import shutil, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(HERE / "stage8_day117" / "Steam_1.info", tmp)
            card = read(tmp)
            self.assertEqual(card["progress"]["day"], 117)
            self.assertIsNone(card["progress"]["happiness"])
            self.assertIn("happiness", card["unproven"])
            self.assertEqual([f["id"] for f in card["facts"]], ["day", "graveyard_quality", "church_quality"])

    def test_missing_input_displays_nothing(self):
        card = read(HERE / "does_not_exist.info")
        self.assertEqual(card["facts"], [])
        self.assertEqual(card["proven"], [])


if __name__ == "__main__":
    unittest.main()
