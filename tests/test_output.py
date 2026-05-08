"""
Output formatting and logging tests.
"""

import re

import swarm


# ---------------------------------------------------------------------------
# format_event
# ---------------------------------------------------------------------------


def test_format_event_produces_correct_format():
    event = swarm.format_event("~/projects/hooks", "abc1234", "[DONE] implement feature")
    # Expected: "YYYY-MM-DD HH:MM:SS [SWARM] PATH: HASH MESSAGE"
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[SWARM\] .+: \w+ .+", event)


def test_format_event_includes_timestamp():
    event = swarm.format_event("~/projects/hooks", "abc1234", "[DONE] implement feature")
    assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", event)


def test_format_event_includes_worktree_path():
    event = swarm.format_event("~/projects/hooks", "abc1234", "[DONE] implement feature")
    assert "~/projects/hooks" in event


def test_format_event_includes_commit_hash():
    event = swarm.format_event("~/projects/hooks", "abc1234", "[DONE] implement feature")
    assert "abc1234" in event


def test_format_event_includes_commit_message():
    event = swarm.format_event("~/projects/hooks", "abc1234", "[DONE] implement feature")
    assert "[DONE] implement feature" in event


# ---------------------------------------------------------------------------
# log_event
# ---------------------------------------------------------------------------


def test_log_event_prints_to_stdout(capsys):
    event = "2026-05-07 12:00:00 [SWARM] ~/projects/hooks: abc1234 [DONE] feat"
    swarm.log_event(event, None)

    captured = capsys.readouterr()
    assert event in captured.out


def test_log_event_writes_to_log_file_when_configured(tmp_path):
    log_file = str(tmp_path / "swarm.log")
    event = "2026-05-07 12:00:00 [SWARM] ~/projects/hooks: abc1234 [DONE] feat"

    swarm.log_event(event, log_file)

    content = open(log_file, encoding="utf-8").read()
    assert event in content


def test_log_event_does_not_write_to_file_when_not_configured(tmp_path, capsys):
    swarm.log_event("some event", None)
    # tmp_path should remain empty — no file was created
    assert list(tmp_path.iterdir()) == []


def test_log_event_appends_to_existing_log_file(tmp_path):
    log_file = str(tmp_path / "swarm.log")

    swarm.log_event("first event", log_file)
    swarm.log_event("second event", log_file)

    content = open(log_file, encoding="utf-8").read()
    assert "first event" in content
    assert "second event" in content
