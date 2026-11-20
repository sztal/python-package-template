---
name: create-wiki
description: Create package overview, API, developer, or tutorial pages under wiki/. Use when documenting verified project knowledge and usage for users or contributors.
argument-hint: Topic and relevant sources, decisions, or validation results
---

# Create Wiki Pages

Create useful Markdown documentation for the requested topic and audience.
Inspect relevant source, tests, configuration, agent notes, and existing
related wiki pages before asserting facts. Determine package and documentation
paths from the current repository rather than assuming a layout.

## Default structure

When creating a wiki, use this structure by default, adapting it to the request
and existing project conventions:

- `wiki/`: one or more overview pages covering package concepts, design,
  functionality, and usage patterns.
- `wiki/api/`: detailed documentation of the package's public API.
- `wiki/dev/`: technical details for developers, including the development
  and integration workflow.
- `wiki/tutorials/`: hands-on tutorials demonstrating core functionality and
  usage patterns.

For developer workflow notes, check the project's integration branch and
changelog policy. By default, prefer `git merge --squash` when merging
development branches into the integration branch (`master` unless configured
otherwise). If a changelog is used, describe work on dedicated branches and
adding changelog entries or fragments only at the integration merge, not for
individual commits or merges into other branches. Distinguish this from any
release-time assembly of the changelog. Respect documented project-specific
policies and do not claim an unverified workflow is already in use.

For a narrower request, create only the relevant pages; do not invent content
or reorganize existing pages merely to fill the structure. Use descriptive
lowercase, hyphenated filenames unless the project uses another convention.

## Example testing

Wiki examples are not run via pytest by convention. Do not ask about or
automatically configure their discovery or testing. Check examples against the
project's implementation and, when practical, validate them independently.

This differs from examples under `docs/`: in projects using `docs/`, set up
those examples to be compatible with automatic pytest/doctest execution.
Use a format and configuration the runner actually collects; ordinary
Markdown code fences are not automatically collected by pytest's doctest
support. Verify collection and execution when configuring documentation tests.
This wiki workflow does not itself configure or modify `docs/` tests.

## Writing and validation

1. Identify the purpose, important facts or decisions, and useful validation
   and follow-up. Distinguish verified facts from assumptions and open questions.
2. Write pages suited to their audience. Link to relevant local sources and use
   diagrams or tables only when they clarify the topic.
3. Verify that pages are supported by their sources, internally consistent, and
   located under `wiki/`. Report example checks and any limitations.

Do not use the wiki as a bug backlog or session log. Report confirmed source
defects for the project's bug ledger rather than recording them in a wiki
page. Do not modify source, tests, or other documentation as part of this
workflow.
