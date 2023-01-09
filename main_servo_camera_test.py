from servo import Servo
from camera import Camera
import cv2


def main():
    #define output pins
    GPIO_SERVO_0_PIN = 32 #  bottom motor, green jumper
    GPIO_SERVO_1_PIN = 33 #  right motor, red jumper

    #define track range file path:
    TRACK_RANGES_FILE_PATH = "trackbar_settings.json"


    try:
        #initialize servos
        servo_0 = Servo()
        servo_1 = Servo()

        #attach servos to selected pins
        servo_0.attach_pin(GPIO_SERVO_0_PIN)
        servo_1.attach_pin(GPIO_SERVO_1_PIN)

        servo_0.set_offset(0)
        servo_1.set_offset(0)

        #starting camera
        cam = Camera()
        cam.set_track_ranges(TRACK_RANGES_FILE_PATH)

        #create position control window
        cv2.namedWindow("orientation")
        cv2.resizeWindow("orientation",640,240)
        
        def set_servo_0(val):
            # x orientation needs to be flipped before sending to check
            servo_0.set_angle(-2*val+100)
        def set_servo_1(val):
            servo_1.set_angle(2*val-100)
        
        cv2.createTrackbar("X","orientation",50,100,set_servo_0)
        cv2.createTrackbar("Y","orientation",50,100,set_servo_1)

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