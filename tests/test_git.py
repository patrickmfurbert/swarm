"""
Git command execution tests.
"""

import subprocess
from unittest.mock import patch, MagicMock

import swarm


def _mock_git(stdout="", returncode=0, stderr=""):
    """Helper: return a mock CompletedProcess."""
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_get_latest_commit_returns_hash_and_message(fake_git_repo):
    with patch("subprocess.run", return_value=_mock_git("abc1234\t[DONE] implement feature\n")):
        result = swarm.get_latest_commit(fake_git_repo)
    assert result == ("abc1234", "[DONE] implement feature")


def test_get_latest_commit_handles_commit_message_with_spaces(fake_git_repo):
    with patch("subprocess.run", return_value=_mock_git("abc1234\t[DONE] add new feature with many words\n")):
        result = swarm.get_latest_commit(fake_git_repo)
    assert result == ("abc1234", "[DONE] add new feature with many words")


def test_get_latest_commit_handles_commit_message_with_special_characters(fake_git_repo):
    msg = "[DONE] fix: handle <html> & 'quotes' — properly"
    with patch("subprocess.run", return_value=_mock_git(f"abc1234\t{msg}\n")):
        result = swarm.get_latest_commit(fake_git_repo)
    assert result == ("abc1234", msg)


# ---------------------------------------------------------------------------
# Error / edge cases
# ---------------------------------------------------------------------------


def test_get_latest_commit_returns_none_when_path_not_exist():
    result = swarm.get_latest_commit("/absolutely/nonexistent/path/xyz123")
    assert result is None


def test_get_latest_commit_returns_none_when_not_a_git_repo(fake_git_repo):
    mock = _mock_git(stdout="", returncode=128, stderr="not a git repository")
    with patch("subprocess.run", return_value=mock):
        result = swarm.get_latest_commit(fake_git_repo)
    assert result is None


def test_get_latest_commit_returns_none_when_git_command_fails(fake_git_repo):
    with patch("subprocess.run", side_effect=OSError("git not found")):
        result = swarm.get_latest_commit(fake_git_repo)
    assert result is None


def test_get_latest_commit_returns_none_when_no_commits(fake_git_repo):
    with patch("subprocess.run", return_value=_mock_git(stdout="", returncode=0)):
        result = swarm.get_latest_commit(fake_git_repo)
    assert result is None


# ---------------------------------------------------------------------------
# Correct git command
# ---------------------------------------------------------------------------


def test_get_latest_commit_calls_correct_git_command(fake_git_repo):
    with patch("subprocess.run", return_value=_mock_git("abc1234\tsome message\n")) as mock_run:
        swarm.get_latest_commit(fake_git_repo)

    call_args = mock_run.call_args[0][0]  # positional arg 0 is the command list
    assert call_args[0] == "git"
    assert "-C" in call_args
    assert fake_git_repo in call_args
    assert "log" in call_args
    assert "-1" in call_args
    assert "--pretty=format:%H\t%s" in call_args
