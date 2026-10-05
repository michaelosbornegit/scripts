# Agent monitor — device side.
#
# Runs on the Desk Buddy XIAO ESP32C3 (OLED + button + LED), separate from
# the Desk Buddy software. Shows a live count of running Claude Code
# sessions, fed by host_monitor.py over USB serial. Flashes the LED once
# per session that stops. Button cycles between the live view, today's
# stats, and a short history. Shows a "not connected" screen when nothing
# has come over serial recently.
#
# Install (see README.md for details):
#   mpremote connect <port> cp ssd1306.py : + cp device_main.py :main.py
#
# Wiring is the same as Desk Buddy's OLED build: SDA=D4 SCL=D5 (I2C),
# BUTTON=D3, LED=D2.

import json
import os
import select
import sys
import time

import framebuf
from machine import I2C, Pin

import ssd1306

WIDTH, HEIGHT = 128, 64
DEVICE_ID = "desk-buddy-agent-monitor"  # so the host can find the right
# port when several boards are plugged in, instead of guessing
HELLO_PERIOD_MS = 2_000
STATS_FILE = "stats.json"
HISTORY_DAYS = 7

NOT_CONNECTED_TIMEOUT_MS = 6_000  # no message in this long -> "not connected"
IDLE_DIM_MS = 10 * 60_000  # no message in this long -> dim further (burn-in guard)
SHIFT_PERIOD_MS = 5 * 60_000  # re-anchor the whole layout this often (burn-in guard)
SHIFT_MAX_PX = 3
FLASH_ON_MS = 120
FLASH_GAP_MS = 220
DEBOUNCE_MS = 30

i2c = I2C(0, sda=Pin(6), scl=Pin(7))
oled = ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)
led = Pin(4, Pin.OUT)
button = Pin(5, Pin.IN, Pin.PULL_UP)


# ---------------------------------------------------------------- storage --

def load_stats():
    try:
        with open(STATS_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"date": None, "history": []}


def save_stats(stats):
    tmp = STATS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(stats, f)
    os.rename(tmp, STATS_FILE)


stats = load_stats()


# ----------------------------------------------------------------- serial --
# Non-blocking line reader: the USB serial here is the same stream as the
# REPL, so a running script has to poll for input rather than block on it.

_poll = select.poll()
_poll.register(sys.stdin, select.POLLIN)
_buf = ""


def poll_serial_lines():
    global _buf
    lines = []
    while _poll.poll(0):
        ch = sys.stdin.read(1)
        if not ch:
            break
        _buf += ch
        if ch == "\n":
            line = _buf.strip()
            _buf = ""
            if line:
                lines.append(line)
    return lines


# ------------------------------------------------------------------ state --

state = {"running": 0, "started_today": 0, "stopped_today": 0, "peak_running_today": 0}
last_msg_ms = None  # drives the "not connected" timeout
last_change_ms = None  # drives idle dimming: only moves when the numbers move
last_session_stopped_today = None  # None until the first message, so a
# backlog from before this device was connected doesn't flash as if it just
# happened. Tracks session_stopped_today (top-level sessions only), NOT the
# on-screen stopped_today/"tasks" tally -- that one also counts subagent
# completions, which would otherwise flash the LED on every little subagent
# finishing during a busy background workflow instead of just real turns.
connected = False


def handle_message(line):
    global last_msg_ms, last_change_ms, last_session_stopped_today, connected
    try:
        msg = json.loads(line)
    except ValueError:
        return
    if msg.get("t") != "state":
        return

    now = time.ticks_ms()
    last_msg_ms = now
    connected = True

    d = msg.get("date")
    if stats["date"] != d:
        if stats["date"] is not None:
            stats["history"].append({
                "date": stats["date"],
                "started": state["started_today"],
                "stopped": state["stopped_today"],
            })
            stats["history"] = stats["history"][-HISTORY_DAYS:]
        stats["date"] = d
        save_stats(stats)

    new_running = msg.get("running", 0)
    new_started = msg.get("started_today", 0)
    new_stopped = msg.get("stopped_today", 0)
    new_peak_running = msg.get("peak_running_today", new_running)
    new_session_stopped = msg.get("session_stopped_today", new_stopped)
    if (new_running, new_started, new_stopped, new_peak_running) != (
        state["running"], state["started_today"], state["stopped_today"], state["peak_running_today"]
    ):
        last_change_ms = now

    if last_session_stopped_today is not None and new_session_stopped > last_session_stopped_today:
        flash_led(new_session_stopped - last_session_stopped_today)
    last_session_stopped_today = new_session_stopped

    state["running"] = new_running
    state["started_today"] = new_started
    state["stopped_today"] = new_stopped
    state["peak_running_today"] = new_peak_running


# -------------------------------------------------------------------- led --
# Flashes are scheduled rather than slept through, so they never stall the
# serial read or the display loop.

_flash_queue = []
_led_off_at = None


def flash_led(n):
    now = time.ticks_ms()
    for i in range(min(n, 5)):  # cap so a burst of stops can't queue forever
        _flash_queue.append(time.ticks_add(now, i * FLASH_GAP_MS))


def service_led():
    global _led_off_at
    now = time.ticks_ms()
    if _led_off_at is not None:
        if time.ticks_diff(now, _led_off_at) >= 0:
            led.off()
            _led_off_at = None
        return
    if _flash_queue and time.ticks_diff(now, _flash_queue[0]) >= 0:
        _flash_queue.pop(0)
        led.on()
        _led_off_at = time.ticks_add(now, FLASH_ON_MS)


# ------------------------------------------------------------------ draw --
# Kept deliberately dark and sparse: an OLED only wears where pixels are lit,
# so a mostly-black UI with thin text is the first and biggest burn-in guard.
# On top of that: the whole layout is nudged by a few px every few minutes,
# and contrast drops further if nothing's changed in a while.

shift_x, shift_y = 0, 0
last_shift_ms = time.ticks_ms()
dimmed = False


def service_shift():
    global shift_x, shift_y, last_shift_ms
    now = time.ticks_ms()
    if time.ticks_diff(now, last_shift_ms) >= SHIFT_PERIOD_MS:
        last_shift_ms = now
        # cheap deterministic wander, no random module needed
        shift_x = (shift_x + 1) % (SHIFT_MAX_PX * 2 + 1) - SHIFT_MAX_PX
        shift_y = (shift_y + 2) % (SHIFT_MAX_PX * 2 + 1) - SHIFT_MAX_PX


def service_dim():
    global dimmed
    # idle = the numbers haven't actually changed in a while, not just "no
    # heartbeat" (a connected host sends one every couple seconds regardless)
    idle = last_change_ms is not None and time.ticks_diff(time.ticks_ms(), last_change_ms) >= IDLE_DIM_MS
    if idle != dimmed:
        dimmed = idle
        oled.contrast(0x10 if dimmed else 0xFF)


def px(x, y):
    return x + shift_x, y + shift_y


def text(s, x, y, margin=4):
    sx, sy = px(x, y)
    w = len(s) * 8
    h = 8
    rx0 = max(0, sx - margin)
    ry0 = max(0, sy - margin)
    rx1 = min(WIDTH, sx + w + margin)
    ry1 = min(HEIGHT, sy + h + margin)
    oled.fill_rect(rx0, ry0, rx1 - rx0, ry1 - ry0, 0)
    oled.text(s, sx, sy, 1)


def big_digits(s, x, y, margin=4):
    # framebuf's built-in font is 8x8; this is a cheap 2x blow-up for a
    # "big number" look without needing a packed font like Desk Buddy's
    x, y = px(x, y)
    w = len(s) * 8
    rx0 = max(0, x - margin)
    ry0 = max(0, y - margin)
    rx1 = min(WIDTH, x + w * 2 + margin)
    ry1 = min(HEIGHT, y + 16 + margin)
    oled.fill_rect(rx0, ry0, rx1 - rx0, ry1 - ry0, 0)
    tmp = bytearray(w)
    f = framebuf.FrameBuffer(tmp, w, 8, framebuf.MONO_VLSB)
    f.text(s, 0, 0, 1)
    for cx in range(w):
        for cy in range(8):
            if f.pixel(cx, cy):
                oled.fill_rect(x + cx * 2, y + cy * 2, 2, 2, 1)


# The big agent count + its "agents" label (one rigid shape, 42px tall) and
# the turns line (16px tall) add up to 58 of the screen's 64px height --
# too tight to give both real INDEPENDENT vertical wiggle room without
# risking exactly the overlap/reordering this needs to avoid. So vertical
# position is pinned per unit (agents always on top, turns always below,
# never touching -- see the band math below), and each unit instead gets
# its own fully independent horizontal bounce, which has plenty of room.
# This guarantees "never overlap" and "turns stays under agents"
# structurally, by construction, rather than by runtime collision checks.
_AGENTS_GAP = 2  # vertical gap between the big digit and the "agents" label
_AGENTS_Y = 2  # agents unit spans y=[2, 2+42]=[2,44]
_TURNS_Y = 46  # turns unit spans y=[46,46+16]=[46,62] -- a clean 2px gap
# below the agents unit and a 2px margin to the bottom edge

_agents_x = 10.0
_agents_dx = 0.6

_turns_x = 20.0
_turns_dx = -0.5


def draw_live():
    global _agents_x, _agents_dx, _turns_x, _turns_dx

    digits = str(state["running"])
    label = "agents"
    turns = "%d turns" % state["stopped_today"]

    bw = len(digits) * 16
    lw = len(label) * 8
    aw = max(bw, lw)
    tw = len(turns) * 8

    _agents_x += _agents_dx
    if _agents_x <= 0 or _agents_x >= WIDTH - aw:
        _agents_dx = -_agents_dx
        _agents_x = max(0, min(WIDTH - aw, _agents_x))

    _turns_x += _turns_dx
    if _turns_x <= 0 or _turns_x >= WIDTH - tw:
        _turns_dx = -_turns_dx
        _turns_x = max(0, min(WIDTH - tw, _turns_x))

    # text()/big_digits() both add the global shift_x/shift_y anti-burn-in
    # nudge (px()) on top of whatever position they're given -- fine for
    # static screens, but these two units already have their own dedicated
    # bounce, so that extra nudge stacking on top of an already-at-the-edge
    # position was pushing them 1-3px past the screen edge. Subtract it
    # here so it cancels out to exactly the bounce-bounded position below.
    ax = int(_agents_x) - shift_x
    bx = ax + (aw - bw) // 2
    big_digits(digits, bx, _AGENTS_Y + 4 - shift_y)
    lx = ax + (aw - lw) // 2
    text(label, lx, _AGENTS_Y + 24 + _AGENTS_GAP + 4 - shift_y)

    tx = int(_turns_x) - shift_x
    text(turns, tx, _TURNS_Y + 4 - shift_y)


def draw_today():
    text("Today", 0, 0)
    text("peak: %d" % state["peak_running_today"], 0, 20)
    text("finished: %d" % state["stopped_today"], 0, 32)
    text("running: %d" % state["running"], 0, 44)


def draw_history():
    text("Last %d days" % HISTORY_DAYS, 0, 0)
    days = stats["history"][-HISTORY_DAYS:]
    if not days:
        text("not enough", 0, 24)
        text("history yet", 0, 36)
        return
    peak = 1
    for d in days:
        if d["started"] > peak:
            peak = d["started"]
    bar_w = WIDTH // HISTORY_DAYS
    base_y = HEIGHT - 10
    for i, d in enumerate(days):
        h = max(1, int(d["started"] / peak * (base_y - 12)))
        bx, by = px(i * bar_w + 1, base_y - h)
        oled.fill_rect(bx, by, bar_w - 2, h, 1)


# Conway's Game of Life, genuinely simulated (real B3/S23 rules, toroidal
# wraparound), running continuously behind every screen -- not an effect
# layered on top, the actual foreground is drawn over this each frame.
# Every live cell is drawn as a 2x2 pixel block, no masking/dimming.
_GOL_CELL = 2  # each cell is a 2x2 pixel block
_GOL_W, _GOL_H = WIDTH // _GOL_CELL, HEIGHT // _GOL_CELL  # 64x32
_GOL_STEP_EVERY_TICKS = 1  # a new generation every tick
_GOL_STAGNANT_WINDOW = 10  # generations of near-constant population before
_GOL_STAGNANT_TOLERANCE = 2  # we call it settled and inject fresh clusters

import random as _random

# Known "methuselah" patterns -- these are famous precisely because they run
# for hundreds or thousands of generations before settling, unlike uniform
# random noise which mostly just dies out or freezes into a few blinkers
# within a handful of steps. (dx, dy) offsets from each pattern's origin.
_GOL_PATTERNS = (
    ((1, 0), (2, 1), (0, 2), (1, 2), (2, 2)),                          # glider
    ((1, 0), (2, 0), (0, 1), (1, 1), (1, 2)),                          # R-pentomino
    ((1, 0), (3, 1), (0, 2), (1, 2), (4, 2), (5, 2), (6, 2)),          # acorn
)


def _gol_stamp(grid, pattern, ox, oy):
    for dx, dy in pattern:
        x = (ox + dx) % _GOL_W
        y = (oy + dy) % _GOL_H
        grid[y * _GOL_W + x] = 1


def _gol_seed(n_clusters=6):
    grid = bytearray(_GOL_W * _GOL_H)
    for _ in range(n_clusters):
        pattern = _GOL_PATTERNS[_random.getrandbits(8) % len(_GOL_PATTERNS)]
        _gol_stamp(grid, pattern, _random.getrandbits(8) % _GOL_W, _random.getrandbits(8) % _GOL_H)
    return grid


_gol_grid = _gol_seed()
_gol_tick = 0
_gol_pop_history = []


@micropython.native
def _gol_hsum_row(g, row, w, out):
    # 3-wide horizontal sum (including the center cell), one pass per row;
    # reused by the three rows that need it in _gol_combine_row rather than
    # recomputed from scratch for every single cell
    prev = g[row + w - 1]
    cur = g[row]
    for x in range(w):
        nxt = g[row + (x + 1) % w]
        out[x] = prev + cur + nxt
        prev = cur
        cur = nxt


@micropython.native
def _gol_combine_row(hs_up, hs_mid, hs_dn, g, row, w, new):
    for x in range(w):
        n = hs_up[x] + hs_dn[x] + hs_mid[x] - g[row + x]
        new[row + x] = 1 if (n == 3 or (g[row + x] and n == 2)) else 0


def _gol_step():
    global _gol_grid, _gol_pop_history
    g = _gol_grid
    w, h = _GOL_W, _GOL_H
    new = bytearray(w * h)
    hsum_rows = [bytearray(w) for _ in range(h)]
    for y in range(h):
        _gol_hsum_row(g, y * w, w, hsum_rows[y])
    for y in range(h):
        _gol_combine_row(hsum_rows[(y - 1) % h], hsum_rows[y], hsum_rows[(y + 1) % h], g, y * w, w, new)
    pop = sum(new)

    if pop == 0:
        new = _gol_seed()  # total extinction: never let the backdrop stay blank
        _gol_pop_history = []
    else:
        _gol_pop_history.append(pop)
        if len(_gol_pop_history) > _GOL_STAGNANT_WINDOW:
            _gol_pop_history.pop(0)
        if (len(_gol_pop_history) == _GOL_STAGNANT_WINDOW
                and max(_gol_pop_history) - min(_gol_pop_history) <= _GOL_STAGNANT_TOLERANCE):
            # settled into still-lifes/oscillators with nothing new happening
            # -- drop a couple of fresh patterns in without clearing what's
            # already there, so it comes back to life instead of sitting static
            for _ in range(2):
                pattern = _GOL_PATTERNS[_random.getrandbits(8) % len(_GOL_PATTERNS)]
                _gol_stamp(new, pattern, _random.getrandbits(8) % w, _random.getrandbits(8) % h)
            _gol_pop_history = []

    _gol_grid = new


@micropython.native
def _gol_draw_direct(grid, buf, gw, gh, cell, pw):
    # writes straight into the OLED's own framebuffer (SSD1306 MONO_VLSB:
    # buf[y//8 * pw + x], bit (y%8) = pixel (x,y)) instead of calling
    # oled.pixel() once per cell -- same picture, far less per-call overhead.
    # pw is the physical display width (buffer stride), which differs from
    # the grid width gw whenever a cell covers more than one pixel.
    for i in range(len(buf)):
        buf[i] = 0
    for gy in range(gh):
        row = gy * gw
        py0 = gy * cell
        for gx in range(gw):
            if grid[row + gx]:
                px0 = gx * cell
                for dy in range(cell):
                    y = py0 + dy
                    page = (y >> 3) * pw
                    bit = 1 << (y & 7)
                    for dx in range(cell):
                        buf[page + px0 + dx] |= bit


def draw_gol_background():
    global _gol_tick
    _gol_tick += 1
    if _gol_tick >= _GOL_STEP_EVERY_TICKS:
        _gol_tick = 0
        _gol_step()
    _gol_draw_direct(_gol_grid, oled.buffer, _GOL_W, _GOL_H, _GOL_CELL, WIDTH)


_NC_TEXT = "not connected"
_NC_W = len(_NC_TEXT) * 8
_nc_x, _nc_y = 10.0, 50.0
_nc_dx, _nc_dy = 0.6, 0.4  # different speeds so it doesn't retrace the same path


def draw_not_connected():
    # this screen can sit unchanged for hours (host down, Mac asleep) --
    # the global shift_x/shift_y wander is too subtle to matter over that
    # long a burn-in risk, so it gets its own full-range bounce on top
    global _nc_x, _nc_y, _nc_dx, _nc_dy
    max_x = WIDTH - _NC_W
    max_y = HEIGHT - 8
    _nc_x += _nc_dx
    _nc_y += _nc_dy
    if _nc_x <= 0 or _nc_x >= max_x:
        _nc_dx = -_nc_dx
        _nc_x = max(0, min(max_x, _nc_x))
    if _nc_y <= 0 or _nc_y >= max_y:
        _nc_dy = -_nc_dy
        _nc_y = max(0, min(max_y, _nc_y))
    text(_NC_TEXT, int(_nc_x), int(_nc_y))


SCREENS = [draw_live, draw_today, draw_history]
screen_index = 0


# --------------------------------------------------------------- button --

_was_pressed = False
_press_ms = None


def service_button():
    global _was_pressed, _press_ms, screen_index
    pressed = button.value() == 0
    now = time.ticks_ms()
    if pressed and not _was_pressed:
        _press_ms = now
    elif not pressed and _was_pressed:
        if _press_ms is not None and time.ticks_diff(now, _press_ms) >= DEBOUNCE_MS:
            screen_index = (screen_index + 1) % len(SCREENS)
    _was_pressed = pressed


# ------------------------------------------------------------------ main --

def main():
    global connected
    led.off()
    led.on()
    time.sleep_ms(80)
    led.off()  # quick hello blink so you know it booted

    last_hello_ms = time.ticks_ms()
    while True:
        for line in poll_serial_lines():
            handle_message(line)

        # Identifies this board on the serial line regardless of whether
        # the host has found it yet — lets host_monitor.py tell this board
        # apart from any other MicroPython board plugged in at the same time
        if time.ticks_diff(time.ticks_ms(), last_hello_ms) >= HELLO_PERIOD_MS:
            last_hello_ms = time.ticks_ms()
            print(json.dumps({"t": "hello", "device": DEVICE_ID}))

        if last_msg_ms is not None and time.ticks_diff(time.ticks_ms(), last_msg_ms) > NOT_CONNECTED_TIMEOUT_MS:
            connected = False

        service_button()
        service_led()
        service_shift()
        service_dim()

        draw_gol_background()
        if connected:
            SCREENS[screen_index]()
        else:
            draw_not_connected()
        oled.show()

        time.sleep_ms(100)


if __name__ == "__main__":
    main()
