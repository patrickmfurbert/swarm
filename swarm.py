"""
Swarm — a generic git worktree watcher for multi-agent development workflows.

Watches multiple git worktrees for commits matching a configurable pattern
and notifies you when a matching commit is found.

Usage: python swarm.py [--config CONFIG] [--interval INTERVAL] [--pattern PATTERN]
"""

import json
import os
import subprocess
import sys
from datetime import datetime

__version__ = "0.1.0"

DEFAULT_PATTERN = "[DONE]"
DEFAULT_POLL_INTERVAL = 30
DEFAULT_STATE_FILE = os.path.expanduser("~/.config/swarm/seen.log")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def find_config_file() -> "str | None":
    """Search standard locations for a config file. Returns path or None."""
    candidates = [
        os.path.join(os.getcwd(), "swarm.json"),
        os.path.expanduser("~/.config/swarm/config.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def load_config(config_path: "str | None") -> dict:
    """Load and parse config JSON from the given path or discovered location.

    Raises FileNotFoundError if no config is found.
    Raises ValueError if the JSON is malformed.
    """
    if config_path is None:
        config_path = find_config_file()
    if config_path is None:
        raise FileNotFoundError("No config file found")
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in config file: {exc}") from exc
    # Expand ~ in worktree paths
    if "worktrees" in config and isinstance(config["worktrees"], list):
        config["worktrees"] = [
            os.path.expanduser(p) for p in config["worktrees"]
        ]
    return config


def validate_config(config: dict) -> None:
    """Validate required config fields; apply defaults for optional fields.

    Raises ValueError if the config is invalid.
    Mutates config in-place to apply defaults.
    """
    if "worktrees" not in config:
        raise ValueError("Config missing required field: 'worktrees'")
    if not isinstance(config["worktrees"], list):
        raise ValueError("Config field 'worktrees' must be a list")
    if len(config["worktrees"]) == 0:
        raise ValueError("Config field 'worktrees' must not be empty")

    if "poll_interval_seconds" in config:
        interval = config["poll_interval_seconds"]
        if not isinstance(interval, int):
            raise ValueError("Config field 'poll_interval_seconds' must be an integer")
        if interval < 1:
            raise ValueError("Config field 'poll_interval_seconds' must be >= 1")

    config.setdefault("pattern", DEFAULT_PATTERN)
    config.setdefault("poll_interval_seconds", DEFAULT_POLL_INTERVAL)
    config.setdefault("log_file", None)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def load_seen_commits(state_file: str) -> "set[str]":
    """Load previously seen commit hashes from the state file.

    Returns an empty set if the file does not exist.
    """
    if not os.path.isfile(state_file):
        return set()
    with open(state_file, "r", encoding="utf-8") as fh:
        return {line.strip() for line in fh if line.strip()}


def save_seen_commit(state_file: str, commit_hash: str) -> None:
    """Append a commit hash to the state file.

    Creates the file (and parent directories) if they do not exist.
    Prints a warning to stderr and continues if the file is not writable.
    """
    try:
        parent = os.path.dirname(state_file)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(state_file, "a", encoding="utf-8") as fh:
            fh.write(commit_hash + "\n")
    except OSError as exc:
        print(f"[SWARM] warning: could not write state file: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------


def get_latest_commit(worktree_path: str) -> "tuple[str, str] | None":
    """Return (hash, message) of the most recent commit in the worktree.

    Returns None if the path does not exist, is not a git repo, has no
    commits, or if the git command fails for any reason.
    """
    if not os.path.exists(worktree_path):
        print(
            f"[SWARM] warning: worktree path does not exist: {worktree_path}",
            file=sys.stderr,
        )
        return None
    try:
        result = subprocess.run(
            ["git", "-C", worktree_path, "log", "-1", "--pretty=format:%H\t%s"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        print(f"[SWARM] warning: git command failed for {worktree_path}: {exc}", file=sys.stderr)
        return None

    if result.returncode != 0 or not result.stdout.strip():
        if result.returncode != 0:
            print(
                f"[SWARM] warning: git log failed for {worktree_path}: {result.stderr.strip()}",
                file=sys.stderr,
            )
        return None

    parts = result.stdout.strip().split("\t", 1)
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


def matches_pattern(message: str, pattern: str) -> bool:
    """Return True if pattern is a substring of message (case-sensitive)."""
    return pattern in message


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def format_event(worktree_path: str, commit_hash: str, message: str) -> str:
    """Format a notification line for a matching commit."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"{timestamp} [SWARM] {worktree_path}: {commit_hash} {message}"


def log_event(event: str, log_file: "str | None") -> None:
    """Print event to stdout and optionally append it to a log file."""
    print(event)
    if log_file:
        log_file = os.path.expanduser(log_file)
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as fh:
                fh.write(event + "\n")
        except OSError as exc:
            print(f"[SWARM] warning: could not write log file: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Watching
# ---------------------------------------------------------------------------


def watch_worktree(
    worktree_path: str,
    pattern: str,
    seen: "set[str]",
    state_file: str,
    log_file: "str | None" = None,
) -> None:
    """Check a worktree for a new matching commit and notify if found.

    Updates the seen set and persists the hash to the state file.
    Does nothing if the latest commit has already been seen, doesn't
    match the pattern, or if git fails.
    """
    result = get_latest_commit(worktree_path)
    if result is None:
        return
    commit_hash, message = result
    if commit_hash in seen:
        return
    if not matches_pattern(message, pattern):
        return
    seen.add(commit_hash)
    save_seen_commit(state_file, commit_hash)
    event = format_event(worktree_path, commit_hash, message)
    log_event(event, log_file)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point: parse arguments, load config, run the main watch loop."""
    import argparse
    import time

    parser = argparse.ArgumentParser(
        prog="swarm",
        description="Watch git worktrees for done commits",
    )
    parser.add_argument("--config", help="path to config file")
    parser.add_argument("--interval", type=int, help="override poll interval in seconds")
    parser.add_argument("--pattern", help="override commit message pattern to match")
    parser.add_argument("--version", action="version", version=f"swarm {__version__}")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except FileNotFoundError as exc:
        print(f"[SWARM] error: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"[SWARM] error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        validate_config(config)
    except ValueError as exc:
        print(f"[SWARM] error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.interval is not None:
        config["poll_interval_seconds"] = args.interval
    if args.pattern is not None:
        config["pattern"] = args.pattern

    state_file = DEFAULT_STATE_FILE
    seen = load_seen_commits(state_file)

    print(f"[SWARM] watching {len(config['worktrees'])} worktree(s) for '{config['pattern']}'")

    try:
        while True:
            for worktree in config["worktrees"]:
                watch_worktree(
                    worktree_path=worktree,
                    pattern=config["pattern"],
                    seen=seen,
                    state_file=state_file,
                    log_file=config.get("log_file"),
                )
            time.sleep(config["poll_interval_seconds"])
    except KeyboardInterrupt:
        print("\n[SWARM] stopped", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
