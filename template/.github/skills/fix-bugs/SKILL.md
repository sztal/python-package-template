---
name: fix-bugs
description: Fix bugs recorded in BUGS.md with focused regression tests.
argument-hint: Optional bug entry or module to fix
---

# Fix Bugs

Resolve entries in `BUGS.md` one at a time. Confirm each entry against the
current source before changing code: remove entries that are stale or already
fixed, rather than restoring obsolete behavior.

For a confirmed bug, make the smallest focused source change and add a
regression test that fails before the fix and passes afterward. Run `make lint`
and `make test` after each fix. Only after validation succeeds, remove that
entry from `BUGS.md`. Never delete the file, even when no entries remain.

Do not mix unrelated refactors or test-audit work into a bug fix.
