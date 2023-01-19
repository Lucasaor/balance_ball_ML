
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


def read_sharepoint_csv_file(SHAREPOINT_DATA_FILE_PATH:str,previous_TS)->pd.DataFrame:
    sharepoint_df = pd.read_csv(SHAREPOINT_DATA_FILE_PATH)
    sharepoint_df['TS'] = pd.to_datetime(sharepoint_df['TS'])

    if len(sharepoint_df)>0:
        current_df = sharepoint_df.query("TS > @previous_TS")
    else:
        current_df = pd.DataFrame(columns=["TS","User","GainX","GainY","IntegratorX","IntegratorY","Speed_compensationX","Speed_compensationY"])
    

    return current_df


async def main():
    #define output pins
    GPIO_SERVO_0_PIN = 32 #  bottom motor"," green jumper
    GPIO_SERVO_1_PIN = 33 #  right motor, red jumper

    #define file paths:
    TRACK_RANGES_FILE_PATH = "trackbar_settings.json"
    PID_PARAMETERS_FILE_PATH  = "PID_parameters.json"
    SHAREPOINT_DATA_FILE_PATH = "sharepoint_connector/Output_test.csv"
    previous_TS = datetime.utcnow()
    print("""
______ _       _ _        _   _____                  _     _            ___  ___ _      ______                     
|  _  (_)     (_) |      | | /  __ \                | |   (_)           |  \/  || |     |  _  \                    
| | | |_  __ _ _| |_ __ _| | | /  \/ ___  _ __ ___  | |    ___   _____  | .  . || |     | | | |___ _ __ ___   ___  
| | | | |/ _` | | __/ _` | | | |    / _ \| '__/ _ \ | |   | \ \ / / _ \ | |\/| || |     | | | / _ \ '_ ` _ \ / _ \ 
| |/ /| | (_| | | || (_| | | | \__/\ (_) | | |  __/ | |___| |\ V /  __/ | |  | || |____ | |/ /  __/ | | | | | (_) |
|___/ |_|\__, |_|\__\__,_|_|  \____/\___/|_|  \___| \_____/_| \_/ \___| \_|  |_/\_____/ |___/ \___|_| |_| |_|\___/ 
          __/ |                                                                                                    
         |___/                                                                                                     
""")
    


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

       
        PID_dict = {}

        #initialize PIDs
        PID_dict['X'] = PID(1,0,0)
        PID_dict['X'].send(None) 
        PID_dict['Y'] = PID(1,0,0)
        PID_dict['Y'].send(None) 
        
        def update_PID(PID_dict,direction):
            PID_dict[direction] = PID(
            k_values[direction]['Kp'],
            k_values[direction]['Ki'],
            k_values[direction]['Kd'],
        )
            #initializing the controllers:
            PID_dict[direction].send(None)

        def update_K_values(current_df):
            if len(current_df)>0:
                k_values['X']['Kp'] = current_df['GainX'].iloc[0]/100
                k_values['X']['Ki'] = current_df['IntegratorX'].iloc[0]/100
                k_values['X']['Kd'] = current_df['Speed_compensationX'].iloc[0]/100
                
                k_values['Y']['Kp'] = current_df['GainY'].iloc[0]/100
                k_values['Y']['Ki'] = current_df['IntegratorY'].iloc[0]/100
                k_values['Y']['Kd'] = current_df['Speed_compensationY'].iloc[0]/100

                return current_df.drop(current_df.index[0])

        #starting camera
        cam = Camera()
        cam.set_track_ranges(TRACK_RANGES_FILE_PATH)


        #cropping the work area
        cam.find_platform()

        #setpoint for ball position (X,Y):
        SP = (200,200)
        # set initial and stop parameters:
        start_time = error_thresh_timer = sharepoint_timer = time.perf_counter_ns()/1e9
        prev_error_x = 0
        prev_error_y = 0
        error_thresh = 5
        
        max_settling_time_seconds = 20
        min_stop_time_seconds = 1
        start_key_status = False
        ball_failed = False

        sharepoint_file_update_interval_seconds = 1
        balance_ready = True
        trial_number = 0
        parameters_df = pd.DataFrame()
        # running the process
        while True:
            cam.get_ball_position()
            cam.show_camera_output()

            if (time.perf_counter_ns()/1e9-sharepoint_timer) >sharepoint_file_update_interval_seconds:
                parameters_df = read_sharepoint_csv_file(SHAREPOINT_DATA_FILE_PATH,previous_TS)
                sharepoint_timer = time.perf_counter_ns()/1e9
            
            if len(parameters_df) > 0:
                print("New table parameters received.")
                current_user = parameters_df['User'].iloc[0]
                previous_TS = parameters_df['TS'].iloc[0]
                print(f"user: {current_user}")
                print(f"Gain(X): {parameters_df['GainX'].iloc[0]},Error Compensation X: {parameters_df['IntegratorX'].iloc[0]},Speed compensation X: {parameters_df['Speed_compensationX'].iloc[0]}")
                print(f"Gain(Y): {parameters_df['GainY'].iloc[0]},Error Compensation Y: {parameters_df['IntegratorY'].iloc[0]},Speed compensation Y: {parameters_df['Speed_compensationY'].iloc[0]}")

                # Update parameters_Df and K_values for next PID config
                parameters_df = update_K_values(parameters_df)
                update_PID(PID_dict,'X') 
                update_PID(PID_dict,'Y') 
                start_key_status = True
                print("\nwaiting for ball...")

            start_balance = cam.ball_in_area and balance_ready and start_key_status
            if start_balance:
                trial_number += 1
                print(f"starting balance. Trial #{trial_number}")
            while start_balance:
                cam.get_ball_position()
                cam.show_camera_output()

                if not cam.ball_in_area:
                    ball_failed = True
                    balance_ready = start_balance = False
                    result = max_settling_time_seconds/t *5000
                    print(f"Trial #{trial_number} failed. Settling time: {result}")
                    update_PID(PID_dict,'X') 
                    update_PID(PID_dict,'Y') 
                    check_save = input("save result to cloud (y/n)? ")
                    if check_save.lower()=='y':
                        event_hub_status = await push_data_to_event_hub(current_user,False,k_values,result) 
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
                if t > max_settling_time_seconds and not ball_failed:
                    balance_ready = start_balance = False
                    position_error = np.sqrt((cam.ball_position[0]-SP[0])**2+(cam.ball_position[1]-SP[1])**2)
                    result = max_settling_time_seconds + position_error**2
                    print(f"Trial #{trial_number} finished. Settling time: {result}")
                    update_PID(PID_dict,'X') 
                    update_PID(PID_dict,'Y') 
                    check_save = input("save result to cloud (y/n)? ")
                    if check_save.lower()=='y':
                        event_hub_status = await push_data_to_event_hub(current_user,True,k_values,result) 
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
                    if (t -error_thresh_timer) > min_stop_time_seconds and not ball_failed:
                        balance_ready = start_balance = False
                        position_error = np.sqrt((cam.ball_position[0]-SP[0])**2+(cam.ball_position[1]-SP[1])**2)
                        result = t + position_error
                        print(f"Trial #{trial_number} finished. Settling time: {result}")
                        update_PID(PID_dict,'X') 
                        update_PID(PID_dict,'Y') 
                        check_save = input("save result to cloud (y/n)? ")
                        if check_save.lower()=='y':
                            event_hub_status = await push_data_to_event_hub(current_user,True,k_values,result) 
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
                    update_PID(PID_dict,'X') 
                    update_PID(PID_dict,'Y') 
                    print("table ready.")
                balance_ready = True
                ball_failed = False

            cam.show_camera_output()
            key = cv2.waitKey(33)
            if key==27:    # Esc key to stop
                break
            # elif key==32:
            #     start_key_status = True # else print its value
            #     print("balance authorized.")
                
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
                                "kp_x":k_values['X']['Kp']*100,
                                "ki_x":k_values['X']['Ki']*100,
                                "kd_x":k_values['X']['Kd']*100,
                                "kp_y":k_values['Y']['Kp']*100,
                                "ki_y":k_values['Y']['Ki']*100,
                                "kd_y":k_values['Y']['Kd']*100,
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