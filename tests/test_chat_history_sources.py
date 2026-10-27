import importlib
import json
import os
from types import SimpleNamespace

from backend.api import create_app


def _write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_get_chat_history_source_accepts_claude(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _write_text(
        tmp_path / ".zoro" / "config.json",
        json.dumps({"chat_history_source": "claude"}),
    )

    utils = importlib.import_module("backend.utils")

    assert utils.get_chat_history_source_from_config() == "claude"


def test_get_chat_history_source_accepts_cursor(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _write_text(
        tmp_path / ".zoro" / "config.json",
        json.dumps({"chat_history_source": "cursor"}),
    )

    utils = importlib.import_module("backend.utils")

    assert utils.get_chat_history_source_from_config() == "cursor"


def test_get_chat_history_source_invalid_defaults_to_cline(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _write_text(
        tmp_path / ".zoro" / "config.json",
        json.dumps({"chat_history_source": "unsupported"}),
    )

    utils = importlib.import_module("backend.utils")

    assert utils.get_chat_history_source_from_config() == "cline"


def test_find_latest_chat_history_path_for_claude(monkeypatch, tmp_path):
    module = importlib.import_module("backend.visualization.services.rule_learning_agent")

    root = tmp_path / ".claude" / "projects"
    older = root / "project-a" / "session-1.jsonl"
    newer = root / "project-b" / "session-2.jsonl"

    _write_text(older, "{}\n")
    _write_text(newer, "{}\n")

    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))

    monkeypatch.setattr(module, "CLAUDE_CODE_PROJECTS_DIR", root)
    monkeypatch.setattr(module, "get_chat_history_source_from_config", lambda: "claude")

    assert module.find_latest_chat_history_path() == newer


def test_find_latest_codex_session_prefers_current_workspace(monkeypatch, tmp_path):
    module = importlib.import_module("backend.visualization.services.rule_learning_agent")

    root = tmp_path / ".codex" / "sessions"
    workspace = tmp_path / "workspace-a"
    workspace.mkdir(parents=True, exist_ok=True)

    matching = root / "2026" / "10" / "match.jsonl"
    non_matching = root / "2026" / "10" / "other.jsonl"

    _write_text(
        matching,
        json.dumps(
            {
                "type": "session_meta",
                "payload": {"cwd": str(workspace)},
            }
        )
        + "\n",
    )
    _write_text(
        non_matching,
        json.dumps(
            {
                "type": "session_meta",
                "payload": {"cwd": str(tmp_path / "workspace-b")},
            }
        )
        + "\n",
    )

    os.utime(matching, (100, 100))
    os.utime(non_matching, (200, 200))

    monkeypatch.setattr(module, "CODEX_SESSIONS_DIR", root)

    assert module.find_latest_chat_history_path(source="codex", cwd=workspace) == matching


def test_find_latest_claude_session_prefers_current_workspace(monkeypatch, tmp_path):
    module = importlib.import_module("backend.visualization.services.rule_learning_agent")

    root = tmp_path / ".claude" / "projects"
    workspace = tmp_path / "workspace-a"
    workspace.mkdir(parents=True, exist_ok=True)

    matching = root / "project-a" / "match.jsonl"
    non_matching = root / "project-b" / "other.jsonl"

    _write_text(
        matching,
        json.dumps({"type": "user", "cwd": str(workspace), "message": {"role": "user", "content": []}})
        + "\n",
    )
    _write_text(
        non_matching,
        json.dumps(
            {
                "type": "user",
                "cwd": str(tmp_path / "workspace-b"),
                "message": {"role": "user", "content": []},
            }
        )
        + "\n",
    )

    os.utime(matching, (100, 100))
    os.utime(non_matching, (200, 200))

    monkeypatch.setattr(module, "CLAUDE_CODE_PROJECTS_DIR", root)

    assert module.find_latest_chat_history_path(source="claude", cwd=workspace) == matching


def test_find_latest_cursor_session_prefers_current_workspace(monkeypatch, tmp_path):
    module = importlib.import_module("backend.visualization.services.rule_learning_agent")

    root = tmp_path / "Cursor" / "User" / "workspaceStorage"
    workspace = tmp_path / "workspace-a"
    workspace.mkdir(parents=True, exist_ok=True)

    matching = root / "store-a" / "chatSessions" / "match.json"
    non_matching = root / "store-b" / "chatSessions" / "other.json"

    _write_text(
        root / "store-a" / "workspace.json",
        json.dumps({"folder": f"file://{workspace}"}),
    )
    _write_text(
        root / "store-b" / "workspace.json",
        json.dumps({"folder": f"file://{tmp_path / 'workspace-b'}"}),
    )

    _write_text(matching, json.dumps({"requests": []}))
    _write_text(non_matching, json.dumps({"requests": []}))

    os.utime(matching, (100, 100))
    os.utime(non_matching, (200, 200))

    monkeypatch.setattr(module, "CURSOR_WORKSPACE_STORAGE_DIR", root)

    assert module.find_latest_chat_history_path(source="cursor", cwd=workspace) == matching


def test_parse_claude_jsonl_messages():
    module = importlib.import_module("backend.visualization.services.rule_learning_agent")

    raw_content = "\n".join(
        [
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": "Please draft a plan."}],
                    },
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "## Implementation Plan\\n1. Add tests."}
                        ],
                    },
                }
            ),
            json.dumps({"type": "queue-operation", "operation": "enqueue"}),
        ]
    )

    messages = module.parse_chat_jsonl_messages(raw_content)

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"][0]["text"] == "Please draft a plan."
    assert messages[1]["role"] == "assistant"
    assert "Implementation Plan" in messages[1]["content"][0]["text"]


def test_format_chat_content_handles_claude_jsonl():
    module = importlib.import_module("backend.visualization.services.rule_learning_agent")

    raw_content = "\n".join(
        [
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": "hello"}],
                    },
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "hi there"}],
                    },
                }
            ),
        ]
    )

    rendered = module.format_chat_content(raw_content)

    assert "**user**:\nhello" in rendered
    assert "**assistant**:\nhi there" in rendered


def test_parse_cursor_chat_session_messages():
    module = importlib.import_module("backend.visualization.services.rule_learning_agent")

    raw_content = json.dumps(
        {
            "requests": [
                {
                    "request": {"text": "Please draft a plan."},
                    "response": {"text": "Sure — here is a plan."},
                },
                {
                    "messages": [
                        {"role": "user", "content": "Add tests."},
                        {"role": "assistant", "content": "Added tests."},
                    ]
                },
            ]
        }
    )

    messages = module.parse_chat_jsonl_messages(raw_content)

    assert len(messages) == 4
    assert messages[0]["role"] == "user"
    assert messages[0]["content"][0]["text"] == "Please draft a plan."
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"][0]["text"] == "Sure — here is a plan."
    assert messages[2]["role"] == "user"
    assert messages[2]["content"][0]["text"] == "Add tests."
    assert messages[3]["role"] == "assistant"
    assert messages[3]["content"][0]["text"] == "Added tests."


def test_plan_loader_supports_claude_jsonl(tmp_path):
    plans_module = importlib.import_module("backend.routes.visualization_api.plans")

    chat_file = tmp_path / "session.jsonl"
    chat_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "role": "user",
                            "content": [{"type": "text", "text": "First request."}],
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "text", "text": "First answer."}],
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    messages = plans_module._load_chat_messages(str(chat_file))

    assert messages == [
        {"role": "user", "content": "First request."},
        {"role": "assistant", "content": "First answer."},
    ]


def test_plan_loader_supports_cursor_chat_session_json(tmp_path):
    plans_module = importlib.import_module("backend.routes.visualization_api.plans")

    chat_file = tmp_path / "cursor-session.json"
    chat_file.write_text(
        json.dumps(
            {
                "requests": [
                    {
                        "request": {"text": "First request."},
                        "response": {"text": "First answer."},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    messages = plans_module._load_chat_messages(str(chat_file))

    assert messages == [
        {"role": "user", "content": "First request."},
        {"role": "assistant", "content": "First answer."},
    ]


def test_init_accepts_claude_chat_history_source(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    init_module = importlib.import_module("backend.cli.commands.init")

    captured = {}

    def fake_save_config(config):
        captured.update(config)

    init_module.cmd_init(
        SimpleNamespace(user_name="Jenny", chat_history_source="claude"),
        fake_save_config,
    )

    assert captured["chat_history_source"] == "claude"


def test_init_accepts_cursor_chat_history_source(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    init_module = importlib.import_module("backend.cli.commands.init")

    captured = {}

    def fake_save_config(config):
        captured.update(config)

    init_module.cmd_init(
        SimpleNamespace(user_name="Jenny", chat_history_source="cursor"),
        fake_save_config,
    )

    assert captured["chat_history_source"] == "cursor"


def test_create_visualization_uses_selected_chat_history_source(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    visualization_manager = importlib.import_module("backend.visualization.services.visualization_manager")
    monkeypatch.setattr(visualization_manager, "VIS_DIR", tmp_path / ".zoro" / "visualization")
    monkeypatch.setattr(visualization_manager, "INDEX_FILE", visualization_manager.VIS_DIR / "index.json")

    chat_file = tmp_path / "claude-session.jsonl"
    chat_file.write_text("", encoding="utf-8")

    captured = {}

    def fake_find_latest(source=None, cwd=None):
        captured["source"] = source
        captured["cwd"] = cwd
        return chat_file

    monkeypatch.setattr(visualization_manager, "find_latest_chat_history_path", fake_find_latest)

    metadata, error = visualization_manager.create_visualization(chat_history_source="claude")

    assert error is None
    assert metadata is not None
    assert captured["source"] == "claude"
    assert str(captured["cwd"]) == str(tmp_path)
    assert metadata["chat_history_source"] == "claude"


def test_create_visualization_api_passes_chat_history_source(monkeypatch):
    sessions_module = importlib.import_module("backend.routes.visualization_api.sessions")

    captured = {}

    def fake_create_visualization(rule_retrieval_source=None, chat_history_source=None):
        captured["rule_retrieval_source"] = rule_retrieval_source
        captured["chat_history_source"] = chat_history_source
        return (
            {
                "chat_id": "chat-1",
                "name": None,
                "chat_file_path": "/tmp/session.jsonl",
                "chat_history_source": chat_history_source,
                "status": "idle",
            },
            None,
        )

    monkeypatch.setattr(sessions_module.vm, "create_visualization", fake_create_visualization)

    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/chat-visualizations",
        json={"chat_history_source": "claude"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["chat_history_source"] == "claude"
    assert captured["chat_history_source"] == "claude"


def test_update_visualization_settings_switches_chat_source(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    visualization_manager = importlib.import_module("backend.visualization.services.visualization_manager")
    runtime_store = importlib.import_module("backend.visualization.services.runtime_store")

    monkeypatch.setattr(visualization_manager, "VIS_DIR", tmp_path / ".zoro" / "visualization")
    monkeypatch.setattr(visualization_manager, "INDEX_FILE", visualization_manager.VIS_DIR / "index.json")

    codex_path = tmp_path / "codex-session.jsonl"
    claude_path = tmp_path / "claude-session.jsonl"
    codex_path.write_text("", encoding="utf-8")
    claude_path.write_text("", encoding="utf-8")

    def fake_find_latest(source=None, cwd=None):
        if source == "claude":
            return claude_path
        return codex_path

    monkeypatch.setattr(visualization_manager, "find_latest_chat_history_path", fake_find_latest)

    created, create_error = visualization_manager.create_visualization(chat_history_source="codex")
    assert create_error is None
    assert created is not None

    chat_id = created["chat_id"]
    runtime_store.save_runtime_document(
        chat_id,
        {
            "token_count": 42,
            "last_message_index": 3,
            "accumulated_content": "old content",
            "cleaned_accumulated_content": "old cleaned content",
        },
    )

    updated, update_error = visualization_manager.update_visualization_settings(
        chat_id,
        chat_history_source="claude",
    )
    assert update_error is None
    assert updated is not None
    assert updated["chat_history_source"] == "claude"
    assert updated["chat_file_path"] == str(claude_path)

    runtime_after = runtime_store.load_runtime_document(chat_id)
    assert runtime_after["token_count"] == 0
    assert runtime_after["last_message_index"] == 0
    assert runtime_after["accumulated_content"] == ""
    assert runtime_after["cleaned_accumulated_content"] == ""

    with open(tmp_path / ".zoro" / "visualization" / "index.json", "r", encoding="utf-8") as f:
        index_doc = json.load(f)
    path_map = index_doc["path_to_chat_id"]
    assert str(claude_path) in path_map
    assert path_map[str(claude_path)] == chat_id
    assert str(codex_path) not in path_map


def test_update_visualization_api_passes_chat_history_source(monkeypatch):
    sessions_module = importlib.import_module("backend.routes.visualization_api.sessions")

    captured = {}

    def fake_update_visualization_settings(chat_id, name=None, chat_history_source=None):
        captured["chat_id"] = chat_id
        captured["name"] = name
        captured["chat_history_source"] = chat_history_source
        return (
            {
                "chat_id": chat_id,
                "name": "Demo",
                "chat_file_path": "/tmp/claude-session.jsonl",
                "chat_history_source": chat_history_source,
                "status": "paused",
            },
            None,
        )

    monkeypatch.setattr(sessions_module.vm, "update_visualization_settings", fake_update_visualization_settings)

    app = create_app()
    client = app.test_client()

    response = client.put(
        "/api/chat-visualizations/chat-1",
        json={"chat_history_source": "claude"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["chat_history_source"] == "claude"
    assert captured["chat_id"] == "chat-1"
    assert captured["chat_history_source"] == "claude"
    assert captured["name"] is None
