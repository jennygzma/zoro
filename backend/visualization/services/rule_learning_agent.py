from datetime import datetime
import json
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

from backend.utils import get_chat_history_source_from_config

VS_CODE_CLAUDE_DEV_TASKS_DIR = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Code"
    / "User"
    / "globalStorage"
    / "saoudrizwan.claude-dev"
    / "tasks"
)

CODEX_SESSIONS_DIR = Path.home() / ".codex" / "sessions"
CLAUDE_CODE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
CURSOR_WORKSPACE_STORAGE_DIR = (
    Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage"
)


def _normalize_path(path_value: str | Path | None) -> Optional[Path]:
    if path_value is None:
        return None

    text = str(path_value).strip()
    if not text:
        return None

    try:
        return Path(text).expanduser().resolve()
    except Exception:
        return None


def _is_session_for_workspace(session_cwd: str | None, workspace: Path) -> bool:
    normalized_session = _normalize_path(session_cwd)
    if normalized_session is None:
        return False

    return (
        normalized_session == workspace
        or workspace in normalized_session.parents
        or normalized_session in workspace.parents
    )


def _extract_codex_session_cwd(path: Path) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            for _ in range(24):
                line = file.readline()
                if not line:
                    break

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if data.get("type") != "session_meta":
                    continue

                payload = data.get("payload", {})
                cwd = payload.get("cwd")
                if isinstance(cwd, str) and cwd.strip():
                    return cwd.strip()
                return None
    except OSError:
        return None

    return None


def _extract_claude_session_cwd(path: Path) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            for _ in range(240):
                line = file.readline()
                if not line:
                    break

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                cwd = data.get("cwd")
                if isinstance(cwd, str) and cwd.strip():
                    return cwd.strip()
    except OSError:
        return None

    return None


def _parse_file_uri_to_path(uri: str) -> Optional[str]:
    if not isinstance(uri, str):
        return None

    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None

    path = unquote(parsed.path or "").strip()
    if not path:
        return None

    if len(path) >= 3 and path[0] == "/" and path[2] == ":":
        path = path[1:]

    return path


def _extract_cursor_session_cwd(path: Path) -> Optional[str]:
    workspace_file = path.parent.parent / "workspace.json"
    if not workspace_file.exists():
        return None

    try:
        with open(workspace_file, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None

    location = payload.get("folder") or payload.get("configPath")
    if not isinstance(location, str) or not location.strip():
        return None

    parsed_path = _parse_file_uri_to_path(location)
    if parsed_path:
        return parsed_path

    clean_location = location.strip()
    if clean_location.startswith("/"):
        return clean_location

    return None


def _select_latest_session(
    candidates: list[Path],
    workspace: Path | None,
    extract_session_cwd,
) -> Optional[Path]:
    if not candidates:
        return None

    ordered = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    if workspace is None:
        return ordered[0]

    for candidate in ordered:
        session_cwd = extract_session_cwd(candidate)
        if _is_session_for_workspace(session_cwd, workspace):
            return candidate

    return ordered[0]


def _find_latest_cline_history_path() -> Optional[Path]:
    root = VS_CODE_CLAUDE_DEV_TASKS_DIR
    if not root.exists():
        return None

    candidates = list(root.glob("*/api_conversation_history.json"))
    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)


def _find_latest_codex_session_path(workspace: Path | None = None) -> Optional[Path]:
    root = CODEX_SESSIONS_DIR
    if not root.exists():
        return None

    candidates = list(root.rglob("*.jsonl"))
    return _select_latest_session(candidates, workspace, _extract_codex_session_cwd)


def _find_latest_claude_code_session_path(workspace: Path | None = None) -> Optional[Path]:
    root = CLAUDE_CODE_PROJECTS_DIR
    if not root.exists():
        return None

    candidates = list(root.rglob("*.jsonl"))
    return _select_latest_session(candidates, workspace, _extract_claude_session_cwd)


def _find_latest_cursor_session_path(workspace: Path | None = None) -> Optional[Path]:
    root = CURSOR_WORKSPACE_STORAGE_DIR
    if not root.exists():
        return None

    candidates = list(root.glob("*/chatSessions/*.json"))
    return _select_latest_session(candidates, workspace, _extract_cursor_session_cwd)


def find_latest_chat_history_path(source: Optional[str] = None, cwd: Path | None = None) -> Optional[Path]:
    source = (source or get_chat_history_source_from_config()).strip().lower()
    workspace = _normalize_path(cwd or Path.cwd())

    if source == "codex":
        return _find_latest_codex_session_path(workspace)
    if source == "claude":
        return _find_latest_claude_code_session_path(workspace)
    if source == "cursor":
        return _find_latest_cursor_session_path(workspace)
    return _find_latest_cline_history_path()


def _parse_codex_jsonl_messages(raw_content: str) -> list[dict]:
    messages: list[dict] = []
    for line in raw_content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("type") != "response_item":
            continue
        payload = data.get("payload", {})
        if payload.get("type") != "message":
            continue
        role = payload.get("role")
        if role not in {"user", "assistant"}:
            continue
        blocks = []
        for block in payload.get("content", []) or []:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "input_text" and role == "user":
                blocks.append({"type": "text", "text": block.get("text", "")})
            elif block_type == "output_text" and role == "assistant":
                blocks.append({"type": "text", "text": block.get("text", "")})
        if blocks:
            messages.append({"role": role, "content": blocks})
    return messages


def _parse_claude_code_jsonl_messages(raw_content: str) -> list[dict]:
    messages: list[dict] = []
    for line in raw_content.splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        if data.get("type") not in {"user", "assistant"}:
            continue

        message = data.get("message")
        if not isinstance(message, dict):
            continue

        role = str(message.get("role") or data.get("type", "")).lower().strip()
        if role not in {"user", "assistant"}:
            continue

        content = message.get("content", [])
        blocks: list[dict] = []

        if isinstance(content, str):
            text = content.strip()
            if text:
                blocks.append({"type": "text", "text": text})
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = str(block.get("type", "")).strip()
                if block_type in {"text", "input_text", "output_text"}:
                    text = str(block.get("text", "")).strip()
                    if text:
                        blocks.append({"type": "text", "text": text})

        if blocks:
            messages.append({"role": role, "content": blocks})

    return messages


def _normalize_role(role_value: object) -> Optional[str]:
    role = str(role_value or "").strip().lower()
    role_map = {
        "user": "user",
        "human": "user",
        "assistant": "assistant",
        "ai": "assistant",
        "bot": "assistant",
        "model": "assistant",
        "system": "system",
    }
    return role_map.get(role)


def _extract_text_from_unknown(value: object, depth: int = 0) -> str:
    if value is None or depth > 6:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, list):
        parts = [
            _extract_text_from_unknown(item, depth + 1)
            for item in value
        ]
        clean_parts = [part for part in parts if part]
        return "\n\n".join(clean_parts).strip()

    if isinstance(value, dict):
        block_type = str(value.get("type", "")).strip().lower()
        if block_type in {"text", "input_text", "output_text"}:
            text = str(value.get("text", "")).strip()
            if text:
                return text
        if block_type == "thinking":
            thinking = str(value.get("thinking", "")).strip()
            if thinking:
                return thinking

        preferred_keys = (
            "text",
            "content",
            "message",
            "value",
            "body",
            "markdown",
            "parts",
            "prompt",
            "query",
            "request",
            "response",
            "answer",
            "output",
            "completion",
            "result",
            "assistantResponse",
            "finalResponse",
            "final",
        )

        fragments: list[str] = []
        for key in preferred_keys:
            if key not in value:
                continue
            fragment = _extract_text_from_unknown(value.get(key), depth + 1)
            if fragment and fragment not in fragments:
                fragments.append(fragment)

        return "\n\n".join(fragments).strip()

    return ""


def _text_to_blocks(text: str) -> list[dict]:
    clean_text = text.strip()
    if not clean_text:
        return []
    return [{"type": "text", "text": clean_text}]


def _parse_generic_message_list(messages: list[object]) -> list[dict]:
    parsed: list[dict] = []

    for message in messages:
        if not isinstance(message, dict):
            continue

        role = _normalize_role(
            message.get("role")
            or message.get("type")
            or message.get("sender")
        )
        if role is None:
            continue

        content_value = message.get("content")
        if content_value is None:
            for key in ("text", "message", "prompt", "query", "request", "response"):
                if key in message:
                    content_value = message.get(key)
                    break

        text = _extract_text_from_unknown(content_value)
        blocks = _text_to_blocks(text)
        if blocks:
            parsed.append({"role": role, "content": blocks})

    return parsed


def _parse_cursor_request_messages(requests: list[object]) -> list[dict]:
    messages: list[dict] = []

    for request in requests:
        if not isinstance(request, dict):
            continue

        nested_messages = request.get("messages") or request.get("turns")
        if isinstance(nested_messages, list):
            nested_parsed = _parse_generic_message_list(nested_messages)
            if nested_parsed:
                messages.extend(nested_parsed)
                continue

        user_text = ""
        for key in ("request", "prompt", "query", "input", "userMessage", "user", "message", "text"):
            if key not in request:
                continue
            user_text = _extract_text_from_unknown(request.get(key))
            if user_text:
                break

        assistant_text = ""
        for key in (
            "response",
            "answer",
            "assistantResponse",
            "assistant",
            "completion",
            "output",
            "result",
            "finalResponse",
            "final",
        ):
            if key not in request:
                continue
            assistant_text = _extract_text_from_unknown(request.get(key))
            if assistant_text:
                break

        user_blocks = _text_to_blocks(user_text)
        if user_blocks:
            messages.append({"role": "user", "content": user_blocks})

        assistant_blocks = _text_to_blocks(assistant_text)
        if assistant_blocks:
            messages.append({"role": "assistant", "content": assistant_blocks})

    return messages


def _parse_cursor_chat_session_messages(raw_content: str) -> list[dict]:
    try:
        payload = json.loads(raw_content)
    except (json.JSONDecodeError, ValueError):
        return []

    if not isinstance(payload, dict):
        return []

    requests = payload.get("requests")
    if not isinstance(requests, list):
        return []

    return _parse_cursor_request_messages(requests)


def _parse_messages_from_json_payload(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return _parse_generic_message_list(payload)

    if not isinstance(payload, dict):
        return []

    messages = payload.get("messages")
    if isinstance(messages, list):
        parsed_messages = _parse_generic_message_list(messages)
        if parsed_messages:
            return parsed_messages

    requests = payload.get("requests")
    if isinstance(requests, list):
        parsed_requests = _parse_cursor_request_messages(requests)
        if parsed_requests:
            return parsed_requests

    for key in ("conversation", "chat", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            parsed_items = _parse_generic_message_list(value)
            if parsed_items:
                return parsed_items

    return []


def parse_chat_jsonl_messages(raw_content: str) -> list[dict]:
    codex_messages = _parse_codex_jsonl_messages(raw_content)
    if codex_messages:
        return codex_messages

    claude_messages = _parse_claude_code_jsonl_messages(raw_content)
    if claude_messages:
        return claude_messages

    cursor_messages = _parse_cursor_chat_session_messages(raw_content)
    if cursor_messages:
        return cursor_messages

    try:
        payload = json.loads(raw_content)
    except (json.JSONDecodeError, ValueError):
        return []

    return _parse_messages_from_json_payload(payload)


def read_new_chat_content(chat_file_path: str, last_polled_at: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    chat_file = Path(chat_file_path)
    if not chat_file.exists():
        return None, None

    modified_at = datetime.fromtimestamp(chat_file.stat().st_mtime).isoformat()

    if last_polled_at and modified_at <= last_polled_at:
        return None, last_polled_at

    with open(chat_file, "r", encoding="utf-8") as file:
        content = file.read()

    return content, modified_at


def format_chat_content(raw_content: str) -> str:
    messages = parse_chat_jsonl_messages(raw_content)
    if not messages:
        return raw_content

    markdown = ""
    for message in messages:
        role = message.get("role", "unknown")
        content = message.get("content", "")
        if isinstance(content, list):
            text = "\n".join(
                str(block.get("text", "")).strip()
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        else:
            text = str(content)
        markdown += f"**{role}**:\n{text}\n\n"

    return markdown
