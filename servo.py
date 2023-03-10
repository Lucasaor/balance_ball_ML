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
        angle = self.__PID_input_to_angle(input)
        if timeout_seconds is None:
            self.servo.ChangeDutyCycle(2+(angle/18))
        else:
            timer0 = time.perf_counter_ns()/1e9
            while (time.perf_counter_ns()/1e9-timer0)<timeout_seconds:
                self.servo.ChangeDutyCycle(2+(angle/18))
            self.servo.ChangeDutyCycle(0)
    
    def set_offset(self,offset=-5) -> None:
        self.offset = offset

    def disconnect(self) -> None:
        self.servo.stop()
        GPIO.cleanup()

    def __PID_input_to_angle(self,input:int) -> int:
        """Converts PID input range (-100 to 100) to angular position of servos between 0 and 90 degrees. 
        Saturates if input is out of bounds."""
        if input <-100:
            input = -100
        elif input > 100:
            input >100
        angle = 0.45*(input+100+self.offset) # expression to linear map the range
        
        return angle
        