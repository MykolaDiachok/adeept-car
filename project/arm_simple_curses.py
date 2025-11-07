#!/usr/bin/env python3
# /home/mykodia/car/server/arm_simple_curses.py
import time
import curses
import board, busio
from adafruit_servokit import ServoKit

# === НАЛАШТУВАННЯ ===
I2C_ADDR = 0x40
CHANNELS = 16
ACTUATION_RANGE = 360   # можна поставити 270/360 для окремих серв, якщо вони позиційні >180

# Мапа твоїх серв: назва -> канал PCA9685
JOINTS = [
    ("gripper", 0),
    ("shoulder", 1),
    ("base",     2),
    ("wrist",    4),
]

HELP = [
    "arm_simple_curses — просте керування сервами (без софт-лімітів)",
    "──────────────────────────────────────────────────────────────",
    "1/2/3/4  : вибір сервопривода (gripper/shoulder/base/wrist)",
    "← / →    : зменшити / збільшити кут на step",
    "↑ / ↓    : змінити step (+1 / -1)",
    "[ / ]    : також змінити step (-1 / +1)",
    "C        : центр усіх (90°)",
    "0 / 9    : встановити 0° / 90° для вибраного",
    "=        : встановити 360° для вибраного (якщо дозволяє actuation_range)",
    "Q        : вихід",
]

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def draw(stdscr, sel_idx, step, angles, act_range):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # Help
    for i, line in enumerate(HELP):
        if i >= h: break
        stdscr.addstr(i, 0, line)

    row = len(HELP) + 1
    stdscr.addstr(row, 0, f"step: {step:.0f}°   actuation_range: {act_range}°   (без софт-лімітів, лише 0..range)")
    row += 2

    stdscr.addstr(row, 0, " Joint      Ch   Angle")
    row += 1
    stdscr.addstr(row, 0, "-" * 28)
    row += 1

    for idx, (name, ch) in enumerate(JOINTS):
        mark = "→" if idx == sel_idx else " "
        ang = angles[ch]
        stdscr.addstr(row, 0, f"{mark} {name:<10} {ch:>2}   {ang:>6.1f}°")
        row += 1

    stdscr.addstr(h-1, 0, "Q=quit")
    stdscr.refresh()

def main(stdscr):
    # curses init
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    stdscr.nodelay(True)
    stdscr.timeout(50)  # ms

    # Servo init
    i2c = busio.I2C(board.SCL, board.SDA)
    kit = ServoKit(channels=CHANNELS, i2c=i2c, address=I2C_ADDR)

    # Поставимо actuation_range на всі канали з карти JOINTS
    for _, ch in JOINTS:
        s = kit.servo[ch]
        s.actuation_range = ACTUATION_RANGE
        s.set_pulse_width_range(600, 2400)

    # Початкові кути: 90°
    angles = { ch: 90.0 for _, ch in JOINTS }
    for _, ch in JOINTS:
        kit.servo[ch].angle = angles[ch]
        time.sleep(0.02)

    sel = 2   # базово керуємо "base"
    step = 5.0
    last = 0.0

    try:
        while True:
            ch = stdscr.getch()
            if ch != -1:
                if ch in (ord('q'), ord('Q')):
                    break
                elif ch in (ord('1'), ord('2'), ord('3'), ord('4')):
                    sel = int(chr(ch)) - 1
                elif ch == curses.KEY_LEFT:
                    name, chan = JOINTS[sel]
                    angles[chan] = clamp(angles[chan] - step, 0, ACTUATION_RANGE)
                    kit.servo[chan].angle = angles[chan]
                elif ch == curses.KEY_RIGHT:
                    name, chan = JOINTS[sel]
                    angles[chan] = clamp(angles[chan] + step, 0, ACTUATION_RANGE)
                    kit.servo[chan].angle = angles[chan]
                elif ch == curses.KEY_UP or ch == ord(']'):
                    step = min(30.0, step + 1.0)
                elif ch == curses.KEY_DOWN or ch == ord('['):
                    step = max(1.0, step - 1.0)
                elif ch in (ord('c'), ord('C')):
                    for _, chan in JOINTS:
                        angles[chan] = 90.0
                        kit.servo[chan].angle = angles[chan]
                        time.sleep(0.01)
                elif ch == ord('0'):
                    name, chan = JOINTS[sel]
                    angles[chan] = 0.0
                    kit.servo[chan].angle = angles[chan]
                elif ch == ord('9'):
                    name, chan = JOINTS[sel]
                    angles[chan] = 90.0
                    kit.servo[chan].angle = angles[chan]
                elif ch in (ord('='), ord('+')):  # на багатьох клавіатурах '=' це '+'
                    name, chan = JOINTS[sel]
                    angles[chan] = float(ACTUATION_RANGE)
                    kit.servo[chan].angle = angles[chan]

            now = time.time()
            if now - last > 0.05:
                draw(stdscr, sel, step, angles, ACTUATION_RANGE)
                last = now

            time.sleep(0.01)

    finally:
        # Повернемо все в центр на виході (можеш прибрати, якщо не треба)
        for _, chan in JOINTS:
            try:
                kit.servo[chan].angle = 90.0
            except Exception:
                pass
            time.sleep(0.01)
        # restore terminal
        stdscr.keypad(False)
        curses.echo()
        curses.nocbreak()
        try:
            curses.curs_set(1)
        except curses.error:
            pass

if __name__ == "__main__":
    curses.wrapper(main)
