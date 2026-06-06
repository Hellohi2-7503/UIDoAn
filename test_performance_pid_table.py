from PySide6.QtCore import QObject, Slot, Signal, QThread

import math
from collections import deque
import os
from itertools import permutations
import threading
import time
import numpy as np
import pyttsx3
import ast
import json
import CCF_LAS5
import ZLAC8015D
import D_MNSV7_X16
from MapHandlerForAGV import MapHandler
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from A_Star_Path_Finding.paths_file_generation import Paths_File_Generation
from track_position_map_offical import track_path_to_intersection


# Keep the UI usable without opening serial ports.
HARDWARE_ENABLED = False


# Trạng thái nút bấm dành cho giao diện
stop_button_pressed = False # Nút dừng
return_kitchen_button_pressed = False # Nút quay lại bếp
disable_test_run_button = False # Nút tắt chương trình chạy thử nghiệm

# Khởi động engine cho thông báo giọng nói
engine = pyttsx3.init()

# Điều chỉnh tốc độ (rate) và âm lượng (volume)
engine.setProperty('rate', 150)     # Slower than default: 200 wpm
engine.setProperty('volume', 0.9)   # 80% volume

# # Khai báo map (0 = đường đi, 1 = tường/vật cản, 2 = các điểm đến, 3 = điểm bắt đầu)
# grid_map = np.array([
#   [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
#   [1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
#   [1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
#   [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1],
#   [1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],
#   [1, 2, 1, 2, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],
#   [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 2, 1, 1],
#   [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
# ])

# # Các điểm bắt đầu và điểm đến trên bản đồ chỉ định
# starts = [
#     (5, 7),  # Point 0 (304)
# ]
# goals = [
#     (1, 7),  # Point 1 (303)
#     (5, 1),  # Point 2 (308)
#     (5, 3),  # Point 3 (306)
#     (6, 17)  # Point 4 (301)
# ]
# ==============================================================================
# 1. ĐỌC MA TRẬN BẢN ĐỒ VÀ TOẠ ĐỘ THÔ (Từ thư mục map_for_robot)
# ==============================================================================

# ==============================================================================
# ĐỌC MAP, START, GOAL TỪ THƯ MỤC map_for_robot
# ==============================================================================

base_dir = os.path.dirname(os.path.abspath(__file__))
map_dir = os.path.join(base_dir, "map_for_robot")


def read_clean_map_file(filename):
    filepath = os.path.join(map_dir, filename)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"no {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            raise ValueError(f"no: {filepath}")

        return ast.literal_eval(content)

    except Exception as e:
        raise ValueError(f"no{filename}: {e}")


# Đọc dữ liệu từ 3 file txt
grid_map = np.array(read_clean_map_file("map.txt"))
starts = read_clean_map_file("start.txt")
goals = read_clean_map_file("goal.txt")


# Kiểm tra dữ liệu sau khi đọc
print(f"grid_map: {type(grid_map)} | shape = {grid_map.shape}")
print(f"starts: {starts}")
print(f"goals: {goals}")


all_points = starts + goals # Dùng để gán điểm và tìm kiếm

# Biến lưu điểm bắt đầu và điểm đến hiện tại
start_point = None
end_point = None

# Lấy thư mục chứa file main.py
base_dir = os.path.dirname(os.path.abspath(__file__))

# Thư mục file dẫn đường nằm trong thư mục main.py
directory = os.path.join(base_dir, "Robot_Map_Directions_2")

# ==================== THÊM ĐOẠN NÀY VÀO ĐÂY ====================
# Kiểm tra nếu thư mục chưa tồn tại hoặc bên trong trống không
if not os.path.exists(directory) or not os.listdir(directory):
    print("Hello")
    # Gọi class và truyền cái grid_map ở trên vào để nó tính toán
    generator = Paths_File_Generation(grid_map, starts, goals, directory)
    # Bóp cò để đẻ ra các file .txt
    generator.generate_directions()
    print("Holle")
# ===============================================================

def load_direction_graph(base_path):
    loaded_graph = {}
    folders = sorted(
        [
            folder
            for folder in os.listdir(base_path)
            if os.path.isdir(os.path.join(base_path, folder)) and folder.isdigit()
        ],
        key=int,
    )

    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        loaded_graph[int(folder)] = {}

        for file_name in os.listdir(folder_path):
            if not file_name.endswith(".txt"):
                continue

            file_parts = file_name.replace(".txt", "").split("_", 1)
            if len(file_parts) != 2:
                continue

            source, target_node = map(int, file_parts)
            if source == target_node:
                continue

            file_path = os.path.join(folder_path, file_name)
            with open(file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
            if len(lines) >= 3:
                loaded_graph[source][target_node] = int(lines[2].strip())

    return loaded_graph


graph = load_direction_graph(directory)


def reload_navigation_data():
    global grid_map, starts, goals, all_points, graph

    grid_map = np.array(read_clean_map_file("map.txt"))
    starts = read_clean_map_file("start.txt")
    goals = read_clean_map_file("goal.txt")
    all_points = starts + goals
    graph = load_direction_graph(directory)

# Các biến xử lý quãng đường đi (centimeter)
shortest_route = []         # Mảng lưu các điểm đến theo thứ tự (tuyến đường ngắn nhất)
stop_turn_distance = 37     # Quãng đường cần dừng để xoay bánh 'L'/'R'
resume_marker_distance = 70 # Quãng đường tổng thể cần đi để tiếp tục chương trình marker_check()

# ===== Thông số xe =====
wheelbase = 25.5  # cm, Khoảng cách 2 bánh xe
Rw = 6.5  # cm, Bán kính bánh xe
t1 = 0.8  # Thời gian tăng tốc để quay góc (s)
t2 = 0.8  # Thời gian giảm tốc để quay góc (s)

# ===== Cấu hình PID =====
pid_table = {   # Thông số PID chính dùng cho tín hiệu analog (rpm: (Kp, Ki, Kd))
 0: (1.082, 0, 13.3571),
 5: (1.0406, 0, 12.7857),
 10: (0.9992, 0, 12.2143),
 15: (0.9578, 0, 11.6429),
 20: (0.9164, 0, 11.0714),
 25: (0.875, 0.0066, 10.5), # Không biết có nên cho Ki = 0 ko?
 30: (0.8336, 0.0095, 9.9286),
 35: (0.7922, 0.0129, 9.3571),
 40: (0.7508, 0.0169, 8.7857),
 45: (0.7094, 0.0214, 8.2143),
 50: (0.668, 0.0264, 7.6429),
 55: (0.6266, 0.0319, 7.0714),
 60: (0.5852, 0.038, 6.5)
}
Kp, Ki, Kd = pid_table.get(0)   # Lấy trước PID từ 0 rpm
Kp_d, Kd_d = 0.2926, 7.5   # Thông số PD riêng dùng cho tín hiệu digital, ko cần I do tín hiệu ít khi có steady-state error
target = 7.5  # Vị trí trung tâm cảm biến cho tín hiệu analog
position_analog = 0  # Giá trị vị trí cho tính toán PID analog
position_digital = 0 # Giá trị vị trí cho tính toán PID digital
error, prevError = 0.0, 0.0
d_value, i_value = 0.0, 0.0 # Giá trị đạo hàm (* Kd) và giá trị tích phân (* Ki)
correction = 0.0 # Điều chỉnh PID

# ===== Biến xử lý cho PID controller =====
cmds = [0, 0]  # Tốc độ điều khiển: Right rpm = cmds[0] (+), Left rpm = cmds[1] (-)
robot_running_analog = True  # Điều khiển trạng thái robot tín hiệu analog
robot_running_digital = False # Điều khiển trạng thái robot tín hiệu digital
pid_interval = 0.09  # Thời gian delay điều khiển PID (0.1 -> 0.09s, do trễ từ giao diện => giảm thời gian thi hành)
lost_line_timer = None # Biến lưu timer xử lý khi xe đi khỏi line
timeout_duration = 0.5  # Thời gian chờ để dừng xe khi trật khỏi line
current_speed_zone = 60 # Biến lưu vùng tốc độ cần đạt ( 60 or 25 rpm )
target_speed = current_speed_zone # Biến lưu tốc độ xe cần đạt ( điều khiển tăng tốc / giảm tốc)
sensor_positions = [-7.5, -6.5, -5.5, -4.5, -3.5, -2.5, -1.5, -0.5,
                     0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]  # Dùng cho điều khiển PID bằng tín hiệu digital

# ===== Biến xử lý cho nhận diện marker =====
line_pin_count = 0 # Dùng cho nhận biết ngã rẽ
digital_value = 0 # Dùng cho nhận biết ngã rẽ
marker_in_zone = False # Khi PID đo được sẽ ko tính toán sai số, cần cập nhật lại prevError giúp tránh giật
marker_check_count = 0 # marker "R" ( > 3 ) ,marker "L" ( < -13 ), tăng độ chính xác cho việc đọc marker bằng cách thêm giới hạn
intersection_marker_check_count = 0 # Tương tự marker_check_count nhưng dùng cho intersection ( > 2 )
intersection_marker_count_met = 0   # Đếm số lần đọc được marker ngã rẽ, max: 2 ( 1-in, 2-out )
start_passed, destination_reached = False, False # Tại điểm bắt đầu và kết thúc sẽ có intersection marker
total_intersection_passed = 0   # Đếm tổng số ngã rẽ đi qua, dùng để xử lý định hướng
travelled_directions = {}   # Lưu các chỉ dẫn đã thực hiện
total_intersection_required, directions = 0, {} # Thành phần định hướng chính
current_analog_array, previous_analog_array = [], []
current_digital_value, prev_digital_value = 0b0, 0b0

# ===== Biến xử lý cho phát hiện vật cản =====
motor_stopped = False # Trạng thái xe dừng, tránh điều khiển PID
slowdown_triggered = False
stop_triggered = False
# === Cấu hình chia vùng phát hiện ===
# SLOW_DOWN_DISTANCE = 50   # cm
# STOP_DISTANCE = 20        # cm
DECREASE_THRESHOLD = 1.0  # cm
# ===== Cấu hình khoảng cách giảm tốc/dừng theo tốc độ =====
brake_distance_table = {
    0:  (15, 10),    # (slowdown_distance, stop_distance)
    5:  (15, 10),
    10: (15, 10),
    15: (30, 15),
    20: (45, 20),
    25: (45, 20),
    30: (45, 20),
    35: (55, 25),
    40: (60, 30),
    45: (70, 35),
    50: (75, 40),
    55: (80, 45),
    60: (90, 50)
}
def interpolate_brake_distance(current_rpm, brake_table):
    keys = sorted(brake_table.keys())

    if current_rpm <= keys[0]:
        return brake_table[keys[0]]
    if current_rpm >= keys[-1]:
        return brake_table[keys[-1]]

    for i in range(len(keys) - 1):
        low, high = keys[i], keys[i+1]
        if low <= current_rpm <= high:
            ratio = (current_rpm - low) / (high - low)
            sd1, stop1 = brake_table[low]
            sd2, stop2 = brake_table[high]
            slowdown_distance = sd1 + ratio * (sd2 - sd1)
            stop_distance = stop1 + ratio * (stop2 - stop1)
            return slowdown_distance, stop_distance

# ===== Khóa đa luồng =====
lock_sensor = threading.Lock()  # Để tránh xung đột giữa các thread lấy dữ liệu cảm biến
lock_motors = threading.Lock()  # Để tránh xung đột giữa các thread lấy dữ liệu từ motor

# ===== Khởi tạo các luồng toàn cục =====
pid_thread = None
marker_thread = None
obstacle_thread = None

# ===== Cấu hình giao tiếp Modbus =====
client1 = None
client2 = None
client3 = None
motors = None
sensor = None
obstacle_sensor = None

if HARDWARE_ENABLED:
    client1 = ModbusClient(method='rtu', port="COM1", baudrate=115200, timeout=1)
    client2 = ModbusClient(method='rtu', port="COM2", baudrate=115200, timeout=1)
    client3 = ModbusClient(method='rtu', port="COM11", baudrate=115200, timeout=1)

    motors = ZLAC8015D.Controller(client1)
    sensor = D_MNSV7_X16.Magnetic_Line_Sensor(client2)
    obstacle_sensor = CCF_LAS5.Laser_Obstacle_Sensor(client3)


# # ===== Kích hoạt động cơ =====
# motors.disable_motor()
# motors.set_mode(3)

# motors.enable_motor()
# motors.set_accel_time(50, 50)
# motors.set_decel_time(50, 50)

## ================ CHƯƠNG TRÌNH XỬ LÝ PHÁT HIỆN VẬT CẢN ================
def check_obstacle():
    global robot_running_analog, robot_running_digital
    global target_speed, current_speed_zone
    global pid_thread, i_value, prevError
    global motor_stopped, slowdown_triggered, stop_triggered

    print("######## Bắt đầu đo vật cản ########")

    error_count = 0
    distance_window = deque(maxlen=5)
    previous_avg_distance = None
    decreasing_count = 0

    while (robot_running_analog or robot_running_digital) and not destination_reached:
        distances = obstacle_sensor.get_pins_distance()

        if not distances:
            error_count += 1
            if error_count > 5:
                print("Lỗi cảm biến vật cản!")
                time.sleep(1)
            continue
        else:
            error_count = 0

        SLOW_DOWN_DISTANCE, STOP_DISTANCE = interpolate_brake_distance(cmds[0], brake_distance_table)
        # min_distance = min(distances[2:4])
        min_distance = distances[3]
        distance_window.append(min_distance)

        if len(distance_window) == distance_window.maxlen:
            avg_distance = sum(distance_window) / len(distance_window)

            if previous_avg_distance is not None:
                if (previous_avg_distance - avg_distance) >= DECREASE_THRESHOLD:
                    decreasing_count += 1
                else:
                    decreasing_count = 0

            previous_avg_distance = avg_distance

            # === Xử lý logic phân vùng ===
            if decreasing_count >= 3:
                if avg_distance <= STOP_DISTANCE and not stop_triggered:
                    print("[!] Vật cản gần, DỪNG robot!")
                    target_speed = 0
                    motor_stopped = False
                    stop_triggered = True

                elif avg_distance <= SLOW_DOWN_DISTANCE and not slowdown_triggered and not stop_triggered:
                    print("[~] Vật cản trung bình, giảm tốc độ về 20 rpm")
                    target_speed = 20
                    motor_stopped = False
                    slowdown_triggered = True

        # === Khi vật cản biến mất ===
        if slowdown_triggered or stop_triggered:
            print(">> Đang ở vùng vật cản")
            while True:
                time.sleep(0.1)
                distances = obstacle_sensor.get_pins_distance()
                # min_distance = min(distances[2:4]) if distances else 999
                min_distance = distances[3]
                distance_window.append(min_distance)

                if len(distance_window) == distance_window.maxlen:
                    avg_distance = sum(distance_window) / len(distance_window)
                    print(f"Khoảng cách trung bình: {avg_distance:.2f} cm")

                    if stop_triggered and avg_distance > STOP_DISTANCE:
                        print("[~] Vật cản đã thoát vùng nguy hiểm, chuyển sang đi chậm")
                        if not destination_reached:
                            target_speed = 20
                            stop_triggered = False
                            slowdown_triggered = True
                            i_value = 0
                            prevError = get_position_value_analog(sensor.get_analog_output()) - target
                        # break  # Thoát vòng lặp chờ và quay lại PID

                    if slowdown_triggered:
                        if avg_distance > SLOW_DOWN_DISTANCE:
                            print("[✓] Vật cản đã biến mất hoàn toàn, khôi phục tốc độ")
                            slowdown_triggered = False

                            if not destination_reached:
                                target_speed = current_speed_zone
                                i_value = 0
                                prevError = get_position_value_analog(sensor.get_analog_output()) - target
                                break
                        elif avg_distance < STOP_DISTANCE:
                            print("[!] Vật cản gần, DỪNG robot từ vùng slow_down!")
                            target_speed = 0
                            motor_stopped = False
                            stop_triggered = True

                if destination_reached:
                    break
            # Reset
            decreasing_count = 0
            previous_avg_distance = None
            distance_window.clear()

            motor_stopped = False

        time.sleep(0.1)

    print("######## Kết thúc đo vật cản ########")

## =================== HÀM DỪNG KHẨN CẤP AGV ===================
# Note: Khi gặp vật cản hoặc ra khỏi line
def AGV_emergency_stop():
    global cmds, robot_running_analog, robot_running_digital, lost_line_timer, destination_reached
    global Kp, Ki, Kd

    if robot_running_analog or robot_running_digital:
        print("Dừng khẩn cấp xe!")
        robot_running_analog = False
        robot_running_digital = False
        with lock_motors:
            left_rpm, right_rpm = motors.get_rpm() # Do vị trí bánh đảo ngược nên left_rpm là của bánh phải (right) và right_rpm là của bánh trái (left)
            average_rpm = (abs(left_rpm) + abs(right_rpm)) / 2
            stop_time = int((average_rpm / 60) * 1500) # ms, Tiêu chuẩn thời gian dừng cho 60 rpm là 1.5s (1500 ms)
            motors.set_decel_time(stop_time, stop_time)
            motors.stop()
        time.sleep(stop_time/1000 + 0.5)   # Đảm bảo điều khiển PID đã được tắt
        cmds = [0, 0]  # Reset lại tốc độ ban đầu
        Kp, Ki, Kd = pid_table.get(0)   # Cập nhật PID về ban đầu
        # target_speed_reached = False
        print("Xe đã dừng!")
        init_AGV() # Xe cần khởi động lại sau khi dừng và cần vô hiệu hóa bánh xe để thả tự do
        print("Khởi động lại xe...")
        time.sleep(0.5)

        if lost_line_timer is not None:
            lost_line_timer.cancel()
            lost_line_timer = None
            motors.disable_motor()  # Thả tự do bánh xe khi đã rời khỏi line
            print("Vô hiệu hóa bánh xe!")
            destination_reached = True # Dừng kiểm tra marker

        print(f"Marker count: {marker_check_count}")
        print(f"Intersection marker count: {intersection_marker_check_count}")

## =================== HÀM DỪNG AGV VỚI BIẾN THỜI GIAN ===================
# Note: Khi cần dừng với thời gian cần thiết (tính toán quãng đường), dùng cho ngã rẽ
def AGV_stop_with_time(stop_time_L, stop_time_R):
    global robot_running_analog, robot_running_digital, cmds
    global Kp, Ki, Kd

    if robot_running_analog or robot_running_digital:
        print("Dừng xe theo thời gian!")
        robot_running_analog = False
        robot_running_digital = False
        with lock_motors:
            motors.set_decel_time(stop_time_L, stop_time_R)
            motors.stop()

        higher_stop_time = max(stop_time_L, stop_time_R)
        time.sleep(higher_stop_time/1000 + 0.5)   # Đảm bảo điều khiển PID đã được tắt
        cmds = [0, 0]  # Reset lại tốc độ ban đầu
        Kp, Ki, Kd = pid_table.get(0)  # Cập nhật PID về ban đầu

        print("Xe đã dừng!")

# =================== HÀM KIỂM TRA LIỆU CÓ DUY NHẤT TÍN HIỆU ANALOG TỪ 1 LINE TỪ ===================
def has_only_1_surge_signal(arr):
    len_arr = len(arr)
    peak_index = np.argmax(arr)

    # Check increasing sequence before the peak
    for i in range(peak_index):
        if arr[i] > arr[i + 1]:
            return False

    # Check decreasing sequence after the peak
    for i in range(peak_index, len_arr - 1):
        if arr[i] < arr[i + 1]:
            return False

    return True
# Tương tự hàm trên nhưng dùng đặc biệt cho marker
def has_only_1_surge_signal_marker(arr):
    len_arr = len(arr)
    peak_index = np.argmax(arr)

    # Check increasing sequence before the peak
    for i in range(peak_index):
        if arr[i] > arr[i + 1]:
            return False, arr[peak_index]

    # Check decreasing sequence after the peak
    for i in range(peak_index, len_arr - 1):
        if arr[i] < arr[i + 1]:
            return False, arr[peak_index]

    return True, arr[peak_index]

# =================== HÀM TÍNH GIÁ TRỊ VỊ TRÍ CỦA CẢM BIẾN LINE TỪ THEO TÍN HIỆU ANALOG ===================
def get_position_value_analog(pin_values):
    # Calculate the weighted sum and total sum of sensor values
    weighted_sum = sum(i * value for i, value in enumerate(pin_values))
    total_sum = sum(pin_values)

    # Avoid division by zero if no sensor is activated
    if total_sum == 0:
        return None  # No line detected

    # Calculate the position as a weighted average
    position_value = weighted_sum / total_sum
    return position_value

# =================== HÀM ĐIỀU KHIỂN PID TÍN HIỆU ANALOG ===================
def pid_controller_analog():
    global cmds, position_analog, error, prevError, d_value, i_value, correction, lost_line_timer
    global Kp, Ki, Kd
    global marker_in_zone, target_speed, motor_stopped
    print("\n=========== Start pid ANALOG ============\n")
    while robot_running_analog:
        start = time.perf_counter()

        # Tăng/giảm tốc độ từ từ
        if cmds[0] != target_speed:
            delta = 2.5 if cmds[0] < target_speed else -2.5
            cmds[0] += delta
            cmds[1] -= delta
            Kp, Ki, Kd = pid_table.get(cmds[0], (Kp, Ki, Kd))

        # Dừng khi hoàn thành quãng đường, giảm dần về 0 để bám line
        if cmds[0] == 0:
            if destination_reached:  # Đã tới điểm đến
                with lock_motors:
                    motors.stop()
                    time.sleep(0.5)
                    Kp, Ki, Kd = pid_table.get(0)  # Cập nhật PID về ban đầu
                    motors.enable_motor()
                    turn_angle(180, 10, 'L', 2)  # Quay 180 độ
                    break
            if stop_button_pressed:  # Nút dừng đã được nhấn
                with lock_motors:
                    motors.stop()
                    time.sleep(0.5)
                    Kp, Ki, Kd = pid_table.get(0)  # Cập nhật PID về ban đầu
                    motors.enable_motor()
                    break
            if stop_triggered:       # Tín hiệu dừng trước vật cản
                if not motor_stopped:
                    with lock_motors:
                        motors.stop()
                        time.sleep(0.5)
                        Kp, Ki, Kd = pid_table.get(0)  # Cập nhật PID về ban đầu
                        motors.enable_motor()
                    motor_stopped = True
                    print("Motor stopped")
                else:
                    print("Motor stopped again")

                time.sleep(0.1)
                continue

        # Chờ lock_sensor được thả từ marker_check()
        with lock_sensor:
            time.sleep(0.0025) # đợi tín hiệu xử lý xong
            analog_array = sensor.get_analog_output()

        # Chỉ bám line khi tín hiệu là từ 1 line từ duy nhất
        if has_only_1_surge_signal(analog_array):
            position_analog = get_position_value_analog(analog_array)
            if position_analog is None:
                print("Không tìm thấy line!")
                if lost_line_timer is None:
                    print("Tiến hành dò tìm line...")
                    lost_line_timer = threading.Timer(timeout_duration, AGV_emergency_stop)
                    lost_line_timer.start()
                correction = 0
            else:
                # Đã dò được line, dừng timer xử lý mất line
                if lost_line_timer is not None:
                    print("Đã dò được line, tiếp tục điều hướng!")
                    lost_line_timer.cancel()
                    lost_line_timer = None

                # Cần cập nhật biến prevError ngay khi ra khỏi marker để tránh giật
                if marker_in_zone:
                    prevError = get_position_value_analog(sensor.get_analog_output()) - target
                    marker_in_zone = False

                # Tính toán PID
                error = position_analog - target
                d_value = error - prevError
                i_value += error
                correction = Kp * error + Kd * d_value + Ki * i_value

                # Giới hạn lại độ điều chỉnh tránh xe lắc mạnh
                if correction > 20: correction = 20
                elif correction < -20: correction = -20

                # Cập nhật biến lỗi quá khứ
                prevError = error
        else:
            marker_in_zone = True
            correction = 0

        # Điều chỉnh tốc độ động cơ
        left_speed = int(cmds[1] - correction)
        right_speed = int(cmds[0] - correction)
        # Can thiệp khi cần thiết (AGV_emergency_stop/AGV_stop_with_time)
        with lock_motors:
            motors.set_rpm(right_speed, left_speed)

        end = time.perf_counter()
        print(f"Elasped time analog: {end-start}")

        # Thời gian delay để tránh quá tải, race giữa các thread
        time.sleep(pid_interval)

    print("\n============ pid ANALOG has stopped ============\n")

# =================== HÀM CHUYỂN GIÁ TRỊ HEX VỀ 1 MẢNG 16 PHẦN TỬ SỐ NGUYÊN ===================
def read_sensor(hex_value):
    binary_string = format(hex_value, '016b')  # Chuyển hex sang binary
    return [int(bit) for bit in binary_string]  # Trả về 1 mảng 16 phần tử gồm 0s và 1s

# =================== HÀM TÍNH GIÁ TRỊ VỊ TRÍ CỦA CẢM BIẾN LINE TỪ THEO TÍN HIỆU DIGITAL ===================
def get_position_value_digital():
    weighted_sum = 0
    active_sensors = 0

    with lock_sensor:  # Chờ lock_sensor được thả từ marker_check()
        time.sleep(0.004)  # đợi tín hiệu xử lý xong
        sensor_digital = sensor.get_digital_output()

    sensor_digital_data = read_sensor(sensor_digital)
    for i, bit in enumerate(sensor_digital_data):
        if bit == 1:
            weighted_sum += sensor_positions[i]
            active_sensors += 1

    # Avoid division by zero if no sensor is activated
    if active_sensors == 0:
        return None, 0  # No line detected

    return weighted_sum / active_sensors, active_sensors

# =================== HÀM ĐIỀU KHIỂN PID TÍN HIỆU DIGITAL ===================
def pid_controller_digital():
    global cmds, position_digital, error, prevError, d_value, correction, lost_line_timer
    global motor_stopped
    print("\n============ Start pid DIGITAL ============\n")
    while robot_running_digital:
        start = time.perf_counter()

        position_digital, pin_count = get_position_value_digital()

        # Tăng/giảm tốc độ từ từ
        if cmds[0] != target_speed:
            delta = 2.5 if cmds[0] < target_speed else -2.5
            cmds[0] += delta
            cmds[1] -= delta

        # Dừng khi hoàn thành quãng đường, giảm dần về 0 để bám line
        if cmds[0] == 0:
            if stop_button_pressed:  # Nút dừng đã được nhấn
                with lock_motors:
                    motors.stop()
                    time.sleep(0.5)
                    motors.enable_motor()
                    break
            if stop_triggered:
                if not motor_stopped:
                    with lock_motors:
                        motors.stop()
                        time.sleep(0.5)
                        motors.enable_motor()
                    motor_stopped = True
                    print("Motor stopped")
                else:
                    print("Motor stopped again")

                time.sleep(0.1)
                continue

        if position_digital is None:
            print("Không tìm thấy line!")
            if lost_line_timer is None:
                print("Tiến hành dò tìm line...")
                lost_line_timer = threading.Timer(timeout_duration, AGV_emergency_stop)
                lost_line_timer.start()
            correction = 0
        else:
            # Đã dò được line, dừng timer xử lý mất line
            if lost_line_timer is not None:
                print("Đã dò được line, tiếp tục điều hướng!")
                lost_line_timer.cancel()
                lost_line_timer = None

            # Tránh việc đo được marker dẫn đến xe dao động mạnh
            if pin_count < 7:

                # Tính toán PID
                error = position_digital
                d_value = error - prevError

                # Giới hạn khoảng điều khiển
                if abs(error) < 1.0:
                    correction = 0
                else:
                    correction = Kp_d * error + Kd_d * d_value

                # Giới hạn lại độ điều chỉnh tránh xe lắc mạnh
                if correction > 20: correction = 20
                elif correction < -20: correction = -20

                # Cập nhật biến lỗi quá khứ
                prevError = error
            else:
                correction = 0

        # Điều chỉnh tốc độ động cơ
        left_speed = int(cmds[1] - correction)
        right_speed = int(cmds[0] - correction)
        # Can thiệp khi cần thiết (AGV_emergency_stop)
        with lock_motors:
            motors.set_rpm(right_speed, left_speed)

        end = time.perf_counter()
        print(f"Elasped time digital: {end - start}")

        # Thời gian delay để tránh quá tải, race giữa các thread
        time.sleep(pid_interval)
    print("\n============ pid DIGITAL has stopped ============\n")

# =================== HÀM PHÁT HIỆN MARKER TỪ CẢM BIẾN detect_marker_shift ===================
# Note: Dùng chung với hàm has_only_1_surge_signal_marker() để xác định marker đúng hơn
def detect_marker_shift(prev, curr):
    # Find the weighted center of mass of the previous and current distributions
    prev_center = np.average(np.arange(len(prev)), weights=prev)
    curr_center = np.average(np.arange(len(curr)), weights=curr)

    # Compare center shifts
    if curr_center < prev_center:
        return "L"
    elif curr_center > prev_center:
        return "R"
    else:
        return "C"

# =================== HÀM KIỂM TRA VẠCH BÁO RẼ Ở NGÃ BA, NGÃ TƯ detect_intersection_marker() ===================
def count_ones(value):
    return bin(value).count('1')
def compute_center_of_mass(value):
    """Calculate the average position of '1's (center of mass)."""
    binary_str = format(value, '016b')
    positions = [i for i, bit in enumerate(binary_str) if bit == '1']
    len_pos = len(positions)
    if len_pos == 0: return None
    return sum(positions) / len_pos
def detect_intersection_marker(prev, curr):
    prev_count = count_ones(prev)
    curr_count = count_ones(curr)
    # Cách biệt số lượng bit 1 quá bé, có thể loại bỏ
    if curr_count - prev_count <= 1:
        return False

    prev_com = compute_center_of_mass(prev)
    curr_com = compute_center_of_mass(curr)
    if prev_com is None or curr_com is None:
        return False # Đa phần là do ko dò được line

    # So sánh trung tâm vị trí bit 1
    shift = curr_com - prev_com

    if shift < -1 or shift > 1:
        return False
    return True # Vị trí trung tâm hoặc sai lệch ko đáng kể

## =================== HÀM/CHƯƠNG TRÌNH ĐO QUÃNG ĐƯỜNG CẦN ĐI ===================
# Note: Khi cần đi 1 quãng đường nhất định để thực hiện các tác vụ khác ( chỉ dùng cho ngã rẽ )
def travel_distance(direction):
    global robot_running_analog, robot_running_digital, pid_thread, obstacle_thread
    global current_speed_zone, target_speed, i_value, prevError, Kp, Ki, Kd
    global stop_turn_distance, travelled_directions
    start_pul_r, start_pul_l = motors.get_pulses_travelled()

    if direction is not None:
        # Cập nhật chỉ dẫn đã thực hiện
        travelled_directions[total_intersection_passed] = direction

        if current_speed_zone == 60: stop_turn_distance = 37
        else: stop_turn_distance = 38.5

        while True:
            with lock_motors:
                right_rpm, left_rpm = motors.get_rpm()  # Do vị trí bánh đảo ngược nên left_rpm là của bánh phải (right) và right_rpm là của bánh trái (left)
                curr_pul_r, curr_pul_l = motors.get_pulses_travelled()
                dist_travelled_r, dist_travelled_l = motors.get_wheels_travelled(start_pul_r, start_pul_l, curr_pul_r, curr_pul_l)
            average_rpm = (abs(left_rpm) + abs(right_rpm)) / 2
            stop_time = int((average_rpm / 60) * 1500)  # ms, Tiêu chuẩn thời gian dừng cho 60 rpm là 1.5s (1500 ms)
            linear_average_v = (average_rpm*2*math.pi/60.0) * Rw # cm/s
            stop_distance = linear_average_v * stop_time / 2000  # Khi xe dừng sẽ còn đi 1 quãng đường nữa theo vận tốc hiện tại
            current_distance = (dist_travelled_r + dist_travelled_l) / 2
            if current_distance + stop_distance >= stop_turn_distance:
                print("\n!!!!!!!!!!!! Tiến hành dừng và rẽ !!!!!!!!!!!!")
                # Trạng thái PID digital và analog đã được gán False, xe đã dừng => Cần khởi động lại PID analog sau khi rẽ
                AGV_stop_with_time(int(stop_time * (average_rpm / abs(right_rpm))), int(stop_time * (average_rpm / abs(left_rpm))))
                turn_angle(90, 15, direction, 1)

                # Khởi tạo giá trị điều khiển PID
                target_speed = 25
                i_value = 0  # Reset giá trị tích phân về ban đầu giúp tránh tích tụ errors
                prevError = get_position_value_analog(sensor.get_analog_output()) - target # Giảm giật lúc bắt đầu PID
                robot_running_analog = True

                # Khởi tạo các luồng đã tắt
                pid_thread = threading.Thread(target=pid_controller_analog)
                obstacle_thread = threading.Thread(target=check_obstacle)

                obstacle_thread.start()
                pid_thread.start()
                break
            time.sleep(0.02)
    else:
        robot_running_digital = True
        robot_running_analog = False
        pid_thread.join() # Đợi PID analog kết thúc
        pid_thread = threading.Thread(target=pid_controller_digital)  # Khởi tạo luồng PID digital
        pid_thread.start()

    while True:
        curr_pul_r, curr_pul_l = motors.get_pulses_travelled()
        dist_travelled_r, dist_travelled_l = motors.get_wheels_travelled(start_pul_r, start_pul_l, curr_pul_r, curr_pul_l)
        current_distance = (dist_travelled_r + dist_travelled_l) / 2
        if current_distance >= resume_marker_distance:
            break
        time.sleep(0.02)

# =================== HÀM CHUYỂN HƯỚNG ROBOT ===================
def turn_angle(angle, rpm, direction, active_wheels):
    """
    Turns the AGV by a given angle.
    :param angle: Turn angle in degrees (always positive)
    :param rpm: Wheel speed in RPM
    :param direction: "L" for left, "R" for right
    :param active_wheels: Number of wheels turning (1 or 2)
    """
    print("Tiến hành xoay xe...")
    motors.enable_motor()
    motors.set_accel_time(t1 * 1000, t1 * 1000)
    motors.set_decel_time(t2 * 1000, t2 * 1000)

    turn_radius = wheelbase / 2 if active_wheels == 2 else wheelbase  # Adjust radius based on mode
    arc_length = math.radians(angle) * turn_radius  # Distance wheel must travel

    turn_dir = 1 if direction == 'L' else -1
    if active_wheels == 2:
        motors.set_rpm(turn_dir * rpm, turn_dir * rpm)  # Counter-rotation
    elif active_wheels == 1:
        # One wheel moves, the other stays still
        right_rpm, left_rpm = (turn_dir * rpm, 0) if direction == 'L' else (0, turn_dir * rpm)
        motors.set_rpm(right_rpm, left_rpm)
    else:
        raise ValueError("Number of active wheels must be 1 or 2")

    # Get initial travel pulses
    start_pul_r, start_pul_l = motors.get_pulses_travelled()
    while True:
        curr_pul_r, curr_pul_l = motors.get_pulses_travelled()
        dist_travelled_r, dist_travelled_l = motors.get_wheels_travelled(start_pul_r, start_pul_l, curr_pul_r, curr_pul_l)
        right_rpm, left_rpm = motors.get_rpm()
        stop_distance_r = abs(right_rpm) * math.pi * Rw * t2 / 60
        stop_distance_l = abs(left_rpm) * math.pi * Rw * t2 / 60
        if active_wheels == 2:
            if dist_travelled_r + stop_distance_r >= abs(arc_length) and \
                dist_travelled_l + stop_distance_l >= abs(arc_length):
                break
        else:  # One-wheel pivot turn
            moving_dist = dist_travelled_r if direction == 'L' else dist_travelled_l
            stop_distance = stop_distance_r if direction == 'L' else stop_distance_l

            if moving_dist + stop_distance >= abs(arc_length):
                break

    motors.stop()  # Stop with deceleration time
    time.sleep(t2 + 0.5)
    init_AGV() # Restart AGV
    print("Khởi động lại xe sau khi xoay...\n")
    time.sleep(0.5)

# =================== HÀM KIỂM TRA NGÃ RẼ ===================
def is_intersection_marker(intersect_marker_check_count):
    if intersect_marker_check_count < 3: return False

    # if intersect_marker_check_count > 2 and current_speed_zone == 60:
    if intersect_marker_check_count > 2 and 25 < cmds[0] <= 60:
        return True

    # if intersect_marker_check_count > 8 and current_speed_zone == 25:
    if intersect_marker_check_count > 8 and cmds[0] <= 25:
        return True

    return False

# =================== HÀM XỬ LÝ ĐỊNH HƯỚNG CHO NGÃ RẼ ===================
def handle_intersection(intersection_count):
    global target_speed, current_speed_zone
    global start_passed, destination_reached
    global total_intersection_passed, travelled_directions, intersection_marker_count_met

    if not start_passed:
        total_intersection_passed -= 1 # Đi qua marker đầu tiên
        intersection_marker_count_met = 0
        target_speed = current_speed_zone
        start_passed = True
        print("\n############# Start passed #############\n")
        return
    if total_intersection_passed > total_intersection_required:
        # Cập nhật lại các biến dẫn đường
        total_intersection_passed = 0
        travelled_directions = {}
        intersection_marker_count_met = 0

        destination_reached = True
        obstacle_thread.join() # Đợi chương trình vật cản kết thúc hoàn toàn
        target_speed = 0 # Điều chỉnh tốc độ về 0 cho hàm PID
        print("\n############# Destination reached #############\n")
        return

    print("\n############# Tạm ngưng marker_check! #############\n")

    direction = directions.get(intersection_count, None)
    distance_thread = threading.Thread(target=travel_distance, args=(direction,))
    distance_thread.start()
    distance_thread.join()

    print("\n############# Tiếp tục marker_check! #############\n")

# =================== CHƯƠNG TRÌNH KIẾM TRA MARKER TỔNG THỂ ===================
def marker_check():
    global Kp, Ki, Kd, i_value, prevError, current_speed_zone, target_speed, robot_running_analog, robot_running_digital, pid_thread
    global line_pin_count, digital_value
    global marker_check_count, intersection_marker_check_count, intersection_marker_count_met, total_intersection_passed
    global current_analog_array, previous_analog_array
    global current_digital_value, prev_digital_value
    print("============= START MARKER CHECK =============")
    while not destination_reached:
        # start = time.perf_counter()
        try:
            with lock_sensor:
                time.sleep(0.0025)  # đợi tín hiệu xử lý xong
                analog_array = sensor.get_analog_output()
                # Nhận diện vạch báo rẽ
                time.sleep(0.0025)  # đợi tín hiệu xử lý xong
                line_pin_count, digital_value = sensor.get_pin_count()
            check_line_condition, max_value = has_only_1_surge_signal_marker(analog_array)
            if check_line_condition:
                previous_analog_array = analog_array

                # Thay đổi tốc độ
                if marker_check_count <= -7 and current_speed_zone == 25: # Tăng tốc
                    current_speed_zone = 60
                    target_speed = current_speed_zone
                    i_value = 0 # Reset giá trị tích phân về ban đầu giúp tránh tích tụ errors

                if marker_check_count > 3 and current_speed_zone == 60:   # Giảm tốc
                    current_speed_zone = 25
                    target_speed = current_speed_zone
                    i_value = 0 # Reset giá trị tích phân về ban đầu giúp tránh tích tụ errors

                marker_check_count = 0 # Reset lại biến đếm marker

                if 7 > line_pin_count > 3:
                    prev_digital_value = digital_value
                    if is_intersection_marker(intersection_marker_check_count): # Đã nhận diện được vạch báo ngã rẽ
                        intersection_marker_count_met += 1
                        if intersection_marker_count_met >= 2:
                            if robot_running_digital:
                                robot_running_analog = True
                                robot_running_digital = False
                                pid_thread.join() # Đợi PID digital kết thúc
                                pid_thread = threading.Thread(target=pid_controller_analog)  # Khởi tạo luồng PID analog
                                pid_thread.start()
                            elif robot_running_analog:
                                target_speed = current_speed_zone
                                i_value = 0  # Reset giá trị tích phân về ban đầu giúp tránh tích tụ errors

                            intersection_marker_count_met = 0
                        else:
                            total_intersection_passed += 1
                            handle_intersection(total_intersection_passed) # Xử lý định hướng

                    intersection_marker_check_count = 0 # Reset biến đếm xác nhận intersection
                elif line_pin_count >= 7 and max_value > 50:
                    current_digital_value = digital_value
                    print(f"Max value: {max_value}")
                    print(f"Previous digital: {prev_digital_value:016b}")
                    print(f"Current digital: {current_digital_value:016b}")
                    # if detect_intersection_marker(prev_digital_value, current_digital_value) and not intersection_marker_met:
                    if detect_intersection_marker(prev_digital_value, current_digital_value):
                        # intersection_marker_met = True
                        intersection_marker_check_count += 1
                        print("Intersection marker detected\n")

            elif max_value > 20: # Tránh nhiễu hoặc line quá xa tâm
                current_analog_array = analog_array
                marker_position = detect_marker_shift(previous_analog_array, current_analog_array)
                # print(f"Current_analog = {current_analog_array}")
                # print("Marker spotted!")

                if marker_position == 'L':
                    # Left marker: Increase speed and change to default configuration
                    print("Left marker detected, minus to marker_count")
                    marker_check_count -= 1 # Update current state
                elif marker_position == 'R':
                    # Right marker: Decrease speed and change to configuration for slower speed
                    # Use this when entering turning track
                    print("Right marker detected, decreasing speed")
                    marker_check_count += 1 # Update current state
                else:
                    print("Center marker detected, AGV oscillates too much")

        except KeyboardInterrupt:
            break
        time.sleep(0.015)
        # end = time.perf_counter()
        # print(end-start)
    print("============= END MARKER CHECK =============")

# =================== ĐỌC FILE DẪN ĐƯỜNG ===================
def read_direction_file(base_path, start_num, end_num):
    directory_path = os.path.join(base_path, str(start_num))
    file_txt_path = os.path.join(directory_path, f"{start_num}_{end_num}.txt")

    if os.path.exists(file_txt_path):
        with open(file_txt_path, 'r', encoding='utf-8') as file_txt:
            file_lines = file_txt.readlines()
            num_intersections = int(file_lines[0].strip())
            num_directions = eval(file_lines[1].strip()) if len(file_lines) > 1 else {}
    else:
        print("File not found.")
    return num_intersections, num_directions

# =================== THUẬT TOÁN TÌM TUYẾN ĐƯỜNG NGẮN NHẤT CHO NHIỀU CẶP ĐIỂM ===================
def find_shortest_route(start_node, end_nodes_set):
    """Find the shortest route visiting all end_nodes and returning to start."""
    min_total_cost = float("inf")
    best_route_path = None

    for perm_order in permutations(end_nodes_set):  # Try all visiting orders
        route_list = [start_node] + list(perm_order) + [start_node]
        route_cost = 0
        valid_route = True

        for i in range(len(route_list) - 1):
            src, dest = route_list[i], route_list[i + 1]
            if dest in graph.get(src, {}):
                route_cost += graph[src][dest]
            else:
                valid_route = False
                break

        if valid_route and route_cost < min_total_cost:
            min_total_cost = route_cost
            best_route_path = route_list

    return best_route_path, min_total_cost

# =================== SET TUYẾN ĐƯỜNG NGẮN NHẤT CHO AGV ===================
def set_route_for_agv(end_tables):
    global shortest_route
    # Mặc định điểm bắt đầu là 0
    shortest_route, _ = find_shortest_route(0, end_tables)

# =================== KHỞI ĐỘNG AGV ===================
def init_AGV():
    motors.enable_motor()
    motors.set_accel_time(50, 50)
    motors.set_decel_time(50, 50)

# =================== KHỞI TẠO BIẾN XỬ LÝ MARKER ===================
def init_marker():
    global line_pin_count, digital_value, marker_in_zone, marker_check_count
    global intersection_marker_check_count, intersection_marker_count_met, start_passed, destination_reached
    global total_intersection_passed, travelled_directions
    global current_analog_array, previous_analog_array
    global current_digital_value, prev_digital_value

    # ===== Biến xử lý cho nhận diện marker =====
    line_pin_count = 0  # Dùng cho nhận biết ngã rẽ
    digital_value = 0  # Dùng cho nhận biết ngã rẽ
    marker_in_zone = False  # Khi PID đo được sẽ ko tính toán sai số, cần cập nhật lại prevError giúp tránh giật
    marker_check_count = 0  # marker "R" ( > 3 ) ,marker "L" ( < -13 ), tăng độ chính xác cho việc đọc marker bằng cách thêm giới hạn
    intersection_marker_check_count = 0  # Tương tự marker_check_count nhưng dùng cho intersection ( > 2 )
    intersection_marker_count_met = 0  # Đếm số lần đọc được marker ngã rẽ, max: 2 ( 1-in, 2-out )
    start_passed, destination_reached = False, False  # Tại điểm bắt đầu và kết thúc sẽ có intersection marker
    total_intersection_passed = 0  # Đếm tổng số ngã rẽ đi qua, dùng để xử lý định hướng
    travelled_directions = {}  # Lưu các chỉ dẫn đã thực hiện
    current_analog_array, previous_analog_array = [], []
    current_digital_value, prev_digital_value = 0b0, 0b0


##############################################################################################
############################## CÁC CHƯƠNG TRÌNH CHO NÚT NHẤN #################################
##############################################################################################

# =================== KÍCH HOẠT CHƯƠNG TRÌNH AGV GIAO ĐỒ ĂN TRONG NHÀ HÀNG ===================
# ========================== Chạy trên 1 thread độc lập với giao diện ========================
def RUN_AGV(selected_tables):
    global start_point, end_point, shortest_route, start_passed, destination_reached
    global total_intersection_required, directions
    global target_speed, current_speed_zone, robot_running_analog, robot_running_digital
    global i_value, prevError, pid_thread, marker_thread, obstacle_thread

    # Khởi động AGV
    init_AGV()

    # Khởi tạo tuyến đường ngắn nhất
    set_route_for_agv(selected_tables)

    print("Bắt đầu giao đồ ăn!")

    num_destination = len(shortest_route)
    for index in range(num_destination):

        if index < num_destination - 1:
            # Cập nhật tọa độ điểm bắt đầu và điểm đến
            start_point = all_points[shortest_route[index]]
            end_point = all_points[shortest_route[index+1]]

            total_intersection_required, directions = read_direction_file(
                directory,
                shortest_route[index],
                shortest_route[index+1]
            )
        else:
            break

        # Khởi động biến trạng thái AGV
        robot_running_analog = True  # Mặc định bắt đầu điều khiển tín hiệu analog
        robot_running_digital = False
        target_speed = 25 # Khởi động tốc độ tạm thời là 25 rpm

        # Khởi tạo các biến xử lý marker, dẫn đường
        init_marker()

        # =================== KHỞI TẠO CÁC THREAD ===================
        pid_thread = threading.Thread(target=pid_controller_analog)
        marker_thread = threading.Thread(target=marker_check)
        obstacle_thread = threading.Thread(target=check_obstacle)

        # =================== KHỞI TẠO TÍN HIỆU ĐIỀU KHIỂN ===================
        i_value = 0  # Tránh tích tụ lỗi
        prevError = get_position_value_analog(sensor.get_analog_output()) - target  # Tránh giật xe

        # =================== BẮT ĐẦU CÁC THREAD ===================
        pid_thread.start()
        marker_thread.start()
        obstacle_thread.start()

        # =================== ĐỢI CÁC THREAD KẾT THÚC ===================
        obstacle_thread.join()
        marker_thread.join()
        pid_thread.join()

        # Kết thúc chương trình sau khi nút RETURN_TO_KITCHEN() được bấm
        if return_kitchen_button_pressed:
            break

        if index < num_destination - 2:
            # Thông báo giao đồ ăn thành công
            engine.say("Your order has arrived! Please take out the order with your current room number!")
            engine.runAndWait()
            # Chờ 3 phút để khách lấy đồ trên xe xuống và tiếp tục
            time.sleep(5)

        else:
            # Thông báo đồ ăn về bếp thành công
            engine.say("The AGV has returned to the kitchen! Waiting for next orders!")
            engine.runAndWait()

        # Cập nhật lại điểm bắt đầu
        start_point = end_point

    print("Kết thúc giao đồ ăn!")
    motors.disable_motor()


# Chương trình con dành riêng cho việc chạy theo chỉ dẫn được khai báo (total_intersection_required, directions)
# Dùng cho nút RETURN_TO_KITCHEN() hoặc các chương trình mới (phát triển thêm)
def run_agv_request(goal):
    global start_point
    global total_intersection_required, directions
    global target_speed, current_speed_zone, robot_running_analog, robot_running_digital
    global i_value, prevError, pid_thread, marker_thread, obstacle_thread

    print("Bắt đầu giao đồ ăn theo chỉ dẫn mới!")

    # Khởi động biến trạng thái AGV
    robot_running_analog = True  # Mặc định bắt đầu điều khiển tín hiệu analog
    robot_running_digital = False
    target_speed = current_speed_zone # Khôi phục tốc độ ban đầu

    # =================== KHỞI TẠO CÁC THREAD ===================
    pid_thread = threading.Thread(target=pid_controller_analog)
    marker_thread = threading.Thread(target=marker_check)
    obstacle_thread = threading.Thread(target=check_obstacle)

    # =================== KHỞI TẠO TÍN HIỆU ĐIỀU KHIỂN ===================
    i_value = 0  # Tránh tích tụ lỗi
    prevError = get_position_value_analog(sensor.get_analog_output()) - target  # Tránh giật xe

    # =================== BẮT ĐẦU CÁC THREAD ===================
    pid_thread.start()
    marker_thread.start()
    obstacle_thread.start()

    # =================== ĐỢI CÁC THREAD KẾT THÚC ===================
    obstacle_thread.join()
    marker_thread.join()
    pid_thread.join()

    # Cập nhật lại điểm bắt đầu
    start_point = goal

    # Thông báo đồ ăn đã được gửi lại bếp
    engine.say("The AGV has returned to the kitchen! Waiting for next orders!")
    engine.runAndWait()

    print("Kết thúc giao đồ ăn theo chỉ dẫn mới!")
    motors.disable_motor()

# =================== KÍCH HOẠT CHƯƠNG TRÌNH DỪNG TỪ TỪ CHO NÚT NHẤN STOP ===================
# ===================== Sau khi ấn STOP, giao diện cần đợi cho đến khi ======================
# ============================ chương trình kết thúc hoàn toàn ==============================
# *******************************************************************************************
# **************************** Chạy chung thread với nút nhấn *******************************
# *******************************************************************************************
def STOP_AGV():
    global stop_button_pressed, target_speed, pid_thread

    stop_button_pressed = True # Trạng thái nút nhấn STOP đã được nhấn

    target_speed = 0
    pid_thread.join() # Đợi PID thread kết thúc

    stop_button_pressed = False

# ====================== TIẾP TỤC CHƯƠNG TRÌNH AGV SAU KHI ĐÃ ẤN STOP =======================
# *******************************************************************************************
# **************************** Chạy chung thread với nút nhấn *******************************
# *******************************************************************************************
def CONTINUE_AGV():
    global stop_button_pressed, target_speed, pid_thread
    global i_value, prevError

    target_speed = current_speed_zone # Khôi phục tốc độ ban đầu

    # =================== KHỞI TẠO TÍN HIỆU ĐIỀU KHIỂN ===================
    i_value = 0  # Tránh tích tụ lỗi
    prevError = get_position_value_analog(sensor.get_analog_output()) - target  # Tránh giật xe

    if robot_running_analog:
        pid_thread = threading.Thread(target=pid_controller_analog)  # Khởi tạo lại PID analog
        pid_thread.start()
        return

    if robot_running_digital:
        pid_thread = threading.Thread(target=pid_controller_digital)  # Khởi tạo lại PID digital
        pid_thread.start()
        return

# ====================== YÊU CẦU AGV QUAY LẠI BẾP SAU KHI ĐÃ ẤN STOP ========================
# *******************************************************************************************
# **************************** Chạy khác thread với nút nhấn *******************************
# *******************************************************************************************
def RETURN_TO_KITCHEN():
    global start_point, return_kitchen_button_pressed
    global total_intersection_passed, total_intersection_required, directions, destination_reached

    # Nút quay lại bếp đã được nhấn (flag để kết thúc RUN_AGV(...))
    return_kitchen_button_pressed = True

    # Đợi marker_thread kết thúc (sau khi STOP, pid_thread đã hoàn toàn kết thúc)
    destination_reached = True # Ngừng marker_thread
    marker_thread.join()
    time.sleep(0.5) # Đợi chương trình RUN_AGV(...) kết thúc hoàn toàn

    destination_reached = False # Khởi tạo lại cho lần khởi động tiếp

    # Khởi tạo trạng thái nút bấm
    return_kitchen_button_pressed = False

    # Theo dõi đường đi để tìm ra điểm đến hiện tại sau ngã rẽ
    final_pos, previous_pos = track_path_to_intersection(
        grid_map,
        start_point,
        travelled_directions,
        total_intersection_passed,
        end_point,
    )

    if final_pos is None and previous_pos is None:
        print("Phát hiện ngõ cụt, kiểm tra lại biến lưu chỉ dẫn đã thực hiện hoặc tổng ngã rẽ đã đi qua!")
        return

    # Điểm bắt đầu sau các chỉ dẫn và điểm đến mới
    start = final_pos
    goal = starts[0] # Vị trí bếp

    # Tạo ra chỉ dẫn kế tiếp cho việc dẫn đường về bếp
    files = Paths_File_Generation(grid_map, starts, goals, directory)
    total_intersection_required, directions, need_turn_180 = files.count_intersections_and_check_rev_dir(
        start, goal, previous_pos
    )

    # Khởi tạo lại biến hỗ trợ dẫn đường
    total_intersection_passed = 0

    if need_turn_180:
        turn_angle(180, 10, 'L', 2)

    run_agv_request(goal)
    motors.disable_motor()

# ======================== NÚT TẮT HOÀN TOÀN CHƯƠNG TRÌNH ĐANG CHẠY =========================
# *******************************************************************************************
# **************************** Chạy khác thread với nút nhấn ********************************
# *******************************************************************************************
def DISABLE_TEST_RUN():
    global disable_test_run_button, destination_reached
    disable_test_run_button = True

    # Dừng điều khiển PID
    STOP_AGV()

    # Dừng hàm check marker
    destination_reached = True
    marker_thread.join()
    obstacle_thread.join()
    destination_reached = False

    # Thả tự do bánh
    motors.disable_motor()

# ============================= CHƯƠNG TRÌNH CHẠY THỬ NGHIỆM ================================
# *******************************************************************************************
# **************************** Chạy khác thread với nút nhấn ********************************
# *******************************************************************************************
def RUN_TEST():
    global total_intersection_required, directions, disable_test_run_button
    global target_speed, current_speed_zone, robot_running_analog, robot_running_digital
    global i_value, prevError, pid_thread, marker_thread, obstacle_thread

    # Khởi động AGV
    init_AGV()

    print("Bắt đầu giao đồ ăn!")

    # Biến dẫn đường để đi liên tục cho đến khi cần quay đầu
    total_intersection_required, directions = 0, {}

    # Khởi tạo trạng thái nút nhấn cho chương trình chạy TEST
    disable_test_run_button = False
    while not disable_test_run_button:

        # Khởi động biến trạng thái AGV
        robot_running_analog = True  # Mặc định bắt đầu điều khiển tín hiệu analog
        robot_running_digital = False
        target_speed = 25  # Khởi động tốc độ tạm thời là 25 rpm

        # Khởi tạo các biến xử lý marker, dẫn đường
        init_marker()

        # =================== KHỞI TẠO CÁC THREAD ===================
        pid_thread = threading.Thread(target=pid_controller_analog)
        marker_thread = threading.Thread(target=marker_check)
        obstacle_thread = threading.Thread(target=check_obstacle)

        # =================== KHỞI TẠO TÍN HIỆU ĐIỀU KHIỂN ===================
        i_value = 0  # Tránh tích tụ lỗi
        prevError = get_position_value_analog(sensor.get_analog_output()) - target  # Tránh giật xe

        # =================== BẮT ĐẦU CÁC THREAD ===================
        pid_thread.start()
        marker_thread.start()
        obstacle_thread.start()

        # =================== ĐỢI CÁC THREAD KẾT THÚC ===================
        obstacle_thread.join()
        marker_thread.join()
        pid_thread.join()

        engine.say("Your order has arrived! Please take out the order with your current room number!")
        engine.runAndWait()
        # time.sleep(5)

    print("Kết thúc giao đồ ăn!")
    # motors.disable_motor()

# RUN_AGV([1])


class AGVController(QObject):
    robotStopped = Signal(str)  # Signal to notify when the robot has stopped
    def __init__(self):
        super().__init__()
        # PHẢI KHỞI TẠO MAP_MANAGER Ở ĐÂY THÌ MỚI DÙNG ĐƯỢC
        self.map_manager = MapHandler()

    def hardware_available(self):
        if HARDWARE_ENABLED:
            return True
        print("Hardware control is disabled. Set HARDWARE_ENABLED = True to enable COM ports.")
        return False

    @Slot('QVariantList')
    def run_agv(self, selected_tables):
        try:
            selected_node_indices = [int(node_index) for node_index in selected_tables]
        except (TypeError, ValueError):
            print("Invalid room selection")
            return

        valid_nodes = set(range(1, len(all_points)))
        if (
            not selected_node_indices
            or len(set(selected_node_indices)) != len(selected_node_indices)
            or any(node_index not in valid_nodes for node_index in selected_node_indices)
        ):
            print(f"Invalid room node indices: {selected_node_indices}")
            return

        if not self.hardware_available():
            self.robotStopped.emit("SUCCESS")
            return

        def task():
            RUN_AGV(selected_node_indices)
            self.robotStopped.emit("SUCCESS")  # Signal to notify when the robot has stopped
        threading.Thread(target=task).start()

    @Slot()
    def return_to_kitchen(self):
        if not self.hardware_available():
            self.robotStopped.emit("RETURNING")
            return

        def task():
          self.robotStopped.emit("RETURNN")
          RETURN_TO_KITCHEN()
          self.robotStopped.emit("RETURNING")  # Signal to notify when the robot has stopped
          # self.robotStopped.emit("RETURNiiiDONE")
        threading.Thread(target=task).start()

    @Slot()
    def stop_agv(self):
        if not self.hardware_available():
            return
        STOP_AGV()

    @Slot()
    def continue_agv(self):
        if not self.hardware_available():
            return
        CONTINUE_AGV()

    @Slot()
    def run_test(self):
        if not self.hardware_available():
            self.robotStopped.emit("STOPTEST")
            return

        def task():
            RUN_TEST()

        threading.Thread(target=task).start()

    @Slot()
    def disable_test_run(self):
        if not self.hardware_available():
            self.robotStopped.emit("STOPTEST")
            return
        DISABLE_TEST_RUN()
        self.robotStopped.emit("STOPTEST")

    @Slot(str, str, str, result=str)
    def save_map_data(self, map_matrix_json, starts_json, goals_json):
        try:
            self.map_manager.save_map(map_matrix_json, starts_json, goals_json)
            reload_navigation_data()
            print("Map and robot directions regenerated")
            return ""
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"Unable to save map: {error}")
            return str(error)

    @Slot(result=str)
    def load_map_data(self):
        # Xin lại dữ liệu từ map_manager và ném ngược về cho QML
        return self.map_manager.load_map()

    @Slot(result=str)
    def list_map_history(self):
        return self.map_manager.list_history()

    @Slot(str, result=str)
    def restore_map_history(self, snapshot_id):
        restored_state = self.map_manager.restore_history(snapshot_id)
        if restored_state:
            reload_navigation_data()
        return restored_state
