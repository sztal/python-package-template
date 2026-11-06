"""Tests for this repository's release script."""

from __future__ import annotations

import pytest

from scripts import release


@pytest.mark.parametrize("dry_run", [False, True])
def test_release_uses_generated_github_notes(
    monkeypatch: pytest.MonkeyPatch, *, dry_run: bool
) -> None:
    """Release without reading or updating a repository changelog."""
    commands: list[list[str]] = []

    def record(command: list[str]) -> int:
        commands.append(command)
        return 0

    monkeypatch.setattr(release, "check_repository", lambda: None)
    monkeypatch.setattr(release, "update_version", lambda: "2026.11.6")
    monkeypatch.setattr(release, "get_current_branch", lambda: "main")
    monkeypatch.setattr(release.subprocess, "check_call", record)
    assert release.main(["--dry-run"] if dry_run else []) == 0
    assert not any(command[0] == "towncrier" for command in commands)
    release_command = [
        "gh",
        "release",
        "create",
        "v2026.11.6",
        "--generate-notes",
    ]
    assert (release_command in commands) is not dry_run
