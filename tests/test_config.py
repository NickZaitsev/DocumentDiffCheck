from __future__ import annotations

from src import config


def test_env_csv_parses_comma_separated_values(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TEST_API_KEYS", "key-one, key-two,,")

    assert config._env_csv("TEST_API_KEYS") == ("key-one", "key-two")


def test_openrouter_key_has_no_default_secret(
    monkeypatch,
) -> None:
    monkeypatch.delenv("MISSING_OPENROUTER_API_KEY", raising=False)

    assert config._env_str("MISSING_OPENROUTER_API_KEY") == ""
