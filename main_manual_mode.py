
import asyncio
from servo import Servo
from camera import Camera
from pid import PID
from event_hub import publish_event
from datetime import datetime
import numpy as np
import pandas as pd
import time
import json
import cv2


async def main():
    #define output pins
    GPIO_SERVO_0_PIN = 32 #  bottom motor, green jumper
    GPIO_SERVO_1_PIN = 33 #  right motor, red jumper

    #define file paths:
    TRACK_RANGES_FILE_PATH = "trackbar_settings.json"
    PID_PARAMETERS_FILE_PATH  = "PID_parameters.json"
    #HISTORICAL_DATA_FILE_PATH = "historical_data.csv"

    NAME = "Lucas A. Rodrigues"

    try:
        #initialize servos
        servo_0 = Servo()
        servo_1 = Servo()

        #attach servos to selected pins
        servo_0.attach_pin(GPIO_SERVO_0_PIN)
        servo_1.attach_pin(GPIO_SERVO_1_PIN)

        servo_0.set_offset(0)
        servo_1.set_offset(0)


        servo_0.set_offset(0)
        servo_1.set_offset(0)


        #initialize K values:
        with open(PID_PARAMETERS_FILE_PATH,'rb') as fp:
            k_values = json.load(fp)
        #Creating the PID controllers (dynamically):

        #open local historical database:
        #history_df = pd.read_csv(HISTORICAL_DATA_FILE_PATH)
        
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

        cv2.createTrackbar("Gain - X direction","Platform parameters control",100,500,set_Kp_X)
        cv2.createTrackbar("Integrator - X direction","Platform parameters control",0,100,set_Ki_X)
        cv2.createTrackbar("Speed compensation - X direction","Platform parameters control",0,100,set_Kd_X)
        cv2.createTrackbar("Gain - Y direction","Platform parameters control",100,500,set_Kp_Y)
        cv2.createTrackbar("Integrator - Y direction","Platform parameters control",0,100,set_Ki_Y)
        cv2.createTrackbar("Speed compensation - Y direction","Platform parameters control",0,100,set_Kd_Y)

        #starting camera
        cam = Camera()
        cam.set_track_ranges(TRACK_RANGES_FILE_PATH)


        #cropping the work area
        cam.find_platform()
        print(f"platform_coords:{cam.platform_coords}")

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
        # running the process
        while True:
            if hasattr(cam,"ball_position"):
                print(f"current ball status:{cam.ball_in_area}. ball position:{cam.ball_position}", end='\r')
            else:
                print(f"current ball status:{cam.ball_in_area}. ball position: None", end='\r')
            if cv2.waitKey(1) & 0xFF is ord('q'):
                break
            cam.get_ball_position()
            cam.show_camera_output()
            start_balance = hasattr(cam, 'error_x') and hasattr(cam, 'error_y') and cam.ball_in_area and balance_ready
            if start_balance:
                trial_number += 1
                print(f"starting balance. Trial #{trial_number}")
            while start_balance:
                cam.get_ball_position()
                cam.show_camera_output()

                if not cam.ball_in_area:
                    balance_ready = start_balance = False
                    result = max_settling_time_seconds/t *5000
                    print(f"Trial #{trial_number} failed. Settling time: {result}")
                    update_PID(PID_dict,'X') 
                    update_PID(PID_dict,'Y') 
                    check_save = input("save result to cloud (y/n)? ")
                    if check_save.lower()=='y':
                        event_hub_status = await push_data_to_event_hub(NAME,False,k_values,result) 
                        if event_hub_status:
                            print("data sucessfully published to the cloud.")
                        else:
                            print('error writing data to the cloud.')
                            print(event_hub_status)
                        check_save ='n'
                    else:
                        print('event ignored.')
                        
                    

                t = time.perf_counter_ns()/1e9 - start_time
                MV_x = -PID_dict['X'].send([t,cam.ball_position[0],SP[0]]) # X orientation is inverted
                servo_0.set_angle(MV_x)
                
                MV_y = PID_dict['Y'].send([t,cam.ball_position[1],SP[1]]) 
                servo_1.set_angle(MV_y)
                if t > max_settling_time_seconds:
                    balance_ready = start_balance = False
                    position_error = np.sqrt((cam.ball_position[0]-SP[0])**2+(cam.ball_position[1]-SP[1])**2)
                    result = max_settling_time_seconds + position_error**2
                    print(f"Trial #{trial_number} finished. Settling time: {result}")
                    update_PID(PID_dict,'X') 
                    update_PID(PID_dict,'Y') 
                    check_save = input("save result to cloud (y/n)? ")
                    if check_save.lower()=='y':
                        event_hub_status = await push_data_to_event_hub(NAME,True,k_values,result) 
                        if event_hub_status:
                            print("data sucessfully published to the cloud.")
                        else:
                            print('error writing data to the cloud.')
                            print(event_hub_status)
                        check_save ='n'
                    else:
                        print('event ignored.')
                    

                absolute_error = np.sqrt((cam.error_x-prev_error_x)**2 + (cam.error_y-prev_error_y)**2)
                if absolute_error < error_thresh:
                    if (t -error_thresh_timer) > min_stop_time_seconds:
                        balance_ready = start_balance = False
                        position_error = np.sqrt((cam.ball_position[0]-SP[0])**2+(cam.ball_position[1]-SP[1])**2)
                        result = t + position_error
                        print(f"Trial #{trial_number} finished. Settling time: {result}")
                        update_PID(PID_dict,'X') 
                        update_PID(PID_dict,'Y') 
                        check_save = input("save result to cloud (y/n)? ")
                        if check_save.lower()=='y':
                            event_hub_status = await push_data_to_event_hub(NAME,True,k_values,result) 
                            if event_hub_status:
                                print("data sucessfully published to the cloud.")
                            else:
                                print('error writing data to the cloud.')
                                print(event_hub_status)
                            check_save ='n'
                        else:
                            print('event ignored.')
                    
                        
                else:
                    error_thresh_timer = time.perf_counter_ns()/1e9 - start_time
                    prev_error_x = cam.error_x
                    prev_error_y = cam.error_y
                
                if cv2.waitKey(1) & 0xFF is ord('q'):
                    balance_ready = start_balance = False
            
            if not cam.ball_in_area:
                start_time = time.perf_counter_ns()/1e9
                error_thresh_timer = time.perf_counter_ns()/1e9 - start_time
                if not balance_ready:
                    servo_0.set_angle(0,timeout_seconds=1)
                    servo_1.set_angle(0,timeout_seconds=1)
                    print("table ready.")
                balance_ready = True

            cam.show_camera_output()
            if cv2.waitKey(1) & 0xFF is ord('q'):
                break
                
    finally:
        #disconnect the motors
        cv2.destroyAllWindows()
        servo_0.disconnect()
        servo_1.disconnect()

        #save historical_data:
        #history_df.to_csv(HISTORICAL_DATA_FILE_PATH,index=False)

def append_historical_data(history_df,NAME,success,k_values,settling_time)->pd.DataFrame:
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
                            "settling_time":[settling_time]
                        }
    return pd.concat([

                        history_df,
                        pd.DataFrame(result_json)
                    ], ignore_index=True)
async def push_data_to_event_hub(NAME,success,k_values,settling_time)->bool:
    try:
        result_json = {
                                "TS":str(datetime.utcnow()),
                                "name":NAME,
                                "sucess":success,
                                "kp_x":k_values['X']['Kp'],
                                "ki_x":k_values['X']['Ki'],
                                "kd_x":k_values['X']['Kd'],
                                "kp_y":k_values['Y']['Kp'],
                                "ki_y":k_values['Y']['Ki'],
                                "kd_y":k_values['Y']['Kd'],
                                "settling_time":settling_time
                            }
        await publish_event(result_json)
        return True
    except Exception as e:
        print(f"error found. Description: {str(e)}")
        return False
    
loop = asyncio.get_event_loop()
loop.run_until_complete(main())

# if __name__ == '__main__':
#     main()