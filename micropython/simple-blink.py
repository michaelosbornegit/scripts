from machine import Pin, Timer
four = Pin(4, Pin.OUT)

timer = Timer()

def blink(timer):
    four.toggle()

timer.init(freq=4, mode=Timer.PERIODIC, callback=blink)