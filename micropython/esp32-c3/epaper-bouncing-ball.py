import utime
from epd2in13 import EPD_2in13_Landscape, BLACK, WHITE

# Refresh rate test: a ball bouncing around the screen using back to back partial
# refreshes, with a full refresh every so often to clean up ghosting.
# Copy the driver onto the board, then run this from your computer:
#   mpremote cp epd2in13.py : + run epaper-bouncing-ball.py

RADIUS = 10
STEP_X = 6  # pixels the ball moves per frame
STEP_Y = 4
CLEAN_EVERY_MS = 30_000
REPORT_EVERY_MS = 5_000

epd = EPD_2in13_Landscape()
x, y = 40, 30
dx, dy = STEP_X, STEP_Y


def draw():
    epd.fill(WHITE)
    epd.rect(0, 0, epd.width, epd.height, BLACK)
    epd.ellipse(x, y, RADIUS, RADIUS, BLACK, True)


draw()
epd.show()
last_clean = last_report = utime.ticks_ms()
frames = 0
while True:
    x += dx
    y += dy
    if x - RADIUS <= 0 or x + RADIUS >= epd.width - 1:
        dx = -dx
        x = min(max(x, RADIUS + 1), epd.width - RADIUS - 2)
    if y - RADIUS <= 0 or y + RADIUS >= epd.height - 1:
        dy = -dy
        y = min(max(y, RADIUS + 1), epd.height - RADIUS - 2)
    draw()

    now = utime.ticks_ms()
    if utime.ticks_diff(now, last_clean) >= CLEAN_EVERY_MS:
        epd.init()
        epd.show()
        last_clean = last_report = utime.ticks_ms()
        frames = 0  # keep the slow full refresh out of the fps numbers
        print("full refresh to clean ghosting")
    else:
        epd.show_partial()
        frames += 1

    now = utime.ticks_ms()
    elapsed = utime.ticks_diff(now, last_report)
    if elapsed >= REPORT_EVERY_MS:
        print("%.1f fps (%d ms per frame)" % (frames * 1000 / elapsed, elapsed // max(frames, 1)))
        frames = 0
        last_report = now
