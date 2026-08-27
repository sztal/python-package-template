---
name: test-audit
description: Audit pytest coverage and quality without mixing in source bug fixes.
argument-hint: Optional module or test concern
---

# Test Audit

Review public behavior, error paths, and meaningful edge cases. Prefer shared
fixtures, factory helpers, parametrization, and short behavioral assertions.
Do not test trivial implementation details.

If an audit reveals a confirmed source bug, do not fix it in this task. Record
it in `BUGS.md` for `fix-bugs`: create the ledger if needed and include
the source file and line number, a one-sentence description, and a minimal
reproduction. When writing the ledger, remove entries that are clearly stale or
already fixed; never delete the file itself. Treat tests that disagree with
current code as potentially stale unless a stronger source of truth confirms a
source bug.
