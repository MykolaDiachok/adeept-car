#!/usr/bin/env python3
from picamera2 import Picamera2
from libcamera import Transform
from datetime import datetime
import time

cam = Picamera2()
cfg = cam.create_still_configuration(
    main={"size": (1280, 720)},
    transform=Transform(hflip=1, vflip=1)  # змінюй 0/1 за потреби
)
cam.configure(cfg)
cam.start()
time.sleep(0.8)  # дати AE/AWB стабілізуватись

path = f"/home/mykodia/car/server/images/photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
cam.capture_file(path)
cam.stop()
print("Saved:", path)