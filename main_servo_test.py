from servo import Servo
import time
import numpy as np

#define output pins
GPIO_SERVO_0_PIN = 11
GPIO_SERVO_1_PIN = 12

#initialize servos
servo_0 = Servo()
servo_1 = Servo()

#attach servos to selected pins
servo_0.attach_pin(GPIO_SERVO_0_PIN)
servo_1.attach_pin(GPIO_SERVO_1_PIN)

#running the motors
input_generator = 0

try:
    while input_generator < 50:
        servo_0.set_angle(np.sin(input_generator)*100)
        servo_1.set_angle(np.cos(input_generator)*100)

        input_generator += 0.2
        time.sleep(0.5)
finally:
    #disconnect the motors
    servo_0.disconnect()
    servo_1.disconnect()
