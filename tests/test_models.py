import pytest

from backend.globals import models


class _FakeOpenAIProvider:
    pass


def test_get_default_provider_uses_openai_by_default(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setattr(models, "OpenAIProvider", _FakeOpenAIProvider)

    provider = models.get_default_provider()

    assert isinstance(provider, _FakeOpenAIProvider)


def test_get_default_provider_rejects_unsupported_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        models.get_default_provider()
