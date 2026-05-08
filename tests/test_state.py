"""
Seen commit state persistence tests.
"""

import os
from unittest.mock import patch

import swarm


# ---------------------------------------------------------------------------
# load_seen_commits
# ---------------------------------------------------------------------------


def test_load_seen_commits_returns_empty_set_when_file_not_exist(tmp_state_file):
    result = swarm.load_seen_commits(tmp_state_file)
    assert result == set()


def test_load_seen_commits_returns_hashes_from_file(tmp_path):
    state_file = tmp_path / "seen.log"
    state_file.write_text("abc1234\ndef5678\nghi9012\n", encoding="utf-8")

    result = swarm.load_seen_commits(str(state_file))

    assert result == {"abc1234", "def5678", "ghi9012"}


def test_load_seen_commits_ignores_empty_lines(tmp_path):
    state_file = tmp_path / "seen.log"
    state_file.write_text("abc1234\n\ndef5678\n\n", encoding="utf-8")

    result = swarm.load_seen_commits(str(state_file))

    assert result == {"abc1234", "def5678"}


def test_load_seen_commits_ignores_whitespace_lines(tmp_path):
    state_file = tmp_path / "seen.log"
    state_file.write_text("abc1234\n   \ndef5678\n\t\n", encoding="utf-8")

    result = swarm.load_seen_commits(str(state_file))

    assert result == {"abc1234", "def5678"}


# ---------------------------------------------------------------------------
# save_seen_commit
# ---------------------------------------------------------------------------


def test_save_seen_commit_appends_hash_to_file(tmp_path):
    state_file = tmp_path / "seen.log"
    state_file.write_text("existing1234\n", encoding="utf-8")

    swarm.save_seen_commit(str(state_file), "newhash5678")

    content = state_file.read_text(encoding="utf-8")
    assert "existing1234" in content
    assert "newhash5678" in content


def test_save_seen_commit_creates_file_if_not_exist(tmp_state_file):
    assert not os.path.exists(tmp_state_file)

    swarm.save_seen_commit(tmp_state_file, "abc1234")

    assert os.path.exists(tmp_state_file)
    content = open(tmp_state_file, encoding="utf-8").read()
    assert "abc1234" in content


def test_save_seen_commit_creates_parent_directories_if_not_exist(tmp_path):
    state_file = str(tmp_path / "deep" / "nested" / "seen.log")

    swarm.save_seen_commit(state_file, "abc1234")

    assert os.path.exists(state_file)
    content = open(state_file, encoding="utf-8").read()
    assert "abc1234" in content


def test_save_seen_commit_handles_unwritable_file_gracefully(tmp_state_file, capsys):
    with patch("builtins.open", side_effect=PermissionError("permission denied")):
        swarm.save_seen_commit(tmp_state_file, "abc1234")  # must not raise

    captured = capsys.readouterr()
    assert "warning" in captured.err.lower()


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def test_round_trip_save_and_load(tmp_state_file):
    hashes = ["abc1234", "def5678", "ghi9012"]
    for h in hashes:
        swarm.save_seen_commit(tmp_state_file, h)

    result = swarm.load_seen_commits(tmp_state_file)

    assert result == set(hashes)
