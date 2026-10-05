# Agent monitor

Shows a live count of actively-generating Claude Code sessions (including
subagents and background/workflow-spawned agents) on the Desk Buddy OLED,
separate from the Desk Buddy software itself, with a continuously-simulated
Game of Life running behind every screen. Flashes the LED once per
top-level session that finishes a turn. Button cycles between a live view,
today's totals, and a short history.

```
  Mac ──Claude Code hooks──► host_monitor.py ──USB serial, JSON lines──► device_main.py ──► OLED + LED + button
       (UserPromptSubmit/Stop/                                           (renders screens,
        Subagent* hooks bracket                                          Game of Life,
        who's actively generating)                                       flashes LED)
```

Two halves, both in this folder:

- **`host_monitor.py`** runs on your Mac. Drains a small event queue written
  by global Claude Code hooks (see "How 'running' is tracked" below) and
  streams the counts over USB serial.
- **`device_main.py`** runs on the board as `main.py`. Reads those counts
  off the same USB serial connection non-blockingly, draws the screens and
  the background Game of Life simulation, and flashes the LED when a
  top-level session stops.

## Hardware

Same wiring as Desk Buddy's OLED build — this runs on that hardware, just
with different software:

| Part | XIAO pin |
|---|---|
| OLED SDA | D4 |
| OLED SCL | D5 |
| Button | D3 |
| LED | D2 |

## Install

```sh
nix-shell -p mpremote python3Packages.pyserial

# find the board
ls /dev/cu.usbmodem*

# back up whatever's currently main.py (skip if you've already done this)
mpremote connect /dev/cu.usbmodemXXXX exec '
import os
if "main_deskbuddy.py" not in os.listdir():
    os.rename("main.py", "main_deskbuddy.py")
'

# install this instead (ssd1306.py lives one directory up, in micropython/esp32-c3/)
mpremote connect /dev/cu.usbmodemXXXX cp ../ssd1306.py : + cp device_main.py :main.py + reset
```

To go back to Desk Buddy later: rename `main_deskbuddy.py` back to `main.py`
on the board.

## Run

The host side also needs the two hook scripts registered in
`~/.claude/settings.json` (see "How 'running' is tracked"). In this repo
owner's own setup they're version-controlled in the `nixos-config` repo's
`dotfiles/` and symlinked into `~/.claude/` via home-manager; adapt the
hook registration to wherever you keep yours.

```sh
python3 host_monitor.py
```

It auto-finds the board's port via a self-identifying hello-beacon (so it
picks the right board even with other MicroPython devices plugged in) and
reconnects automatically if the board gets unplugged. `--port` pins a
specific port; `--interval` changes the poll rate (default 2s).

The board shows a "not connected" screen whenever it hasn't heard from
`host_monitor.py` in the last 6 seconds — unplugged, host script not
running, or the board just rebooted. That screen bounces around the full
display (it can sit unchanged for hours — the Mac asleep, the service not
started yet — so it gets its own full-range burn-in treatment rather than
the subtler one everything else gets).

## Screens (short button press cycles through them)

1. **Live** — the big running-agent count and its "agents" label (one
   unit), and the "N turns" line (a separate unit), each independently
   bouncing left-right and never overlapping or reordering (see "Burn-in"
   below for why).
2. **Today** — peak concurrent running today, finished (turns) today, and
   running right now.
3. **History** — a bar per day for the last 7 days (sessions started that
   day, ps-based), tallest = busiest day. Needs at least one day rollover
   to have anything to show.

A live Conway's Game of Life simulation (B3/S23 rules, toroidal wraparound,
seeded with real methuselah patterns and re-seeded if it goes stagnant)
runs behind all of the above, continuously, on the device's own CPU.

Both halves track "today" independently right now (the device keeps its
own small `stats.json` so history survives reboots and doesn't depend on
the host's file). They agree because both use the same `date` string the
host sends with every message.

## How "running" is tracked

"Running" means *actively generating a response right now* — not just a
process sitting open idle. It's bracketed by global hooks registered in
`~/.claude/settings.json`:

- **Start a bracket:** `UserPromptSubmit` (a turn begins), `SubagentStart`
  (a subagent spawns — including background/workflow-spawned ones, which
  go through the identical mechanism), and also `PostToolUse`/
  `PostToolUseFailure` (a tool call happening proves the session is still
  active, which self-heals a session that was already mid-turn when
  `host_monitor.py` itself was last restarted — its in-memory state isn't
  persisted across restarts).
- **End a bracket:** `Stop`, `StopFailure`, `SubagentStop`.

Subagent hook payloads share their *parent* session's `session_id` but
carry their own unique `agent_id`, so the hook scripts key on `agent_id`
when present and fall back to `session_id` for top-level turns.

A `start` with no matching `stop` ever arriving (a killed/crashed session,
a lost async hook write) is force-expired after 30 minutes rather than
leaking the "running" count upward forever.

Three related but distinct counters, all derived from the same event
stream:

- **`stopped_today` ("turns")** — every finished bracket: top-level turns
  *and* subagent completions.
- **`session_stopped_today`** — top-level turns only. Drives the LED flash,
  so a busy background workflow spawning many quick subagents doesn't
  flash the LED for each one.
- **`peak_running_today`** — the highest concurrent "running" count seen
  today.

`started_today` (used only for the History bar chart) is the one thing
still tracked the old way, via `ps`: a process counts if it's a real
Claude Code CLI process (not the separate desktop app, not
`--bg-spare`/`daemon run`/`agents` infrastructure), de-duplicated across
the pty-host-wrapper-plus-wrapped-process pair a single session can show
up as. See `classify()` in `host_monitor.py`.

## Burn-in

This is a small OLED, so the display deliberately:

- stays mostly black with thin text/bars rather than bright filled areas
  (an OLED only wears where pixels are actually lit), with a solid
  background rectangle cleared behind every piece of text so the Game of
  Life underneath can't blend into it and hurt legibility
- nudges the whole layout a few pixels every 5 minutes (all screens)
- drops contrast further if the numbers haven't changed in 10 minutes
  (back to full brightness as soon as something does)
- the Live screen's two units (agent count + label, and the turns line)
  each independently bounce left-right across the screen on top of that —
  they're the highest-ink elements on the device, so they get more than
  the shared subtle nudge. Vertical position is pinned per unit (agent
  count always above, turns always below, with a fixed gap) rather than
  independently bounced too: the two units' heights already use 58 of the
  screen's 64px, leaving no real room for both to also wiggle vertically
  without risking exactly the overlap/reordering this is designed to
  avoid. Both units cancel out the shared global nudge above for their own
  positioning, rather than stacking it on top of their own bounce — the
  combination was otherwise pushing them 1-3px past the screen edge.
- the "not connected" screen gets a dedicated full-screen bounce (see
  "Run" above) since it's the one screen that can plausibly sit static for
  hours at a time

## Known limits

- Daily totals (`started_today`, and the History bar chart built from it)
  are a same-machine, same-user, ps-based view. If you run Claude Code on
  more than one machine, this only sees the one it's running on.
- `host_monitor.py`'s "active" set is in-memory only — not persisted
  across restarts. A session already mid-turn when it restarts won't show
  as running until its next tool call or prompt (see "How 'running' is
  tracked" above for the self-healing mitigation).
- LED flashes are queued and played back at a steady pace (a burst of
  5+ simultaneous stops is capped so it can't queue forever).
