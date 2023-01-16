import pandas as pd
from datetime import datetime
from geneticalgorithm import geneticalgorithm as ga
from pid import PID
import numpy as np
import json


def calculate_cinematics(system,time,pid,setpoint,dt,simulation_duration_seconds):
    logs = {
    'acceleration':[],
    'velocity':[],
    'position':[],
    'MV':[],
    'table_angle':[],
    'time':[],
    'error':[]
}

    for t in time:
        #calculating PID inputs:
        error = system['position'] - setpoint
        MV = pid.send([t,system['position'],setpoint])-system['offset']
        table_angle = (3/40)*(MV+100)-8-system['offset']
        #system['acceleration'] = (system["inertia"]*MV*system['input_adjustment']-system['dumping']*system['velocity']*2)/system["inertia"]
        system['acceleration'] = system["inertia"]*MV
        system["velocity"] += system['dumping']*system["acceleration"]*dt 
        system["position"] += system['input_adjustment']*system["velocity"]*dt

        logs['acceleration'].append(system['acceleration'])
        logs['velocity'].append(system['velocity'])
        logs['position'].append(system['position'])
        logs['MV'].append(MV)
        logs['table_angle'].append(table_angle)
        logs['time'].append(t)
        logs['error'].append(error)
        
    return logs

def get_settling_time(position,time,max_error=1e-3,settling_time_threshold = 1):
    relative_error = max(position)*1e3
    if type(position)==pd.Series:
        position = position.to_list()
    if type(time)==pd.Series:
        time = time.to_list()
   
       
    t_prev = time[0]

    for i,t in enumerate(time):
        if i > 0:
            relative_error = abs(position[i]-position[i-1])
        if relative_error > max_error:
            t_prev = t

        elif t-t_prev > settling_time_threshold:
            return t
    
    return t

def evaluate_PID_response(logs,setpoint,target):
    df_logs = pd.DataFrame(logs)
    
    overshoot = df_logs['position'].max()/setpoint
    peak_time = df_logs['position'].idxmax()

    settling_time = get_settling_time(df_logs.loc[peak_time:]['position'],df_logs.loc[peak_time:]['time'])

    error= df_logs['position'].iloc[-1]-setpoint

    return (overshoot-target[0])**2 + 1e1*(settling_time-target[1])**2 + error**2
    


    

def main():
    SHAREPOINT_DATA_FILE_PATH = "sharepoint_connector/Output_test.csv"

    # defining time parameters
    dt_seconds = 0.01
    simulation_duration_seconds = 14

    #creating PIDs
    PID_dict = {}

    PID_dict['X'] = PID(1,0,0)
    PID_dict['X'].send(None) 

    PID_dict['Y'] = PID(1,0,0)
    PID_dict['Y'].send(None) 

    #defining setpoint:
    SP = (200,200)

    def test_PID(X):
        system_x={
            "position":46,  # m
            "velocity":0, # m/s
            "acceleration":0,  # m/s^2
            "inertia":4.671009954467505,
            "dumping":0.8084436234411967,
            "offset":0,
            "input_adjustment":2.760671432076397
        }

        pid = PID(0.1+X[0],X[1],0.2+X[2])
        pid.send(None) 

        time = np.linspace(dt_seconds,simulation_duration_seconds,int(simulation_duration_seconds/dt_seconds)+1)
        logs = calculate_cinematics(system_x,time,pid,SP[0],dt_seconds,simulation_duration_seconds)
        return evaluate_PID_response(logs,SP[0],[1,3])



    parameters_df = pd.read_csv(SHAREPOINT_DATA_FILE_PATH)

    varbound=np.array([[0.1,0.4],[0.1,0.5],[0.18,0.5]])

    algorithm_param = {'max_num_iteration': 100,\
                    'population_size':50,\
                    'mutation_probability':0.1,\
                    'elit_ratio': 0.01,\
                    'crossover_probability': 0.5,\
                    'parents_portion': 0.3,\
                    'crossover_type':'uniform',\
                    'max_iteration_without_improv':20}

    model=ga(function=test_PID,dimension=len(varbound),variable_type='real',variable_boundaries=varbound,algorithm_parameters=algorithm_param)

    model.run()

    k_values = {
        'X':{
            "Kp":model.best_variable[0],
            "Ki":model.best_variable[1],
            "Kd":model.best_variable[2],
        },
        'Y':{
            "Kp":model.best_variable[0],
            "Ki":model.best_variable[1],
            "Kd":model.best_variable[2],
        }
    }

    TS = datetime.utcnow()
    user = "Digital Core ML"

    ML_df = pd.DataFrame({
        "TS":[TS.strftime("%Y-%m-%d %H:%M:%S")],
        "User":[user],
        "GainX":[k_values['X']['Kp']*100],
        "GainY":[k_values['Y']['Kp']*100],
        "IntegratorX":[k_values['X']['Ki']*100],
        "IntegratorY":[k_values['Y']['Ki']*100],
        "Speed_compensationX":[k_values['X']['Kd']*100],
        "Speed_compensationY":[k_values['Y']['Kd']*100]
    })

    parameters_df = pd.concat([parameters_df,ML_df],ignore_index=True)

    columns = ["TS","User","GainX","GainY","IntegratorX","IntegratorY","Speed_compensationX","Speed_compensationY"]
    parameters_df[columns].to_csv(SHAREPOINT_DATA_FILE_PATH)
    print("\n\nML datapoints sent.")

if __name__ == '__main__':
     main()
