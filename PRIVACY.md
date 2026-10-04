# Privacy

lean-handoff collects nothing and sends nothing.

- It makes no network calls and no model calls.
- It reads the current session's transcript file (the path Claude Code passes to the hook)
  only to count tokens, and reads `HANDOFF.md` in your project folder.
- It writes one small number per session to `~/.claude/lean-handoff/` (the last band that
  fired) and never anything else.

Nothing leaves your machine.
