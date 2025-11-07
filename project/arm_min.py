#!/usr/bin/env python3
import time, board, busio
from adafruit_servokit import ServoKit

ADDR = 0x40
MIN_US, MAX_US = 600, 2400  # центр ≈1500us
CENTER = 90

JOINTS = {
    "gripper":  0,  # щупальці
    "shoulder": 1,  # плече
    "base":     2,  # поворот
    "wrist":    4,  # кисть
}

# Обережні межі (потім звузиш/підженеш під механіку)
LIMITS = {
    "gripper":  (60, 120),   # 60=закрито, 120=відкрито (приклад)
    "shoulder": (15, 165),
    "base":     (0, 180),
    "wrist":    (10, 170),
}

# Офсети (у градусах) для кожного суглоба: додаються до CENTER
OFFSETS = {
    "gripper":  0,
    "shoulder": 0,
    "base":    52,   # <<< ТВОЄ: база зсунуто на -30°
    "wrist":    0,
}

i2c = busio.I2C(board.SCL, board.SDA)
kit = ServoKit(channels=16, i2c=i2c, address=ADDR)

for name, ch in JOINTS.items():
    s = kit.servo[ch]
    s.actuation_range = 180
    s.set_pulse_width_range(MIN_US, MAX_US)

def clamp(x, lo, hi): return lo if x < lo else hi if x > hi else x

def set_joint(name: str, delta_from_center: float, wait: float = 0.0):
    """
    delta_from_center: відносно CENTER (від’ємне — вниз/ліво, додатне — вгору/право).
    ФАКТИЧНИЙ кут = CENTER + OFFSETS[name] + delta_from_center, обмежений LIMITS[name].
    """
    ch = JOINTS[name]
    lo, hi = LIMITS[name]
    target = CENTER + OFFSETS.get(name, 0) + delta_from_center
    target = clamp(target, lo, hi)
    kit.servo[ch].angle = target
    if wait: time.sleep(wait)

def center_all():
    for j in JOINTS:
        set_joint(j, 0)
    time.sleep(0.4)

def gripper_open():  set_joint("gripper",  +30, 0.3)  # піджени при потребі
def gripper_close(): set_joint("gripper",  -30, 0.3)

if __name__ == "__main__":
    # Швидкий самотест
    center_all()  # тепер "центр" бази вже з урахуванням OFFSETS["base"] = -30
    set_joint("base", +20, 0.5); set_joint("base", -20, 0.5); set_joint("base", 0, 0.3)
    set_joint("shoulder", +15, 0.5); set_joint("shoulder", -10, 0.5); set_joint("shoulder", 0, 0.3)
    set_joint("wrist", +15, 0.5); set_joint("wrist", -15, 0.5); set_joint("wrist", 0, 0.3)
    gripper_open(); gripper_close()
    center_all()
