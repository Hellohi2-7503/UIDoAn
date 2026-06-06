import tempfile
import unittest

import numpy as np

from A_Star_Path_Finding.a_star_path_finding import A_Star
from A_Star_Path_Finding.paths_file_generation import Paths_File_Generation


class AStarTests(unittest.TestCase):
    def test_finds_shortest_four_direction_path(self):
        grid = np.array(
            [
                [0, 0, 0, 0],
                [1, 1, 0, 1],
                [0, 0, 0, 0],
            ]
        )

        path = A_Star(grid).astar_path((0, 0), (2, 3))

        self.assertEqual(5, len(path) - 1)
        self.assertEqual((0, 0), path[0])
        self.assertEqual((2, 3), path[-1])

    def test_returns_empty_path_for_invalid_or_blocked_points(self):
        grid = np.array([[0, 1], [0, 0]])
        finder = A_Star(grid)

        self.assertEqual([], finder.astar_path((-1, 0), (1, 1)))
        self.assertEqual([], finder.astar_path((0, 0), (0, 1)))

    def test_start_equal_goal_returns_single_cell(self):
        grid = np.zeros((2, 2), dtype=int)

        self.assertEqual([(1, 1)], A_Star(grid).astar_path((1, 1), (1, 1)))

    def test_unreachable_goal_returns_empty_path(self):
        grid = np.array([[0, 1, 0], [0, 1, 0], [0, 1, 0]])

        self.assertEqual([], A_Star(grid).astar_path((0, 0), (0, 2)))


class DirectionGenerationTests(unittest.TestCase):
    def make_generator(self, grid):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return Paths_File_Generation(np.array(grid), [], [], directory.name)

    def test_intersection_check_is_safe_on_grid_edges(self):
        generator = self.make_generator([[0, 0], [0, 0]])

        for cell in [(0, 0), (0, 1), (1, 0), (1, 1)]:
            self.assertFalse(generator.is_intersection(cell))

    def test_start_and_goal_cells_are_walkable_at_intersections(self):
        generator = self.make_generator([[1, 2, 1], [0, 0, 3], [1, 0, 1]])

        self.assertTrue(generator.is_intersection((1, 1)))

    def test_reverse_check_handles_start_equal_goal_and_no_path(self):
        generator = self.make_generator([[0, 1], [1, 0]])

        self.assertEqual(
            (0, {}, False),
            generator.count_intersections_and_check_rev_dir((0, 0), (0, 0), (0, 1)),
        )
        self.assertEqual(
            (0, {}, False),
            generator.count_intersections_and_check_rev_dir((0, 0), (1, 1), (0, 1)),
        )

    def test_path_cost_is_number_of_edges(self):
        generator = self.make_generator([[0, 0, 0]])

        intersections, directions, cost = generator.count_intersections((0, 0), (0, 2))

        self.assertEqual(0, intersections)
        self.assertEqual({}, directions)
        self.assertEqual(2, cost)

    def test_generation_rejects_disconnected_points(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        generator = Paths_File_Generation(
            np.array([[0, 1, 0]]),
            [(0, 0)],
            [(0, 2)],
            directory.name,
        )

        with self.assertRaisesRegex(ValueError, "No path found"):
            generator.generate_directions()


if __name__ == "__main__":
    unittest.main()
