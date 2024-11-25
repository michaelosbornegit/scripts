from machine import Pin, I2C
import ssd1306

# using default address 0x3C
i2c = I2C(0,sda=Pin(6), scl=Pin(7))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

display.text('Hello, World!', 0, 0, 1)
display.show()