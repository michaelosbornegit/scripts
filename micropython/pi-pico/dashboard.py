## CO2 / temp / humidity dashboard rendering for a 128x64 SSD1306, no network required.

_SEGMENTS = {
    '0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd',
    '4': 'fgbc', '5': 'afgcd', '6': 'afgecd', '7': 'abc',
    '8': 'abcdefg', '9': 'abcdfg',
}

def draw_digit(fb, x, y, w, h, t, ch, color=1):
    half = h // 2
    arm = half - t - t // 2
    segs = {
        'a': (x + t, y, w - 2 * t, t),
        'g': (x + t, y + half - t // 2, w - 2 * t, t),
        'd': (x + t, y + h - t, w - 2 * t, t),
        'f': (x, y + t, t, arm),
        'b': (x + w - t, y + t, t, arm),
        'e': (x, y + half + t - t // 2, t, arm),
        'c': (x + w - t, y + half + t - t // 2, t, arm),
    }
    for key in _SEGMENTS.get(ch, ''):
        rx, ry, rw, rh = segs[key]
        fb.fill_rect(rx, ry, rw, rh, color)

def draw_number(fb, x, y, value, digit_w=16, digit_h=20, thickness=3, gap=3, color=1):
    s = str(int(value))
    for ch in s:
        draw_digit(fb, x, y, digit_w, digit_h, thickness, ch, color)
        x += digit_w + gap
    return x - gap

def number_width(value, digit_w=16, gap=3):
    n = len(str(int(value)))
    return n * digit_w + (n - 1) * gap

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def co2_status(co2):
    if co2 < 800:
        return 'GOOD'
    if co2 < 1200:
        return 'FAIR'
    return 'POOR'

def draw_gauge(fb, x, y, w, h, frac, color=1):
    fb.rect(x, y, w, h, color)
    filled = int(clamp(frac, 0.0, 1.0) * (w - 2))
    if filled > 0:
        fb.fill_rect(x + 1, y + 1, filled, h - 2, color)

def draw_sparkline(fb, x, y, w, h, history, lo, hi, color=1):
    n = len(history)
    if n == 0:
        return
    start = x + max(0, w - n)
    for i, v in enumerate(history[-w:]):
        frac = clamp((v - lo) / float(hi - lo), 0.0, 1.0)
        bar_h = max(1, int(frac * h))
        fb.vline(start + i, y + h - bar_h, bar_h, color)

def render(fb, co2, temp_f, humidity, history, width=128, height=64):
    fb.fill(0)

    # Header
    fb.fill_rect(0, 0, width, 10, 1)
    title = 'CO2 MONITOR'
    fb.text(title, (width - len(title) * 8) // 2, 1, 0)

    # Big CO2 number + ppm label, centered as a group
    num_w = number_width(co2)
    group_w = num_w + 6 + 3 * 8
    nx = (width - group_w) // 2
    ny = 12
    end_x = draw_number(fb, nx, ny, co2, digit_h=20, thickness=3)
    fb.text('ppm', end_x + 6, ny + 7, 1)

    # Gauge + status word
    gauge_y = 37
    gauge_w = 64
    frac = (co2 - 400) / 1600.0
    draw_gauge(fb, 4, gauge_y, gauge_w, 6, frac)
    status = co2_status(co2)
    fb.text(status, 4 + gauge_w + 10, gauge_y - 1, 1)

    # Sparkline trend (recent CO2 history)
    draw_sparkline(fb, 6, 45, 116, 8, history, 400, 2000)

    # Divider
    fb.hline(0, 54, width, 1)

    # Temp / humidity row
    temp_str = '{:.1f}F'.format(temp_f)
    hum_str = '{:.0f}% RH'.format(humidity)
    fb.text(temp_str, 4, 56, 1)
    fb.vline(64, 56, 8, 1)
    fb.text(hum_str, 70, 56, 1)

    fb.show()
