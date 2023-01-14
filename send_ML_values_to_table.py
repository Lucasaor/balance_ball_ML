import pandas as pd
from datetime import datetime
import json

PID_PARAMETERS_FILE_PATH  = "PID_parameters.json"
SHAREPOINT_DATA_FILE_PATH = "sharepoint_connector/Output_test.csv"

parameters_df = pd.read_csv(SHAREPOINT_DATA_FILE_PATH)

with open(PID_PARAMETERS_FILE_PATH,"rb") as fp:
    k_values = json.load(fp)

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

parameters_df.to_csv(SHAREPOINT_DATA_FILE_PATH)
print("ML datapoints sent.")
