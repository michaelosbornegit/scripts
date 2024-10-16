from machine import Pin, I2C
import ssd1306
import time
import utime

i2c = I2C(1, sda=Pin(2), scl=Pin(3))
displayOne = ssd1306.SSD1306_I2C(128, 64, i2c)

button = Pin(14, Pin.IN, Pin.PULL_UP)
counter = 0
lastTime = 0
newTime = 0

def button_pressed(event):
    global lastTime, counter, newTime
    newTime = utime.ticks_ms()
    if (newTime - lastTime) > 100 and event.value() is 1:
        lastTime = newTime
        print('pressed')
        counter += 1
        displayOne.printToScreenBreakLines(f'Button pressed {counter} times', True)

def main():
    displayOne.printToScreenBreakLines('Press the button', True)
    print('hi!')
    while True:
        time.sleep(1)

button.irq(handler=button_pressed, trigger=Pin.IRQ_RISING)
main()
