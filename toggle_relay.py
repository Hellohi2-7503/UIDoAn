from PySide6.QtCore import QObject, Slot

from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from LH_04 import LH04Relay
import logging

HARDWARE_ENABLED = False

def toggle_relay(relay_index=0, port='COM12', baudrate=115200, slave_id=1):
    """
    Toggle trạng thái relay tại chỉ số relay_index (0 đến 3).
    """
    client = ModbusClient(
        method='rtu',
        port=port,
        baudrate=baudrate,
        stopbits=1,
        bytesize=8,
        parity='N',
        timeout=1
    )

    relay = LH04Relay(client, slave_id=slave_id)

    current_state = relay.read_relay_stage(relay_index)

    if current_state is None:
        print("Không thể đọc trạng thái relay.")
    else:
        new_state = not current_state
        relay_address = relay.RELAY_ADDRESSES[relay_index]
        if relay.write_relay(relay_address, new_state):
            print(f"Relay {relay_index + 1} đã được {'BẬT' if new_state else 'TẮT'}.")
        else:
            print("Không ghi được trạng thái mới cho relay.")

    client.close()

class TurnLedOn(QObject):
    def __init__(self):
        super().__init__()

    @Slot()
    def turnOnLed(self):
        if not HARDWARE_ENABLED:
            print("Relay control is disabled. Set HARDWARE_ENABLED = True to enable COM12.")
            return
        toggle_relay()
