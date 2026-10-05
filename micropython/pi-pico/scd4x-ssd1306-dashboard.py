from machine import Pin, I2C
import time
import ssd1306
import scd4x
import dashboard

i2c = I2C(0, sda=Pin(0), scl=Pin(1))
display = ssd1306.SSD1306_I2C(128, 64, i2c)
sensor = scd4x.SCD4X(i2c)

HISTORY_MAX = 116
history = []

def boot_screen():
    display.fill(0)
    display.text('CO2 MONITOR', 8, 20, 1)
    display.text('booting sensor', 0, 36, 1)
    display.show()

boot_screen()
sensor.start_periodic_measurement()

while True:
    try:
        co2 = sensor.co2
        if co2 is not None:
            temp_f = float(sensor.temperature) * 9 / 5 + 32
            humidity = sensor.relative_humidity
            history.append(co2)
            if len(history) > HISTORY_MAX:
                history.pop(0)
            dashboard.render(display, co2, temp_f, humidity, history)
    except Exception as err:
        print(err)
    time.sleep(2)
