#!/usr/bin/env python3
# /home/mykodia/car/server/steering.py
import time, board, busio
from adafruit_servokit import ServoKit

PCA_ADDR        = 0x40
STEER_CHANNEL   = 0        # ← твій канал
ACTUATION_RANGE = 180
MIN_US, MAX_US  = 500, 2500   # якщо серво дзижчить — звузь діапазон
CENTER_ANGLE    = 90
OFFSET_DEG      = 0         # підкрутиш після пробігу
LEFT_MAX        = 35         # вліво  (відносно центру)
RIGHT_MAX       = 35         # вправо (відносно центру)

i2c = busio.I2C(board.SCL, board.SDA)
kit = ServoKit(channels=16, i2c=i2c, address=PCA_ADDR)

s = kit.servo[STEER_CHANNEL]
s.actuation_range = ACTUATION_RANGE
s.set_pulse_width_range(MIN_US, MAX_US)

def _clamp(x, lo, hi): return lo if x < lo else hi if x > hi else x

def steer_set(delta_deg: float):
    """delta_deg: -ліво, +вправо (відносно центру)"""
    a = _clamp(delta_deg, -LEFT_MAX, RIGHT_MAX)
    target = _clamp(CENTER_ANGLE + OFFSET_DEG + a, 0, ACTUATION_RANGE)
    s.angle = target

def center():          steer_set(0)
def steer_left(deg=20):  steer_set(-abs(deg))
def steer_right(deg=20): steer_set(+abs(deg))

if __name__ == "__main__":
    try:
        print("Center"); center(); time.sleep(2.0)
        print("Left");   steer_left(35); time.sleep(5.0)
        print("Right");  steer_right(35); time.sleep(5.0)
        print("Center"); center(); time.sleep(0.8)
    finally:
        center()
        pass
