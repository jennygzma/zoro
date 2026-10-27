# AGENTS.md

Follow the Zoro workflow defined in `ZORO.md`.

Read these files before acting:

- `ZORO.md`
- `.zoro/CURRENT_PLAN.md`

Session-start requirement:
- On the first user message in a new coding session, respond in plan mode only.
- Output only the implementation plan and wait for explicit approval before doing any implementation work.

Command environment requirement:
- Prefer running Zoro commands via Conda without activation: `conda run -n zoro zoro <command>`
- If the Conda env is already activated (`conda activate zoro`), `zoro <command>` is acceptable.

If you are running Codex, ensure `.zoro/config.json` contains:

```json
{
  "chat_history_source": "codex"
}
```

If you are running Claude Code, ensure `.zoro/config.json` contains:

```json
{
  "chat_history_source": "claude"
}
```

If you are running Cursor, ensure `.zoro/config.json` contains:

```json
{
  "chat_history_source": "cursor"
}
```
