from servo import Servo
from camera import Camera
from pid import PID
import time
import numpy as np
import cv2


def main():
    #define output pins
    GPIO_SERVO_0_PIN = 11 #  bottom motor, green jumper
    GPIO_SERVO_1_PIN = 12 #  right motor, red jumper

    #define track range file path:
    TRACK_RANGES_FILE_PATH = "trackbar_settings.json"

    try:
        #initialize servos
        servo_0 = Servo()
        servo_1 = Servo()

        #attach servos to selected pins
        servo_0.attach_pin(GPIO_SERVO_0_PIN)
        servo_1.attach_pin(GPIO_SERVO_1_PIN)

        #starting camera
        cam = Camera()
        cam.set_track_ranges(TRACK_RANGES_FILE_PATH)

        #cropping the work area
        cam.find_platform()

    # running the process
        while True:
            cam.get_ball_position()
            cam.show_camera_output()
            if cv2.waitKey(1) & 0xFF is ord('q'):
                break
                
    finally:
        #disconnect the motors
        cv2.destroyAllWindows()
        servo_0.disconnect()
        servo_1.disconnect()

 
if __name__ == '__main__':
    main()