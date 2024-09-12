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
longLivedToken = secrets.long_lived_token

i2c = I2C(1, sda=Pin(2), scl=Pin(3))
i2c2 = I2C(0, sda=Pin(16), scl=Pin(17))
displayOne = ssd1306.SSD1306_I2C(128, 64, i2c)
displayTwo = ssd1306.SSD1306_I2C(128, 64, i2c2)
wlan = network.WLAN(network.STA_IF)

def printToScreenBreakLines(displayToPrintTo, content, centered=False):
    displayToPrintTo.fill(0)
    splitOnNewlines = content.split('\n')
    lineCounter = 0
    for line in splitOnNewlines:
        displayToPrintTo.text(f'{line : ^16}' if centered else line, 0, lineCounter * 12, 1)
        lineCounter += 1
    displayToPrintTo.show()

def connectToNetwork():
    wlan.active(True)
    wlan.config(pm=0xa11140)  # Disable power-save mode
    wlan.connect(ssidPrimary, passwordPrimary)

    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        printToScreenBreakLines(displayOne, f'Connecting to:\n{ssidPrimary}...')
        max_wait -= 1
        time.sleep(1)

    if wlan.status() != 3:
        printToScreenBreakLines(displayOne, 'Network connection failed, check Wi-Fi')
        time.sleep(2)
    else:
        printToScreenBreakLines(displayOne, 'Connected!')
        status = wlan.ifconfig()
        print('ip = ' + status[0])

def fetch_current_time():
    try:
        response = requests.get('http://worldtimeapi.org/api/timezone/Etc/UTC')
        if response.status_code == 200:
            time_data = response.json()
            utc_time_str = time_data['utc_datetime']  # Format: '2024-09-06T02:18:06.000Z'
            utc_timestamp = parse_utc_datetime(utc_time_str)
            return utc_timestamp
        else:
            print("Failed to get time from API")
    except Exception as e:
        print(f"Error fetching time: {e}")
    return None

def parse_utc_datetime(datetime_str):
    # Parse 'YYYY-MM-DDTHH:MM:SSZ' format
    year = int(datetime_str[0:4])
    month = int(datetime_str[5:7])
    day = int(datetime_str[8:10])
    hour = int(datetime_str[11:13])
    minute = int(datetime_str[14:16])
    second = int(datetime_str[17:19])
    
    # Create a tuple compatible with utime.mktime() without using it (manual calculation)
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        days_in_month[1] = 29

    total_days = (year - 1970) * 365 + sum(days_in_month[:month - 1]) + (day - 1)
    total_days += (year - 1972) // 4 - (year - 1900) // 100 + (year - 1600) // 400
    utc_timestamp = total_days * 86400 + hour * 3600 + minute * 60 + second
    return utc_timestamp

def pretty_print_time(unix_time):
    # Convert the UNIX timestamp to a human-readable format
    tm = utime.localtime(unix_time)
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(tm[0], tm[1], tm[2], tm[3], tm[4], tm[5])

connectToNetwork()

while True:
    try:
        # Fetch the current time from the public API
        current_time = fetch_current_time()
        if current_time is None:
            printToScreenBreakLines(displayOne, "Failed to fetch time.")
            continue

        # Fetch the timer state
        res = requests.get(f'{apiHost}{"timer.2_hours_since_last_out"}', headers={ "Authorization": "Bearer " + longLivedToken })
        data = json.loads(res.text)

        if data['state'] == 'idle':
            printToScreenBreakLines(displayOne, 'Timer is idle!')
            
        elif data['state'] == 'active':
            # Calculate the remaining time
            finishes_at_str = data['attributes']['finishes_at']
            finishes_at = parse_utc_datetime(finishes_at_str)
            remaining_time = finishes_at - current_time
            remaining_hours = int(remaining_time / 3600)
            remaining_minutes = int((remaining_time % 3600) / 60)
            remaining_seconds = int(remaining_time % 60)


            finishes_at_pretty = pretty_print_time(finishes_at)

            # Display the time information
            printToScreenBreakLines(displayOne, f'Timer active!\n{remaining_hours}:{remaining_minutes}:{remaining_seconds} left')
        print(data)
        res.close()
    except Exception as err:
        print(f"Error: {err}")
    time.sleep(1)
