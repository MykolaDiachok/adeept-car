#!/usr/bin/env python3
# /home/mykodia/car/server/steer_probe.py
import time, board, busio
from adafruit_pca9685 import PCA9685

i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c, address=0x40)
pca.frequency = 50
#ch =3 # канал керма

try:
    ch = 0
    print("Test channel", ch)
    pca.channels[ch].duty_cycle = 0x1300  # ~середина
    time.sleep(2.0)
    pca.channels[ch].duty_cycle = 0x0A00  # в один бік
    time.sleep(0.6)
    pca.channels[ch].duty_cycle = 0x1C00  # в інший бік
    time.sleep(0.6)
    pca.channels[ch].duty_cycle = 0x0000  # вимк
    time.sleep(0.3)
finally:
    pca.deinit()
