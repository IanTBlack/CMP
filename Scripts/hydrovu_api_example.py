#Description: Functions for requesting the last week of salinity and temperature data from each sensor from HydroVu.
#Author: Ian Black (blackia@oregonstate.edu)
#Date: 2020-02-06

import math, json, datetime
import pandas as pd
import matplotlib.pyplot as plt, matplotlib.dates as mdates
from pandas.io.json import json_normalize
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

client_id = ''  #ID created via Manage API Credentials.
client_secret = ''  #Secret created via Manage API Credentials.
user = ''  #HydroVu username/email.
pw = ''  #HydroVu password.

oauth = OAuth2Session(client=LegacyApplicationClient(client_id=client_id))  #Create an OAuth2 session.
token = oauth.fetch_token(token_url='https://www.hydrovu.com/public-api/oauth/token', username=user, password=pw, client_id=client_id, client_secret=client_secret)  #Handshake with HydroVu API with credentials.

def get_variables(oauth): #Returns a dataframe of all variable ids and units that HydroVu can contain.
    var_r = oauth.get('https://www.hydrovu.com/public-api/v1/sispec/friendlynames')
    var_data = var_r.json()  #Jsonize data.
    var_data = json.dumps(var_data)  #Dump it.
    var_df = pd.read_json(var_data)  #Read it into a Pandas dataframe. This would appear to be a dumbed down version of how json_normalize works.
    var_df['parameter_id'] = var_df.index #Assign index.
    var_df['variable'] = var_df.parameters  #Rename the column.
    var_df = var_df[['parameter_id','variable','units']] #Clean up the dataframe.
    var_df = var_df.reset_index(drop = True)  #Reset the index.
    print(var_df)
    return var_df
    
def get_locs(oauth):  #Returns the locations of the data producing instruments that are attached to your HydroVu account.
    loc_r = oauth.get('https://www.hydrovu.com/public-api/v1/locations/list')
    loc_data = loc_r.json()
    loc_df = json_normalize(loc_data)  #Open this to view ids.
    
    
    #You will need to change how the ID is identified based on your platform.
    id3ft = loc_df['id'].loc[loc_df['name'].str.contains('3ft')].iloc[0]  #Based on the name assigned in HydroVu, find the id.
    id7ft = loc_df['id'].loc[loc_df['name'].str.contains('7ft')].iloc[0]
    id11ft = loc_df['id'].loc[loc_df['name'].str.contains('11ft')].iloc[0]
    idcube = loc_df['id'].loc[loc_df['name'].str.contains('Cube')].iloc[0]
    
    
    
    return id3ft,id7ft,id11ft,idcube


def get_last_week(oauth,loc_id): #Calculates the timeframe for the last week and requests each hours worth of data. Returns salinity and temperature data as dataframes.
    seconds_per_hour = 3600
    init = math.floor((datetime.datetime(2019,1,3) - datetime.datetime(1970,1,1)).total_seconds())  #Testing on the station started on 2019-01-03. Get that date in seconds since 1970-01-01
    today = math.floor((datetime.datetime.now() - datetime.datetime(1970,1,1)).total_seconds())  #Get the current time in seconds since 1970-01-01.
    week = math.floor(((datetime.datetime.now() - datetime.datetime(1970,1,1)) - datetime.timedelta(days=7)).total_seconds()) #Compute the timestamp for a week ago.
    temperature = pd.DataFrame()  #Create a holder array.
    salinity = pd.DataFrame()
    for i in range(week,today,int(seconds_per_hour)): #Request the last 7 days of data at hour intervals.
        r = oauth.get('https://www.hydrovu.com/public-api/v1/locations/' + str(loc_id) + '/data?startTime=' + str(i) + '&endTime=' + str(i + seconds_per_hour * 2) , headers={'Authorization': token})
        data = r.json() #Jsonize data.
        parameters = json_normalize(data['parameters'],sep = ',')  #Pull out parameters.
        sdf = parameters.loc[parameters['parameterId'] == '12']  #Parameter ID 12 is salinity.
        sdf = sdf.reset_index(drop = True)  #Reset the index.
        sdf = json_normalize(sdf['readings'][0],sep =',')  #Pull the readings out.
        salinity = pd.concat([salinity,sdf]) #Concatenate data with the previous loop.
        tdf = parameters.loc[parameters['parameterId'] == '1']  #Parameter ID 1 is temperature.
        tdf = tdf.reset_index(drop = True)
        tdf = json_normalize(tdf['readings'][0],sep =',')
        temperature = pd.concat([temperature,tdf])
        print(i) #Print the day number so that we know data is being concatenated.
    salinity = salinity.drop_duplicates()  #Drop duplicate data if it exists.
    salinity.timestamp = pd.to_datetime(salinity.timestamp,unit = 's',origin = 'unix')  #Convert the time to something understandable.
    salinity = salinity.sort_values(by='timestamp')
    salinity = salinity.reset_index(drop = True)

    temperature = temperature.drop_duplicates() 
    temperature.timestamp = pd.to_datetime(temperature.timestamp,unit = 's',origin = 'unix')
    temperature = temperature.sort_values(by='timestamp')
    temperature = temperature.reset_index(drop = True)
    return salinity,temperature

id3ft,id7ft,id11ft,idcube = get_locs(oauth)  #Get the ids.
sft3,tft3 = get_last_week(oauth,id3ft)  #Request the last week of data for the sensor at 3ft.
sft7,tft7 = get_last_week(oauth,id7ft)  #Request the last week of data for the sensor at 7ft.
sft11,tft11 = get_last_week(oauth,id11ft)  #Request the last week of data for the sensor at 11ft.

fig,ax = plt.subplots(2,1,figsize=(20,14))  #Create a fig with two stacked subplots.
fmt = mdates.DateFormatter('%m/%d/%y')  #Formatter for x axis.
ax[0].plot(sft3.timestamp,sft3.value,color = 'r',label = '3ft')
ax[0].plot(sft7.timestamp,sft7.value,color = 'b',label = '7ft')
ax[0].plot(sft11.timestamp,sft11.value,color = 'k',label = '11ft')
ax[0].legend(loc='upper left')
ax[0].set_ylabel('Salinity (PSU)')
ax[0].xaxis.set_major_formatter(fmt)

ax[1].plot(tft3.timestamp,tft3.value,color = 'r',label = '3ft')
ax[1].plot(tft7.timestamp,tft7.value,color = 'b',label = '7ft')
ax[1].plot(tft11.timestamp,tft11.value,color = 'k',label = '11ft')
ax[1].legend(loc='upper left')
ax[1].set_ylabel('Temperature (degC)')
ax[1].xaxis.set_major_formatter(fmt)
fig.savefig('data.png',orientation = 'landscape')