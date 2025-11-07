#!/usr/bin/env python3
import time
import atexit
import RPi.GPIO as GPIO

GPIO.setwarnings(False)

_initialized = False


# EN pins (PWM), IN1/IN2 pins (direction)
Motor_A_EN    = 4
Motor_B_EN    = 17

Motor_A_Pin1  = 26
Motor_A_Pin2  = 21
Motor_B_Pin1  = 27
Motor_B_Pin2  = 18  # ⚠️ не використовуй одночасно для WS2812!

Dir_forward   = 0
Dir_backward  = 1

left_forward  = Dir_forward
left_backward = Dir_backward
right_forward = Dir_forward
right_backward= Dir_backward

pwm_A = None
pwm_B = None

def motorStop():
    # викликаємо тільки коли GPIO активний
    if GPIO.getmode() is None:
        return
    GPIO.output(Motor_A_Pin1, GPIO.LOW)
    GPIO.output(Motor_A_Pin2, GPIO.LOW)
    GPIO.output(Motor_B_Pin1, GPIO.LOW)
    GPIO.output(Motor_B_Pin2, GPIO.LOW)
    GPIO.output(Motor_A_EN, GPIO.LOW)
    GPIO.output(Motor_B_EN, GPIO.LOW)

def _cleanup():
    """Безпечне завершення при виході"""
    try:
        if GPIO.getmode() is not None:   # режим виставлений
            motorStop()
            try:
                pwm_A and pwm_A.stop()
                pwm_B and pwm_B.stop()
            except Exception:
                pass
            GPIO.cleanup()
    except Exception:
        # глушимо будь-яку помилку на виході, щоб не засмічувати лог
        pass

def setup():
    global pwm_A, pwm_B, _initialized
    if _initialized:
        return
    GPIO.setmode(GPIO.BCM)
    for pin in (Motor_A_EN, Motor_B_EN, Motor_A_Pin1, Motor_A_Pin2, Motor_B_Pin1, Motor_B_Pin2):
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
    pwm_A = GPIO.PWM(Motor_A_EN, 1000); pwm_A.start(0)
    pwm_B = GPIO.PWM(Motor_B_EN, 1000); pwm_B.start(0)
    atexit.register(_cleanup)   # реєструємо після успішного setup
    _initialized = True

def _apply_motor(en_pwm, in1, in2, direction, duty):
    # direction = Dir_forward/backward ; duty=0..100
    if duty <= 0:
        GPIO.output(in1, GPIO.LOW)
        GPIO.output(in2, GPIO.LOW)
        en_pwm.ChangeDutyCycle(0)
        return
    if direction == Dir_forward:
        GPIO.output(in1, GPIO.LOW)
        GPIO.output(in2, GPIO.HIGH)
    else:
        GPIO.output(in1, GPIO.HIGH)
        GPIO.output(in2, GPIO.LOW)
    en_pwm.ChangeDutyCycle(duty)

def motor_left(status, direction, speed):
    if status == 0:
        _apply_motor(pwm_B, Motor_B_Pin1, Motor_B_Pin2, Dir_forward, 0)
    else:
        _apply_motor(pwm_B, Motor_B_Pin1, Motor_B_Pin2, direction, speed)

def motor_right(status, direction, speed):
    if status == 0:
        _apply_motor(pwm_A, Motor_A_Pin1, Motor_A_Pin2, Dir_forward, 0)
    else:
        _apply_motor(pwm_A, Motor_A_Pin1, Motor_A_Pin2, direction, speed)

def move(speed, direction, turn, radius=0.6):
    # speed: 0..100 ; radius: (0,1]
    ls = rs = speed
    if direction == 'forward':
        ld, rd = left_forward, right_forward
        if   turn == 'right': ls = int(speed*radius)
        elif turn == 'left':  rs = int(speed*radius)
    elif direction == 'backward':
        ld, rd = left_backward, right_backward
        if   turn == 'right': ls = int(speed*radius)
        elif turn == 'left':  rs = int(speed*radius)
    elif direction == 'no':
        ld, rd = left_forward, right_backward  # на місці
        if   turn == 'right':
            ls, rs = speed, speed
        elif turn == 'left':
            ld, rd = left_backward, right_forward
            ls, rs = speed, speed
        else:
            motorStop(); return
    else:
        return
    motor_left(1, ld, ls)
    motor_right(1, rd, rs)

def ramp_to(speed_target, step=5, dt=0.03):
    # плавна зміна тяги для обох моторів (вперед)
    for s in range(0, speed_target+1, step):
        motor_left(1, left_forward, s)
        motor_right(1, right_forward, s)
        time.sleep(dt)

if __name__ == "__main__":
    try:
        setup()
        speed = 50
        ramp_to(60)
        time.sleep(0.8)

        move(speed, 'forward', 'no', 1.0); time.sleep(3.0)
        move(speed, 'backward', 'no', 1.0); time.sleep(3.0)
        # move(speed, 'forward', 'right', 0.7); time.sleep(1.0)
        # move(speed, 'forward', 'left', 0.7);  time.sleep(1.0)
        # move(speed, 'backward', 'no', 0.8);   time.sleep(1.0)
        # move(speed, 'no', 'right', 0.8);      time.sleep(1.0)
        # move(speed, 'no', 'left', 0.8);       time.sleep(1.0)

        motorStop()
    except KeyboardInterrupt:
        pass
    finally:
        _cleanup()
