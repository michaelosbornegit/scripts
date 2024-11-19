from machine import Pin, I2C
import ssd1306
import time
import ntptime
import utime
import network
import secrets

wlan = network.WLAN(network.STA_IF)

i2c = I2C(1, sda=Pin(2), scl=Pin(3))
displayOne = ssd1306.SSD1306_I2C(128, 64, i2c)

apiHost = secrets.apiHost
ssidPrimary = secrets.ssid
passwordPrimary = secrets.password
longLivedToken = secrets.long_lived_token

counter = 0
lastTime = 0
newTime = 0

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
        ntptime.settime()
        print('ip = ' + status[0])

connectToNetwork()

def main():
    while True:
        # Get the current time in UTC
        current_time = time.localtime()
        
        # Convert to seconds since epoch
        current_time_seconds = time.mktime(current_time)
        
        # Los Angeles is UTC-8 or UTC-7 depending on daylight saving time
        # Assuming standard time (UTC-8)
        # Determine if daylight saving time is in effect
        # Daylight saving time in the US starts on the second Sunday in March
        # and ends on the first Sunday in November
        year, month, day, hour, minute, second, weekday, yearday = current_time
        
        # Calculate the second Sunday in March
        second_sunday_march = 14 - (weekday + 1) % 7
        
        # Calculate the first Sunday in November
        first_sunday_november = 7 - (weekday + 1) % 7
        
        if (month > 3 or (month == 3 and day >= second_sunday_march)) and (month < 11 or (month == 11 and day < first_sunday_november)):
            la_offset_seconds = -7 * 3600  # Daylight saving time (UTC-7)
        else:
            la_offset_seconds = -8 * 3600  # Standard time (UTC-8)
        
        # Convert to Los Angeles time
        la_time_seconds = current_time_seconds + la_offset_seconds
        la_time = time.localtime(la_time_seconds)
        
        # Display the time in Los Angeles timezone
        displayOne.printToScreenBreakLines(f'The current time in Seattle is\n{la_time}', True)
        time.sleep(1)

main()
