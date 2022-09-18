from dataclasses import fields
from http.client import HTTPResponse
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.core.serializers import serialize
from .models import ApiTestModel
import pyrebase


# Iot APIs

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
    #................load ANN model.........................

    json_file = open("D:/PythonIshpreetSir/IoT/IoT/content/model2.json", 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    loaded_model = model_from_json(loaded_model_json)
    # load weights into new model
    loaded_model.load_weights("D:/PythonIshpreetSir/IoT/IoT/content/model2.h5")
    print("Loaded model from disk")
    
    city="mohali"
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

    sand_infodb=pd.read_excel("D:/PythonIshpreetSir/IoT/IoT/content/sand_info.xlsx",sheet_name="Sand_info")
    crop_infodb=pd.read_excel("D:/PythonIshpreetSir/IoT/IoT/content/sand_info.xlsx",sheet_name="Crop_Coff")
    root_db=pd.read_excel("D:/PythonIshpreetSir/IoT/IoT/content/sand_info.xlsx",sheet_name="Root Depth")

    fc=sand_infodb['Field_Capacity'][8]
    Critical_moisture=80/100*fc
    fg=-1
    ET_coef=0
    cr="oil"
    for i in crop_infodb.index:
        if cr==crop_infodb['Crop'][i]:
            print("yes we find")
    fg=i
    stage=1
    if stage==1:
        ET_coef=crop_infodb['kc_ini'][fg]
    elif stage==2:
        ET_coef=crop_infodb['kc_mid'][fg]
    elif stage==3:
        ET_coef=crop_infodb['kc_end'][fg]
    
    root_depth=crop_infodb['Height(m)'][fg]*100
    soil_moisture=20

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
    
    tdf['ETc']=tdf['ET']*ET_coef
    return HttpResponse(tdf)
    # rm=[]
    # ETcr=[]
    # ETcr=tdf['ET']
    # r=soil_moisture-100*(ETcr[0]/root_depth)
    # j=0;
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

