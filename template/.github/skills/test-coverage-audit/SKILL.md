---
name: test-coverage-audit
description: Find meaningful missing pytest coverage without mixing in source bug fixes.
argument-hint: Optional module or coverage concern
---

# Test Coverage Audit

Start with `make coverage`, then inspect uncovered behavior alongside its tests.
Prioritize branches, validation, error paths, and public behavior. Avoid adding
tests only to execute trivial lines.

If coverage work exposes a confirmed source bug, do not fix it in this task.
Record it in `BUGS.md` for `fix-bugs`: create the ledger if needed and
include the source file and line number, a one-sentence description, and a
minimal reproduction. When writing the ledger, remove entries that are clearly
stale or already fixed; never delete the file itself.
