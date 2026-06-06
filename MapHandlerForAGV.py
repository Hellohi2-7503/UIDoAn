import json
import os
import shutil
import tempfile
from datetime import datetime

import numpy as np

from A_Star_Path_Finding.paths_file_generation import Paths_File_Generation


class MapHandler:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.map_dir = os.path.join(self.base_dir, "map_for_robot")
        self.history_dir = os.path.join(self.map_dir, "history")
        self.directions_dir = os.path.join(self.base_dir, "Robot_Map_Directions_2")
        os.makedirs(self.map_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)

        if not os.listdir(self.history_dir):
            current_state = self._read_current_state()
            if current_state:
                self._save_snapshot(current_state, "Initial map")

    def save_map(self, map_matrix_json, starts_json, goals_json):
        state = {
            "matrix": json.loads(map_matrix_json),
            "starts": json.loads(starts_json),
            "goals": json.loads(goals_json),
        }
        self._validate_state(state)
        self._apply_state(state, "Saved map")
        return self.map_dir

    def _validate_state(self, state):
        matrix = state.get("matrix")
        if not isinstance(matrix, list) or not matrix or not isinstance(matrix[0], list):
            raise ValueError("Map matrix must be a non-empty two-dimensional list")

        column_count = len(matrix[0])
        if column_count == 0 or any(not isinstance(row, list) or len(row) != column_count for row in matrix):
            raise ValueError("All map rows must have the same non-zero length")

        if any(cell not in (0, 1, 2, 3) for row in matrix for cell in row):
            raise ValueError("Map cells must use values 0, 1, 2, or 3")

        if not isinstance(state.get("starts"), list) or not isinstance(state.get("goals"), list):
            raise ValueError("Map starts and goals must be lists")

        starts = state["starts"]
        goals = state["goals"]
        if len(starts) != 1:
            raise ValueError("Map must contain exactly one starting point")
        if not goals:
            raise ValueError("Map must contain at least one destination")

        rows = len(matrix)
        columns = len(matrix[0])
        coordinates = []
        for point in starts:
            if not isinstance(point, list) or len(point) < 2:
                raise ValueError("Invalid starting point")
            coordinates.append((point[0], point[1], 3))
        for point in goals:
            if not isinstance(point, list) or len(point) < 3:
                raise ValueError("Invalid destination")
            coordinates.append((point[0], point[1], 2))

        room_labels = [str(point[2]).strip() for point in goals]
        if any(not label for label in room_labels):
            raise ValueError("Every destination must have a room label")
        if len(set(room_labels)) != len(room_labels):
            raise ValueError("Room labels must be unique")

        seen = set()
        for row, column, expected_type in coordinates:
            if not isinstance(row, int) or not isinstance(column, int):
                raise ValueError("Map coordinates must be integers")
            if not (0 <= row < rows and 0 <= column < columns):
                raise ValueError("Map point is outside the matrix")
            if (row, column) in seen:
                raise ValueError("Map points must use unique coordinates")
            if matrix[row][column] != expected_type:
                raise ValueError("Map point type does not match its matrix cell")
            seen.add((row, column))

    def _generate_directions(self, state, output_directory):
        generator = Paths_File_Generation(
            np.asarray(state["matrix"]),
            [tuple(point[:2]) for point in state["starts"]],
            [tuple(point[:2]) for point in state["goals"]],
            output_directory,
        )
        generator.generate_directions()

        point_count = len(state["starts"]) + len(state["goals"])
        expected_file_count = point_count * (point_count - 1)
        generated_file_count = sum(
            1
            for _, _, filenames in os.walk(output_directory)
            for filename in filenames
            if filename.endswith(".txt")
        )
        if generated_file_count != expected_file_count:
            raise ValueError(
                f"Expected {expected_file_count} direction files, generated {generated_file_count}"
            )

    def _apply_state(self, state, history_label):
        previous_state = self._read_current_state()
        temporary_parent = tempfile.mkdtemp(prefix="map_directions_", dir=self.base_dir)
        generated_directory = os.path.join(temporary_parent, "generated")
        backup_directory = os.path.join(temporary_parent, "previous")
        directions_swapped = False

        try:
            self._generate_directions(state, generated_directory)

            if os.path.exists(self.directions_dir):
                os.replace(self.directions_dir, backup_directory)
            os.replace(generated_directory, self.directions_dir)
            directions_swapped = True

            self._write_current_state(state)
            self._save_snapshot(state, history_label)
        except Exception:
            if directions_swapped and os.path.exists(self.directions_dir):
                shutil.rmtree(self.directions_dir)
            if os.path.exists(backup_directory):
                os.replace(backup_directory, self.directions_dir)
            if previous_state:
                self._write_current_state(previous_state)
            raise
        finally:
            shutil.rmtree(temporary_parent, ignore_errors=True)

    def _write_current_state(self, state):
        map_matrix = state["matrix"]
        starts = state["starts"]
        goals = state["goals"]
        map_txt_path = os.path.join(self.map_dir, "map.txt")
        start_txt_path = os.path.join(self.map_dir, "start.txt")
        goal_txt_path = os.path.join(self.map_dir, "goal.txt")
        json_path = os.path.join(self.map_dir, "map_state.json")

        with open(map_txt_path, "w", encoding="utf-8") as f:
            f.write("[\n")
            for row in map_matrix:
                f.write("    " + str(row) + ",\n")
            f.write("]\n")

        with open(start_txt_path, "w", encoding="utf-8") as f:
            f.write("[\n")
            for st in starts:
                f.write(f"    ({st[0]}, {st[1]}),\n")
            f.write("]\n")

        with open(goal_txt_path, "w", encoding="utf-8") as f:
            f.write("[\n")
            for gl in goals:
                f.write(f"    ({gl[0]}, {gl[1]}),\n")
            f.write("]\n")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)

    def _read_current_state(self):
        json_path = os.path.join(self.map_dir, "map_state.json")
        if not os.path.exists(json_path):
            return None

        with open(json_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self._validate_state(state)
        return state

    def _save_snapshot(self, state, label):
        now = datetime.now().astimezone()
        snapshot_id = now.strftime("%Y%m%d_%H%M%S_%f")
        snapshot = {
            "id": snapshot_id,
            "created_at": now.isoformat(timespec="seconds"),
            "label": label,
            "matrix": state["matrix"],
            "starts": state["starts"],
            "goals": state["goals"],
        }
        snapshot_path = os.path.join(self.history_dir, f"{snapshot_id}.json")
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False)
        return snapshot_id

    def _snapshot_path(self, snapshot_id):
        if not snapshot_id or snapshot_id != os.path.basename(snapshot_id):
            raise ValueError("Invalid map history identifier")

        snapshot_path = os.path.abspath(os.path.join(self.history_dir, f"{snapshot_id}.json"))
        if os.path.dirname(snapshot_path) != os.path.abspath(self.history_dir):
            raise ValueError("Invalid map history path")
        return snapshot_path

    def load_map(self):
        state = self._read_current_state()
        return json.dumps(state, ensure_ascii=False) if state else ""

    def list_history(self):
        history = []
        for filename in os.listdir(self.history_dir):
            if not filename.endswith(".json"):
                continue

            snapshot_path = os.path.join(self.history_dir, filename)
            try:
                with open(snapshot_path, "r", encoding="utf-8") as f:
                    snapshot = json.load(f)
                matrix = snapshot["matrix"]
                history.append(
                    {
                        "id": snapshot["id"],
                        "created_at": snapshot["created_at"],
                        "label": snapshot.get("label", "Saved map"),
                        "rows": len(matrix),
                        "columns": len(matrix[0]) if matrix else 0,
                        "start_count": len(snapshot.get("starts", [])),
                        "goal_count": len(snapshot.get("goals", [])),
                    }
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue

        history.sort(key=lambda item: item["id"], reverse=True)
        return json.dumps(history, ensure_ascii=False)

    def restore_history(self, snapshot_id):
        snapshot_path = self._snapshot_path(snapshot_id)
        if not os.path.exists(snapshot_path):
            return ""

        with open(snapshot_path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

        restored_state = {
            "matrix": snapshot["matrix"],
            "starts": snapshot.get("starts", []),
            "goals": snapshot.get("goals", []),
        }
        self._validate_state(restored_state)

        current_state = self._read_current_state()
        if current_state:
            self._save_snapshot(current_state, "Before restore")

        self._apply_state(restored_state, "Restored map")
        return json.dumps(restored_state, ensure_ascii=False)
