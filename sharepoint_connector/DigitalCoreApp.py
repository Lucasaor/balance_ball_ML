import requests
import logging as log
from logging.handlers import RotatingFileHandler
import pandas as pd
import json
import time
from datetime import datetime
import configparser
from bs4 import BeautifulSoup
from csv import DictWriter

def read_File_Config(config):
    try:
        config.read('config.ini')
        filenameLog = 'log.log'

        app_log = log.getLogger()
        my_handler = RotatingFileHandler(filenameLog, mode='a', maxBytes=5*1024*1024, backupCount=1, encoding=None, delay=0)
        my_handler.setFormatter(log.Formatter('[%(asctime)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        app_log.addHandler(my_handler)

        log.basicConfig(filename=f'{filenameLog}', format='[%(asctime)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        return True   
    except Exception  as ex:    
        log.warning('ERROR during configuration app. Exception: {0}'.format(ex.args[0]))
        return False


def setup_Collector(config):
    try:        
        client_sp = {
            'client_id': config['SHAREPOINT_SOURCE']['client_id'],
            'client_secret': config['SHAREPOINT_SOURCE']['client_secret'],
            'tenant': config['SHAREPOINT_SOURCE']['tenant'],
            'url_site_base': config['SHAREPOINT_SOURCE']['url_site_base'],
            'url_domain': config['SHAREPOINT_SOURCE']['url_domain'],
            'sharepoint_list_name': config['SHAREPOINT_SOURCE']['sharepoint_list_name'],
            'access_token': None
        }

        return client_sp

    except Exception  as ex:
        log.warning('Failed to setup Service. Exception: {}'.format(ex.args[0]))
        return None


def get_token_sp(client_sp):
    try:
        url = "https://accounts.accesscontrol.windows.net/" + client_sp['tenant'] + "/tokens/OAuth/2/"

        payload = {
            'grant_type':'client_credentials',
            'client_id':client_sp['client_id'] + '@' + client_sp['tenant'],
            'client_secret':client_sp['client_secret'],
            'resource':'00000003-0000-0ff1-ce00-000000000000/'+client_sp['url_domain']+'@'+client_sp['tenant']
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded;odata=verbos',
        }

        response = requests.request("GET", url, headers=headers, data=payload, timeout= (30, 30))

        if response.status_code == 200:
            return json.loads(response.text)['access_token']
        else:
            log.warning('Not possible to get token. Status Code: {}'.format(response.status_code))
            return None

    except Exception as exec:
        log.warning('Failure to get token. Exception: {}'.format(exec.args[0]))
        return None


def get_list_items_sp(client_sp):

    try:
        sharepoint_list = None
        
        url = f"https://{client_sp['url_domain']}{client_sp['url_site_base']}/_api/Web/Lists/getbytitle('{client_sp['sharepoint_list_name']}')/items"
        
        payload={}
        headers = {
        'Content-Type': 'application/json;odata=verbose',
        'Authorization': f'Bearer {client_sp["access_token"]}'
        }

        response = requests.request("GET", url, headers=headers, data=payload, timeout= (30, 120))

        if response.status_code == 401:
            client_sp["access_token"] = get_token_sp(client_sp)

            if client_sp["access_token"] != None:
                headers = {
                'Content-Type': 'application/json;odata=verbose',
                'Authorization': f'Bearer {client_sp["access_token"]}'
                }
                response = requests.request("GET", url, headers=headers, data=payload, timeout= (30, 120))
                
            else:
                log.warning('Not possible to get SP list without access_token')
                return pd.DataFrame()

        if response.status_code == 200:
            sharepoint_list = BeautifulSoup(response.text, 'xml')

        if sharepoint_list != None:
            return dataframe_sp(sharepoint_list.find_all('entry')) 

        else:
            log.warning('Not possible to get SP list. response.status_code: {}'.format(response.status_code))     
            return pd.DataFrame()

    except Exception as exec:
        log.warning('Failure to get list items SP. Exception: {}'.format(exec.args[0]))
        return pd.DataFrame()


def dataframe_sp(items_sp):

    try:

        data_item = [[line.find('Created').text,                
                line.find('User').text,
                line.find('GainX').text,
                line.find('GainY').text,
                line.find('IntegratorX').text,
                line.find('IntegratorY').text,
                line.find('Speed_compensationX').text,
                line.find('Speed_compensationY').text] for line in items_sp]    

        col = ['TS', "User", "GainX", "GainY", "IntegratorX", "IntegratorY", "Speed_compensationX", "Speed_compensationY"]
        df_list = pd.DataFrame(data=data_item, columns=col)

        df_list['TS'] = df_list['TS'].astype('datetime64[ns]')

        return df_list if len(df_list) > 0 else pd.DataFrame()        

    except Exception as exc:
        log.warning('Failure to create Dataframe from sharepoint list. Exception: {}'.format(exc.args[0]))
        return pd.DataFrame()


def output_file(df_sp, df_cache):
    
    df_aux = pd.DataFrame()
    try:

        if len(df_cache) == 0:        
            if len(df_sp) > 0:
                df_aux = df_sp.query(f"TS >= '{datetime.today().date()}'")       
                
        else:
            df_aux = df_sp.query(f"TS > '{df_cache.iloc[-1,0]}'")
        
        if len(df_aux) > 0:
            with open('Output_test.csv', 'a', newline='') as csvfile:

                csvwriter = DictWriter(csvfile, fieldnames=df_cache.columns)

                for _, row in df_aux.iterrows():
                    csvwriter.writerow(dict(row))
            
            return pd.concat([df_cache, df_aux], ignore_index= True)
        else:
            return df_cache

    except Exception as exc:
        log.warning('Failure to write into file. Exception: {}'.format(exc.args[0]))
        return pd.DataFrame()     
            

def starter(client_sp, df_cache):
    try:

        if client_sp["access_token"] == None:
            client_sp["access_token"] = get_token_sp(client_sp)

        df_sp = get_list_items_sp(client_sp)   
        
        df_cache = output_file(df_sp, df_cache)
        
        return df_cache

    except Exception as exc:
        log.warning("Failed Starter. Class: {} - Args_0: {}".format(exc.__class__,exc.args[0]))
        return pd.DataFrame()
   

def main():

    print(f"SharePoint Connector started at {str(datetime.utcnow())}")
    config = configparser.ConfigParser()

    read_File_Config(config)

    log.warning('Started Service')

    parameters = setup_Collector(config)

    interval = int(config['DEFAULT']['interval'])

    if (interval <= 3) | (interval > 3600):
        interval = 3

    try:
        try:          
            df_cache = pd.read_csv("Output_test.csv")
            df_cache["TS"] = df_cache["TS"].astype('datetime64[ns]')

        except:
            log.warning("File 'Output_test.csv' not found. Creating File")
            col = ["TS", "User", "GainX", "GainY", "IntegratorX", "IntegratorY", "Speed_compensationX", "Speed_compensationY"]
            df_cache = pd.DataFrame(columns=col)
            df_cache["TS"] = df_cache["TS"].astype('datetime64[ns]')
            df_cache.to_csv('Output_test.csv', index=False)
            log.warning("File 'Output_test.csv' created.")

        while True: 
            df_cache = starter(parameters, df_cache)                

            time.sleep(interval)
            
    except Exception as exc:
        log.warning("Fatal Error. Class: {} - Args_0: {}".format(exc.__class__,exc.args[0]))


if __name__ == "__main__":
    main()
    







