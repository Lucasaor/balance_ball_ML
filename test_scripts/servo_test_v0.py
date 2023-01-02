# Import libraries
import RPi.GPIO as GPIO
import time

# Set GPIO numbering mode
GPIO.setmode(GPIO.BOARD)

# pin 11 for bottom motor (0), pin 12 for right motor (1)
SELECTED_PIN = 12

GPIO.setup(SELECTED_PIN,GPIO.OUT)
servo1 = GPIO.PWM(SELECTED_PIN,50) # pin 11 for servo1, pulse 50Hz

# Start PWM running, with value of 0 (pulse off)
servo1.start(0)

# Loop to allow user to set servo angle. Try/finally allows exit
# with execution of servo.stop and GPIO cleanup :)

try:
    while True:
        #Ask user for angle and turn servo to it
        # Range for motor 0: 0-90
        # Range for motor 1: 0-90
        angle = float(input('Enter angle between 0 & 180: '))
        servo1.ChangeDutyCycle(2+(angle/18))
        time.sleep(0.5)
        servo1.ChangeDutyCycle(0)

finally:
    #Clean things up at the end
    servo1.stop()
    GPIO.cleanup()
    print("Goodbye!")
