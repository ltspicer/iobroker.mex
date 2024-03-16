#!/usr/bin/python3

###################################################################################################
#################################             V1.8               ##################################
#################################  MEX-Daten per MQTT versenden  ##################################
#################################   (C) 2024 Daniel Luginbühl    ##################################
###################################################################################################

####################################### WICHTIGE INFOS ############################################
################     Im Smarthome System ist ein MQTT Broker zu installieren      #################
################ ---------------------------------------------------------------- #################
################          Falls Raspberry: Alles als User PI ausführen!           #################
################ ---------------------------------------------------------------- #################
################ mex.py Script auf Rechte 754 setzen mit:                         #################
################ chmod 754 mex.py                                                 #################
################ Dieses Script per Cronjob alle 2 bis 4 Stunden ausführen:        #################
################ crontab -e                                                       #################
################ 0 */3 * * * /home/pi/mex.py          # Pfad ggf anpassen!        #################
################ ---------------------------------------------------------------- #################
################ Vorgängig zu installieren (auf Host, wo dieses Script läuft):    #################
################    pip3 install requests                                         #################
################    pip3 install paho-mqtt                                        #################
################    pip3 install typing-extensions                                #################
###################################################################################################

###################################################################################################
################################### Hier Einträge anpassen! #######################################

username = "AAAAA@gmail.com"    # Deine Email Adresse bei HeizOel24
passwort = "BBBBBBBBB"          # Dein Passwort bei HeizOel24

broker_address = "192.168.1.50" # MQTT Broker IP (da wo der MQTT Broker läuft)
mqtt_user = "uuuuuu"            # MQTT User      (im MQTT Broker definiert)
mqtt_pass = "pppppp"            # MQTT Passwort  (im MQTT Broker definiert)
mqtt_port = 1883                # MQTT Port      (default: 1883)

delay = False                   # Auf True setzen, wenn der MQTT Broker nur die 1. Zeile empfängt
debug = False                   # True = Debug Infos auf die Konsole.
#                                 Unbedingt nach debuggen zurück setzen!!
#                                 Be sure to reset after debugging!!

###################################################################################################
###################################################################################################


import time, json, requests, random
import paho.mqtt.client as mqtt

# Zufällige Zeitverzögerung 0 bis 3540 Sekunden (0-59min)
verzoegerung = random.randint(0,3540)
if debug:
    verzoegerung = random.randint(0,5)
print("Datenabfrage startet in", verzoegerung, "Sekunden")
time.sleep(verzoegerung)

def mqtt_send(client, topic, wert):
    client.publish("MEX/" + topic, wert)

def login():
    if debug:
        print('Login in...')
    url = "https://api.heizoel24.de/app/api/app/Login"
    newHeaders = {'Content-type': 'application/json'}
    reply = requests.post(url, json = { "Password" : passwort, "Username" : username}, headers=newHeaders, timeout=5)

    return_flag = False
    if reply.status_code == 200:
        if debug:
            print("Login OK")
        reply_json = json.loads(reply.text)
        if reply_json['ResultCode'] == 0:
            session_id = reply_json['SessionId']
            if debug:
                print('Session ID: ' + session_id)
            return_flag = True
        else:
            if debug:
                print('ResultCode nicht 0. Keine Session ID erhalten!')
    else:
        if debug:
            print('Login fehlgeschlagen! Heizoel24 Login Status Code: ' + str(reply.status_code))
    return return_flag, session_id

def mex():
    login_status, session_id = login()
    if login_status == False:
        return "error"
    if debug:
        print('Refresh sensor data cache...')
    url = 'https://api.heizoel24.de/app/api/app/GetDashboardData/'+ session_id + '/1/1/False'
    reply = requests.get(url, timeout=5)
    if reply.status_code == 200:
        if debug:
            print("Daten wurden empfangen")
        sensor_data = reply
    else:
        if debug:
            print('Heizoel24 GetDashboardData > Status Code: ' + str(reply.status_code))
        sensor_data = "error"   # Fehler. Keine Daten empfangen.
    return sensor_data, session_id

def measurement(sensor_id, session_id):
    if debug:
        print('Hole zukünftige Restölstände...')
    url = 'https://api.heizoel24.de/app/api/app/measurement/CalculateRemaining/'+ session_id + '/' + str(sensor_id) + '/False'
    reply = requests.get(url, timeout=5)
    if reply.status_code == 200:
        if debug:
            print("Zukünftige Restölstände wurden empfangen")
        zukunfts_daten = reply
    else:
        if debug:
            print('Heizoel24 Restölstände > Status Code: ' + str(reply.status_code))
        zukunfts_daten = "error"   # Fehler. Keine Daten empfangen.
    return zukunfts_daten

def main():
    topic1 = ['SensorId', 'IsMain', 'CurrentVolumePercentage', 'CurrentVolume', 'NotifyAtLowLevel', 'NotifyAtAlmostEmptyLevel', 'NotificationsEnabled', 'Usage', 'RemainsUntil', 'MaxVolume', 'ZipCode', 'MexName', 'LastMeasurementTimeStamp', 'LastMeasurementWithDifferentValue', 'BatteryPercentage', 'Battery', 'LitresPerCentimeter', 'LastMeasurementWasSuccessfully', 'SensorTypeId', 'HasMeasurements', 'MeasuredDaysCount', 'LastMeasurementWasTooHigh', 'YearlyOilUsage', 'RemainingDays', 'LastOrderPrice', 'ResultCode', 'ResultMessage']
    topic2 = ['LastOrderPrice', 'PriceComparedToYesterdayPercentage', 'PriceForecastPercentage', 'HasMultipleMexDevices', 'DashboardViewMode', 'ShowComparedToYesterday', 'ShowForecast', 'ResultCode', 'ResultMessage']
    RemainsUntilCombined = ['MonthAndYear', 'RemainsValue', 'RemainsUnit']

    try:
        client = mqtt.Client("mex")
        if debug:
            print("paho-mqtt version < 2.0")
    except:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "mex")
        if debug:
            print("paho-mqtt version >= 2.0")

    if debug:
        print("---------------------")
        print("client:", client)
        print("---------------------")

    client.username_pw_set(mqtt_user, mqtt_pass)
    try:
        client.connect(broker_address, port=mqtt_port)
    except:
        print("Verbindung zum MQTT-Broker fehlgeschlagen")
        print("Connection to MQTT broker failed")
        exit(1)

    daten, session_id = mex()
    if daten == "error":
        if debug:
            print("Fehler. Keine Daten empfangen.")
        mqtt_send(client, "Items/DataReceived", False)
        client.disconnect()
        return

    daten = daten.json()

    if debug:
        print()
        print("JSON-Daten:")
        print("===========")
        print()
        print(daten)
        print()
        print("---------------------")
        print()
    for n in range(len(topic2)):
        if debug:
            print(topic2[n] + ":", daten[topic2[n]])
        mqtt_send(client, "PricingForecast/" + topic2[n], daten[topic2[n]])
        if delay:
            time.sleep(0.05)

    daten = daten["Items"]
    daten = daten[0]

    if debug:
        print("---------------------")
    for n in range(len(topic1)):
        if debug:
            print(topic1[n] + ":", daten[topic1[n]])
        mqtt_send(client, "Items/" + topic1[n], daten[topic1[n]])
        if delay:
            time.sleep(0.05)
    mqtt_send(client, "Items/DataReceived", True)

    sensor_id = daten["SensorId"]
    print("******* sensor, session:", sensor_id, session_id)

    daten3 = daten['RemainsUntilCombined']

    if debug:
        print("---------------------")
        print('RemainsUntilCombined:')
    for n in range(len(RemainsUntilCombined)):
        if debug:
            print(RemainsUntilCombined[n] + ":", daten3[RemainsUntilCombined[n]])
        mqtt_send(client, "RemainsUntilCombined/" + RemainsUntilCombined[n], daten3[RemainsUntilCombined[n]])
        if delay:
            time.sleep(0.05)

    zukunfts_daten = measurement(sensor_id, session_id)

    if zukunfts_daten == "error":
        if debug:
            print("Fehler. Keine Daten empfangen.")
            return

    # {'NotifyAtLowLevel': 20, 'NotifyAtAlmostEmptyLevel': 10, 'MaxVolume': 3920, 'CurrentVolume': 2649, 'ConsumptionCurveResult': {'2024-03-14T19:48:15.7952315+01:00': 2649, ...
    zukunfts_daten = zukunfts_daten.json()
    zukunfts_daten = zukunfts_daten['ConsumptionCurveResult']

    n = 0
    for key in zukunfts_daten:
        if debug:
            print(key.split('T')[0], zukunfts_daten[key], "Liter remaining")
        mqtt_send(client, "CalculatedRemaining/Day_" + str(n).zfill(4), str(key).split('T')[0] + " = " + str(zukunfts_daten[key]) + " Ltr.")
        n+=1
        if delay:
            time.sleep(0.05)

    client.disconnect()

if __name__ == '__main__':
    main()
