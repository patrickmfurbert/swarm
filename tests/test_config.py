"""
Config loading and validation tests.
"""

import json
import os
import sys

import pytest
from unittest.mock import patch

import swarm


# ---------------------------------------------------------------------------
# find_config_file / load_config discovery
# ---------------------------------------------------------------------------


def test_load_config_from_explicit_path(tmp_config):
    config = swarm.load_config(tmp_config)
    assert "worktrees" in config


def test_load_config_from_current_directory(tmp_path, tmp_config):
    # tmp_config already wrote swarm.json into tmp_path
    with patch("os.getcwd", return_value=str(tmp_path)):
        config = swarm.load_config(None)
    assert "worktrees" in config


def test_load_config_from_user_config_directory(tmp_path, valid_config):
    user_config_dir = tmp_path / ".config" / "swarm"
    user_config_dir.mkdir(parents=True)
    user_config_file = user_config_dir / "config.json"
    user_config_file.write_text(json.dumps(valid_config), encoding="utf-8")

    def fake_expanduser(p):
        return p.replace("~", str(tmp_path), 1) if p.startswith("~") else p

    # cwd has no swarm.json; expanduser redirects to our tmp config
    with patch("os.getcwd", return_value="/nonexistent_cwd_xyz"), \
         patch("os.path.expanduser", side_effect=fake_expanduser):
        config = swarm.load_config(None)

    assert "worktrees" in config


def test_load_config_returns_none_when_not_found(tmp_path):
    # find_config_file() returns None when no config exists anywhere
    empty_dir = str(tmp_path / "empty")
    os.makedirs(empty_dir)
    nonexistent = str(tmp_path / "nonexistent" / "config.json")

    with patch("os.getcwd", return_value=empty_dir), \
         patch("os.path.expanduser", return_value=nonexistent):
        result = swarm.find_config_file()

    assert result is None


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


def test_validate_config_passes_with_valid_config(valid_config):
    swarm.validate_config(valid_config)  # must not raise


def test_validate_config_raises_when_worktrees_missing():
    with pytest.raises(ValueError, match="worktrees"):
        swarm.validate_config({})


def test_validate_config_raises_when_worktrees_empty():
    with pytest.raises(ValueError, match="worktrees"):
        swarm.validate_config({"worktrees": []})


def test_validate_config_raises_when_worktrees_not_a_list():
    with pytest.raises(ValueError, match="worktrees"):
        swarm.validate_config({"worktrees": "/some/single/path"})


def test_validate_config_uses_defaults_for_optional_fields(tmp_path):
    config = {"worktrees": [str(tmp_path)]}
    swarm.validate_config(config)
    assert config["pattern"] == swarm.DEFAULT_PATTERN
    assert config["poll_interval_seconds"] == swarm.DEFAULT_POLL_INTERVAL
    assert config["log_file"] is None


def test_validate_config_raises_when_interval_not_integer(tmp_path):
    config = {"worktrees": [str(tmp_path)], "poll_interval_seconds": "30"}
    with pytest.raises(ValueError, match="poll_interval_seconds"):
        swarm.validate_config(config)


def test_validate_config_raises_when_interval_less_than_one(tmp_path):
    config = {"worktrees": [str(tmp_path)], "poll_interval_seconds": 0}
    with pytest.raises(ValueError, match="poll_interval_seconds"):
        swarm.validate_config(config)


# ---------------------------------------------------------------------------
# load_config error paths
# ---------------------------------------------------------------------------


def test_load_config_raises_on_malformed_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not: valid json!!}", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed JSON"):
        swarm.load_config(str(bad_file))


def test_load_config_expands_tilde_in_worktree_paths(tmp_path):
    config_data = {"worktrees": ["~/agent-a", "~/agent-b"]}
    config_file = tmp_path / "swarm.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    config = swarm.load_config(str(config_file))

    for path in config["worktrees"]:
        assert not path.startswith("~"), f"Path was not expanded: {path}"
        assert os.path.sep in path


# ---------------------------------------------------------------------------
# CLI flag overrides
# ---------------------------------------------------------------------------


def test_cli_flags_override_config_values(tmp_config, monkeypatch):
    captured = {}

    def mock_watch_worktree(worktree_path, pattern, seen, state_file, log_file=None):
        captured["pattern"] = pattern
        raise KeyboardInterrupt

    monkeypatch.setattr(swarm, "watch_worktree", mock_watch_worktree)
    monkeypatch.setattr(swarm, "load_seen_commits", lambda _: set())
    monkeypatch.setattr(
        sys, "argv",
        ["swarm", "--config", tmp_config, "--pattern", "[CUSTOM]", "--interval", "5"],
    )

    with pytest.raises(SystemExit) as exc_info:
        swarm.main()

    assert exc_info.value.code == 0
    assert captured.get("pattern") == "[CUSTOM]"
