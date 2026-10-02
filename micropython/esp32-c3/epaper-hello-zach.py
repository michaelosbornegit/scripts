import framebuf
from epd2in13 import EPD_2in13_Landscape, BLACK, WHITE

# Says hello to Zach on a Waveshare 2.13inch e-Paper HAT, wiring is in epd2in13.py
# Copy the driver onto the board, then run this from your computer:
#   mpremote cp epd2in13.py : + run epaper-hello-zach.py


def big_text(display, text, y, scale):
    # framebuf only has an 8x8 font, so draw it small and blow each pixel up
    width = len(text) * 8
    small = framebuf.FrameBuffer(bytearray(width), width, 8, framebuf.MONO_VLSB)
    small.text(text, 0, 0, 1)
    x = (display.width - width * scale) // 2
    for px in range(width):
        for py in range(8):
            if small.pixel(px, py):
                display.fill_rect(x + px * scale, y + py * scale, scale, scale, BLACK)


epd = EPD_2in13_Landscape()
epd.fill(WHITE)
big_text(epd, "Hello,", 24, 4)
big_text(epd, "Zach!", 66, 4)
epd.show()
epd.sleep()
