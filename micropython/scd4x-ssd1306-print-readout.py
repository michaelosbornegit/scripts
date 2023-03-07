from machine import Pin, I2C
import time
import ssd1306
import scd4x

i2c = I2C(0,sda=Pin(0), scl=Pin(1), freq=100000)
display = ssd1306.SSD1306_I2C(128, 64, i2c)
sensor = scd4x.SCD4X(i2c)
sensor.start_periodic_measurement()

def printToScreenRaw(content, centered = False):
    display.fill(0)
    split = content.split('\n')
    lineCounter = 0
    for line in split:
        display.text(f'{line : ^16}' if centered else line, 0, lineCounter * 12, 1)
        lineCounter += 1
        
    display.show()

while True:
    time.sleep(5)
    try:
        co2 = sensor.co2
        temp = float(sensor.temperature) * 9 / 5 + 32
        humidity = sensor.relative_humidity
        printToScreenRaw(f'CO2 (PPM): {co2}\nTemp (F):\n{temp}\nHumidity (%):\n{humidity}')
    except Exception as err:
        print(err)
        printToScreenRaw('Error:\nerr')