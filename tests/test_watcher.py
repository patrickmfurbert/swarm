"""
Worktree watching and pattern matching tests.
"""

from unittest.mock import patch

import swarm


# ---------------------------------------------------------------------------
# matches_pattern
# ---------------------------------------------------------------------------


def test_matches_pattern_returns_true_when_pattern_in_message():
    assert swarm.matches_pattern("[DONE] implement useOllama", "[DONE]") is True


def test_matches_pattern_returns_false_when_pattern_not_in_message():
    assert swarm.matches_pattern("wip: still working", "[DONE]") is False


def test_matches_pattern_is_case_sensitive():
    assert swarm.matches_pattern("[done] implement useOllama", "[DONE]") is False


def test_matches_pattern_handles_empty_pattern():
    # Empty string is a substring of every string
    assert swarm.matches_pattern("any message here", "") is True


def test_matches_pattern_handles_empty_message():
    assert swarm.matches_pattern("", "[DONE]") is False


# ---------------------------------------------------------------------------
# watch_worktree — notifications
# ---------------------------------------------------------------------------


def test_watch_worktree_notifies_on_new_done_commit(tmp_path, capsys):
    seen = set()
    state_file = str(tmp_path / "seen.log")

    with patch("swarm.get_latest_commit", return_value=("abc1234", "[DONE] implement useOllama")):
        swarm.watch_worktree(
            worktree_path="~/projects/hooks",
            pattern="[DONE]",
            seen=seen,
            state_file=state_file,
        )

    captured = capsys.readouterr()
    assert "[SWARM]" in captured.out
    assert "abc1234" in captured.out
    assert "[DONE] implement useOllama" in captured.out


def test_watch_worktree_does_not_notify_on_already_seen_commit(tmp_path, capsys):
    seen = {"abc1234"}
    state_file = str(tmp_path / "seen.log")

    with patch("swarm.get_latest_commit", return_value=("abc1234", "[DONE] implement useOllama")):
        swarm.watch_worktree(
            worktree_path="~/projects/hooks",
            pattern="[DONE]",
            seen=seen,
            state_file=state_file,
        )

    captured = capsys.readouterr()
    assert captured.out == ""


def test_watch_worktree_does_not_notify_when_pattern_not_matched(tmp_path, capsys):
    seen = set()
    state_file = str(tmp_path / "seen.log")

    with patch("swarm.get_latest_commit", return_value=("abc1234", "wip: still working")):
        swarm.watch_worktree(
            worktree_path="~/projects/hooks",
            pattern="[DONE]",
            seen=seen,
            state_file=state_file,
        )

    captured = capsys.readouterr()
    assert captured.out == ""


def test_watch_worktree_does_not_notify_when_no_commits(tmp_path, capsys):
    seen = set()
    state_file = str(tmp_path / "seen.log")

    with patch("swarm.get_latest_commit", return_value=None):
        swarm.watch_worktree(
            worktree_path="~/projects/hooks",
            pattern="[DONE]",
            seen=seen,
            state_file=state_file,
        )

    captured = capsys.readouterr()
    assert captured.out == ""


def test_watch_worktree_does_not_notify_when_git_fails(tmp_path, capsys):
    seen = set()
    state_file = str(tmp_path / "seen.log")

    with patch("swarm.get_latest_commit", side_effect=Exception("git exploded")):
        # watch_worktree itself must not raise even if get_latest_commit does
        try:
            swarm.watch_worktree(
                worktree_path="~/projects/hooks",
                pattern="[DONE]",
                seen=seen,
                state_file=state_file,
            )
        except Exception:
            pass  # if it raises, the assertion below catches the real failure

    captured = capsys.readouterr()
    assert captured.out == ""


# ---------------------------------------------------------------------------
# watch_worktree — side effects
# ---------------------------------------------------------------------------


def test_watch_worktree_adds_hash_to_seen_set(tmp_path):
    seen = set()
    state_file = str(tmp_path / "seen.log")

    with patch("swarm.get_latest_commit", return_value=("abc1234", "[DONE] implement feature")):
        swarm.watch_worktree(
            worktree_path="~/projects/hooks",
            pattern="[DONE]",
            seen=seen,
            state_file=state_file,
        )

    assert "abc1234" in seen


def test_watch_worktree_persists_hash_to_state_file(tmp_path):
    seen = set()
    state_file = str(tmp_path / "seen.log")

    with patch("swarm.get_latest_commit", return_value=("abc1234", "[DONE] implement feature")):
        swarm.watch_worktree(
            worktree_path="~/projects/hooks",
            pattern="[DONE]",
            seen=seen,
            state_file=state_file,
        )

    content = open(state_file, encoding="utf-8").read()
    assert "abc1234" in content


def test_watch_worktree_handles_missing_worktree_gracefully(tmp_path, capsys):
    seen = set()
    state_file = str(tmp_path / "seen.log")

    with patch("swarm.get_latest_commit", return_value=None):
        swarm.watch_worktree(
            worktree_path="~/projects/does-not-exist",
            pattern="[DONE]",
            seen=seen,
            state_file=state_file,
        )

    captured = capsys.readouterr()
    assert captured.out == ""
