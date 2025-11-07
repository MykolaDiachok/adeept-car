#!/usr/bin/env python3
# /home/mykodia/car/server/arm_teleop_cli_curses.py
import time
import curses
from arm import Arm

JOINTS = ["gripper", "shoulder", "base", "wrist"]

HELP_TEXT = [
    "Arm Teleop (curses)",
    "------------------------------------------",
    "1/2/3/4 : select joint (gripper/shoulder/base/wrist)",
    "←/→  or  A/D : move selected joint (-/+) by step (deg)",
    "C : center all joints (delta = 0)",
    "[ / ] : decrease / increase step",
    "S : save OFFSETS to JSON",
    "Q : quit",
]

def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v

def draw_ui(stdscr, sel_idx, step, delta_map, arm):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # Title & help
    for i, line in enumerate(HELP_TEXT):
        if i >= h: break
        stdscr.addstr(i, 0, line)

    row = len(HELP_TEXT) + 1
    stdscr.addstr(row, 0, f"Step: {step:>4.0f} deg   Selected: {JOINTS[sel_idx]}")
    row += 2

    # Current OFFSETS & CENTER
    stdscr.addstr(row, 0, f"CENTER: {arm.CENTER}   OFFSETS: {arm.OFFSETS}")
    row += 2

    # Per-joint table
    stdscr.addstr(row, 0, "Joint      Delta(°)   AbsTarget(°)   Limits")
    row += 1
    stdscr.addstr(row, 0, "-" * 60)
    row += 1
    for j in JOINTS:
        rel = delta_map[j]
        abs_target = arm._abs_target(j, rel)  # uses CENTER+OFFSETS and clamps to LIMITS
        lo, hi = arm.LIMITS[j]
        mark = "←" if j == JOINTS[sel_idx] else " "
        stdscr.addstr(row, 0, f"{mark} {j:<9} {rel:>8.1f}      {abs_target:>7.1f}     [{lo:>3},{hi:<3}]")
        row += 1

    # Footer
    stdscr.addstr(h - 1, 0, "Press Q to quit")
    stdscr.refresh()

def main(stdscr):
    # Curses init
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    stdscr.nodelay(True)
    stdscr.timeout(50)  # ms

    # Arm init
    arm = Arm()
    arm.center()

    # State
    sel = 2              # start with 'base'
    step = 5.0           # degrees per nudge
    delta = {j: 0.0 for j in JOINTS}

    last_render = 0.0

    try:
        while True:
            ch = stdscr.getch()

            if ch != -1:
                # Normalize to lowercase char where applicable
                low = None
                if 0 <= ch < 256:
                    low = chr(ch).lower()

                if ch in (ord('q'), ord('Q')):  # quit
                    break

                elif ch in (ord('1'), ord('2'), ord('3'), ord('4')):
                    sel = int(chr(ch)) - 1

                elif ch in (curses.KEY_LEFT, ord('a'), ord('A')):
                    j = JOINTS[sel]
                    delta[j] -= step
                    arm.set_joint(j, delta[j])

                elif ch in (curses.KEY_RIGHT, ord('d'), ord('D')):
                    j = JOINTS[sel]
                    delta[j] += step
                    arm.set_joint(j, delta[j])

                elif ch in (ord('c'), ord('C')):
                    for j in JOINTS:
                        delta[j] = 0.0
                    arm.center()

                elif ch == ord('['):
                    step = max(1.0, step - 1.0)

                elif ch == ord(']'):
                    step = min(20.0, step + 1.0)

                elif ch in (ord('s'), ord('S')):
                    arm.save_offsets()

            # periodic redraw (to stay responsive)
            now = time.time()
            if now - last_render > 0.05:
                draw_ui(stdscr, sel, step, delta, arm)
                last_render = now

            time.sleep(0.01)

    finally:
        try:
            arm.center(0.0)
        except Exception:
            pass
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
