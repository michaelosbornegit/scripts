from machine import Pin, I2C
import ssd1306

# using default address 0x3C
i2c = I2C(0,sda=Pin(0), scl=Pin(1))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

display.text('Hello, World!', 0, 0, 1)
display.show()