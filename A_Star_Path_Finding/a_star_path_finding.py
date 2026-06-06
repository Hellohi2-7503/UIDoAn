import numpy as np
import heapq

class A_Star:
    def __init__(self, grid):
        self.grid = np.asarray(grid)
        if self.grid.ndim != 2:
            raise ValueError("grid must be a two-dimensional matrix")

    def heuristic(self, a, b):
        return abs(b[0] - a[0]) + abs(b[1] - a[1])

    def is_within_bounds(self, cell):
        row, col = cell
        return 0 <= row < self.grid.shape[0] and 0 <= col < self.grid.shape[1]

    def is_walkable(self, cell):
        return self.is_within_bounds(cell) and self.grid[cell] != 1

    def astar_path(self, start, goal):
        start = tuple(start)
        goal = tuple(goal)

        if not self.is_walkable(start) or not self.is_walkable(goal):
            return []
        if start == goal:
            return [start]

        neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        came_from = {}
        gscore = {start: 0}
        open_heap = [(self.heuristic(start, goal), 0, start)]
        closed_set = set()

        while open_heap:
            _, current_gscore, current = heapq.heappop(open_heap)
            if current in closed_set or current_gscore != gscore.get(current):
                continue

            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                return path[::-1]

            closed_set.add(current)

            for dx, dy in neighbors:
                neighbor = (current[0] + dx, current[1] + dy)
                if not self.is_walkable(neighbor):
                    continue

                tentative_g_score = current_gscore + 1
                if tentative_g_score >= gscore.get(neighbor, float("inf")):
                    continue

                came_from[neighbor] = current
                gscore[neighbor] = tentative_g_score
                estimated_total = tentative_g_score + self.heuristic(neighbor, goal)
                heapq.heappush(open_heap, (estimated_total, tentative_g_score, neighbor))

        return []
