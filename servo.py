import RPi.GPIO as GPIO
import time

class Servo():
    '''
    Servo class developed to control the servo motors connected to the GPIO ports of a raspberry pi.
    '''
    def __init__(self) -> None:
        # Set GPIO numbering modepython
        GPIO.setmode(GPIO.BOARD)

    def attach_pin(self,pin,frequency=50) -> None:
        GPIO.setup(pin,GPIO.OUT)
        self.servo = GPIO.PWM(pin,frequency) 
        self.servo.start(0)

    def set_angle(self,input,timeout_seconds = None) -> None:
        angle = self.__angle_to_pid_input(input)
        if type(timeout_seconds)!=float or type(timeout_seconds)!=int:
            timeout_seconds = None
        if timeout_seconds is None:
            self.servo.ChangeDutyCycle(2+(angle/18))
        else:
            timer0 = time.perf_counter()
            while (time.perf_counter()-timer0)<timeout_seconds:
                self.servo.ChangeDutyCycle(2+(angle/18))
            self.servo.ChangeDutyCycle(0)
    
    def disconnect(self) -> None:
        self.servo.stop()
        GPIO.cleanup()

    def __angle_to_pid_input(self,input:int) -> int:
        if input <-100:
            input = -100
        elif input > 100:
            input >100
        angle = 0.9*(input+100)
        
        return angle
        