import time

import numpy as np

from A_Star_Path_Finding.a_star_path_finding import A_Star
from A_Star_Path_Finding.paths_file_generation import Paths_File_Generation


def detect_turn(previous, current, next_position):
    """Return L, R, or Straight for three consecutive cells."""
    dx1 = current[0] - previous[0]
    dy1 = current[1] - previous[1]
    dx2 = next_position[0] - current[0]
    dy2 = next_position[1] - current[1]
    cross = dx1 * dy2 - dy1 * dx2

    if cross > 0:
        return "L"
    if cross < 0:
        return "R"
    return "Straight"


def available_paths(grid, position):
    """Return every walkable neighbor of position."""
    grid = np.asarray(grid)
    row, col = position
    neighbors = []

    for row_offset, col_offset in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        next_row = row + row_offset
        next_col = col + col_offset
        if (
            0 <= next_row < grid.shape[0]
            and 0 <= next_col < grid.shape[1]
            and grid[next_row, next_col] != 1
        ):
            neighbors.append((next_row, next_col))

    return neighbors


def _position_on_planned_path(grid, start_pos, goal_pos, total_intersections):
    """Locate the robot on the same A* path used to generate its directions."""
    path = A_Star(grid).astar_path(start_pos, goal_pos)
    if len(path) < 2:
        return (start_pos, None) if path else (None, None)

    # Before the first intersection, the old implementation represented the
    # robot by the first cell after its route origin.
    if total_intersections == 0:
        return path[1], path[0]

    intersection_count = 0
    for index in range(1, len(path) - 1):
        if len(available_paths(grid, path[index])) < 3:
            continue

        intersection_count += 1
        if intersection_count == total_intersections:
            return path[index + 1], path[index]

    return None, None


def _position_from_directions(grid, start_pos, directions, total_intersections):
    """Fallback tracker for callers that do not know the planned destination."""
    current = start_pos
    previous = None
    intersection_count = 0
    visited_states = set()
    max_steps = max(np.asarray(grid).size * 4, 1)

    for _ in range(max_steps):
        state = (previous, current, intersection_count)
        if state in visited_states:
            return None, None
        visited_states.add(state)

        paths = available_paths(grid, current)
        forward_paths = [position for position in paths if position != previous]
        if not forward_paths:
            return None, None

        if len(paths) >= 3:
            # A direction alone cannot establish orientation when the route
            # starts directly on an intersection.
            if previous is None:
                return None, None

            intersection_count += 1
            expected_turn = directions.get(intersection_count, "Straight")
            matching_paths = [
                position
                for position in forward_paths
                if detect_turn(previous, current, position) == expected_turn
            ]
            if len(matching_paths) != 1:
                return None, None
            next_position = matching_paths[0]
        else:
            if len(forward_paths) != 1:
                return None, None
            next_position = forward_paths[0]

        previous, current = current, next_position
        if intersection_count == total_intersections:
            return current, previous

    return None, None


def track_path_to_intersection(
    grid,
    start_pos,
    directions,
    total_intersections,
    goal_pos=None,
):
    """Estimate the current route cell after passing N intersections."""
    grid = np.asarray(grid)
    start_pos = tuple(start_pos) if start_pos is not None else None
    goal_pos = tuple(goal_pos) if goal_pos is not None else None

    if (
        grid.ndim != 2
        or start_pos is None
        or not isinstance(total_intersections, int)
        or total_intersections < 0
        or not A_Star(grid).is_walkable(start_pos)
    ):
        return None, None

    if goal_pos is not None:
        return _position_on_planned_path(
            grid,
            start_pos,
            goal_pos,
            total_intersections,
        )

    return _position_from_directions(
        grid,
        start_pos,
        directions,
        total_intersections,
    )


def main():
    start_time = time.perf_counter()
    grid_map = np.array(
        [
            [1, 1, 1, 1, 1, 1, 1],
            [1, 2, 1, 0, 1, 2, 1],
            [1, 0, 1, 0, 1, 0, 1],
            [1, 0, 0, 0, 0, 0, 1],
            [1, 1, 1, 3, 1, 1, 1],
        ]
    )
    starts = [(4, 3)]
    goals = [(1, 1), (1, 5)]
    start_point = starts[0]
    goal = goals[1]

    final_pos, previous_pos = track_path_to_intersection(
        grid_map,
        start_point,
        {},
        1,
        goal,
    )
    if final_pos is None:
        print("Unable to determine the current route position.")
        return

    files = Paths_File_Generation(grid_map, starts, goals, "Robot_Map_Directions_2")
    result = files.count_intersections_and_check_rev_dir(
        final_pos,
        starts[0],
        previous_pos,
    )
    print(f"Execution time: {time.perf_counter() - start_time:.4f} seconds")
    print(f"Current position: {final_pos}")
    print(f"Return directions: {result}")


# if __name__ == "__main__":
#     main()
