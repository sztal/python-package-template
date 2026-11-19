---
name: update-readme
description: Update the project README to reflect the package's current source code, wiki, documentation, installation, usage, and development workflow.
argument-hint: Optional README focus or relevant source and documentation
---

# Update README

Update the project README for its users and contributors. Inspect the
existing README, package source and public API, tests, package metadata,
available wiki and documentation pages, agent notes, and development and
release configuration. Resolve disagreements against the implementation and
configuration; do not repeat stale wiki claims or invent missing features.

## Default content

Unless the request specifies a narrower scope, keep the README concise and
include:

1. A one- to three-sentence description near the beginning explaining what
   the package does and who or what it is for.
2. Installation instructions appropriate to the package's actual distribution
   and supported Python versions. Distinguish the distribution name from the
   import name and state any necessary prerequisites.
3. A quick overview of core functionality and use cases, with short, accurate
   examples where useful. Link to existing relevant wiki and documentation
   pages for details and tutorials; do not create links to missing pages.
4. A short developer section covering setup, important checks, and the actual
   contribution and integration workflow. Include the integration branch,
   squash-merge and changelog policies when applicable, and point to existing
   `merge-branch`, `build-package`, and `release-package` skills and release
   documentation where available. Make clear that building, merging, and
   releasing are separate actions and that publication requires authorization.

## Installation sources

Use an index installation only when the package's publication and distribution
identity are supported by reliable project evidence. A configured publishing
workflow or package name alone does not establish that it is published.

When an index installation is unavailable or unconfirmed, inspect the Git
fetch remote configuration, such as with `git remote -v`, for a suitable
repository URL. If available, provide a valid pip VCS installation command,
converting an SCP-style SSH remote to a `git+ssh://` URL when necessary.
Explain access requirements for private repositories without claiming they
are public. Do not copy credentials, tokens, or other secrets from remote URLs
into the README or reports, and do not invent a host, repository, branch, or
release tag. If there are multiple plausible remotes, resolve the intended
source from project evidence or ask the user.

If no suitable remote can be established, document installation from a local
checkout when supported, and report the limitation. Do not contact a remote
or package index merely to verify availability without appropriate permission.

## Validation

Check all changed claims, links, commands, and examples against the current
project. Run relevant README doctests or documentation checks when configured;
otherwise validate practical examples with the existing environment when
feasible. Report checks that could not be run and any unresolved discrepancies.
Do not modify source code, tests, wiki pages, or other documentation as part
of this workflow.
