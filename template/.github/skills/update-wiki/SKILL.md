---
name: update-wiki
description: Update existing architecture, design, investigation, or technical reference pages under wiki/. Use when correcting or extending durable project knowledge.
argument-hint: Wiki page, requested update, and relevant sources or decisions
---

# Update Wiki Pages

Update the requested Markdown pages under `wiki/` without rewriting unrelated
content. Read each target and the relevant source, tests, and configuration;
discover current package and documentation paths rather than assuming a layout.

1. Determine which facts, decisions, or follow-up items need to change.
2. Make the smallest complete update. Retain useful context, correct stale
   paths and claims, and distinguish verified facts from open questions.
3. Follow the page's concise style, linking to local sources when useful.
   Use diagrams or tables only when they improve clarity.
4. Check the resulting pages for accuracy, consistency, and valid Markdown.

Do not introduce a bug backlog or session log in the wiki. If an existing page
contains unresolved defects, report them for the project's bug ledger before
removing the backlog material. Do not modify files outside `wiki/` as part of
this workflow.
