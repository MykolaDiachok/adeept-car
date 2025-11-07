#!/usr/bin/env python3
import time, curses
from move import setup, motor_left, motor_right, motorStop, left_forward, right_forward, left_backward, right_backward, Dir_forward, Dir_backward
from steering import steer_set, center

SPEED_STEP = 10      # крок швидкості %
TURN_STEP  = 5       # крок керма, градуси
MAX_SPEED  = 100
MAX_TURN   = 35      # збігається з LEFT_MAX/RIGHT_MAX у steering.py

def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v

def apply_drive(speed, turn_deg):
    # turn_deg: -вліво, +вправо
    steer_set(turn_deg)
    if speed > 0:
        motor_left(1, left_forward,  speed)
        motor_right(1, right_forward, speed)
    elif speed < 0:
        motor_left(1, left_backward,  -speed)
        motor_right(1, right_backward, -speed)
    else:
        motorStop()

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)

    setup()
    center()

    speed = 0       # -100..+100
    turn  = 0       # -MAX_TURN..+MAX_TURN

    try:
        while True:
            ch = stdscr.getch()
            if ch != -1:
                if ch in (ord('q'), ord('Q')):
                    break
                elif ch in (ord('w'), curses.KEY_UP):
                    speed = clamp(speed + SPEED_STEP, -MAX_SPEED, MAX_SPEED)
                elif ch in (ord('s'), curses.KEY_DOWN):
                    speed = clamp(speed - SPEED_STEP, -MAX_SPEED, MAX_SPEED)
                elif ch in (ord('a'), curses.KEY_LEFT):
                    turn  = clamp(turn - TURN_STEP, -MAX_TURN, MAX_TURN)
                elif ch in (ord('d'), curses.KEY_RIGHT):
                    turn  = clamp(turn + TURN_STEP, -MAX_TURN, MAX_TURN)
                elif ch == ord(' '):
                    speed = 0
                elif ch in (ord('c'), ord('C')):
                    turn = 0

            apply_drive(speed, turn)

            stdscr.erase()
            stdscr.addstr(0, 0, "Teleop: W/S speed, A/D steer, SPACE stop, C center, Q quit")
            stdscr.addstr(1, 0, f"Speed: {speed:>4}   Turn: {turn:>4} deg")
            stdscr.refresh()

            time.sleep(0.02)
    finally:
        motorStop()
        center()

if __name__ == "__main__":
    curses.wrapper(main)
