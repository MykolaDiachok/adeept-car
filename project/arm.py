#!/usr/bin/env python3
import time, json, os, math
import board, busio
from adafruit_servokit import ServoKit
from typing import Dict, Tuple

def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x

class Arm:
    """
    Контролер руки на PCA9685 (через adafruit_servokit.ServoKit).

    Кути API задаються ВІД центру:
      set_joint("base", delta) -> фактичний абсолютний кут =
        CENTER + OFFSETS["base"] + delta, далі кламп:
          - якщо enforce_limits = True -> у LIMITS["base"] (із авто-сортуванням min/max)
          - якщо enforce_limits = False -> у 0 .. joint_range["base"]

    Підтримка:
      - Пер-суглобні actuation_range (joint_range), напр. base=270/360 (якщо серво позиційне >180).
      - Збереження/завантаження OFFSETS і LIMITS у JSON.
      - Плавні пози (pose).
    """

    def __init__(
        self,
        i2c_addr: int = 0x40,
        channels: int = 16,
        center: int = 90,
        pulse_us: Tuple[int,int] = (600, 2400),   # ~1500us по центру
        default_range: int = 360,                 # базовий actuation_range, якщо не задано в joint_range
        offsets_file: str = "/home/mykodia/car/server/arm_offsets.json",
        limits_file:  str = "/home/mykodia/car/server/arm_limits.json",
    ):
        # --- канали (твоя мапа)
        self.JOINTS: Dict[str, int] = {
            "gripper":  0,  # щупальці
            "shoulder": 1,  # плече
            "base":     2,  # поворот
            "wrist":    4,  # кисть
        }

        # --- межі за замовчуванням (акуратні; перезапишемо з JSON, якщо є)
        self.LIMITS: Dict[str, Tuple[float,float]] = {
            "gripper":  (30, 150),   # приклад: 70=закрито, 115=відкрито (підіграй під свій)
            "shoulder": (25, 150),
            "base":     (0, 180),
            "wrist":    (30, 150),
        }

        # --- офсети (база як у тебе)
        self.OFFSETS: Dict[str, float] = {
            "gripper":  0.0,
            "shoulder": 0.0,
            "base":     0.0,
            "wrist":    0.0,
        }

        # --- пер-суглобні діапазони (actuation_range) у градусах
        # якщо база реально позиційна >180°, постав 270 або 360
        self.joint_range: Dict[str, int] = {
            "gripper": default_range,
            "shoulder": default_range,
            "base":     default_range,  # ← змінюй на 270/360, якщо твоє серво це підтримує
            "wrist":    default_range,
        }

        self.CENTER = float(center)
        self.PULSE_US = pulse_us
        self.offsets_file = offsets_file
        self.limits_file = limits_file
        self.enforce_limits = True  # перемикач ПЗ-обмежень

        # --- HW init
        i2c = busio.I2C(board.SCL, board.SDA)
        self.kit = ServoKit(channels=channels, i2c=i2c, address=i2c_addr)

        # --- налаштувати кожен канал
        for name, ch in self.JOINTS.items():
            s = self.kit.servo[ch]
            s.actuation_range = int(self.joint_range.get(name, default_range))
            s.set_pulse_width_range(*self.PULSE_US)

        # --- завантажити конфіги, якщо існують
        self._load_offsets_if_any()
        self._load_limits_if_any()

    # ========== I/O (JSON) ==========
    def _load_offsets_if_any(self):
        if os.path.exists(self.offsets_file):
            try:
                data = json.load(open(self.offsets_file))
                for k in self.OFFSETS:
                    if k in data: self.OFFSETS[k] = float(data[k])
            except Exception:
                pass

    def save_offsets(self):
        with open(self.offsets_file, "w") as f:
            json.dump(self.OFFSETS, f, indent=2)

    def _load_limits_if_any(self):
        if os.path.exists(self.limits_file):
            try:
                data = json.load(open(self.limits_file))
                for j in self.JOINTS:
                    if j in data and isinstance(data[j], (list, tuple)) and len(data[j]) == 2:
                        lo, hi = float(data[j][0]), float(data[j][1])
                        # трохи санітуємо, але без надмірної строгості
                        lo = clamp(lo, 0, max(self.joint_range.get(j, 180), 180))
                        hi = clamp(hi, 0, max(self.joint_range.get(j, 180), 180))
                        # авто-сортування
                        if hi < lo: lo, hi = hi, lo
                        self.LIMITS[j] = (lo, hi)
            except Exception:
                pass

    def save_limits(self):
        # авто-сортування перед збереженням
        out = {}
        for j, (lo, hi) in self.LIMITS.items():
            if hi < lo: lo, hi = hi, lo
            out[j] = [int(round(lo)), int(round(hi))]
        with open(self.limits_file, "w") as f:
            json.dump(out, f, indent=2)

    # ========== сервісні налаштування ==========
    def set_limits_enabled(self, enabled: bool):
        self.enforce_limits = bool(enabled)

    def toggle_limits(self) -> bool:
        self.enforce_limits = not self.enforce_limits
        return self.enforce_limits

    def set_offset(self, joint: str, degrees: float, save: bool = False):
        self.OFFSETS[joint] = float(degrees)
        if save: self.save_offsets()

    def set_joint_range(self, joint: str, degrees: int):
        """Змінити actuation_range конкретного суглоба (наприклад, base: 270/360)."""
        self.joint_range[joint] = int(degrees)
        ch = self.JOINTS[joint]
        self.kit.servo[ch].actuation_range = int(degrees)

    # ========== внутрішня математика ==========
    def _abs_target(self, joint: str, delta_from_center: float) -> float:
        """Обчислює абсолютний кут з урахуванням CENTER+OFFSETS і клампить:
           - у LIMITS (із авто-сортуванням), якщо enforce_limits=True;
           - у 0..joint_range[joint], якщо enforce_limits=False.
        """
        target = self.CENTER + self.OFFSETS[joint] + float(delta_from_center)
        if self.enforce_limits:
            lo, hi = self.LIMITS[joint]
            if hi < lo: lo, hi = hi, lo
            return clamp(target, lo, hi)
        # без софт-лімітів все одно тримаємося в апаратному 0..actuation_range суглоба
        return clamp(target, 0, float(self.joint_range[joint]))

    def _current_rel(self, joint: str) -> float:
        ch = self.JOINTS[joint]
        cur = self.kit.servo[ch].angle
        if cur is None:
            cur = self.CENTER + self.OFFSETS[joint]
        return cur - (self.CENTER + self.OFFSETS[joint])

    # ========== публічне керування ==========
    def set_joint(self, joint: str, delta_from_center: float, wait: float = 0.0):
        ch = self.JOINTS[joint]
        self.kit.servo[ch].angle = self._abs_target(joint, delta_from_center)
        if wait: time.sleep(wait)

    def center(self, wait_each: float = 0.0):
        for j in self.JOINTS:
            self.set_joint(j, 0.0, wait_each)

    def gripper_open(self):  self.set_joint("gripper", +30, 0.15)
    def gripper_close(self): self.set_joint("gripper", -30, 0.15)

    # ========== плавні пози ==========
    def _easing(self, x: float, mode: str) -> float:
        if mode == "linear":  return x
        if mode == "easein":  return x * x
        if mode == "easeout": return 1 - (1 - x) * (1 - x)
        if mode == "easeio":  return 0.5 - 0.5 * math.cos(math.pi * x)
        return x

    def pose(self, t: float = 0.0, steps: int = 20, easing: str = "easeio", **targets_rel):
        """Одночасний рух кількох суглобів до відносних кутів (delta від центру)."""
        if t <= 0 or steps <= 1:
            for j, v in targets_rel.items():
                self.set_joint(j, float(v))
            return
        start = { j: self._current_rel(j) for j in targets_rel.keys() }
        dt = t / steps
        for k in range(1, steps + 1):
            a = self._easing(k / steps, easing)
            for j, goal in targets_rel.items():
                val = start[j] + (float(goal) - start[j]) * a
                self.set_joint(j, val)
            time.sleep(dt)
