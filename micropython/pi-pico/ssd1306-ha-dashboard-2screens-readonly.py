import json
from machine import Pin, I2C
import time
import ssd1306
import urequests as requests
import secrets
import network
import utime

apiHost = secrets.apiHost
ssidPrimary = secrets.ssid
passwordPrimary = secrets.password
apiSecret = secrets.apiSecret

# Hard Wired Board
# i2c = I2C(0, sda=Pin(0), scl=Pin(1))
# i2c2 = I2C(1, sda=Pin(6), scl=Pin(7))
# displayOne = ssd1306.SSD1306_I2C(128, 64, i2c)
# displayTwo = ssd1306.SSD1306_I2C(128, 64, i2c2)
# button1 = Pin(2, Pin.IN, Pin.PULL_UP)
# button2 = Pin(3, Pin.IN, Pin.PULL_UP)
# button3 = Pin(14, Pin.IN, Pin.PULL_UP)
# button4 = Pin(15, Pin.IN, Pin.PULL_UP)

# Test board
i2c = I2C(1, sda=Pin(2), scl=Pin(3))
i2c2 = I2C(0, sda=Pin(16), scl=Pin(17))
displayOne = ssd1306.SSD1306_I2C(128, 64, i2c)
displayTwo = ssd1306.SSD1306_I2C(128, 64, i2c2)
button1 = Pin(12, Pin.IN, Pin.PULL_UP)
button2 = Pin(13, Pin.IN, Pin.PULL_UP)
button3 = Pin(14, Pin.IN, Pin.PULL_UP)
button4 = Pin(15, Pin.IN, Pin.PULL_UP)

wlan = network.WLAN(network.STA_IF)
headers = {'Authorization': f'{apiSecret}', 'Content-Type': 'application/json'}
dashboardConfiguration = 'dog/two-screens-readonly'

def connectToNetwork():
    wlan.active(True)
    wlan.config(pm=0xa11140)  # Disable power-save mode
    wlan.connect(ssidPrimary, passwordPrimary)

    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        displayOne.printToScreenBreakLines(f'Connecting to:\n{ssidPrimary}...')
        max_wait -= 1
        time.sleep(1)

    if wlan.status() != 3:
        displayOne.printToScreenBreakLines('Network connection failed, check Wi-Fi')
        time.sleep(2)
    else:
        displayOne.printToScreenBreakLines('Connected!')
        status = wlan.ifconfig()
        print('ip = ' + status[0])

connectToNetwork()

def fetch_dashboard():
    try:
        response = requests.get(f'{apiHost}/dashboard/{dashboardConfiguration}', headers=headers)
        responseJson = response.json()
        displayOne.printToScreenBreakLines(responseJson['screen_one']['text'], True)
        displayTwo.printToScreenBreakLines(responseJson['screen_two']['text'], True)
        response.close()
    except Exception as err:
        print(f"Error: {err}")
        displayOne.printToScreenBreakLines(f'Error: {err}')

def main():
    # Fetch the dashboard once before entering the loop
    fetch_dashboard()
    last_fetch_time = utime.ticks_ms()
    fetch_interval = 30000  # 30 seconds in milliseconds
    while True:
        curr_time = utime.ticks_ms()
        # Check if it's time to fetch the dashboard
        if utime.ticks_diff(curr_time, last_fetch_time) > fetch_interval:
            last_fetch_time = curr_time
            fetch_dashboard()
        # Short sleep to prevent CPU hogging
        utime.sleep_ms(10)

main()
