import sys
import time
import serial


class SDS011:
    MSG_HEADER = 0xAA
    MSG_CMD = 0xC0
    MSG_TAIL = 0xAB

    def __init__(self, dev):
        self.dev = dev
        self.open()

    def open(self):
        self.device = serial.Serial(self.dev,
                                    baudrate=9600,
                                    stopbits=serial.STOPBITS_ONE,
                                    parity=serial.PARITY_NONE,
                                    timeout=2)

    def close(self):
        self.device.close()

    def sleep(self):
        """
         (1) Send command, set the sensor with ID A160 to sleep: AA B4 06 01 00 00 00 00 00 00 00 00 00 00 00 A1 60 08 AB
             Sensor with ID A160 response: AA C5 06 01 00 00 A1 60 08 AB
        """

        data = [0xAA, 0xB4, 0x06, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x05, 0xAB]
#        checksum = sum(data[2:17]) % 256
#        data[17] = checksum
        self.device.write(bytearray(data))

    def wake_up(self):
        """
        (2) Send command, set the sensor with ID A160 to work: AA B4 06 01 01 00 00 00 00 00 00 00 00 00 00 A1 60 09 AB
        Sensor with ID A160 response: AA C5 06 01 01 00 A1 60 09 AB

        Sensor with ID A160 response, show it is in working mode: AA C5 06 00 01 00 A1 60 08 AB Or reply Sensor with ID A160 response,
        show it is NOT in working mode: AA C5 06 00 00 00 A1 60 07 AB

        (3) Send command, query the working mode of the sensor with ID A160: AA B4 06 00 00 00 00 00 00 00 00 00 00 00 00 A1 60 07 AB
        Notes: The data is stable when the sensor works after 30 seconds; The fan and laser stop working in sleeping mode.
        """

        data = [0xAA, 0xB4, 0x06, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x06, 0xAB]
#        checksum = sum(data[2:17]) % 256
#        data[17] = checksum
        self.device.write(bytearray(data))

    def read(self):
        # Wait until message header: 0xAA, 0xC0
        while True:
            s = self.device.read(1)
            if len(s) < 1:
                raise IOError("Device timed out")
            if ord(s) == self.MSG_HEADER:
                s = self.device.read(1)
                if ord(s) == self.MSG_CMD:
                    break

        s = self.device.read(8)
        if len(s) < 8:
            raise Exception("Data packet too short")

        data = [ord(x) if type(x) == str else int(x) for x in s]
        PM25_L, PM25_H, PM10_L, PM10_H, ID1, ID2, check_sum, tail = data

        if check_sum != sum(data[:6]) % 256:
            self.close()
            self.open()
            raise Exception("Checksum test failed, restarting connection")

        if tail != self.MSG_TAIL:
            raise Exception("Message was not correctly terminated")

        PM25 = float(PM25_H * 256 + PM25_L) / 10.0
        PM10 = float(PM10_H * 256 + PM10_L) / 10.0

        return PM10, PM25
