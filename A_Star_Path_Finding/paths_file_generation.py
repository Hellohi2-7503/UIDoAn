import os
from A_Star_Path_Finding.a_star_path_finding import A_Star

class Paths_File_Generation(A_Star):
    def __init__(self, grid, starts, goals, directory):
        super().__init__(grid) # Call the parent A_Star's constructor
        self.starts = starts
        self.goals = goals

        # Create a directory if not exist given directory
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.directory = directory

    def is_intersection(self, cell):
        """
        Determines if the current cell is an intersection.
        An intersection occurs if there are at least two open paths excluding the previous cell.
        """
        x, y = cell
        adjacent_paths = 0

        # Possible directions: Up, Down, Left, Right
        directions = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]

        for nx, ny in directions:
            if self.is_walkable((nx, ny)):
                adjacent_paths += 1

        return adjacent_paths >= 3

    def detect_turn(self, prev, current, next):
        """
        Determines the turn direction based on three points (prev -> current -> next).
        """
        # Calculate vectors
        dx1, dy1 = current[0] - prev[0], current[1] - prev[1]
        dx2, dy2 = next[0] - current[0], next[1] - current[1]

        # Cross product
        cross_product = dx1 * dy2 - dy1 * dx2

        if cross_product > 0:
            return "L"  # Left Turn
        elif cross_product < 0:
            return "R"  # Right Turn
        else:
            return "Straight"  # No Turn

    def count_intersections(self, start, goal):
        """
        Counts intersections and their directions ("L" or "R") along the path.
        """
        total_intersections = 0
        directions = {}  # Store intersection index and direction
        path = super().astar_path(start, goal)

        if not path:
            return 0, directions, 0

        for i in range(1, len(path) - 1):
            prev, current, next = path[i - 1], path[i], path[i + 1]

            # Check if the current cell is an intersection
            if self.is_intersection(current):
                total_intersections += 1
                # Determine the turn direction
                turn = self.detect_turn(prev, current, next)
                if turn in ["L", "R"]:
                    directions[total_intersections] = turn

        # Print results
        return total_intersections, directions, len(path) - 1

    def count_intersections_and_check_rev_dir(self, start, goal, prev_point):
        """
        The same as count_intersections(...) but now return checking if the path need turning 180deg (reverse)
        """
        total_intersections = 0
        directions = {}  # Store intersection index and direction
        check_rev = False
        path = super().astar_path(start, goal)

        if not path:
            return total_intersections, directions, check_rev

        if len(path) > 1 and prev_point == path[1]:
            check_rev = True

        for i in range(1, len(path) - 1):
            prev, current, next = path[i - 1], path[i], path[i + 1]

            # Check if the current cell is an intersection
            if self.is_intersection(current):
                total_intersections += 1
                # Determine the turn direction
                turn = self.detect_turn(prev, current, next)
                if turn in ["L", "R"]:
                    directions[total_intersections] = turn

        # Print results
        return total_intersections, directions, check_rev

    def generate_directions(self):
        """
        Use directions and total intersections from count_intersections() to generate multiple files with different start and goal
        """
        # Create the main directory
        # main_directory = "E:\Robot_Map_Directions"
        # if not os.path.exists(main_directory):
        #     os.makedirs(main_directory)

        # Create subdirectories and files inside them
        file_size = len(self.starts) + len(self.goals)
        all_components = self.starts + self.goals
        for i in range(0, file_size):  # Create subdirectories
            subdirectory = os.path.join(self.directory, f"{i}")
            os.makedirs(subdirectory, exist_ok=True)  # Create subdirectory if it doesn't exist
            for j in range(0, file_size):
                if j != i:
                    total_intersections, directions, numb_step = self.count_intersections(all_components[i], all_components[j])
                    if numb_step == 0 and all_components[i] != all_components[j]:
                        raise ValueError(f"No path found between point {i} and point {j}")
                    file_path = os.path.join(subdirectory, f"{i}_{j}.txt")
                    with open(file_path, "w") as file:
                        file.write(f"{total_intersections}\n{directions}\n{numb_step}\n")
