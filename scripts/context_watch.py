#!/usr/bin/env python3
"""Stop hook: watch the context window, arm a handoff before the session gets expensive.

Every turn re-reads the whole conversation, so a long session costs more per step the
longer it runs. This hook reads the real token count of the last turn from the transcript
and, when the session crosses 40, 70 or 85 percent of the window, asks Claude to write or
refresh HANDOFF.md in the project folder. It fires once per band per session.

It never interrupts the work: Claude writes the file and carries on. You decide when to
switch sessions; the companion SessionStart hook hands the file to the next one.

Window size: CLAUDE_CONTEXT_WINDOW if set, otherwise 200k, or 1M once a turn has gone past 200k.
"""
import json
import os
import sys
import tempfile

BANDS = [
    (40, "Write it now and keep working. No need to stop."),
    (70, "Refresh it. Switch at the next clean seam - a finished sub-job."),
    (85, "Refresh it. Every turn now re-reads most of the window. Switch soon."),
]


def context_tokens(transcript_path):
    """Context size of the most recent turn, from its usage record."""
    if not transcript_path or not os.path.exists(transcript_path):
        return None
    total = None
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                usage = (entry.get("message") or {}).get("usage")
                if not isinstance(usage, dict):
                    continue
                n = (
                    usage.get("input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                )
                if n > 0:
                    total = n
    except OSError:
        return None
    return total


def window(used):
    env = os.environ.get("CLAUDE_CONTEXT_WINDOW")
    if env and env.isdigit():
        return int(env)
    return 1000000 if used > 200000 else 200000


def state_file(session_id):
    base = os.path.join(os.path.expanduser("~"), ".claude", "session-handoff")
    try:
        os.makedirs(base, exist_ok=True)
    except OSError:
        return None
    safe = "".join(c for c in (session_id or "unknown") if c.isalnum() or c in "-_")
    return os.path.join(base, safe + ".band")


def already_fired(path, pct):
    if not path or not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            return int((fh.read() or "0").strip()) >= pct
    except (OSError, ValueError):
        return False


def record(path, pct):
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(str(pct))
    except OSError:
        pass


def skipped(cwd):
    """No real project folder means nowhere sensible to put a handoff."""
    norm = os.path.normcase(os.path.abspath(cwd))
    home = os.path.normcase(os.path.expanduser("~"))
    temp = os.path.normcase(tempfile.gettempdir())
    return norm == home or norm.startswith(temp)


def main():
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0

    cwd = data.get("cwd") or os.getcwd()
    if skipped(cwd):
        return 0

    used = context_tokens(data.get("transcript_path"))
    if not used:
        return 0

    pct = used * 100 // window(used)
    band = None
    for threshold, advice in BANDS:
        if pct >= threshold:
            band = (threshold, advice)
    if not band:
        return 0

    threshold, advice = band
    sf = state_file(data.get("session_id"))
    if already_fired(sf, threshold):
        return 0
    record(sf, threshold)

    handoff = os.path.join(cwd, "HANDOFF.md")
    verb = "Refresh" if os.path.exists(handoff) else "Write"

    reason = (
        "Context is at {pct}% ({used:,} tokens), past the {threshold}% mark. "
        "{verb} {path} now, then carry on with whatever you were doing.\n\n"
        "Keep it under 2 KB - it is a handoff, not a diary. Four headings only:\n"
        "  DONE - what this session finished\n"
        "  NEXT - the immediate next step\n"
        "  BLOCKED - anything parked or waiting on the user\n"
        "  FILES - the paths a fresh session must open first\n\n"
        "Longer history belongs in the project's own notes, not here.\n"
        "Then tell the user in one line: the percentage, that the handoff is written, "
        "and this - {advice}"
    ).format(pct=pct, used=used, threshold=threshold, verb=verb, path=handoff, advice=advice)

    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "systemMessage": "Context {pct}% ({used:,} tok) - arming HANDOFF.md".format(pct=pct, used=used),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
