import json
import os
import tempfile
import unittest

from MapHandlerForAGV import MapHandler


class MapHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.handler = MapHandler(self.temp_dir.name)

    def save_state(self, matrix, starts, goals):
        self.handler.save_map(
            json.dumps(matrix),
            json.dumps(starts),
            json.dumps(goals),
        )

    def test_save_creates_history_and_restore_recovers_old_map(self):
        first_matrix = [[3, 0, 2]]
        second_matrix = [[3, 0, 0, 2]]

        self.save_state(first_matrix, [[0, 0]], [[0, 2, "301"]])
        self.save_state(second_matrix, [[0, 0]], [[0, 3, "302"]])

        history = json.loads(self.handler.list_history())
        self.assertEqual(2, len(history))
        self.assertEqual(4, history[0]["columns"])
        self.assertEqual(3, history[1]["columns"])

        restored = json.loads(self.handler.restore_history(history[1]["id"]))
        self.assertEqual(first_matrix, restored["matrix"])
        self.assertEqual(first_matrix, json.loads(self.handler.load_map())["matrix"])

        history_after_restore = json.loads(self.handler.list_history())
        self.assertEqual(4, len(history_after_restore))
        self.assertEqual("Restored map", history_after_restore[0]["label"])
        self.assertEqual("Before restore", history_after_restore[1]["label"])

    def test_invalid_history_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            self.handler.restore_history("../map_state")

    def test_save_replaces_all_old_direction_files(self):
        self.save_state([[3, 0, 2]], [[0, 0]], [[0, 2, "301"]])
        stale_file = os.path.join(self.handler.directions_dir, "stale.txt")
        with open(stale_file, "w", encoding="utf-8") as f:
            f.write("old")

        self.save_state(
            [[3, 0, 2, 0, 2]],
            [[0, 0]],
            [[0, 2, "301"], [0, 4, "302"]],
        )

        self.assertFalse(os.path.exists(stale_file))
        direction_files = [
            filename
            for _, _, filenames in os.walk(self.handler.directions_dir)
            for filename in filenames
            if filename.endswith(".txt")
        ]
        self.assertEqual(6, len(direction_files))

    def test_failed_generation_preserves_current_map_and_directions(self):
        current_matrix = [[3, 0, 2]]
        self.save_state(current_matrix, [[0, 0]], [[0, 2, "301"]])
        current_direction = os.path.join(self.handler.directions_dir, "0", "0_1.txt")
        with open(current_direction, "r", encoding="utf-8") as f:
            direction_before = f.read()

        with self.assertRaisesRegex(ValueError, "No path found"):
            self.save_state(
                [[3, 1, 2]],
                [[0, 0]],
                [[0, 2, "301"]],
            )

        self.assertEqual(current_matrix, json.loads(self.handler.load_map())["matrix"])
        with open(current_direction, "r", encoding="utf-8") as f:
            self.assertEqual(direction_before, f.read())

    def test_room_labels_must_be_present_and_unique(self):
        with self.assertRaisesRegex(ValueError, "room label"):
            self.save_state([[3, 0, 2]], [[0, 0]], [[0, 2, ""]])

        with self.assertRaisesRegex(ValueError, "unique"):
            self.save_state(
                [[3, 0, 2, 0, 2]],
                [[0, 0]],
                [[0, 2, "301"], [0, 4, "301"]],
            )


if __name__ == "__main__":
    unittest.main()
