import json
import os
import sys
from itertools import permutations
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

SIMULATION_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SIMULATION_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from A_Star_Path_Finding.a_star_path_finding import A_Star


MAP_STATE_PATH = PROJECT_DIR / "map_for_robot" / "map_state.json"


class SimulationController(QObject):
    mapChanged = Signal()

    def __init__(self):
        super().__init__()
        self._state = {}
        self._grid = np.empty((0, 0), dtype=int)
        self._start = None
        self._goals = []
        self._labels = []
        self.reload_map()

    def _load_state(self):
        with MAP_STATE_PATH.open("r", encoding="utf-8") as file:
            state = json.load(file)

        matrix = state.get("matrix")
        starts = state.get("starts", [])
        goals = state.get("goals", [])
        if not matrix or len(starts) != 1 or not goals:
            raise ValueError("Map must contain a matrix, one kitchen, and at least one room")

        self._state = state
        self._grid = np.asarray(matrix)
        self._start = tuple(starts[0][:2])
        self._goals = [tuple(goal[:2]) for goal in goals]
        self._labels = [str(goal[2]) for goal in goals]

    @Property(str, notify=mapChanged)
    def mapData(self):
        return json.dumps(self._state, ensure_ascii=False)

    @Slot()
    def reload_map(self):
        self._load_state()
        self.mapChanged.emit()

    @Slot("QVariantList", result=str)
    def calculate_route(self, selected_nodes):
        try:
            selected = [int(node) for node in selected_nodes]
        except (TypeError, ValueError):
            return self._error("Invalid room selection")

        valid_nodes = set(range(1, len(self._goals) + 1))
        if (
            not selected
            or len(selected) != len(set(selected))
            or any(node not in valid_nodes for node in selected)
        ):
            return self._error("Select at least one valid room")

        all_points = [self._start] + self._goals
        finder = A_Star(self._grid)
        path_cache = {}

        def path_between(source, target):
            key = (source, target)
            if key not in path_cache:
                path_cache[key] = finder.astar_path(
                    all_points[source],
                    all_points[target],
                )
            return path_cache[key]

        best_route = None
        best_cost = float("inf")
        for order in permutations(selected):
            candidate = [0, *order, 0]
            cost = 0
            valid = True
            for source, target in zip(candidate, candidate[1:]):
                path = path_between(source, target)
                if not path:
                    valid = False
                    break
                cost += len(path) - 1

            if valid and cost < best_cost:
                best_route = candidate
                best_cost = cost

        if best_route is None:
            return self._error("No route connects all selected rooms")

        segments = []
        combined_path = []
        for source, target in zip(best_route, best_route[1:]):
            path = path_between(source, target)
            intersections, turns = self._route_directions(path)
            if combined_path:
                combined_path.extend(path[1:])
            else:
                combined_path.extend(path)

            segments.append(
                {
                    "from": self._node_label(source),
                    "to": self._node_label(target),
                    "steps": len(path) - 1,
                    "intersections": intersections,
                    "turns": [
                        {
                            "intersection": index,
                            "direction": direction,
                            "label": self._turn_label(direction),
                        }
                        for index, direction in sorted(turns.items())
                    ],
                    "path": [list(cell) for cell in path],
                }
            )

        return json.dumps(
            {
                "ok": True,
                "routeNodes": best_route,
                "routeLabels": [self._node_label(node) for node in best_route],
                "totalSteps": int(best_cost),
                "segments": segments,
                "path": [list(cell) for cell in combined_path],
            },
            ensure_ascii=False,
        )

    def _node_label(self, node):
        return "Kitchen" if node == 0 else f"Room {self._labels[node - 1]}"

    def _route_directions(self, path):
        intersection_count = 0
        turns = {}

        for index in range(1, len(path) - 1):
            previous = path[index - 1]
            current = path[index]
            next_position = path[index + 1]
            if not self._is_intersection(current):
                continue

            intersection_count += 1
            direction = self._detect_turn(previous, current, next_position)
            if direction in ("L", "R"):
                turns[intersection_count] = direction

        return intersection_count, turns

    def _is_intersection(self, cell):
        row, column = cell
        neighbors = (
            (row - 1, column),
            (row + 1, column),
            (row, column - 1),
            (row, column + 1),
        )
        finder = A_Star(self._grid)
        return sum(finder.is_walkable(neighbor) for neighbor in neighbors) >= 3

    @staticmethod
    def _detect_turn(previous, current, next_position):
        incoming_row = current[0] - previous[0]
        incoming_column = current[1] - previous[1]
        outgoing_row = next_position[0] - current[0]
        outgoing_column = next_position[1] - current[1]
        cross = (
            incoming_row * outgoing_column
            - incoming_column * outgoing_row
        )
        if cross > 0:
            return "L"
        if cross < 0:
            return "R"
        return "Straight"

    @staticmethod
    def _turn_label(direction):
        return {"L": "Turn left", "R": "Turn right"}.get(
            direction,
            "Go straight",
        )

    @staticmethod
    def _error(message):
        return json.dumps({"ok": False, "error": message})


def main():
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    controller = SimulationController()
    engine.rootContext().setContextProperty("simulationController", controller)
    engine.load(SIMULATION_DIR / "simulation.qml")

    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
