import unittest

import numpy as np

from track_position_map_offical import (
    available_paths,
    track_path_to_intersection,
)


class TrackPositionTests(unittest.TestCase):
    def test_uses_the_runtime_grid_and_treats_start_goal_as_walkable(self):
        grid = np.ones((12, 4), dtype=int)
        grid[8, 1] = 3
        grid[9, 1] = 0
        grid[10, 1] = 2

        self.assertEqual([(9, 1)], available_paths(grid, (8, 1)))
        self.assertEqual(
            ((9, 1), (8, 1)),
            track_path_to_intersection(grid, (8, 1), {}, 0, (10, 1)),
        )

    def test_planned_route_handles_a_start_located_on_an_intersection(self):
        grid = np.array(
            [
                [1, 0, 1],
                [0, 3, 2],
                [1, 0, 1],
            ]
        )

        self.assertEqual(
            ((1, 2), (1, 1)),
            track_path_to_intersection(grid, (1, 1), {}, 0, (1, 2)),
        )

    def test_returns_cell_after_requested_intersection(self):
        grid = np.array(
            [
                [1, 1, 0, 1, 1],
                [3, 0, 0, 0, 2],
                [1, 1, 0, 1, 1],
            ]
        )

        self.assertEqual(
            ((1, 3), (1, 2)),
            track_path_to_intersection(grid, (1, 0), {}, 1, (1, 4)),
        )

    def test_rejects_more_intersections_than_the_route_contains(self):
        grid = np.array([[3, 0, 2]])

        self.assertEqual(
            (None, None),
            track_path_to_intersection(grid, (0, 0), {}, 1, (0, 2)),
        )

    def test_direction_fallback_fails_cleanly_when_turn_is_impossible(self):
        grid = np.array(
            [
                [1, 0, 1],
                [3, 0, 2],
                [1, 0, 1],
            ]
        )

        self.assertEqual(
            (None, None),
            track_path_to_intersection(grid, (1, 0), {1: "U"}, 1),
        )


if __name__ == "__main__":
    unittest.main()
