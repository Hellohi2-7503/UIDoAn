import json
import sys
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from simulation.simulation_main import SimulationController


class SimulationControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controller = SimulationController()

    def test_single_room_route_returns_to_kitchen(self):
        result = json.loads(self.controller.calculate_route([1]))

        self.assertTrue(result["ok"])
        self.assertEqual([0, 1, 0], result["routeNodes"])
        self.assertGreater(result["totalSteps"], 0)
        self.assertEqual(2, len(result["segments"]))

    def test_multiple_rooms_are_all_in_optimal_route(self):
        result = json.loads(self.controller.calculate_route([1, 2, 3]))

        self.assertTrue(result["ok"])
        self.assertEqual(0, result["routeNodes"][0])
        self.assertEqual(0, result["routeNodes"][-1])
        self.assertEqual({1, 2, 3}, set(result["routeNodes"][1:-1]))

    def test_invalid_selection_is_rejected(self):
        result = json.loads(self.controller.calculate_route([999]))

        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
