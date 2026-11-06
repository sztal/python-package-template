---
name: docstring-audit
description: Audit public documentation and doctest examples for accuracy.
argument-hint: Optional module or documentation concern
---

# Docstring Audit

Check public classes, functions, and properties for concise, accurate
docstrings in the project's configured style. Determine the public API from
exports and documentation, not just naming conventions. Review examples and
the doctests actually collected by pytest. Keep comments focused on
non-obvious behavior and avoid documenting implementation details as API
contracts.

Record confirmed unresolved source defects in `BUGS.md`, not in `wiki/`, and
leave their fixes to a separate bug-fixing task. After documentation changes,
run the applicable lint, pytest, and documentation build checks, accounting for
optional features. Report checks that are unavailable or fail.
