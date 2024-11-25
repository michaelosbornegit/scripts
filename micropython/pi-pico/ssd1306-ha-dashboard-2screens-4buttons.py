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
dashboardConfiguration = 'dog/two-screens-four-buttons'

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

# Initialize per-button debounce tracking
last_press_time = {}
buttons_to_process = []

def button_pressed(event):
    curr_time = utime.ticks_ms()
    last_time = last_press_time.get(event, 0)
    # Debounce period of 300 milliseconds
    if utime.ticks_diff(curr_time, last_time) > 300:
        last_press_time[event] = curr_time
        buttons_to_process.append(event)

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
        # Process any buttons that have been pressed
        while buttons_to_process:
            event = buttons_to_process.pop(0)
            displayOne.whiteScreen()
            displayTwo.whiteScreen()
            try:
                if event == button1:
                    response = requests.post(
                        f'{apiHost}/dashboard/{dashboardConfiguration}',
                        headers=headers,
                        data=json.dumps({'button': 'button1'})
                    )
                    response.close()
                elif event == button2:
                    response = requests.post(
                        f'{apiHost}/dashboard/{dashboardConfiguration}',
                        headers=headers,
                        data=json.dumps({'button': 'button2'})
                    )
                    response.close()
                elif event == button3:
                    response = requests.post(
                        f'{apiHost}/dashboard/{dashboardConfiguration}',
                        headers=headers,
                        data=json.dumps({'button': 'button3'})
                    )
                    response.close()
                elif event == button4:
                    response = requests.post(
                        f'{apiHost}/dashboard/{dashboardConfiguration}',
                        headers=headers,
                        data=json.dumps({'button': 'button4'})
                    )
                    response.close()
                fetch_dashboard()
            except Exception as err:
                print(f"Error: {err}")
                displayOne.printToScreenBreakLines(f'Error: {err}')
        # Short sleep to prevent CPU hogging
        utime.sleep_ms(10)

# Set up interrupts with the correct trigger
button1.irq(handler=button_pressed, trigger=Pin.IRQ_FALLING)
button2.irq(handler=button_pressed, trigger=Pin.IRQ_FALLING)
button3.irq(handler=button_pressed, trigger=Pin.IRQ_FALLING)
button4.irq(handler=button_pressed, trigger=Pin.IRQ_FALLING)

main()
