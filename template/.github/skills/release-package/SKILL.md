---
name: release-package
description: Build, check, rehearse, or explicitly publish Python package releases. Use for package release preparation and deployment; checks alone do not authorize tags, pushes, releases, or uploads.
argument-hint: Version and requested release stage
---

# Release Package

Determine the requested stage before taking action. Building or reviewing a
release does not authorize publishing, pushing, creating a real release tag,
or creating a GitHub release. A request to publish authorizes only the stated
destination and version. Do not infer the version from commit messages.

## Inspect and validate

1. Read the project's release documentation, `pyproject.toml`, release
   scripts, and CI/CD workflows. Identify the integration branch, version
   source and tag convention, changelog policy, distribution names, and what
   each push or release event actually publishes.
2. Verify the complete working tree, including staged and untracked files;
   preserve existing work. Check the intended branch against its remote and
   ensure the version, tag, and any temporary release branch do not already
   exist. Stop on discrepancies rather than overwriting or moving refs.
3. Run the required tests and checks, preview release notes using the
   configured changelog tool, and build and inspect the sdist and wheel using
   the `build-package` skill. For a tag-derived version, distinguish a
   development build from an artifact built at the release tag; verify the
   release artifact metadata matches that tag.
4. Inspect the implementation of any rehearsal command before using it.
   A dry run may still create commits, branches, tags, or modify files; report
   its local effects and do not assume it is read-only.

## Release

Only perform the authorized release stage. Read `RELEASING.md` for the
generated workflow. `make release-notes VERSION=1.2.0` previews notes;
`uv run --group release python -m scripts.release --dry-run 1.2.0` rehearses
in an isolated clone. `make release VERSION=1.2.0` prepares a validated
commit and annotated tag locally without pushing or publishing.

Push only when requested, using the printed atomic push command. A tag push
validates but does not publish. Only when publication is explicitly requested,
run `make publish TAG=v1.2.0`: prereleases go to TestPyPI and final releases
to PyPI. The workflow creates a GitHub release after publication succeeds.

Use the current project's actual script and workflow if they differ. Do not
push or upload separately unless requested. A successful push does not prove
publication succeeded: inspect the relevant workflow runs and package
destination, and report the exact tag, destinations, and outcomes.

On failure, inspect local and remote state and report partial completion.
Never blindly retry an upload or recreate, move, or delete an existing tag;
follow the project's recovery procedure.
