#!/usr/bin/env python3
# /home/mykodia/car/server/joint_test.py
import time, board, busio
from adafruit_servokit import ServoKit

ADDR = 0x40
CHANNEL = 4          # ← тут підстав свій канал для конкретного суглоба
CENTER = 90
MIN_US, MAX_US = 600, 2400

i2c = busio.I2C(board.SCL, board.SDA)
kit = ServoKit(channels=16, i2c=i2c, address=ADDR)
s = kit.servo[CHANNEL]
s.actuation_range = 180
s.set_pulse_width_range(MIN_US, MAX_US)

def go(angle):
    s.angle = angle; time.sleep(0.6)

if __name__ == "__main__":
    go(CENTER)       # центр
    go(CENTER-20)    # в одну сторону
    go(CENTER+20)    # в іншу
    go(CENTER)       # назад у центр
