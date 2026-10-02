import utime
from array import array
from machine import Pin
from epd2in13 import EPD_2in13_Portrait, BLACK, WHITE

# A potted plant with a face, drawn portrait (122x250). The button on D1 swaps it
# between happy and sad. Copy the driver onto the board, then run this from your computer:
#   mpremote cp epd2in13.py : + run epaper-plant-mood.py


def thick_line(fb, x0, y0, x1, y1, color, width=3):
    half = width // 2
    for dx in range(-half, width - half):
        for dy in range(-half, width - half):
            fb.line(x0 + dx, y0 + dy, x1 + dx, y1 + dy, color)


def thick_path(fb, points, color, width=3):
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        thick_line(fb, x0, y0, x1, y1, color, width)


def shape(fb, points, color):
    fb.poly(0, 0, array("h", [v for point in points for v in point]), color, True)


def draw_pot(fb):
    fb.fill_rect(14, 152, 94, 18, BLACK)
    shape(fb, [(20, 170), (102, 170), (92, 244), (30, 244)], BLACK)


def draw_sad(fb):
    draw_pot(fb)
    # sad face on the pot, drawn in white
    thick_line(fb, 32, 185, 51, 178, WHITE, 2)  # brows tilt up toward the middle
    thick_line(fb, 71, 178, 90, 185, WHITE, 2)
    fb.ellipse(43, 196, 5, 6, WHITE, True)
    fb.ellipse(79, 196, 5, 6, WHITE, True)
    shape(fb, [(37, 207), (34, 214), (40, 214)], WHITE)  # tear
    fb.ellipse(37, 216, 3, 4, WHITE, True)
    for dy in range(3):
        fb.ellipse(61, 232 + dy, 14, 9, WHITE, False, 0b0011)  # frown: top half of an ellipse

    # stem bending over to the right
    thick_path(fb, [(61, 152), (59, 125), (58, 100), (62, 78), (72, 62), (86, 56), (98, 60), (104, 72), (106, 84)], BLACK)

    # drooping flower hanging off the end
    fb.ellipse(106, 92, 6, 6, BLACK, True)
    fb.ellipse(99, 104, 3, 7, BLACK, True)
    fb.ellipse(106, 107, 3, 8, BLACK, True)
    fb.ellipse(113, 104, 3, 7, BLACK, True)

    # leaves hanging down
    shape(fb, [(59, 126), (46, 128), (34, 136), (28, 148), (37, 146), (49, 140), (58, 132)], BLACK)
    shape(fb, [(60, 104), (73, 107), (85, 115), (91, 128), (82, 125), (70, 119), (60, 110)], BLACK)

    # one leaf falling, one already on the ground
    shape(fb, [(12, 96), (18, 87), (27, 85), (22, 94)], BLACK)
    thick_line(fb, 8, 80, 12, 84, BLACK, 1)
    thick_line(fb, 14, 76, 17, 80, BLACK, 1)
    shape(fb, [(2, 244), (8, 236), (18, 234), (14, 243)], BLACK)


def draw_happy(fb):
    draw_pot(fb)
    # happy face on the pot, drawn in white
    for dy in range(2):
        fb.ellipse(43, 200 + dy, 6, 5, WHITE, False, 0b0011)  # closed, smiling eyes
        fb.ellipse(79, 200 + dy, 6, 5, WHITE, False, 0b0011)
    fb.ellipse(33, 212, 4, 2, WHITE, True)  # cheeks
    fb.ellipse(89, 212, 4, 2, WHITE, True)
    for dy in range(3):
        fb.ellipse(61, 214 + dy, 16, 11, WHITE, False, 0b1100)  # smile: bottom half of an ellipse

    # stem standing up straight
    thick_path(fb, [(61, 152), (60, 120), (61, 90), (61, 66)], BLACK)

    # leaves reaching up
    shape(fb, [(60, 128), (48, 122), (37, 111), (32, 98), (43, 103), (53, 113), (60, 121)], BLACK)
    shape(fb, [(62, 108), (74, 102), (85, 91), (90, 78), (80, 82), (70, 92), (62, 101)], BLACK)

    # flower in full bloom
    for x, y in ((74, 52), (67, 41), (55, 41), (48, 52), (55, 63), (67, 63)):
        fb.ellipse(x, y, 7, 7, BLACK, True)
    fb.ellipse(61, 52, 6, 6, WHITE, True)
    fb.ellipse(61, 52, 6, 6, BLACK)

    # sun in the corner
    fb.ellipse(16, 16, 7, 7, BLACK, True)
    for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
        thick_line(fb, 16 + dx * 10, 16 + dy * 10, 16 + dx * 14, 16 + dy * 14, BLACK, 2)
    for dx, dy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        thick_line(fb, 16 + dx * 7, 16 + dy * 7, 16 + dx * 10, 16 + dy * 10, BLACK, 2)


def wait_for_press(button):
    # wait for a release first so one long press only counts once
    while button.value() == 0:
        utime.sleep_ms(10)
    while True:
        if button.value() == 0:
            utime.sleep_ms(30)  # debounce
            if button.value() == 0:
                return
        utime.sleep_ms(10)


# Every change uses a quick partial refresh; this often a full one clears the ghosting
FULL_REFRESH_EVERY = 10

button = Pin(3, Pin.IN, Pin.PULL_UP)  # D1 to GND, reads 0 while pressed
epd = EPD_2in13_Portrait()
happy = False
changes = 0
while True:
    epd.fill(WHITE)
    (draw_happy if happy else draw_sad)(epd)
    start = utime.ticks_ms()
    if changes % FULL_REFRESH_EVERY == 0:
        epd.init()  # wakes the panel from the previous sleep
        epd.show()
        kind = "full"
    else:
        epd.show_partial()
        kind = "partial"
    epd.sleep()
    print("showing %s (%s refresh, %d ms)" % ("happy" if happy else "sad", kind, utime.ticks_diff(utime.ticks_ms(), start)))
    wait_for_press(button)
    happy = not happy
    changes += 1
