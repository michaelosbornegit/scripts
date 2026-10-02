# Waveshare 2.13inch e-Paper HAT (V3/V4, 250x122) driver for the ESP32-C3.
# Adapted from Waveshare's Pico_ePaper-2.13_V4.py:
# https://github.com/waveshareteam/Pico_ePaper_Code/blob/main/python/Pico_ePaper-2.13_V4.py
# Partial refresh (and its waveform) comes from Pico_ePaper-2.13_V3.py in the same repo.
#
# Default pins are for this wiring on a XIAO ESP32C3:
#   VCC -> 3V3   GND -> GND   DIN -> D10   CLK -> D8
#   CS  -> D4    DC  -> D2    RST -> D0    BUSY -> D3   (PWR -> 3V3 if the cable has it)
# If VCC is on a GPIO instead of 3V3, pass power=<gpio> (e.g. power=3 for D1)
#
# Original notice:
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from machine import Pin, SPI
import framebuf
import utime

BLACK = 0
WHITE = 1

# The panel's RAM is portrait: 122 visible columns (padded to 128) by 250 rows
PANEL_COLUMNS = 128
PANEL_ROWS = 250

# Waveshare's V3 partial refresh waveform: 153 LUT bytes, then the EOPT, gate voltage,
# three source voltages and VCOM
WF_PARTIAL = bytes([
    0x0, 0x40, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x80, 0x80, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x40, 0x40, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x80, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x14, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x1, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x1, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x22, 0x22, 0x22, 0x22, 0x22, 0x22, 0x0, 0x0, 0x0,
    0x22, 0x17, 0x41, 0x00, 0x32, 0x36,
])


class _EPD_2in13(framebuf.FrameBuffer):
    # Shared panel driver, the subclasses pick the orientation
    ENTRY_MODE = None

    def __init__(self, fb_width, fb_height, fb_format, sck, mosi, cs, dc, rst, busy, power):
        if power is not None:
            # VCC can hang off a GPIO, the panel draws only a few mA while refreshing
            self.power_pin = Pin(power, Pin.OUT, value=1, drive=Pin.DRIVE_3)
            utime.sleep_ms(300)
        self.cs_pin = Pin(cs, Pin.OUT, value=1)
        self.dc_pin = Pin(dc, Pin.OUT, value=0)
        self.reset_pin = Pin(rst, Pin.OUT, value=1)
        self.busy_pin = Pin(busy, Pin.IN, Pin.PULL_UP)
        # miso=None matters: the C3 default MISO is GPIO2, which would steal the RST pin
        self.spi = SPI(1, baudrate=4_000_000, sck=Pin(sck), mosi=Pin(mosi), miso=None)
        self.buffer = bytearray(PANEL_ROWS * PANEL_COLUMNS // 8)
        self.on_screen = None  # what the last refresh put up, partial refresh diffs against it
        self.partial_ready = False  # waveform loaded and panel powered for back-to-back partials
        super().__init__(self.buffer, fb_width, fb_height, fb_format)
        self.init()

    def _command(self, command, data=None):
        self.dc_pin(0)
        self.cs_pin(0)
        self.spi.write(bytes([command]))
        self.cs_pin(1)
        if data is not None:
            self._data(data)

    def _data(self, data):
        self.dc_pin(1)
        self.cs_pin(0)
        self.spi.write(data)
        self.cs_pin(1)

    def wait_until_idle(self, timeout_ms=10_000):
        # BUSY is high while the panel works; a pull-up means a loose wire reads busy forever
        start = utime.ticks_ms()
        while self.busy_pin.value() == 1:
            if utime.ticks_diff(utime.ticks_ms(), start) > timeout_ms:
                raise OSError("e-Paper stayed busy: check the VCC, GND and BUSY wires")
            utime.sleep_ms(10)

    def reset(self):
        self.reset_pin(1)
        utime.sleep_ms(20)
        self.reset_pin(0)
        utime.sleep_ms(10)  # 2ms (Waveshare's value) isn't enough to wake it from deep sleep
        self.reset_pin(1)
        utime.sleep_ms(20)

    def init(self):
        self.partial_ready = False
        self.reset()
        utime.sleep_ms(100)
        self.wait_until_idle()
        self._command(0x12)  # software reset
        self.wait_until_idle()

        self._set_ram_layout()
        self._command(0x3C, b"\x05")  # border waveform
        self._command(0x21, b"\x00\x80")  # display update control
        self._command(0x18, b"\x80")  # use the built-in temperature sensor
        self.wait_until_idle()

    def _set_ram_layout(self):
        self._command(0x01, b"\xf9\x00\x00")  # driver output control
        self._command(0x11, bytes([self.ENTRY_MODE]))  # data entry mode for this orientation
        self._command(0x44, bytes([0, (PANEL_COLUMNS - 1) >> 3]))  # RAM x window
        self._command(0x45, bytes([0, 0, (PANEL_ROWS - 1) & 0xFF, (PANEL_ROWS - 1) >> 8]))  # RAM y window

    def _write_ram(self, command, data):
        self._command(0x4E, b"\x00")  # RAM x cursor
        self._command(0x4F, b"\x00\x00")  # RAM y cursor
        self._command(command, data)

    def _refresh(self):
        self._command(0x22, b"\xf7")  # full refresh
        self._command(0x20)
        self.wait_until_idle()

    def clear(self):
        self.fill(WHITE)
        self.show()

    def _panel_bytes(self):
        return self.buffer

    def show(self):
        # Full refresh: flashes a few times but clears any ghosting
        data = self._panel_bytes()
        self._write_ram(0x24, data)  # new image
        self._write_ram(0x26, data)  # previous image, used by the next partial refresh
        self._refresh()
        self.on_screen = bytes(data)

    def show_partial(self):
        # Only redraws pixels that changed: no flashing and well under a second, but
        # ghosting builds up, so do a full show() every so often
        if self.on_screen is None:
            return self.show()
        if not self.partial_ready:
            self._prepare_partial()
        data = self._panel_bytes()
        self._write_ram(0x26, self.on_screen)  # old image, so the panel knows what changed
        self._write_ram(0x24, data)
        self._command(0x22, b"\x0c")  # refresh with the loaded waveform, stay powered for the next one
        self._command(0x20)
        self.wait_until_idle()
        self.on_screen = bytes(data)

    def _prepare_partial(self):
        # Done once, then partials can follow back to back until the next sleep() or init()
        self.reset()  # also wakes the panel from sleep
        self._command(0x32, WF_PARTIAL[:153])  # partial waveform
        self.wait_until_idle()
        self._command(0x3F, WF_PARTIAL[153:154])
        self._command(0x03, WF_PARTIAL[154:155])  # gate voltage
        self._command(0x04, WF_PARTIAL[155:158])  # source voltages
        self._command(0x2C, WF_PARTIAL[158:159])  # VCOM
        self._command(0x3C, b"\x80")  # border waveform
        self._command(0x22, b"\xc0")  # power up clock and analog
        self._command(0x20)
        self.wait_until_idle()
        self._set_ram_layout()
        self.partial_ready = True

    def sleep(self):
        # The image stays on screen while the panel sleeps
        self.partial_ready = False
        self._command(0x10, b"\x01")
        utime.sleep_ms(100)


class EPD_2in13_Landscape(_EPD_2in13):
    ENTRY_MODE = 0x07

    def __init__(self, sck=8, mosi=10, cs=6, dc=4, rst=2, busy=5, power=None):
        self.width = PANEL_ROWS
        self.height = 122  # visible rows, the framebuffer has 128
        super().__init__(PANEL_ROWS, PANEL_COLUMNS, framebuf.MONO_VLSB, sck, mosi, cs, dc, rst, busy, power)

    def _panel_bytes(self):
        # Landscape buffer bytes go out one panel column band at a time, last band first
        out = bytearray(len(self.buffer))
        k = 0
        for band in range(PANEL_COLUMNS // 8 - 1, -1, -1):
            out[k : k + PANEL_ROWS] = self.buffer[band * PANEL_ROWS : (band + 1) * PANEL_ROWS]
            k += PANEL_ROWS
        return out


class EPD_2in13_Portrait(_EPD_2in13):
    ENTRY_MODE = 0x03

    def __init__(self, sck=8, mosi=10, cs=6, dc=4, rst=2, busy=5, power=None):
        self.width = 122  # visible columns, the framebuffer has 128
        self.height = PANEL_ROWS
        super().__init__(PANEL_COLUMNS, PANEL_ROWS, framebuf.MONO_HLSB, sck, mosi, cs, dc, rst, busy, power)
