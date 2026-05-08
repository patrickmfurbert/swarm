"""
Shared pytest fixtures for the Swarm test suite.
"""

import json
import os
import pytest


def pytest_sessionfinish(session, exitstatus):
    """Exit with 0 when no tests are collected (scaffold phase)."""
    if exitstatus == 5:
        session.exitstatus = 0


@pytest.fixture
def valid_config(tmp_path):
    """Return a valid config dict with temp paths filled in."""
    return {
        "pattern": "[DONE]",
        "worktrees": [str(tmp_path / "agent-a"), str(tmp_path / "agent-b")],
        "poll_interval_seconds": 30,
        "log_file": None,
    }


@pytest.fixture
def tmp_config(tmp_path, valid_config):
    """Write a valid config dict to a temp file and return the file path."""
    config_path = tmp_path / "swarm.json"
    config_path.write_text(json.dumps(valid_config), encoding="utf-8")
    return str(config_path)


@pytest.fixture
def tmp_state_file(tmp_path):
    """Return a path to a temporary seen.log file (not yet created)."""
    return str(tmp_path / "seen.log")


@pytest.fixture
def fake_git_repo(tmp_path):
    """Create a minimal fake git repository directory structure in tmp_path."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    return str(tmp_path)
