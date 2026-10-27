# Zoro

Zoro is a local-first workflow assistant for coding sessions.

It provides:
- a Flask backend API
- a React + Vite frontend
- a `zoro` CLI for plan tracking and rule evidence

## Requirements

- Python `3.10+`
- Conda or Mamba (recommended)
- Node.js `20+`
- npm
- `OPENAI_API_KEY`

## Quickstart (Recommended)

From this repository root:

```bash
make setup
cp .env.example .env
# edit .env and set OPENAI_API_KEY
make dev
```

Then open `http://127.0.0.1:5274`.

Notes:
- `make setup` creates/reuses Conda env `zoro` and installs backend/frontend deps.
- `make dev` runs `conda run -n zoro zoro-api`.
- You do **not** need to manually run `conda activate zoro` for Make commands.

## Core Commands

```bash
make setup          # install dependencies into Conda env + frontend
make dev            # start backend + frontend
make backend        # backend only
make test           # backend tests
make build-frontend # frontend production build
make clean          # clear local build/cache outputs
```

## Use Zoro in Another Repository

Install Zoro once from this repo, then in any target repo:

```bash
cd /path/to/target-repo
conda run -n zoro zoro init --user-name "Your Name" --chat-history-source codex
conda run -n zoro zoro-api --backend-only
```

Supported chat sources:
- `codex`
- `claude` (Claude Code)
- `cline`
- `cursor`

If frontend is not auto-launched from the target repo:

```bash
cd /path/to/this-zoro-repo/frontend
npm run dev
```

## Per-Task Chat Source (Current UX)

Each session can use a different coding agent source.

1. Click `+` to create/select a session.
2. Set that session’s `chat_history_source` (`codex`, `claude`, `cline`, or `cursor`).
3. Start polling with Run/Play.

Zoro reads chat history from:
- Codex: `~/.codex/sessions`
- Claude Code: `~/.claude/projects`
- Cline: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/tasks/*/api_conversation_history.json`
- Cursor: `~/Library/Application Support/Cursor/User/workspaceStorage/*/chatSessions/*.json`

For Codex, Claude Code, and Cursor, Zoro first tries matching sessions for the current workspace path, then falls back to the latest session.

## Automatic Behavior

- Pressing Run/Play triggers plan preparation automatically:
  - no plan yet → extract plan
  - plan exists but no attached rules → enrich plan with rules
- Supervisor auto-runs during live polling once enough new tokens accumulate.
- Rule Learning auto-runs during live polling while there is more transcript window to analyze.
- Both Supervisor and Rule Learning can also be run manually from their panel buttons.

## Initial Rules: JSON Format

You have two good options:
- markdown-first: drop `.md` files into `.zoro/rules/unstructured/`, then structure them in UI
- easiest: use **Rules Management** UI (`Add rule`)
- direct: add items via API or by editing `.zoro/rules/structured/knowledge_base.json`

### Option 0: Markdown → Structured Rules

Yes — this is supported and is great for bulk onboarding.

1. Add one or more markdown files under:

```bash
.zoro/rules/unstructured/
```

2. Open **Rules Management → Unstructured Files**.
3. Click **Structure** for one file, or **Structure all pending files**.
4. Zoro parses those `.md` files and writes structured items into:

```bash
.zoro/rules/structured/knowledge_base.json
```

Optional:
- use **Structure repo AGENTS.md** to ingest the current repo’s root `AGENTS.md` directly
- the raw source snapshot is archived under `.zoro/rules/unstructured/processed/`

### Option A: API (`POST /api/kb/items`)

Minimum required fields:

```json
{
  "type": "rule",
  "category": "workflow",
  "title": "Write tests before refactor",
  "content": "Add/adjust tests first, then refactor safely."
}
```

Common optional fields:
- `context`, `evidence`
- `confidence` (default `0.5`)
- `decay` (default `0.5`)
- `confidence_reasoning`, `decay_reasoning`
- `usage_count` (default `0`)
- `is_favorite` (default `false`)
- `is_strict` (default `false`)
- `is_testable` (default `false`)

### Option B: File (`.zoro/rules/structured/knowledge_base.json`)

Create this file if it does not exist:

```json
{
  "items": [
    {
      "item_id": "rule-001",
      "type": "rule",
      "category": "workflow",
      "title": "Write tests before refactor",
      "content": "Add/adjust tests first, then refactor safely.",
      "context": "Applies to backend and frontend refactors",
      "evidence": null,
      "confidence": 0.8,
      "decay": 0.2,
      "confidence_reasoning": "Repeatedly prevented regressions",
      "decay_reasoning": "Stable project practice",
      "source_file": "manual",
      "usage_count": 0,
      "is_favorite": true,
      "is_strict": false,
      "is_testable": true,
      "created_at": "2026-01-01T00:00:00"
    }
  ],
  "categories": []
}
```

You can keep this minimal (only required fields) when seeding; missing optional fields are filled with defaults when added through API/UI.

## Config

Set default chat source in `.zoro/config.json`:

```json
{
  "chat_history_source": "codex"
}
```

## Troubleshooting

- `Conda env 'zoro' was not found` → run `make setup`.
- `OpenAI API key not found` → set `OPENAI_API_KEY` in `.env`.
- Frontend cannot reach backend → verify ports `5010` and `5274`.
- No chat history found → confirm the chosen source and local history files exist.
