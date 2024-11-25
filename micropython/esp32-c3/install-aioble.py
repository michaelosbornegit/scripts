import json
from machine import Pin, I2C
import time
import urequests as requests
import secrets
import network
import utime
import mip

ssidPrimary = secrets.ssid
passwordPrimary = secrets.password

def connectToNetwork():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print(f'Connecting to network...')
        sta_if.active(True)
        sta_if.connect(ssid=ssidPrimary, key=passwordPrimary)
        while not sta_if.isconnected():
            pass
    print('Network config:', sta_if.ipconfig('addr4'))

connectToNetwork()

mip.install('aioble')