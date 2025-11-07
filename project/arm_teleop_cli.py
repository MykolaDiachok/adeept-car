#!/usr/bin/env python3
import sys, termios, tty, select, time
from arm import Arm

JOINT_ORDER = ["gripper", "shoulder", "base", "wrist"]

def get_key(timeout=0.05):
    dr, _, _ = select.select([sys.stdin], [], [], timeout)
    if not dr: return None
    ch1 = sys.stdin.read(1)
    if ch1 == '\x1b':
        if select.select([sys.stdin], [], [], 0.0005)[0]:
            ch2 = sys.stdin.read(1)
            if ch2 == '[' and select.select([sys.stdin], [], [], 0.0005)[0]:
                return 'ESC[' + sys.stdin.read(1)
        return 'ESC'
    return ch1

def main():
    arm = Arm()
    arm.center()
    sel = 2  # стартово керуватимемо "base"
    step = 5.0

    print("Arm Teleop: 1=gripper 2=shoulder 3=base 4=wrist | ←/→ або A/D: рух | C=center | [ / ]: step | S=save offsets | Q=quit")
    old = termios.tcgetattr(sys.stdin.fileno())
    try:
        tty.setraw(sys.stdin.fileno())
        delta = { j:0.0 for j in JOINT_ORDER }  # відносний кут кожного

        while True:
            key = get_key(0.05)
            if key:
                low = key.lower()
                if low == 'q': break
                elif low == '1': sel = 0
                elif low == '2': sel = 1
                elif low == '3': sel = 2
                elif low == '4': sel = 3
                elif low in ('c',):
                    for j in JOINT_ORDER: delta[j]=0.0
                    arm.center()
                elif low in ('[',): step = max(1.0, step-1.0); print(f"\nstep={step}")
                elif low in (']',): step = min(20.0, step+1.0); print(f"\nstep={step}")
                elif low in ('s',): arm.save_offsets(); print("\nOffsets saved.")
                elif low in ('a','esc[D'):  # вліво/менше
                    j = JOINT_ORDER[sel]
                    delta[j] -= step
                    arm.set_joint(j, delta[j])
                elif low in ('d','esc[C'):  # вправо/більше
                    j = JOINT_ORDER[sel]
                    delta[j] += step
                    arm.set_joint(j, delta[j])

            # невеликий рендер статусу
            sys.stdout.write(f"\rSelected: {JOINT_ORDER[sel]:>8} | step={step:>4.0f} | " +
                             " ".join([f"{j[:3]}={delta[j]:>5.1f}" for j in JOINT_ORDER]))
            sys.stdout.flush()
            time.sleep(0.02)

    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old)
        arm.center()

if __name__ == "__main__":
    main()
