#!/usr/bin/env python3
"""Agent monitor — host side.

Watches for running Claude Code CLI sessions on this machine and streams
their counts over USB serial to a XIAO ESP32C3 running device_main.py, so
Desk Buddy's OLED can show a live "how many agents are running" readout.

    nix-shell -p python3Packages.pyserial
    python3 host_monitor.py

It auto-finds the board's serial port and reconnects if it's unplugged.
Pass --port to pin a specific one if more than one board is attached.

"Running" means *actively generating a response right now* — not just a
process sitting open idle. It's bracketed by hooks registered in
~/.claude/settings.json: UserPromptSubmit/SubagentStart
(../agent-monitor-start-hook) marks a key active, Stop/StopFailure/
SubagentStop (../agent-monitor-stop-hook) marks it inactive again — the
same signal the ghostty-bg terminal green/red indicator uses. These fire
for subagents and background/workflow-spawned agents too, not just
top-level sessions, since they all go through the same hook pipeline.
Subagent hook payloads share their PARENT session's session_id but carry
a unique agent_id, so the hook scripts key on agent_id when present.
This script drains the small JSON-lines queue file those hooks append to
and keeps a live dict of currently-active keys -> start time; an entry
with no matching stop within STALE_ACTIVE_S is force-expired so a
crashed/killed session or a lost async hook write can't leak forever and
inflate "running" indefinitely.

"stopped_today" (the on-screen "tasks" tally) counts every finished turn
AND every finished subagent. "session_stopped_today" counts only
top-level session stops, not subagents — it drives the board's LED flash,
so a busy background workflow spawning many quick subagents doesn't
flash the LED for each one.

"Started today" still comes from watching `ps` for live Claude Code
processes (first-seen-today), since that's a separate question from
whether a session is generating right now.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

STATE_DIR = os.path.expanduser("~/.cache/claude-agent-monitor")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
LIVE_FILE = os.path.join(STATE_DIR, "live.json")  # full current snapshot,
# rewritten every tick — for any other consumer (a desktop widget, a web
# page) that wants this data without also owning the serial connection
SESSION_EVENTS_LOG = os.path.join(STATE_DIR, "session_events.log")  # written
# by ../agent-monitor-start-hook and ../agent-monitor-stop-hook, one JSON
# line per start/stop event; drained here
HISTORY_DAYS = 14
SAVE_INTERVAL_S = 30  # safety save even if nothing changed
STALE_ACTIVE_S = 30 * 60  # bounds how long a leaked "start" (no matching
# Stop ever arrives -- a killed/crashed session, a lost async hook write)
# can inflate "running" before it's forcibly expired

# The real Claude Code CLI lives under these paths, or as bare "claude" on
# PATH. The separate Claude *desktop* app under /Applications/Claude.app is
# deliberately not matched — it's a different product, not a CLI session.
CLI_PATH_PREFIXES = (
    os.path.expanduser("~/.local/bin/claude"),
    os.path.expanduser("~/.local/share/claude/"),
)


def is_cli_binary(argv0):
    return argv0 == "claude" or argv0.startswith(CLI_PATH_PREFIXES)


def classify(pid, cmd):
    """Return a dedupe key for a real, user-facing session, or None if this
    process is infrastructure (an idle spare-pool worker, the background
    daemon, the agent-panel process) rather than a session itself."""
    argv0, _, rest = cmd.partition(" ")
    if not is_cli_binary(argv0):
        return None

    # idle pre-warmed workers waiting to be claimed, not a started session
    if "--bg-spare" in rest:
        return None
    # the background daemon supervisor, not a session itself
    if re.search(r"\bdaemon\s+run\b", rest):
        return None
    # the agent-panel/management subcommand, not a session itself
    if re.match(r"^agents\b", rest):
        return None

    # A session can show up as two processes — a pty-host wrapper plus the
    # real process it wraps — so key on whatever identifies the underlying
    # session rather than the pid, so the pair collapses to one.
    m = re.search(r"--session-id (\S+)", rest)
    if m:
        return "session:" + m.group(1)
    m = re.search(r"--resume (\S+\.jsonl)", rest)
    if m:
        return "resume:" + m.group(1)
    m = re.search(r"-n (\S+)", rest)
    if m:
        return "name:" + m.group(1)
    # a plain foreground session with nothing on disk to key on yet
    return "pid:" + str(pid)


def current_sessions():
    """{dedupe_key: representative command} for every live session right now."""
    out = subprocess.run(
        ["ps", "-axwwo", "pid=,command="],  # -ww: don't truncate long commands
        capture_output=True, text=True, check=True,
    ).stdout
    sessions = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        pid_str, _, cmd = line.partition(" ")
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        key = classify(pid, cmd)
        if key:
            sessions.setdefault(key, cmd)
    return sessions


def today():
    return time.strftime("%Y-%m-%d")


def load_state():
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {
            "date": today(),
            "started_today": 0,
            "stopped_today": 0,
            "session_stopped_today": 0,
            "peak_running_today": 0,
            "seen_today": [],
            "history": [],
        }
    state.setdefault("session_stopped_today", 0)  # added after initial release
    state.setdefault("peak_running_today", 0)  # added after initial release
    return state


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def save_live(msg):
    # best-effort, rewritten every tick; not worth retrying on failure
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = LIVE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(dict(msg, updated_at=time.time()), f)
        os.replace(tmp, LIVE_FILE)
    except OSError:
        pass


def drain_session_events():
    """Return and clear the start/stop-hook queue file as a list of parsed
    events, since the last call. Renaming rather than truncating means a
    hook invocation racing this can't lose an event — it just recreates the
    file fresh under the original path."""
    tmp = SESSION_EVENTS_LOG + ".draining"
    try:
        os.rename(SESSION_EVENTS_LOG, tmp)
    except OSError:
        return []  # nothing has fired since the last drain
    events = []
    try:
        with open(tmp) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except ValueError:
                    continue
    finally:
        os.remove(tmp)
    return events


def roll_day_if_needed(state):
    d = today()
    if state["date"] != d:
        state["history"].append({
            "date": state["date"],
            "started": state["started_today"],
            "stopped": state["stopped_today"],
        })
        state["history"] = state["history"][-HISTORY_DAYS:]
        state.update(date=d, started_today=0, stopped_today=0,
                      session_stopped_today=0, peak_running_today=0, seen_today=[])
    return state


DEVICE_ID = "desk-buddy-agent-monitor"  # must match device_main.py's DEVICE_ID
HELLO_SCAN_S = 3.0  # device_main.py announces itself every 2s; give it a margin


def open_serial(port, baud=115200, timeout=0):
    import serial
    return serial.Serial(port, baud, timeout=timeout)


def find_port():
    """Scan every /dev/cu.usbmodem* port for this specific board's hello
    beacon, rather than guessing from port order — more than one MicroPython
    board can be plugged in at once, and port names aren't stable."""
    for candidate in sorted(glob.glob("/dev/cu.usbmodem*")):
        try:
            with open_serial(candidate, timeout=0.3) as probe:
                deadline = time.time() + HELLO_SCAN_S
                buf = b""
                while time.time() < deadline:
                    chunk = probe.read(256)
                    if not chunk:
                        continue
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        try:
                            msg = json.loads(line)
                        except ValueError:
                            continue
                        if msg.get("t") == "hello" and msg.get("device") == DEVICE_ID:
                            return candidate
        except Exception:
            continue  # port busy, permission denied, unplugged mid-scan, etc.
    return None


def run(interval, port_override):
    import serial

    state = load_state()
    state = roll_day_if_needed(state)
    seen_today = set(state["seen_today"])
    active_sessions = {}  # key -> start time (time.time()); keys currently
    # between a start (UserPromptSubmit/SubagentStart) and a matching stop
    # (Stop/StopFailure/SubagentStop) — i.e. actively generating right now.
    # Not persisted across restarts. A "stop" for an unknown key is a
    # harmless no-op discard, but a "start" with NO matching stop ever
    # arriving (a killed/crashed session, a lost async hook write) would
    # otherwise leak forever and inflate "running" indefinitely — see
    # STALE_ACTIVE_S below, which bounds that.

    first_tick = True  # on the very first poll, don't claim everything
    # already running just "started" — only count genuinely new sessions
    # from here on
    ser = None
    port = None
    last_save = time.time()
    drain_session_events()  # discard any backlog from before this run started

    print("Agent monitor starting. Ctrl-C to stop.")
    while True:
        try:
            if ser is None:
                port = port_override or find_port()
                if not port:
                    print("No board found on /dev/cu.usbmodem*, waiting...")
                    time.sleep(interval)
                    continue
                try:
                    ser = open_serial(port)
                    print(f"Connected to {port}")
                except serial.SerialException as e:
                    print(f"Couldn't open {port}: {e}, retrying...")
                    time.sleep(interval)
                    continue

            state = roll_day_if_needed(state)
            sessions = current_sessions()
            current_keys = set(sessions)

            if first_tick:
                # count anything already running as "seen" without
                # claiming we know it started just now
                seen_today |= current_keys
                first_tick = False
            else:
                newly_started = current_keys - seen_today
                if newly_started:
                    state["started_today"] += len(newly_started)
                    seen_today |= newly_started
            state["seen_today"] = sorted(seen_today)

            stopped = 0
            session_stopped = 0
            for event in drain_session_events():
                sid = event.get("session_id")
                etype = event.get("type")
                if not sid or not etype:
                    continue
                if etype == "start":
                    active_sessions[sid] = time.time()
                elif etype == "stop":
                    active_sessions.pop(sid, None)
                    stopped += 1
                    if event.get("kind") != "subagent":
                        session_stopped += 1
            if stopped:
                state["stopped_today"] += stopped
                print(f"  {stopped} turn(s) finished (Stop hook)")
            if session_stopped:
                state["session_stopped_today"] += session_stopped

            now = time.time()
            stale = [k for k, t0 in active_sessions.items() if now - t0 > STALE_ACTIVE_S]
            for k in stale:
                del active_sessions[k]
            if stale:
                print(f"  {len(stale)} stale active session(s) expired (no Stop within {STALE_ACTIVE_S}s)")

            state["peak_running_today"] = max(state["peak_running_today"], len(active_sessions))

            msg = {
                "t": "state",
                "date": state["date"],
                "running": len(active_sessions),
                "started_today": state["started_today"],
                "stopped_today": state["stopped_today"],
                "session_stopped_today": state["session_stopped_today"],
                "peak_running_today": state["peak_running_today"],
            }
            # active_keys/active_ages are diagnostic only -- not sent over
            # serial, just dumped to live.json so a leaked/stuck entry can
            # actually be inspected (which key, how old) instead of only
            # ever seeing the aggregate count.
            save_live(dict(
                msg,
                active_keys={k: round(now - t0, 1) for k, t0 in active_sessions.items()},
            ))
            try:
                ser.write((json.dumps(msg) + "\n").encode())
            except serial.SerialException:
                print("Board disconnected, will retry...")
                ser.close()
                ser = None

            print(
                f"\rrunning={msg['running']:<3} "
                f"started today={msg['started_today']:<4} "
                f"stopped today={msg['stopped_today']:<4}",
                end="", flush=True,
            )

            if time.time() - last_save > SAVE_INTERVAL_S:
                save_state(state)
                last_save = time.time()

        except KeyboardInterrupt:
            print("\nStopping.")
            save_state(state)
            return
        except Exception as e:
            print(f"\nUnexpected error, continuing: {e}")

        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="serial port, auto-detected if omitted")
    parser.add_argument("--interval", type=float, default=2.0, help="poll interval in seconds")
    args = parser.parse_args()
    run(args.interval, args.port)
