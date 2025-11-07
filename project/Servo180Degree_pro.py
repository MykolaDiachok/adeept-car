#!/usr/bin/env python3
import time
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

I2C_ADDR      = 0x40
FREQUENCY_HZ  = 50
MIN_US, MAX_US = 500, 2400   # для MG996R це ок; центр ≈1500us
CHANNEL        = 0           # змініть на свій канал (0..15)

# --- HW init ---
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=I2C_ADDR)
pca.frequency = FREQUENCY_HZ

# Створюємо ОДИН раз: далі тільки .angle
srv = servo.Servo(
    pca.channels[CHANNEL],
    min_pulse=MIN_US, max_pulse=MAX_US,
    actuation_range=180,
)

def sweep(ch=srv, delay=0.01):
    # 0 -> 180
    for a in range(0, 181, 1):
        ch.angle = a
        time.sleep(delay)
    time.sleep(0.3)
    # 180 -> 0
    for a in range(180, -1, -1):
        ch.angle = a
        time.sleep(delay)
    time.sleep(0.3)

def center(ch=srv, angle=90):
    ch.angle = angle

if __name__ == "__main__":
    try:
        print(f"[i2c=0x{I2C_ADDR:02x}] channel={CHANNEL} freq={FREQUENCY_HZ}Hz, pulses={MIN_US}-{MAX_US}us")
        center()
        while True:
            sweep(delay=0.01)  # змініть delay=0.02 якщо б’є по живленню
    except KeyboardInterrupt:
        print("Ctrl+C -> center & deinit")
        center()
    finally:
        pca.deinit()
