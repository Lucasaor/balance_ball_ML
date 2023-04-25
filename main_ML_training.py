
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
    TRACK_RANGES_FILE_PATH = "trackbar_settings orange.json"
    PID_PARAMETERS_FILE_PATH  = "PID_parameters.json"
    HISTORICAL_DATA_FILE_PATH = "historical_data.csv"

    NAME = "ML Training"

    SAMPLES_PER_PID = 5

    try:
        #initialize servos
        servo_0 = Servo()
        servo_1 = Servo()

        #attach servos to selected pins
        servo_0.attach_pin(GPIO_SERVO_0_PIN)
        servo_1.attach_pin(GPIO_SERVO_1_PIN)

        servo_0.set_offset(0)
        servo_1.set_offset(0)

        #initialize K values:
        with open(PID_PARAMETERS_FILE_PATH,'rb') as fp:
            k_values = json.load(fp)
        #Creating the PID controllers (dynamically):

        #open local historical database:
        history_df = pd.read_csv(HISTORICAL_DATA_FILE_PATH)
        
        PID_dict = {}

               
        def update_PID(PID_dict,direction):
            PID_dict[direction] = PID(
            k_values[direction]['Kp'],
            k_values[direction]['Ki'],
            k_values[direction]['Kd'],
        )
            #initializing the controllers:
            PID_dict[direction].send(None) 

        #Initialize PID:
        Kp_range = [0.1,5] 
        Ki_range = [0.1,2]
        Kd_range = [0.15,2]

        k_values['X']['Kp'] = np.random.uniform(Kp_range[0],Kp_range[1])
        k_values['X']['Ki'] = np.random.uniform(Ki_range[0],Ki_range[1])
        k_values['X']['Kd'] = np.random.uniform(Kd_range[0],Kd_range[1])
        k_values['Y']['Kp'] = k_values['X']['Kp'] + np.random.uniform(-0.05,0.05)
        k_values['Y']['Ki'] = k_values['X']['Ki'] + np.random.uniform(-0.01,0.01)
        k_values['Y']['Kd'] = k_values['X']['Kd'] + np.random.uniform(-0.1,0.1)

        update_PID(PID_dict,'X')
        update_PID(PID_dict,'Y')
        print(f"Next PID values are: [{[k_values['X']['Kp'],k_values['X']['Ki'],k_values['X']['Kd'],k_values['Y']['Kp'],k_values['Y']['Ki'],k_values['Y']['Kd']]}] ")
        #starting camera
        cam = Camera()
        cam.set_track_ranges(TRACK_RANGES_FILE_PATH)


        #cropping the work area
        cam.find_platform()

        #setpoint for ball position (X,Y):
        SP = (200,200)
        # set initial and stop parameters:
        start_time = error_thresh_timer = time.perf_counter_ns()/1e9
        prev_error_x = 0
        prev_error_y = 0
        error_thresh = 5
        
        max_settling_time_seconds = 20
        min_stop_time_seconds = 1

        balance_ready = True
        trial_number = 0
        ball_failed = False
        # running the process
        while True:
            cam.get_ball_position()
            cam.show_camera_output()
            start_balance = hasattr(cam, 'error_x') and hasattr(cam, 'error_y') and cam.ball_in_area and balance_ready
            #print(f"balance_ready={balance_ready},start_balance={start_balance}")

            if start_balance:
                trial_number += 1
                print(f"starting balance. Trial #{trial_number}")
            while start_balance:
                cam.get_ball_position()
                cam.show_camera_output()

                t = time.perf_counter_ns()/1e9 - start_time
                if not cam.ball_in_area:
                    balance_ready = start_balance = False
                    ball_failed = True
                    result = max_settling_time_seconds/t *5000
                    print(f"Trial #{trial_number} failed. Settling time: {result}")
                    check_save = input("save result to cloud (y/n)? ")
                    if check_save.lower()=='y':
                        history_df = append_historical_data(history_df,NAME,False,k_values,result) 
                        print("data saved in data frame")
                        time.sleep(0.2)     

                    
                MV_x = -PID_dict['X'].send([t,cam.ball_position[0],SP[0]]) # X orientation is inverted
                servo_0.set_angle(MV_x)
                
                MV_y = PID_dict['Y'].send([t,cam.ball_position[1],SP[1]]) 
                servo_1.set_angle(MV_y)
                if t > max_settling_time_seconds and not ball_failed:
                    balance_ready = start_balance = False
                    position_error = np.sqrt((cam.ball_position[0]-SP[0])**2+(cam.ball_position[1]-SP[1])**2)
                    result = max_settling_time_seconds + position_error**2
                    print(f"Trial #{trial_number} finished. Settling time: {result}")
                    history_df = append_historical_data(history_df,NAME,True,k_values,result)
                    print("data saved in data frame")   
                    time.sleep(0.2)             
                    

                absolute_error = np.sqrt((cam.error_x-prev_error_x)**2 + (cam.error_y-prev_error_y)**2)
                if absolute_error < error_thresh:
                    if (t -error_thresh_timer) > min_stop_time_seconds and not ball_failed:
                        balance_ready = start_balance = False
                        position_error = np.sqrt((cam.ball_position[0]-SP[0])**2+(cam.ball_position[1]-SP[1])**2)
                        result = t + position_error
                        print(f"Trial #{trial_number} finished. Settling time: {result}")
                        history_df = append_historical_data(history_df,NAME,True,k_values,result) 
                        print("data saved in data frame")
                        time.sleep(0.2)     
                   
                        
                else:
                    error_thresh_timer = time.perf_counter_ns()/1e9 - start_time
                    prev_error_x = cam.error_x
                    prev_error_y = cam.error_y
                
                if cv2.waitKey(1) & 0xFF is ord('e'):
                    balance_ready = start_balance = False
            
            if not cam.ball_in_area:
                start_time = time.perf_counter_ns()/1e9
                error_thresh_timer = time.perf_counter_ns()/1e9 - start_time
                if not balance_ready:
                    balance_ready = True
                    ball_failed = False
                    print("reseting table...")
                    servo_0.set_angle(0,timeout_seconds=1)
                    servo_1.set_angle(0,timeout_seconds=1)
                    time.sleep(0.5)
                    print("table ready.")                  

                    k_values['X']['Kp'] = np.random.uniform(Kp_range[0],Kp_range[1])
                    k_values['X']['Ki'] = np.random.uniform(Ki_range[0],Ki_range[1])
                    k_values['X']['Kd'] = np.random.uniform(Kd_range[0],Kd_range[1])
                    k_values['Y']['Kp'] = k_values['X']['Kp'] + np.random.uniform(-0.05,0.05)
                    k_values['Y']['Ki'] = k_values['X']['Ki'] + np.random.uniform(-0.01,0.01)
                    k_values['Y']['Kd'] = k_values['X']['Kd'] + np.random.uniform(-0.1,0.1)


                    update_PID(PID_dict,'X')
                    update_PID(PID_dict,'Y')
                    print(f"Next PID values are: [{[k_values['X']['Kp'],k_values['X']['Ki'],k_values['X']['Kd'],k_values['Y']['Kp'],k_values['Y']['Ki'],k_values['Y']['Kd']]}] ")
                

            cam.show_camera_output()
            if cv2.waitKey(1) & 0xFF is ord('q'):
                break
            

    finally:
        #save historical_data:
        history_df.to_csv(HISTORICAL_DATA_FILE_PATH,index=False)
        
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