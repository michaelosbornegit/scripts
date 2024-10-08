import json
from machine import Pin, I2C
import time
import ssd1306
import scd4x
import urequests as requests
import secrets
import network

apiHost = secrets.apiHost
ssidPrimary = secrets.ssid
passwordPrimary = secrets.password
longLivedToken = secrets.long_lived_token

i2c = I2C(0,sda=Pin(0), scl=Pin(1))
display = ssd1306.SSD1306_I2C(128, 64, i2c)
sensor = scd4x.SCD4X(i2c)
wlan = network.WLAN(network.STA_IF)

def printToScreenRaw(content, centered = False):
    display.fill(0)
    split = content.split('\n')
    lineCounter = 0
    for line in split:
        display.text(f'{line : ^16}' if centered else line, 0, lineCounter * 12, 1)
        lineCounter += 1
        
    display.show()

def printToScreenBreakLines(content, centered = False):
    display.fill(0)
    splitOnNewlines = content.split('\n')
    # print(splitOnNewlines)
    lineCounter = 0
    for line in splitOnNewlines:
        currentLine = ''
        lineLengthCounter = 0
        split = line.split()
        for word in split:
            wordSpace = f'{word} '
            lineLengthCounter += len(wordSpace)
            if (lineLengthCounter > 16):
                display.text(f'{currentLine : ^16}' if centered else currentLine, 0, lineCounter * 12, 1)
                lineCounter += 1
                currentLine = wordSpace
                lineLengthCounter = len(wordSpace)
            else:
                currentLine += wordSpace
        display.text(f'{currentLine : ^16}' if centered else currentLine, 0, lineCounter * 12, 1)
        lineCounter += 1
            
    display.show()

def connectToNetwork():
    wlan.active(True)
    wlan.config(pm = 0xa11140)  # Disable power-save mode
    wlan.connect(ssidPrimary, passwordPrimary)

    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        printToScreenBreakLines(f'Connecting to:\n{ssidPrimary}...')
        max_wait -= 1
        time.sleep(1)

    if wlan.status() != 3:
        printToScreenBreakLines('Network connection failed, are you within range of wifi?')
        time.sleep(2)
        # raise RuntimeError('network connection failed')
    else:
        printToScreenBreakLines('Connected!')
        status = wlan.ifconfig()
        print('ip = ' + status[0])

connectToNetwork()
sensor.start_periodic_measurement()
while True:
    try:
        printToScreenRaw(f'Reading...')
        co2 = sensor.co2
        temp = float(sensor.temperature) * 9 / 5 + 32
        humidity = sensor.relative_humidity
        printToScreenRaw(f'CO2 (PPM): {co2}\nTemp (F):\n{temp}\nHum (%): {humidity}\nPosting Co2...')
        res = requests.post(f'{apiHost}{"MIKE_ROOM_CO2"}', headers={ "Authorization": "Bearer " + longLivedToken, "content-type": "application/json" }, data=json.dumps({ "state": co2, "attributes": { "unit_of_measurement": "ppm", "friendly_name": "Mike Room Co2" }}) )
        res.close()
        printToScreenRaw(f'CO2 (PPM): {co2}\nTemp (F):\n{temp}\nHum (%): {humidity}\nPosting Temp...')
        res = requests.post(f'{apiHost}{"MIKE_ROOM_TEMP"}', headers={ "Authorization": "Bearer " + longLivedToken, "content-type": "application/json" }, data=json.dumps({ "state": round(temp, 2), "attributes": { "unit_of_measurement": "F", "friendly_name": "Mike Room Temp" }}) )
        res.close()
        printToScreenRaw(f'CO2 (PPM): {co2}\nTemp (F):\n{temp}\nHum (%): {humidity}\nPosting Hum...')
        res = requests.post(f'{apiHost}{"MIKE_ROOM_HUMIDITY"}', headers={ "Authorization": "Bearer " + longLivedToken, "content-type": "application/json" }, data=json.dumps({ "state": round(humidity, 2), "attributes": { "unit_of_measurement": "%", "friendly_name": "Mike Room Humidity" }}) )
        printToScreenRaw(f'CO2 (PPM): {co2}\nTemp (F):\n{temp}\nHum (%): {humidity}\nres:{res.status_code}')
        res.close()
    except Exception as err:
        print(err)
    time.sleep(30)