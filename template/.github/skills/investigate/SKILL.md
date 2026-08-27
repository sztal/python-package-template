---
name: investigate
description: Investigate a reported behavior without fixing existing source files.
argument-hint: Describe the issue, command, failure, or behavior
---

# Investigate

Start from the nearest failing test, command, symbol, or file. Reproduce the
behavior when possible, identify the controlling code path, and report facts,
hypotheses, evidence, and a minimal fix direction.

Do not modify existing source, tests, configuration, or documentation during an
investigation. If the investigation confirms a source bug, record it in
`BUGS.md` rather than fixing it. Create the file if necessary; each entry
must give the source file and line number, a one-sentence description, and a
minimal reproduction. When updating the ledger, remove entries that are clearly
stale or already fixed, but never delete the ledger itself.
