---
name: create-wiki
description: Create durable architecture, design, investigation, or technical reference pages under wiki/. Use when recording verified project knowledge for future contributors.
argument-hint: Topic and relevant sources, decisions, or validation results
---

# Create Wiki Pages

Create concise Markdown notes for future contributors. Use the requested topic
and audience, and inspect the relevant source, tests, configuration, and any
existing related wiki pages before asserting facts. Determine package and
documentation paths from the current repository rather than assuming a layout.

1. Identify the purpose, important facts or decisions, and useful validation
   and follow-up. Distinguish verified facts from assumptions and open questions.
2. Choose a descriptive lowercase, hyphenated filename under `wiki/` or a
   subdirectory. Follow existing wiki conventions when they differ.
3. Write a brief page using the existing example as a starting point. Use
   headings such as Goal, Decisions and findings, Validation, and Follow-up
   when useful; omit empty sections. Link to relevant local sources and use
   diagrams or tables only when they clarify the topic.
4. Verify the page is supported by its sources, internally consistent, and
   located under `wiki/`.

Do not use the wiki as a bug backlog or session log. Report confirmed source
defects for the project's bug ledger rather than recording them in a wiki
page. Do not modify source, tests, or other documentation as part of this
workflow.
