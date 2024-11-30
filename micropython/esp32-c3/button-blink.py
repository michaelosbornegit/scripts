import utime
from machine import Pin

# Light LED when (and while) a BUTTON is pressed

LED = Pin(4, Pin.OUT)
BUTTON = Pin(5, Pin.IN, Pin.PULL_UP)

while 1:
    LED.value(not BUTTON.value())
    # Don't burn CPU
    utime.sleep_ms(10)