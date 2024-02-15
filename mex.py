#!/usr/bin/python3

##################################
#             V1.1               #
# MEX-Daten in ioBroker einlesen #
#    Benötigt den MQTT Adapter   #
#    (C) 2024 Daniel Luginbühl   #
##################################

########################### WICHTIGE INFOS ###############################
#### Dieses Script per Cronjob alle 2 bis 4 Stunden ausführen         ####

#### Im ioBroker ist der MQTT Broker/Client Adapter zu installieren   ####
#### Einstellungen:                                                   ####
####    IP: Server/Broker                                             ####
####    Authentifizierungseinstellungen: Benutzer/Passwort definieren ####

#### Zu installieren (auf Host, wo dieses Script läuft):              ####
####    sudo apt install python3-requests                             ####
####    pip install paho-mqtt                                         ####
##########################################################################

#### Hier Einträge anpassen! ####
username = "AAAAA@gmail.com"    # Deine Email Adresse bei Heizoel24
passwort = "BBBBBBBBB"          # Dein Passwort bei Heizoel24

broker_address = "192.168.1.50" # ioBroker IP, auf welchem der MQTT (Server) Adapter läuft
mqtt_user = "uuuuuu"            # ioBroker MQTT User     (in Authentifizierungseinstellungen definiert)
mqtt_pass = "pppppp"            # ioBroker MQTT Passwort (in Authentifizierungseinstellungen definiert)

debug = False                   # True = Debug Infos auf die Konsole

##########################################################################

import requests
import time
import json
import paho.mqtt.client as mqtt

def mqtt_send(client, topic, wert):
    client.publish("MEX/" + topic, wert)

def login():
    if debug:
        print('Login in...')
    global session_id
    global logged_in
    url = "https://api.heizoel24.de/app/api/app/Login"
    newHeaders = {'Content-type': 'application/json'}
    reply = requests.post(url, json = { "Password" : passwort, "Username" : username}, headers=newHeaders)

    if reply.status_code == 200:
        if debug:
            print("Login OK")
        reply_json = json.loads(reply.text)
        if reply_json['ResultCode'] == 0:
            session_id = reply_json['SessionId']
            if debug:
                print('Session ID: ' + session_id)
            logged_in = True
    else:
        print('Login nicht OK! Heizoel24 Login Status Code: ' + str(reply.status_code))

def mex():  
    login()
    if debug:
        print('Refresh sensor data cache...')
    url = 'https://api.heizoel24.de/app/api/app/GetDashboardData/'+ session_id + '/1/1/False'
    reply = requests.get(url)     
    if reply.status_code == 200:
        if debug:
            print("Daten wurden empfangen")
        sensor_data = reply
    else:
        if debug:
            print('Heizoel24 GetDashboardData Status Code: ' + str(reply.status_code))
        sensor_data = "error"   # Fehler. Keine Daten empfangen.
    return sensor_data

def main():
    daten = mex()
    if daten == "error":
        print("Fehler. Keine Daten empfangen.")
        return
    daten = daten.json()
    if debug:
        print(daten)

    topic1 = ['SensorId', 'IsMain', 'CurrentVolumePercentage', 'CurrentVolume', 'NotifyAtLowLevel', 'NotifyAtAlmostEmptyLevel', 'NotificationsEnabled', 'Usage', 'RemainsUntil', 'MaxVolume', 'ZipCode', 'MexName', 'LastMeasurementTimeStamp', 'LastMeasurementWithDifferentValue', 'BatteryPercentage', 'Battery', 'LitresPerCentimeter', 'LastMeasurementWasSuccessfully', 'SensorTypeId', 'HasMeasurements', 'MeasuredDaysCount', 'LastMeasurementWasTooHigh', 'YearlyOilUsage', 'RemainingDays', 'LastOrderPrice', 'ResultCode', 'ResultMessage']

    topic2 = ['LastOrderPrice', 'PriceComparedToYesterdayPercentage', 'PriceForecastPercentage', 'HasMultipleMexDevices', 'DashboardViewMode', 'ShowComparedToYesterday', 'ShowForecast', 'ResultCode', 'ResultMessage']

    RemainsUntilCombined = ['MonthAndYear', 'RemainsValue', 'RemainsUnit']

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "MEX")
    client.username_pw_set(mqtt_user, mqtt_pass)
    client.connect(broker_address)

    if debug:
        print("---------------------")
    for n in range(len(topic2)):
        if debug:
            print(topic2[n] + ":", daten[topic2[n]])
        mqtt_send(client, "PricingForecast/" + topic2[n], daten[topic2[n]])

    daten = daten["Items"]
    daten = daten[0]

    if debug:
        print("---------------------")
    for n in range(len(topic1)):
        if debug:
            print(topic1[n] + ":", daten[topic1[n]])
        mqtt_send(client, "Items/" + topic1[n], daten[topic1[n]])

    daten3 = daten['RemainsUntilCombined']

    if debug:
        print("---------------------")
        print('RemainsUntilCombined:')
    for n in range(len(RemainsUntilCombined)):
        if debug:
            print(RemainsUntilCombined[n] + ":", daten3[RemainsUntilCombined[n]])
        mqtt_send(client, "RemainsUntilCombined/" + RemainsUntilCombined[n], daten3[RemainsUntilCombined[n]])

    client.disconnect()

#### Beispiel Ausgaben. Diese können dann natürlich auch in Datenpunkte geschrieben werden. ####
#    print()
#    print("SensorId:                 ", daten["SensorId"])
#    print("Aktueller Inhalt in %:    ", daten["CurrentVolumePercentage"])
#    print("Aktueller Inhalt in Liter:", daten["CurrentVolume"])
#    print("Max Tankinhalt in Liter:  ", daten["MaxVolume"])
#    print("MEX Batterie in %:        ", daten["BatteryPercentage"])
#    print("Letzte Messung in Ordnung:", daten["LastMeasurementWasSuccessfully"])
#    print("Letzte Messung war am:    ", daten["LastMeasurementTimeStamp"])
#    print("Reicht noch für Tage:     ", daten["RemainingDays"])        


if __name__ == '__main__':   
    main()
