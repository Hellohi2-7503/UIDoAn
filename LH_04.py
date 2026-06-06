import logging
from pymodbus.client.sync import ModbusSerialClient as ModbusClient

class LH04Relay:
    def __init__(self, client, slave_id=1):
        self.client = client
        self.ID = slave_id

        # Địa chỉ thanh ghi
        self.RELAY_ADDRESSES = [0x0000, 0x0001, 0x0002, 0x0003]
        self.BAUDRATE_ADDRESS = 0x0200

        # Map giá trị baudrate
        self.baudrate_map = {
            300: 0x00, 600: 0x01, 1200: 0x02, 2400: 0x03,
            4800: 0x04, 9600: 0x05, 14400: 0x06, 19200: 0x07,
            38400: 0x08, 56000: 0x09, 57600: 0x0A, 115200: 0x0B
        }

    def is_connected(self):
        if not self.client.is_socket_open():
            if not self.client.connect():
                logging.error("Không thể kết nối Modbus!")
                return False
        return True

    def modbus_fail_read_handler(self, ADDR, WORD):
        retry_count = 5
        for attempt in range(retry_count):
            result = self.client.read_coils(ADDR, WORD, unit=self.ID)
            if result and not result.isError():
                return result.bits
            logging.error(f"Đọc lỗi tại địa chỉ {ADDR}, lần thử {attempt + 1}")
        logging.error(f"Đọc lỗi tại địa chỉ {ADDR} sau {retry_count} lần thử!")
        return None

    def write_relay(self, address, state):
        if not self.is_connected():
            return False
        response = self.client.write_coil(address, state, unit=self.ID)
        if response.isError():
            logging.error(f"Lỗi khi ghi relay tại địa chỉ {address}!")
            return False
        logging.info(f"Relay {address} {'bật' if state else 'tắt'} thành công!")
        return True

    def write_multiple_relays(self, states):
        if not self.is_connected():
            return False
        response = self.client.write_coils(self.RELAY_ADDRESSES[0], states, unit=self.ID)
        if response.isError():
            logging.error("Lỗi khi ghi nhiều relay!")
            return False
        logging.info(f"Đã cập nhật relay: {states}")
        return True

    def read_relay(self, address):
        result = self.modbus_fail_read_handler(address, 1)
        return result[0] if result else None

    def read_relay_stage(self, relay_index):
        """
        Đọc trạng thái của relay tại vị trí relay_index (0 đến 3).
        Trạng thái lấy từ một thanh ghi duy nhất.
        """
        if not self.is_connected():
            return None
        result = self.client.read_holding_registers(self.RELAY_ADDRESSES[0], 1, unit=self.ID)
        if result.isError():
            logging.error("Lỗi khi đọc trạng thái relay!")
            return None
        value = result.registers[0]
        return (value >> relay_index) & 1  # Trả về 0 hoặc 1

    def set_baud_rate(self, baud):
        if baud not in self.baudrate_map:
            logging.error("Baudrate không hợp lệ!")
            return False
        if not self.is_connected():
            return False
        response = self.client.write_register(self.BAUDRATE_ADDRESS, self.baudrate_map[baud], unit=self.ID)
        if response.isError():
            logging.error("Lỗi khi ghi baudrate!")
            return False
        logging.info(f"Đã đặt baudrate {baud} thành công! Cần khởi động lại module.")
        return True

    def get_baud_rate(self):
        if not self.is_connected():
            return None
        result = self.client.read_holding_registers(self.BAUDRATE_ADDRESS, 1, unit=self.ID)
        if result.isError():
            logging.error("Lỗi khi đọc baudrate!")
            return None
        for baud, code in self.baudrate_map.items():
            if code == result.registers[0]:
                return baud
        logging.error("Baudrate không xác định!")
        return None
