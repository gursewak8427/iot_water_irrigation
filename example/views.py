from dataclasses import fields
from http.client import HTTPResponse
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.core.serializers import serialize
from .models import ApiTestModel
import pyrebase

import os

# Iot APIs
import json
import pandas as pd
from tensorflow import keras 
from keras.models import model_from_json
import requests, json
from datetime import datetime


config = {
   "apiKey": "AIzaSyBIEbp43zf8ZSfSsHVBs82RsrDtxJ61YFA",
    "authDomain": "iot-water-irrigation-system.firebaseapp.com",
    "projectId": "iot-water-irrigation-system",
    "storageBucket": "iot-water-irrigation-system.appspot.com",
    "messagingSenderId": "886856412095",
    "appId": "1:886856412095:web:ff6743272dc570101fcf0a",
    "measurementId": "G-34XQEXSHJ3",
    "databaseURL": "https://iot-water-irrigation-system-default-rtdb.firebaseio.com/",
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

# # Create your views here.
# def index(request) :
#     # q = ApiTestModel.objects.all();
#     # data = serialize('json',q, fields=("title"))
#     name = db.child("data").child("name").get().val();
#     return HttpResponse(name)

def index(request) :
    script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
    # inputs from database
    input_city = db.child("data").child("city").get().val();
    input_cropStage = db.child("data").child("cropStage").get().val();
    input_cropType = db.child("data").child("cropType").get().val();
    input_soilMoisture = db.child("data").child("soilMoisture").get().val();
    input_soilType = db.child("data").child("soilType").get().val();
    input_soilMoisture = int(input_soilMoisture)
    #................load ANN model.........................
    json_file = open(script_dir + "/model2.json", 'r')
    loaded_model_json = json_file.read() 
    json_file.close()
    loaded_model = model_from_json(loaded_model_json)
    # load weights into new model
    loaded_model.load_weights(script_dir + "/model2.h5")
    print("Loaded model from disk")
    city=input_city
    API_KEY = "e5eacbd0bf06d6b63bbef51659e1bbed"
    # upadting the URL
    burl = "https://api.openweathermap.org/data/2.5/forecast?"
    CITY1 = city
    nurl = burl + "q=" + CITY1+"&units=metric" + "&appid=" + API_KEY
    res=requests.get(nurl)
    data1=res.json()
    df=pd.json_normalize(data1['list'])
    df['city']=data1['city']['name']
    #with all data
    df['Dates'] = pd.to_datetime(df['dt_txt']).dt.date
    df['Time'] = pd.to_datetime(df['dt_txt']).dt.time

    sand_infodb=pd.read_excel(script_dir + "/sand_info.xlsx",sheet_name="Sand_info")
    crop_infodb=pd.read_excel(script_dir + "/sand_info.xlsx",sheet_name="Crop_Coff")
    root_db=pd.read_excel(script_dir + "/sand_info.xlsx",sheet_name="Root Depth")

    fc=sand_infodb['Field_Capacity'][8]
    Critical_moisture=80/100*fc
    fg=-1
    ET_coef=0
    cr=input_cropType
    for i in crop_infodb.index:
        if cr==crop_infodb['Crop'][i]:
            print("yes we find")
    fg=i
    stage=input_cropStage
    if stage==1:
        ET_coef=crop_infodb['kc_ini'][fg]
    elif stage==2:
        ET_coef=crop_infodb['kc_mid'][fg]
    elif stage==3:
        ET_coef=crop_infodb['kc_end'][fg]
    
    root_depth=crop_infodb['Height(m)'][fg]*100
    soil_moisture=input_soilMoisture

    X_test=pd.DataFrame()
    X_test['Temp']=df['main.temp']
    X_test['Tmin']=df['main.temp_min']
    X_test['Tmax']=df['main.temp_max']
    X_test['Cloudiness']=df['clouds.all']
    X_test['Humidity']=df['main.humidity']
    X_test['windsp']=df['wind.speed']

    prediction = loaded_model.predict(X_test)
    df['ET']=prediction
    df_set=set(df['Dates'])
    tdf=df.groupby(['Dates']).agg({'main.temp':'mean','main.temp_min':'min','main.temp_max':'max','clouds.all': 'mean',
                                'main.humidity':'mean','wind.speed':'mean','main.pressure':'mean','ET':'mean'})
    tdf['Dates']=sorted(list(df_set))
    print(ET_coef)
    tdf['ETc']=tdf['ET']*ET_coef
    tdf['new_col']=""
    tdf['decision']=""
    print(tdf)
    print("root")
    print(root_depth)
    r=soil_moisture-100*(tdf['ETc'][0]/root_depth)
    for i in tdf.index:
        tdf['new_col'][i]=r
        r=r-100*(tdf['ETc'][i]/root_depth)

    for k in tdf.index:
        if Critical_moisture>=tdf['new_col'][k]:
            s='True'
            tdf['decision'][k]=s
        else:
            s='False'
            tdf['decision'][k]=s
    
    print(tdf)
    # print(tdf['Dates'])
    # print(tdf['main.temp'])
    # print(len(tdf['Dates']))
    # print(tdf['Dates'][0])

    tempArr = tdf['main.temp']
    minTempArr = tdf['main.temp_min']
    maxTempArr = tdf['main.temp_max']
    cloudsArr = tdf['clouds.all']
    humidityArr = tdf['main.humidity']
    windArr = tdf['wind.speed']
    pressureArr = tdf['main.pressure']
    etArr = tdf['ET']
    datesArr = tdf['Dates']
    EtcArr = tdf['ETc']
    newColArr = tdf['new_col']
    decisionArr = tdf['decision']

    # update all decisions to the database
    db.child("data").child("forCasting").update({
        "0" : {
            "0" : str(datesArr[0].strftime("%d/%m/%Y")),
            "1" : str(tempArr[0]),
            "2" : str(minTempArr[0]),
            "3" : str(maxTempArr[0]),
            "4" : str(cloudsArr[0]),
            "5" : str(humidityArr[0]),
            "6" : str(windArr[0]),
            "7" : str(pressureArr[0]),
            "8" : str(etArr[0]),
            "9" : str(EtcArr[0]),
            "10" : str(newColArr[0]),
            "11" : str(decisionArr[0]),
        },
        "1" : {
            "0" : str(datesArr[1].strftime("%d/%m/%Y")),
            "1" : str(tempArr[1]),
            "2" : str(minTempArr[1]),
            "3" : str(maxTempArr[1]),
            "4" : str(cloudsArr[1]),
            "5" : str(humidityArr[1]),
            "6" : str(windArr[1]),
            "7" : str(pressureArr[1]),
            "8" : str(etArr[1]),
            "9" : str(EtcArr[1]),
            "10" : str(newColArr[1]),
            "11" : str(decisionArr[1]),
        },
        "2" : {
            "0" : str(datesArr[2].strftime("%d/%m/%Y")),
            "1" : str(tempArr[2]),
            "2" : str(minTempArr[2]),
            "3" : str(maxTempArr[2]),
            "4" : str(cloudsArr[2]),
            "5" : str(humidityArr[2]),
            "6" : str(windArr[2]),
            "7" : str(pressureArr[2]),
            "8" : str(etArr[2]),
            "9" : str(EtcArr[2]),
            "10" : str(newColArr[2]),
            "11" : str(decisionArr[2]),
        },
        "3" : {
            "0" : str(datesArr[3].strftime("%d/%m/%Y")),
            "1" : str(tempArr[3]),
            "2" : str(minTempArr[3]),
            "3" : str(maxTempArr[3]),
            "4" : str(cloudsArr[3]),
            "5" : str(humidityArr[3]),
            "6" : str(windArr[3]),
            "7" : str(pressureArr[3]),
            "8" : str(etArr[3]),
            "9" : str(EtcArr[3]),
            "10" : str(newColArr[3]),
            "11" : str(decisionArr[3]),
        },
        "4" : {
            "0" : str(datesArr[4].strftime("%d/%m/%Y")),
            "1" : str(tempArr[4]),
            "2" : str(minTempArr[4]),
            "3" : str(maxTempArr[4]),
            "4" : str(cloudsArr[4]),
            "5" : str(humidityArr[4]),
            "6" : str(windArr[4]),
            "7" : str(pressureArr[4]),
            "8" : str(etArr[4]),
            "9" : str(EtcArr[4]),
            "10" : str(newColArr[4]),
            "11" : str(decisionArr[4]),
        },
        "5" : {
            "0" : str(datesArr[5].strftime("%d/%m/%Y")),
            "1" : str(tempArr[5]),
            "2" : str(minTempArr[5]),
            "3" : str(maxTempArr[5]),
            "4" : str(cloudsArr[5]),
            "5" : str(humidityArr[5]),
            "6" : str(windArr[5]),
            "7" : str(pressureArr[5]),
            "8" : str(etArr[5]),
            "9" : str(EtcArr[5]),
            "10" : str(newColArr[5]),
            "11" : str(decisionArr[5]),
        },
    })


    # THIS FOLLOWING CODE HAVE ERROR... SHOULD BE REMOVED AND ITS ALTERNATIVE IS WRITTEN ABOVE

    # rm=[]
    # ETcr=[]
    # ETcr=tdf['ET']
    # r=soil_moisture-100*(ETcr[0]/root_depth)
    # j=0
    # for i in ETcr:  
    #     rm.append(r)
    #     r=r-100*(ETcr[j]/root_depth)
    #     j=j+1
    # tdf['ETc']=tdf['ET']*ET_coef
    # m=[]
    # f=0
    
    # for k in tdf['nd']:
    #     if Critical_moisture>=k:    
    #         s='y'
    #         m.append(s)
    #     else:
    #         s='n'
    #         m.append(s)
    #     f=f+1 
    # tdf['decision']=m

    return HttpResponse("Data Updated to Database")
