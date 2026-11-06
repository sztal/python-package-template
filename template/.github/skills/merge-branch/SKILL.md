---
name: merge-branch
description: Prepare or perform an explicitly requested feature branch merge into the project's integration branch, including validation and appropriate release notes. Use for integration, not ordinary development.
argument-hint: Source branch and optional target branch
---

# Merge Branch

Preparation or review does not authorize a merge, push, tag, or release.
Determine the target from the request and repository configuration; do not
assume its name. Use the project's documented merge helper if one exists,
after inspecting what it changes and validating its prerequisites.

## Prepare

1. Inspect the working tree, source and target branches, their common ancestor,
   and relevant remote state. Preserve existing work. Do not switch branches
   or update refs if that would overwrite or mix unrelated changes.
2. Review the final integrated changes against the target, including tests,
   documentation, and migrations. Resolve conflicts in the source branch
   only when authorized; never reset or force-update the target.
3. Follow the repository's changelog policy. Where Towncrier is configured,
   record concise user-visible changes in the configured fragment categories
   and naming format, unless the project has a merge helper that does this.
   Do not add fragments for changes the policy excludes.
4. Run the relevant tests, lint, and other required project checks on the
   integrated result. Report failures or conflicts; do not bypass checks.

## Merge

Only when the user explicitly requests a merge, apply the project's normal
merge procedure to the verified target. If the target has moved since
validation, re-evaluate the integrated result before completing the merge.
Do not push unless requested. Report the source, target, resulting commit,
release-note treatment, validation results, and any remaining remote action.
