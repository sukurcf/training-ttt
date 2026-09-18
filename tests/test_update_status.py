import csv
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_status import CommandError, apply_comment, parse_status_comment  # noqa: E402


FIELDNAMES = [
    "day",
    "topic",
    "focus",
    "how_to_cover",
    "practice",
    "resource",
    "Person 1",
    "Person 2",
    "Person 3",
]
ROWS = [
    {
        "day": "1",
        "topic": "Python setup and workflow",
        "focus": "focus",
        "how_to_cover": "how",
        "practice": "practice",
        "resource": "resource",
        "Person 1": "not-started",
        "Person 2": "not-started",
        "Person 3": "not-started",
    },
    {
        "day": "2",
        "topic": "Conditionals and loops",
        "focus": "focus",
        "how_to_cover": "how",
        "practice": "practice",
        "resource": "resource",
        "Person 1": "not-started",
        "Person 2": "not-started",
        "Person 3": "not-started",
    },
]


def write_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ROWS)


class UpdateStatusTests(unittest.TestCase):
    def test_parses_person_and_status_aliases(self):
        command = parse_status_comment(
            "Day 1, p1-inprogress, Person 2: complete",
            FIELDNAMES,
        )
        self.assertIsNotNone(command)
        self.assertEqual(
            command.updates,
            {"Person 1": "in-progress", "Person 2": "done"},
        )

    def test_ignores_normal_comments(self):
        self.assertIsNone(parse_status_comment("Great discussion today!", FIELDNAMES))

    def test_updates_matching_day_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "training.csv"
            write_csv(path)

            result = apply_comment(path, "Day 2, person1-done, person3-blocked")

            self.assertTrue(result.changed)
            with path.open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(rows[1]["Person 1"], "done")
            self.assertEqual(rows[1]["Person 3"], "blocked")
            self.assertEqual(rows[0]["Person 1"], "not-started")

    def test_rejects_unknown_topic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "training.csv"
            write_csv(path)

            with self.assertRaises(CommandError):
                apply_comment(path, "Day 9, person1-done")

    def test_rejects_conflicting_duplicate_updates(self):
        with self.assertRaises(CommandError):
            parse_status_comment(
                "Day 1, person1-done, p1-blocked",
                FIELDNAMES,
            )


if __name__ == "__main__":
    unittest.main()
