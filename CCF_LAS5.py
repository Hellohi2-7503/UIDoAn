import logging
# import numpy as np
## Class for laser obstacle avoidance sensor CCF_LAS5
class Laser_Obstacle_Sensor:

        def __init__(self, client):

                # Enable logging
                # logging.basicConfig()
                # log = logging.getLogger()
                # log.setLevel(logging.DEBUG)

                self.client = client

                self.client.connect()	# If the client is already connected, then it just returns True

                self.ID = 3

                # The addresses are always 2 bytes, if declare with 0x02, it will know as 0x0002
                ######################
                ## Register Address ##
                ######################
                ## Starting data of 7 pins return (cm) (pin 1)
                self.SENSOR_DATA = 0x00

                ## Baudrate setter/getter
                self.BAUD_RATE = 0x08
                self.baud_rate_map = {
                        2400: 0x0001,
                        4800: 0x0002,
                        9600: 0x0003,
                        19200: 0x0004,
                        38400: 0x0005,
                        57600: 0x0006,
                        115200: 0x0007,
                }

                ## RS-485 MODBUS-based device ID (R/W)
                self.ID_ADDRESS = 0x07

        ## Some time if read immediatly after write, it would show ModbusIOException when get data from registers
        def modbus_fail_read_handler(self, ADDR, WORD):
                read_success = False
                reg = [None]*WORD
                while not read_success:
                        result = self.client.read_holding_registers(ADDR, WORD, unit=self.ID)
                        try:
                                for i in range(WORD):
                                        reg[i] = result.registers[i]
                                read_success = True
                        except AttributeError as e:
                                print(e)
                                pass
                return reg

        ## Basic function to read sensor data
        def get_pins_distance(self):
                hex_values = self.client.read_holding_registers(self.SENSOR_DATA, 7, unit=self.ID)
                int_values = [int(x) for x in hex_values.registers]
                return int_values

        # Return baud command with exact baud rate
        def baud_command_check(self, baud):
                return self.baud_rate_map.get(baud, "Invalid baud rate") # Return invalid baud rate if check unmatched

        ## Set baud rate / Get baud rate
        # Need power on again after setting new baud rate
        # Remember to set client on the current baud rate before changing new baud rate
        def set_baud_rate(self, baud):
                command = self.baud_command_check(baud)
                print(command)
                if command != "Invalid baud rate":
                        result =  self.client.write_register(self.BAUD_RATE, command, unit=self.ID)
                        if result.isError():
                                print('Failed to write baud rate')
                        else:
                                print('Baud rate set successfully')
                else:
                        print(command)

        def get_baud_rate(self):
                result = self.modbus_fail_read_handler(self.BAUD_RATE, 1)
                for baud_rate, value in self.baud_rate_map.items():
                        if value == result[0]:
                                return baud_rate
                return None  # Return None if no match is found

        # Set different ID, default is 1
        def set_ID(self, id):
                result = self.client.write_register(self.ID_ADDRESS, id, unit=self.ID)
                if result.isError():
                        print("Failed to set ID")
                else:
                        print("ID set complete")
                        self.ID = id

        def get_ID(self):
                value = self.modbus_fail_read_handler(self.ID_ADDRESS, 1)
                return int(value[0])
