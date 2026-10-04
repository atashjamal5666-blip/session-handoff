# session-handoff

Every turn of a Claude Code session re-reads the whole conversation. At 400k tokens a
simple "ok, continue" costs about ten times what it did at the start. Long sessions get
expensive quietly.

This plugin hands a long session over to a fresh one before that happens.

- **At 40%, 70% and 85% of the context window**, a Stop hook asks Claude to write (or
  refresh) `HANDOFF.md` in the project folder, then keep working. It never interrupts.
- **When a new session opens in that folder**, a SessionStart hook reads `HANDOFF.md`
  into it. No model call, just a file read.
- **The handoff stays small**: four headings (DONE, NEXT, BLOCKED, FILES), under 2 KB.
  Over 4 KB it is truncated, and Claude offers to cut it back.

You decide when to switch. The advice: switch at a seam (a job finished, the next one
different), never at a number.

## Install

```
/plugin install session-handoff
```

Needs Python 3 on the PATH (`python3` or `python`). No dependencies, no network.

## Settings

- `CLAUDE_CONTEXT_WINDOW`: the window size in tokens. Without it the hook assumes 200k,
  and switches to 1M as soon as a turn goes past 200k.
- Home and temp folders are skipped: no project there, nowhere to put a handoff.
- State (which band already fired, per session) lives in `~/.claude/session-handoff/`.

## Why

Built by a one-person studio in Montréal that runs its whole business on scheduled
Claude Code sessions. Used daily since September 2026.

MIT licence.
