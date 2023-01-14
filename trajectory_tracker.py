
from servo import Servo
from camera import Camera
from pid import PID
from datetime import datetime
import numpy as np
import pandas as pd
import time
import json
import cv2


def main():
    #define output pins
    GPIO_SERVO_0_PIN = 32 #  bottom motor, green jumper
    GPIO_SERVO_1_PIN = 33 #  right motor, red jumper

    #define file paths:
    TRACK_RANGES_FILE_PATH = "trackbar_settings.json"
    PID_PARAMETERS_FILE_PATH  = "PID_parameters.json"
    TRAJECTORY_DATA_FILE_PATH = "trajectory_data.json"

    NAME = "ML Training"


    try:
        #initialize servos
        servo_0 = Servo()
        servo_1 = Servo()

        #attach servos to selected pins
        servo_0.attach_pin(GPIO_SERVO_0_PIN)
        servo_1.attach_pin(GPIO_SERVO_1_PIN)

        servo_0.set_offset(-8)
        servo_1.set_offset(10)

        #initialize K values:
        with open(PID_PARAMETERS_FILE_PATH,'rb') as fp:
            k_values = json.load(fp)
        #Creating the PID controllers (dynamically):

        
        PID_dict = {}

               
        def update_PID(PID_dict,direction):
            PID_dict[direction] = PID(
            k_values[direction]['Kp'],
            k_values[direction]['Ki'],
            k_values[direction]['Kd'],
        )
            #initializing the controllers:
            PID_dict[direction].send(None) 

        # defining trackbar functions
        def set_Kp_X(val):
            k_values['X']['Kp'] = val/100
            update_PID(PID_dict,'X')    
        def set_Ki_X(val):
            k_values['X']['Ki'] = val/100
            update_PID(PID_dict,'X')    
        def set_Kd_X(val):
            k_values['X']['Kd'] = val/100
            update_PID(PID_dict,'X')    
        def set_Kp_Y(val):
            k_values['Y']['Kp'] = val/100
            update_PID(PID_dict,'Y')    
        def set_Ki_Y(val):
            k_values['Y']['Ki'] = val/100
            update_PID(PID_dict,'Y')    
        def set_Kd_Y(val):
            k_values['Y']['Kd'] = val/100
            update_PID(PID_dict,'Y')    

        #creating PID trackbar window
        cv2.namedWindow("Platform parameters control")
        cv2.resizeWindow("Platform parameters control",640,480)

        cv2.createTrackbar("Gain - X direction","Platform parameters control",40,500,set_Kp_X)
        cv2.createTrackbar("Integrator - X direction","Platform parameters control",0,100,set_Ki_X)
        cv2.createTrackbar("Speed compensation - X direction","Platform parameters control",15,100,set_Kd_X)
        cv2.createTrackbar("Gain - Y direction","Platform parameters control",40,500,set_Kp_Y)
        cv2.createTrackbar("Integrator - Y direction","Platform parameters control",0,100,set_Ki_Y)
        cv2.createTrackbar("Speed compensation - Y direction","Platform parameters control",15,100,set_Kd_Y)

        update_PID(PID_dict,'X')
        update_PID(PID_dict,'Y')


        #starting camera
        cam = Camera()
        cam.set_track_ranges(TRACK_RANGES_FILE_PATH)


        #cropping the work area
        cam.find_platform()

        #setpoint for ball position (X,Y):
        SP = (200,200)
        
        #trajectory data
        with open(TRAJECTORY_DATA_FILE_PATH,'rb') as fp:
            trajectory_data = json.load(fp)
        
        # set initial and stop parameters:
        start_time = error_thresh_timer = time.perf_counter_ns()/1e9
        prev_error_x = 0
        prev_error_y = 0
        error_thresh = 5
        
        max_settling_time_seconds = 20
        min_stop_time_seconds = 10

        balance_ready = True
        start_key_status = False
        trial_number = 0
        ball_failed = False
        # running the process
        while True:
            cam.get_ball_position()
            cam.show_camera_output()
            start_balance = cam.ball_in_area and balance_ready and start_key_status
            #print(f"balance_ready={balance_ready},start_balance={start_balance}")

            if start_balance:
                trial_number += 1
                trial_dt = str(datetime.utcnow())
                print(f"starting balance. Trial #{trial_number}")
                trajectory_data.update({trial_dt:{
                    "X":[],
                    "Y":[],
                    "time":[],
                    "MV_X":[],
                    "MV_Y":[],
                    "SP":[SP[0],SP[1]]
                }})
            while start_balance:
                cam.get_ball_position()
                cam.show_camera_output()


                t = time.perf_counter_ns()/1e9 - start_time
                if not cam.ball_in_area:
                    balance_ready = start_balance = False
                    ball_failed = True

                    
                MV_x = -PID_dict['X'].send([t,cam.ball_position[0],SP[0]]) # X orientation is inverted
                servo_0.set_angle(MV_x)
                
                MV_y = PID_dict['Y'].send([t,cam.ball_position[1],SP[1]]) 
                servo_1.set_angle(MV_y)

                trajectory_data[trial_dt]['X'].append(cam.ball_position[0])
                trajectory_data[trial_dt]['Y'].append(cam.ball_position[1])
                trajectory_data[trial_dt]['time'].append(t)
                trajectory_data[trial_dt]['MV_X'].append(MV_x)
                trajectory_data[trial_dt]['MV_Y'].append(MV_y)

                if t > max_settling_time_seconds and not ball_failed:
                    balance_ready = start_balance = False
                    position_error = np.sqrt((cam.ball_position[0]-SP[0])**2+(cam.ball_position[1]-SP[1])**2)
                    result = max_settling_time_seconds + position_error**2
                    print(f"Trial #{trial_number} finished. Settling time: {result}")

                    time.sleep(0.2)             
                    

                absolute_error = np.sqrt((cam.error_x-prev_error_x)**2 + (cam.error_y-prev_error_y)**2)
                if absolute_error < error_thresh:
                    if (t -error_thresh_timer) > min_stop_time_seconds and not ball_failed:
                        balance_ready = start_balance = False
                        position_error = np.sqrt((cam.ball_position[0]-SP[0])**2+(cam.ball_position[1]-SP[1])**2)
                        result = t + position_error
                        print(f"Trial #{trial_number} finished. Settling time: {result}")
    

                        time.sleep(0.2)     
                   
                        
                else:
                    error_thresh_timer = time.perf_counter_ns()/1e9 - start_time
                    prev_error_x = cam.error_x
                    prev_error_y = cam.error_y
                

            
            if not cam.ball_in_area:
                start_time = time.perf_counter_ns()/1e9
                error_thresh_timer = time.perf_counter_ns()/1e9 - start_time
                if not balance_ready:
                    start_key_status = False
                    balance_ready = True
                    ball_failed = False
                    print("reseting table...")
                    servo_0.set_angle(0,timeout_seconds=1)
                    servo_1.set_angle(0,timeout_seconds=1)
                    time.sleep(0.5)
                    print("table ready.")                  

                    update_PID(PID_dict,'X')
                    update_PID(PID_dict,'Y')
                

            cam.show_camera_output()
            key = cv2.waitKey(33)
            if key==27:    # Esc key to stop
                break
            elif key==32:
                start_key_status = True # else print its value
                print("balance authorized.")
            

    finally:
        #save trjectory data:
        with open(TRAJECTORY_DATA_FILE_PATH,'w') as fp:
            json.dump(trajectory_data,fp)
        
        #disconnect the motors
        cv2.destroyAllWindows()
        servo_0.disconnect()
        servo_1.disconnect()


def append_historical_data(history_df,NAME,success,k_values,score)->pd.DataFrame:
    result_json = {
                            "TS":[datetime.utcnow()],
                            "name":[NAME],
                            "sucess":[success],
                            "kp_x":[k_values['X']['Kp']],
                            "ki_x":[k_values['X']['Ki']],
                            "kd_x":[k_values['X']['Kd']],
                            "kp_y":[k_values['Y']['Kp']],
                            "ki_y":[k_values['Y']['Ki']],
                            "kd_y":[k_values['Y']['Kd']],
                            "score":[score]
                        }
    return pd.concat([

                        history_df,
                        pd.DataFrame(result_json)
                    ], ignore_index=True)



if __name__ == '__main__':
     main()