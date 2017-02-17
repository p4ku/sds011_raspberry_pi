import sys
import time
import serial


class SDS011:
    MSG_HEADER = 0xAA
    MSG_CMD = 0xC0
    MSG_TAIL = 0xAB

    def __init__(self, dev):
        self.device = serial.Serial(dev,
                                    baudrate=9600,
                                    stopbits=serial.STOPBITS_ONE,
                                    parity=serial.PARITY_NONE,
                                    timeout=2)

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
            raise Exception("Checksum test failed")

        if tail != self.MSG_TAIL:
            raise Exception("Message was not correctly terminated")

        PM25 = float(PM25_H * 256 + PM25_L) / 10.0
        PM10 = float(PM10_H * 256 + PM10_L) / 10.0

        return PM10, PM25
