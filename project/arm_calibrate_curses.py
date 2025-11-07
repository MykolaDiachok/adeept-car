#!/usr/bin/env python3
# /home/mykodia/car/server/arm_calibrate_curses.py
import time, json, os, curses
from arm import Arm, clamp

JOINTS = ["gripper", "shoulder", "base", "wrist"]
LIMITS_FILE  = "/home/mykodia/car/server/arm_limits.json"
OFFSETS_FILE = "/home/mykodia/car/server/arm_offsets.json"

HELP = [
    "Arm Calibrator (curses)",
    "─────────────────────────────────────────────────────────────",
    "1/2/3/4   : select joint (gripper/shoulder/base/wrist)",
    "←/→ or A/D: move selected joint (delta, deg)",
    "C         : center all (delta=0 for all)",
    ", / .     : set MIN / set MAX (absolute degrees)",
    "- / +     : change step (-1° / +1°)",
    "O / P     : adjust OFFSET (-1° / +1°) for selected joint",
    "S         : save LIMITS & OFFSETS to JSON",
    "Q         : quit",
]

def draw(stdscr, arm: Arm, sel, step, delta, limits):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # Help
    for i, line in enumerate(HELP):
        if i >= h: break
        stdscr.addstr(i, 0, line)

    row = len(HELP) + 1
    stdscr.addstr(row, 0, f"Step: {step:.0f}°   Selected: {JOINTS[sel]}   CENTER={arm.CENTER}   LIMITS={'ON' if arm.enforce_limits else 'OFF'}")
    row += 1
    stdscr.addstr(row, 0, f"OFFSETS: {arm.OFFSETS}")
    row += 2

    stdscr.addstr(row, 0, "Joint       Δ (deg)   AbsTarget   Limits [min,max]")
    row += 1
    stdscr.addstr(row, 0, "-" * 64)
    row += 1

    for j in JOINTS:
        mark = "→" if j == JOINTS[sel] else " "
        rel  = delta[j]
        abs_target = arm._abs_target(j, rel)  # CENTER + OFFSETS + rel, clamped to LIMITS
        lo, hi = limits[j]
        stdscr.addstr(row, 0, f"{mark} {j:<10} {rel:>7.1f}      {abs_target:>7.1f}     [{int(lo):>3},{int(hi):<3}]")
        row += 1

    row += 1
    stdscr.addstr(row, 0, f"Saves: limits→{LIMITS_FILE}  offsets→{OFFSETS_FILE}")
    stdscr.addstr(h-1, 0, "Press Q to quit")
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
    stdscr.timeout(50)

    arm = Arm()           # підхопить існуючі offsets/limits, якщо вже є автозавантаження
    arm.set_limits_enabled(False)
    # локальні копії меж, щоб не псувати arm поки не збережемо
    limits = { j: list(arm.LIMITS[j]) for j in JOINTS }
    delta  = { j: 0.0 for j in JOINTS }  # відносні кути для пошуку меж
    sel    = 2            # почнемо з base
    step   = 5.0

    arm.center()

    try:
        last = 0.0
        while True:
            ch = stdscr.getch()
            if ch != -1:
                # selection
                if ch in (ord('1'), ord('2'), ord('3'), ord('4')):
                    sel = int(chr(ch)) - 1

                elif ch in (ord('q'), ord('Q')):
                    break

                # move selected joint
                elif ch in (curses.KEY_LEFT, ord('a'), ord('A')):
                    j = JOINTS[sel]
                    delta[j] -= step
                    arm.set_joint(j, delta[j])

                elif ch in (curses.KEY_RIGHT, ord('d'), ord('D')):
                    j = JOINTS[sel]
                    delta[j] += step
                    arm.set_joint(j, delta[j])

                # center all
                elif ch in (ord('c'), ord('C')):
                    for j in JOINTS:
                        delta[j] = 0.0
                    arm.center()

                # step adjust
                elif ch in (ord('-'), ):
                    step = max(1.0, step - 1.0)
                elif ch in (ord('+'), ord('=')):   # '=' on many keyboards is '+'
                    step = min(20.0, step + 1.0)

                # set MIN / MAX at current absolute position
                elif ch == ord(','):
                    j = JOINTS[sel]
                    abs_now = arm._abs_target(j, delta[j])
                    limits[j][0] = int(round(abs_now))
                elif ch == ord('.'):
                    j = JOINTS[sel]
                    abs_now = arm._abs_target(j, delta[j])
                    limits[j][1] = int(round(abs_now))

                # OFFSET adjust for selected joint
                elif ch in (ord('o'), ord('O')):
                    j = JOINTS[sel]
                    arm.OFFSETS[j] -= 1.0
                    # при зміні офсету варто підправити фактичне положення до тієї ж delta
                    arm.set_joint(j, delta[j])
                elif ch in (ord('p'), ord('P')):
                    j = JOINTS[sel]
                    arm.OFFSETS[j] += 1.0
                    arm.set_joint(j, delta[j])
                elif ch in (ord('l'), ord('L')):
                    on = arm.toggle_limits()
                # save both limits & offsets
                elif ch in (ord('s'), ord('S')):
                    # впорядкуємо межі (min<=max) і трохи обіжмемо у 0..180
                    to_save_limits = {}
                    for j in JOINTS:
                        lo, hi = limits[j]
                        lo = clamp(int(lo), 0, 180)
                        hi = clamp(int(hi), 0, 180)
                        if hi < lo: lo, hi = hi, lo
                        to_save_limits[j] = [int(lo), int(hi)]
                    with open(LIMITS_FILE, "w") as f:
                        json.dump(to_save_limits, f, indent=2)

                    with open(OFFSETS_FILE, "w") as f:
                        json.dump({ j: float(arm.OFFSETS[j]) for j in JOINTS }, f, indent=2)

                    # одразу підкинемо в arm актуальні межі
                    arm.LIMITS = { j: tuple(to_save_limits[j]) for j in JOINTS }

            now = time.time()
            if now - last > 0.05:
                draw(stdscr, arm, sel, step, delta, limits)
                last = now

            time.sleep(0.01)

    finally:
        try:
            arm.center(0.0)
        except Exception:
            pass
        stdscr.keypad(False)
        curses.echo()
        curses.nocbreak()
        try:
            curses.curs_set(1)
        except curses.error:
            pass

if __name__ == "__main__":
    curses.wrapper(main)
