# Swarm — Build Plan
## A generic git worktree watcher for multi-agent development workflows

---

## What Swarm Is

Swarm is a lightweight, cross-platform Python script that watches multiple git worktrees for commits matching a configurable pattern. It is designed to support multi-agent development workflows where multiple AI coding agents work in parallel on separate branches, signaling completion via commit messages.

Swarm has one job: notify you when an agent commits a `[DONE]` message (or any pattern you configure). It does nothing else. Merging, coordinating, and instructing agents is left to you or other tools.

**Package:** `swarm` (run as `python swarm.py` or `swarm` if installed)
**Language:** Python 3.8+
**Dependencies:** None — standard library only
**GitHub:** `patrickmfurbert/swarm`
**Platform:** Windows, Linux, macOS

---

## Git Concepts — Worktrees vs Branches

Understanding the difference between a branch and a worktree is important for understanding how Swarm fits into a multi-agent workflow.

**A branch** is a named pointer to a commit in your git history. Branches exist inside a single repository checkout. When you switch branches with `git checkout`, your working directory changes to reflect that branch — but you can only be on one branch at a time in a given directory.

**A worktree** is a separate working directory linked to the same underlying git repository. Each worktree can be on a different branch simultaneously. Unlike switching branches, worktrees let multiple branches be checked out and actively worked on at the same time in different directories.

**The analogy:**
A branch is like a bookmark in a book. A worktree is like having multiple physical copies of the book open to different pages at the same time.

**Why this matters for multi-agent workflows:**
When multiple AI agents work in parallel, each agent needs its own filesystem sandbox so they do not overwrite each other's in-progress work. Git worktrees provide exactly that — each agent gets its own directory (its own worktree) on its own branch. When an agent finishes its work and commits, it does not affect any other agent's working directory.

Swarm watches the directories (worktrees), not the branches directly. When an agent makes a commit in its worktree that matches the configured pattern, Swarm sees it and notifies you.

```bash
# One repo, four worktrees, four branches — all active simultaneously
git worktree add ../my-project-agent-a -b feature/agent-a
git worktree add ../my-project-agent-b -b feature/agent-b
git worktree add ../my-project-agent-c -b feature/agent-c
git worktree add ../my-project-agent-d -b feature/agent-d
```

---

## Design Principles

- **Zero dependencies** — standard library only, no pip installs required
- **Single file** — the entire application lives in `swarm.py`
- **Generic** — knows nothing about your project, agents, or workflow
- **Minimal output** — only prints when something happens, no noise
- **Persistent state** — remembers seen commits across restarts so it never double-notifies
- **Cross-platform** — works on Windows (PowerShell, CMD, WSL2), Linux, macOS

---

## File Structure

```
swarm/
├── swarm.py              # The entire application
├── config.json           # Example config file
├── README.md             # Usage documentation
├── tests/
│   ├── test_config.py    # Config loading and validation tests
│   ├── test_git.py       # Git command execution tests
│   ├── test_watcher.py   # Worktree watching and pattern matching tests
│   ├── test_state.py     # Seen commit state persistence tests
│   └── conftest.py       # Shared fixtures
└── .github/
    └── workflows/
        └── test.yml      # CI — runs tests on push
```

---

## Configuration

Swarm looks for config in the following locations in order:

1. Path provided via `--config` flag
2. `./swarm.json` (current directory)
3. `~/.config/swarm/config.json` (user config)

**config.json:**
```json
{
  "pattern": "[DONE]",
  "worktrees": [
    "~/projects/my-project-agent-a",
    "~/projects/my-project-agent-b",
    "~/projects/my-project-agent-c",
    "~/projects/my-project-agent-d"
  ],
  "poll_interval_seconds": 30,
  "log_file": "~/.config/swarm/swarm.log"
}
```

**Config fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pattern` | string | no | `"[DONE]"` | Substring to match in commit messages |
| `worktrees` | array | yes | — | List of paths to watch. Supports `~` expansion |
| `poll_interval_seconds` | int | no | `30` | How often to check each worktree |
| `log_file` | string | no | `null` | Optional path to write events to a log file |

---

## State File

Swarm persists seen commit hashes to avoid double-notifying across restarts.

- **Location:** `~/.config/swarm/seen.log`
- **Format:** One commit hash per line
- **Behavior:** If the file doesn't exist, Swarm creates it on first run
- **On startup:** Swarm loads all previously seen hashes into memory before watching

---

## Output Format

Swarm prints one line per new matching commit to stdout:

```
2026-05-07 23:14:02 [SWARM] ~/projects/my-project-agent-c: abc1234 [DONE] implement useOllama streaming hook
2026-05-07 23:44:15 [SWARM] ~/projects/my-project-agent-b: def5678 [DONE] implement ReadFile tool with error handling
```

Format: `TIMESTAMP [SWARM] WORKTREE_PATH: HASH MESSAGE`

If `log_file` is configured, the same lines are written to the log file in addition to stdout.

---

## Error Handling

Swarm should never crash due to a single worktree having a problem. Errors are printed to stderr and Swarm continues watching the remaining worktrees.

| Scenario | Behavior |
|----------|---------|
| Worktree path doesn't exist | Print warning to stderr, skip that worktree, continue |
| Path exists but isn't a git repo | Print warning to stderr, skip that worktree, continue |
| `git log` command fails | Print warning to stderr, skip that worktree this cycle, retry next cycle |
| Config file not found | Print error to stderr, exit with code 1 |
| Config file is malformed JSON | Print error to stderr, exit with code 1 |
| Config missing required `worktrees` field | Print error to stderr, exit with code 1 |
| State file not writable | Print warning to stderr, continue without persisting state |
| KeyboardInterrupt (Ctrl+C) | Print clean exit message, exit with code 0 |

---

## CLI Interface

```
usage: swarm.py [-h] [--config CONFIG] [--interval INTERVAL] [--pattern PATTERN] [--version]

Watch git worktrees for done commits

options:
  -h, --help            show this help message and exit
  --config CONFIG       path to config file (default: searches standard locations)
  --interval INTERVAL   override poll interval in seconds
  --pattern PATTERN     override commit message pattern to match
  --version             show version and exit
```

CLI flags override config file values when both are present.

---

## Internal Architecture

Swarm is structured as a set of pure functions with a single main loop. No classes unless absolutely necessary. Each function does one thing.

```python
# Config
load_config(config_path: str | None) -> dict
validate_config(config: dict) -> None  # raises ValueError if invalid
find_config_file() -> str | None

# State
load_seen_commits(state_file: str) -> set[str]
save_seen_commit(state_file: str, commit_hash: str) -> None

# Git
get_latest_commit(worktree_path: str) -> tuple[str, str] | None
# returns (hash, message) or None if error

# Matching
matches_pattern(message: str, pattern: str) -> bool

# Watching
watch_worktree(
    worktree_path: str,
    pattern: str,
    seen: set[str],
    state_file: str
) -> None  # prints and persists if new matching commit found

# Output
format_event(worktree_path: str, commit_hash: str, message: str) -> str
log_event(event: str, log_file: str | None) -> None

# Main
main() -> None  # argument parsing + main loop
```

---

## Unit Tests

### Testing Stack

| Tool | Purpose |
|------|---------|
| **pytest** | Test runner |
| **unittest.mock** | Mock subprocess calls and filesystem |
| **tmp_path** (pytest fixture) | Temporary directories for filesystem tests |

### Test Coverage Targets

| Module | Target |
|--------|--------|
| Config loading and validation | 100% |
| Git command execution | 100% |
| Pattern matching | 100% |
| State persistence | 100% |
| Output formatting | 100% |
| Main loop | 80%+ |

### Test Files

#### `tests/conftest.py`
Shared fixtures used across test files:
- `tmp_config` — writes a valid config dict to a temp file, returns path
- `tmp_state_file` — returns path to a temp seen.log file
- `fake_git_repo` — creates a minimal fake git repo directory structure in tmp_path
- `valid_config` — returns a valid config dict with temp paths filled in

#### `tests/test_config.py`
```
test_load_config_from_explicit_path
test_load_config_from_current_directory
test_load_config_from_user_config_directory
test_load_config_returns_none_when_not_found
test_validate_config_passes_with_valid_config
test_validate_config_raises_when_worktrees_missing
test_validate_config_raises_when_worktrees_empty
test_validate_config_raises_when_worktrees_not_a_list
test_validate_config_uses_defaults_for_optional_fields
test_validate_config_raises_when_interval_not_integer
test_validate_config_raises_when_interval_less_than_one
test_load_config_raises_on_malformed_json
test_load_config_expands_tilde_in_worktree_paths
test_cli_flags_override_config_values
```

#### `tests/test_git.py`
```
test_get_latest_commit_returns_hash_and_message
test_get_latest_commit_returns_none_when_path_not_exist
test_get_latest_commit_returns_none_when_not_a_git_repo
test_get_latest_commit_returns_none_when_git_command_fails
test_get_latest_commit_returns_none_when_no_commits
test_get_latest_commit_handles_commit_message_with_spaces
test_get_latest_commit_handles_commit_message_with_special_characters
test_get_latest_commit_calls_correct_git_command
```

#### `tests/test_watcher.py`
```
test_matches_pattern_returns_true_when_pattern_in_message
test_matches_pattern_returns_false_when_pattern_not_in_message
test_matches_pattern_is_case_sensitive
test_matches_pattern_handles_empty_pattern
test_matches_pattern_handles_empty_message
test_watch_worktree_notifies_on_new_done_commit
test_watch_worktree_does_not_notify_on_already_seen_commit
test_watch_worktree_does_not_notify_when_pattern_not_matched
test_watch_worktree_does_not_notify_when_no_commits
test_watch_worktree_does_not_notify_when_git_fails
test_watch_worktree_adds_hash_to_seen_set
test_watch_worktree_persists_hash_to_state_file
test_watch_worktree_handles_missing_worktree_gracefully
```

#### `tests/test_state.py`
```
test_load_seen_commits_returns_empty_set_when_file_not_exist
test_load_seen_commits_returns_hashes_from_file
test_load_seen_commits_ignores_empty_lines
test_load_seen_commits_ignores_whitespace_lines
test_save_seen_commit_appends_hash_to_file
test_save_seen_commit_creates_file_if_not_exist
test_save_seen_commit_creates_parent_directories_if_not_exist
test_save_seen_commit_handles_unwritable_file_gracefully
test_round_trip_save_and_load
```

#### `tests/test_output.py`
```
test_format_event_produces_correct_format
test_format_event_includes_timestamp
test_format_event_includes_worktree_path
test_format_event_includes_commit_hash
test_format_event_includes_commit_message
test_log_event_prints_to_stdout
test_log_event_writes_to_log_file_when_configured
test_log_event_does_not_write_to_file_when_not_configured
test_log_event_appends_to_existing_log_file
```

### Example Tests

```python
# tests/test_watcher.py

from unittest.mock import patch, MagicMock
from swarm import watch_worktree, matches_pattern


def test_matches_pattern_returns_true_when_pattern_in_message():
    assert matches_pattern("[DONE] implement useOllama", "[DONE]") is True


def test_matches_pattern_returns_false_when_pattern_not_in_message():
    assert matches_pattern("wip: still working", "[DONE]") is False


def test_matches_pattern_is_case_sensitive():
    assert matches_pattern("[done] implement useOllama", "[DONE]") is False


def test_watch_worktree_notifies_on_new_done_commit(tmp_path, capsys):
    seen = set()
    state_file = str(tmp_path / "seen.log")

    with patch("swarm.get_latest_commit") as mock_git:
        mock_git.return_value = ("abc1234", "[DONE] implement useOllama")
        watch_worktree(
            worktree_path="~/projects/hooks",
            pattern="[DONE]",
            seen=seen,
            state_file=state_file
        )

    captured = capsys.readouterr()
    assert "[SWARM]" in captured.out
    assert "abc1234" in captured.out
    assert "[DONE] implement useOllama" in captured.out


def test_watch_worktree_does_not_notify_on_already_seen_commit(capsys):
    seen = {"abc1234"}

    with patch("swarm.get_latest_commit") as mock_git:
        mock_git.return_value = ("abc1234", "[DONE] implement useOllama")
        watch_worktree(
            worktree_path="~/projects/hooks",
            pattern="[DONE]",
            seen=seen,
            state_file="/tmp/seen.log"
        )

    captured = capsys.readouterr()
    assert captured.out == ""


def test_watch_worktree_handles_missing_worktree_gracefully(capsys):
    seen = set()

    with patch("swarm.get_latest_commit") as mock_git:
        mock_git.return_value = None
        watch_worktree(
            worktree_path="~/projects/does-not-exist",
            pattern="[DONE]",
            seen=seen,
            state_file="/tmp/seen.log"
        )

    captured = capsys.readouterr()
    assert captured.out == ""
```

---

## Build Order

**Step 1 — Project scaffold:**
- Create repo with `swarm.py`, `config.json`, `README.md`, `tests/` directory
- Set up pytest with `pyproject.toml` or `pytest.ini`
- Write `conftest.py` with shared fixtures
- Confirm `pytest` runs with zero tests and passes

**Step 2 — Config loading:**
- Implement `find_config_file()`, `load_config()`, `validate_config()`
- Write and pass all `test_config.py` tests before moving on

**Step 3 — Git integration:**
- Implement `get_latest_commit()` using `subprocess.run`
- Write and pass all `test_git.py` tests before moving on

**Step 4 — State persistence:**
- Implement `load_seen_commits()`, `save_seen_commit()`
- Write and pass all `test_state.py` tests before moving on

**Step 5 — Pattern matching and watching:**
- Implement `matches_pattern()`, `watch_worktree()`
- Write and pass all `test_watcher.py` tests before moving on

**Step 6 — Output and logging:**
- Implement `format_event()`, `log_event()`
- Write and pass all `test_output.py` tests before moving on

**Step 7 — Main loop and CLI:**
- Implement `main()` with argparse
- Wire everything together
- Manual integration test: run against real worktrees, make a `[DONE]` commit, confirm notification appears

**Step 8 — Polish:**
- README with installation and usage instructions
- Example config file
- GitHub Actions CI workflow that runs pytest on push
- Confirm it works on Windows (test in WSL2 and PowerShell)

---

## How to Use This Plan with Copilot CLI

Open Copilot CLI in `~/projects/swarm` and use it to build step by step. Start each session with:

```
I am building Swarm — a generic git worktree watcher for multi-agent 
development workflows. It is a single Python file with zero dependencies.

Stack: Python 3.8+, standard library only, pytest for tests.
Build plan: [paste relevant section]
Current step: [specific step from build order]

Rules:
- Zero external dependencies. Standard library only.
- Write tests before or alongside implementation — never after.
- Every function must have a corresponding test.
- Handle all errors gracefully — Swarm must never crash.
```

---

## Notes

- **Swarm is the first thing to build** — before your main project. It can then be used to coordinate that build itself.
- **Keep it small** — resist the urge to add features. One job, done well.
- **The pattern is configurable** — `[DONE]` is the default but any substring works. Teams can use their own conventions.
- **Swarm is reusable** — any multi-agent project using git worktrees can use Swarm regardless of language, framework, or what the agents are doing.
- **Future extension** — desktop notifications (`notify-send` on Linux, `osascript` on macOS, `toast` on Windows) could be added as an optional feature without changing the core design. Not for v1.
