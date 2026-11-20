# python-package-template

[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-purple.json)](https://github.com/copier-org/copier)
![Latest release](https://img.shields.io/github/v/release/sztal/python-package-template)
[![CI](https://img.shields.io/github/actions/workflow/status/sztal/python-package-template/ci.yaml?branch=master&logo=github&label=CI)](https://github.com/sztal/python-package-template/actions/workflows/ci.yaml)
[![License](https://img.shields.io/github/license/sztal/python-package-template)](https://github.com/sztal/python-package-template/blob/master/LICENSE)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

Copier template for modern Python packages, with configurable packaging,
testing, documentation, release workflows, and agent guidance. This repository
contains the template; projects generated from it are independent.

## What Copier Does

Copier reads the answers and rendering rules in `copier.yaml`, evaluates the
files under `template/`, and writes a new project into a destination directory.
The generated project is independent: it gets its own `pyproject.toml`, source
tree, tests, documentation, CI configuration, and Git history.

The main flow is:

```text
copier.yaml + template/ + extensions/
              |
              | answers and Jinja rendering
              v
        generated Python project
```

The generated project also receives `.copier-answers.yml`. Copier uses that
file during `copier update` to remember the choices made when the project was
created and to apply later template changes consistently.

## Requirements

- [Git](https://git-scm.com/) 2 or newer
- [Python](https://www.python.org/) 3.13 or newer
- [Copier](https://copier.readthedocs.io/) 9.6 or newer
- [Copier Template-Extensions](https://github.com/copier-org/copier-template-extensions) 0.3.2 or newer

Install Copier with [uv](https://docs.astral.sh/uv/) or `pipx`:

```bash
# uv
uv tool install copier --with copier-template-extensions

# pipx
pipx install copier
pipx inject copier copier-template-extensions
```

## Generate A Project

Use the GitHub shorthand or a Git URL as the template source:

```bash
# HTTPS through the GitHub shorthand.
copier copy --trust gh:sztal/python-package-template ./path/to/project

# SSH.
copier copy --trust git@github.com:sztal/python-package-template ./path/to/project
```

For a Git-backed template, Copier selects the latest release tag by default,
including when the source is a local directory. The options described below
reflect the current repository and may not all be present in an older release.
To use the current local revision instead, run:

```bash
copier copy --trust --vcs-ref=HEAD /path/to/python-package-template ./path/to/project
```

For a remote source, the chosen revision must be available on that remote.

## Project Options

Copier prompts for the following choices. Conditional questions appear only
when their prerequisites are selected. Values such as the import name, package
paths, repository and documentation URLs, and copyright details are derived
from the answers rather than prompted for separately.

### Identity and repository

- `project_name` and `project_description`: the project name and description.
- `distribution_name`: the name used by pip; defaults to a slug of
  `project_name` and can differ from the Python import name.
- `user_name` and `user_email`: author and maintainer details, defaulting to
  the local Git `user.name` and `user.email`.
- `public_github`: whether to assume a public GitHub repository; enabled by
  default. Disabling it avoids generated public repository and Pages URLs.
- `github_user`: GitHub username, prompted only for a public GitHub project;
  defaults to `sztal`. The repository path is derived from this username and
  the distribution name.
- `github_actions`: generate GitHub Actions workflows; defaults to the value of
  `public_github`, but can be selected independently.
- `pypi_publish`: configure explicit PyPI publishing; also defaults to
  `public_github` and can be overridden independently. Without Actions,
  publishing uses Twine locally. Configuration does not publish the package.
- `license`: choose Apache-2.0, BSD-3-Clause, GPL-3.0-only, LGPL-3.0,
  MIT (default), MPL-2.0, or no license. Choosing no license does not prevent
  publishing or make the project private.
- `code_of_conduct`: generate `CODE_OF_CONDUCT.md`; disabled by default.

### Package and Python versions

- `package_layout`: a flat (default) or `src` source layout.
- `package_type`: a standard (default) or implicit namespace package, selected
  independently of the layout. With `namespace`, `namespace_name` specifies
  the top-level namespace; it defaults to the package name and must be a Python
  identifier that does not conflict with generated `tests` or `scripts`.
- `minimum_python`: the minimum supported version, `3.13` (default), `3.14`,
  or `3.15`. When enabled, generated CI tests supported versions through
  Python 3.15.
- `target_python`: the default interpreter and Ruff and mypy target: `py313`,
  `py314`, or `py315` (default). It must be at least the minimum version;
  code and tool suggestions must still support the minimum.
- `entry_points`: optional entry points; the available choice is a command-line
  interface (`cli`), and none is selected by default. When selected, `cli`
  prompts for the framework: argparse, Click, Typer, or Cyclopts.

### Development and release

- `package_manager`: uv (default), Pixi, or Mamba. Pixi uses locked
  environments for Nox. Mamba uses a named environment and pip dependencies
  from `pyproject.toml` without a lockfile.
- `mamba_environment_name`: prompted only for Mamba; defaults to the
  distribution name. Create the environment from `environment.yaml` before
  installing project dependencies.
- `integration_branch`: the branch used for integration and releases;
  defaults to `master`.
- `typecheck_level`: `none`, `basic` (default), or `strict`. Basic also checks
  unannotated function bodies; strict enables mypy's strict checks and additional
  diagnostics.
- `typecheck_source_only`: check only the package source by default. Set to
  false to also check tests and tooling. Mypy may still follow imports from
  the selected paths.
- `require_typecheck`: require passing type checks for merge and release
  validation; disabled by default. Enabled checks still run and report errors.
  These settings can be changed after generation in `[tool.project-checks]` in
  `pyproject.toml`; they apply to local validation and CI.
- `changelog`: enable changelog and Towncrier support; enabled by default.
  Fragments are added when a development branch is merged into the integration
  branch and assembled during release preparation.
- `pytest_testmon`: `no` (default), `manual` to opt in with `pytest --testmon`,
  or `automatic` to use it by default. Coverage targets disable testmon so
  they run the full suite.
- `features`: select documentation and interactive example testing.
  Documentation is selected by default and uses Zensical.
- `nox`: configure Nox sessions for local checks and the Python test matrix;
  enabled by default, independently of GitHub Actions. CI uses Nox when
  enabled and runs the checks directly otherwise.
- `install`: when Nox and uv are selected, choose locked
  dependencies with `uv sync` (default) or latest versions with `uv pip`
  for Nox sessions.
- `doctest`: when interactive example testing is selected, choose docstrings,
  documentation, and/or the README; none is selected by default. Documentation
  examples require the documentation feature.

For example, set `project_name` to `common`, `distribution_name` to
`montec-common`, `package_type` to `namespace`, and `namespace_name` to
`montec` to create the distribution `montec-common` with import name
`montec.common`. Copier saves the distribution name for subsequent updates.

To provide answers non-interactively, pass Copier data explicitly:

```bash
copier copy --trust \
  --data project_name=example \
  --data project_description='An example package' \
  --data minimum_python=3.13 \
  --data target_python=py315 \
  gh:sztal/python-package-template ./example
```

## Update A Project

Run this command from a generated project:

```bash
copier update --trust
```

Copier compares the saved `.copier-answers.yml` with the current template and
updates files while preserving project-specific changes where possible. Review
the resulting diff before committing an update, especially when changing
package layout or documentation settings.

Existing projects using `main` should set `integration_branch=main` when
updating; the new default is `master`. Review existing changelog files when
disabling changelog support, as project-specific files may be preserved.
Existing projects previously used strict type checking; the new
`typecheck_level` defaults to `strict` when updating their saved answers.
The newly visible `distribution_name` defaults to the slug of `project_name`;
if an existing project used a different distribution name, enter it when
prompted and review the update diff.
Review the update diff when disabling public GitHub, Actions, publishing, or
a license: Copier can preserve locally modified files. Existing projects keep
their saved answers; review the selected manager and regenerate its lockfile
if switching between managers. Mamba uses no dependency lockfile; review any
previously generated or locally maintained lockfiles separately.

For projects generated with the former `package_layout: namespace` option,
Copier defaults to a flat namespace package on update. This corrects the
previously built top-level package to use the qualified import name
`namespace_name.package_name`; update downstream imports and review the
generated distribution before releasing it. When overriding both the layout
and namespace name during that update, also set `package_type=namespace`.

Projects using a `target_python` below `py313` must select a supported target
when updating. Existing saved targets are retained; the new `minimum_python`
answer defaults to `3.13`. Review `.python-version` and tooling changes on update.

## Template Mechanics

### `copier.yaml`

This is the template manifest and answer schema. It controls:

- the minimum Copier version;
- the `template/` source directory;
- the `.jinja` suffix used by template files;
- the Jinja extensions loaded during rendering;
- files that should be skipped or preserved;
- the post-generation message;
- interactive answers, defaults, choices, conditional answers, and derived values.

Answers with `when: false` are internal implementation values. For example,
`package_name`, `package_root`, and `repository_url` are derived from visible
answers and are used by templates without asking the user to enter them.

### `template/`

This directory contains the files that can appear in a generated project.
Files ending in `.jinja` are rendered as Jinja templates; ordinary files are
copied as-is. Jinja expressions such as `{{ package_name }}` substitute an
answer, while `{% if docs %}` and similar blocks include content only when a
feature is enabled.

Some filenames contain Jinja expressions too. For example:

```text
template/{% if docs == 'zensical' %}zensical.toml{% endif %}.jinja
```

When `docs` is `zensical`, Copier renders this as `zensical.toml`. When another
documentation option is selected, the filename renders to an empty name and
the file is not generated. This is why conditional filenames are used instead
of putting an unused configuration file in every generated project.

The same mechanism is used for `noxfile.py`, `zensical.toml`, the optional Code
of Conduct, CLI framework files, and the package source tree.

### `zensical.toml` in this repository

The root [zensical.toml](zensical.toml) is **not** a generated-project
template. It configures Zensical for this repository's own documentation site:
site metadata, navigation, theme features, icons, fonts, social links, and
Markdown extensions.

The generated-project version is a separate conditional file:

```text
template/{% if docs == 'zensical' %}zensical.toml{% endif %}.jinja
```

That file is copied only when a generated project chooses Zensical and points
its site metadata at that generated project's repository and documentation.

### Extensions

The `extensions/` package provides small Jinja helpers used by `copier.yaml`:

- `git.py`: reads Git identity values for author and maintainer defaults;
- `slugify.py`: derives distribution and import-safe package names;
- `today.py`: supplies the current date for generated metadata.

These helpers are loaded through `_jinja_extensions` in `copier.yaml`.

## Generated Components

The template produces a complete project workflow rather than only a package
directory:

- `pyproject.toml`: Hatchling build backend, Git-tag versioning through
  `uv-dynamic-versioning`, project metadata, dependency groups, Ruff, pytest,
  coverage, mypy, and optional Towncrier settings;
- a flat or `src/` package directory, optionally under an implicit namespace:
  selected independently by `package_layout` and `package_type`;
- `tests/`: pytest fixtures and version checks;
- `noxfile.py`: optional test, lint, type-check, and documentation sessions
  using the selected package manager;
- `.pre-commit-config.yaml`: Ruff checking and formatting plus repository
  hygiene hooks;
- `Makefile`: commands for installation, testing, linting, type checking,
  coverage, distribution validation, documentation, and release preparation;
- `docs/` and `zensical.toml`: optional Zensical documentation support;
- `.github/workflows/`: optional shared CI checks, optional Pages deployment, and
  explicitly dispatched package publication;
- `AGENTS.md` and `.github/skills/`: generated repository context and
  on-demand workflows for development, audits, wiki notes, package builds,
  branch integration, and releases, including a first-run inspection checklist;
- `scripts/` and `RELEASING.md`: distribution checks, local Git-tag release
  preparation, and optional explicit publication guidance;
- optional `LICENSE`, `CHANGELOG.md`, and `CODE_OF_CONDUCT.md`.

The generated build uses Git tags as its version source. A release tag such as
`v1.2.3` produces package metadata with version `1.2.3`.

## Agent Context And Skills

Generated projects include an `AGENTS.md` guide with the selected package
layout, development conventions, validation commands, and integration and
changelog policy. `STYLE.md` complements the configured Python lint rules.
The files under `.github/skills/` provide task-specific instructions for
agent tools that support repository skills; they are guidance, not commands
that run automatically.

After generating a project, ask your agent to use `agent-context-update` to
inspect the actual repository, replace placeholders, and adapt the guide and
skills to the project. Run it again when the structure, tooling, or workflow
changes. Review its changes and validation results.

The generated guide directs agents to work on the current branch unless
otherwise requested or clearly required, and requires squash-merging development
branches into the configured integration branch. When changelog support is
enabled, it calls for fragments at integration merge time; release preparation
assembles them. Building, merging, pushing,
tagging, and publishing are separate actions: the merge and release skills
require explicit authorization for the relevant operations.

| Skill                                                                         | Purpose                                                               |
| ----------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [agent-context-update](template/.github/skills/agent-context-update/SKILL.md) | Inspect the project and update agent guidance.                        |
| [build-package](template/.github/skills/build-package/SKILL.md.jinja)         | Build and verify distributions without publishing.                    |
| [create-wiki](template/.github/skills/create-wiki/SKILL.md)                   | Create verified overview, API, developer, or tutorial pages.          |
| [docstring-audit](template/.github/skills/docstring-audit/SKILL.md)           | Review public docstrings and collected examples.                      |
| [fix-bugs](template/.github/skills/fix-bugs/SKILL.md)                         | Fix confirmed `BUGS.md` entries with regression tests.                |
| [investigate](template/.github/skills/investigate/SKILL.md)                   | Investigate behavior and record confirmed bugs without fixing source. |
| [merge-branch](template/.github/skills/merge-branch/SKILL.md.jinja)           | Prepare or perform an explicitly requested integration merge.         |
| [release-package](template/.github/skills/release-package/SKILL.md.jinja)     | Validate, prepare, or explicitly publish a release.                   |
| [test-audit](template/.github/skills/test-audit/SKILL.md)                     | Audit test quality and coverage.                                      |
| [test-coverage-audit](template/.github/skills/test-coverage-audit/SKILL.md)   | Address meaningful coverage gaps.                                     |
| [tidy-code](template/.github/skills/tidy-code/SKILL.md)                       | Organize code while preserving behavior.                              |
| [update-readme](template/.github/skills/update-readme/SKILL.md)               | Align the README with the source, documentation, and workflow.        |
| [update-wiki](template/.github/skills/update-wiki/SKILL.md)                   | Correct or extend existing wiki pages.                                |

## Working On This Template

After changing the template, render representative projects before committing:

```bash
uv run copier copy --trust --defaults \
  --data project_name=smoke-test \
  --data project_description='Template smoke test' \
  . /tmp/smoke-test
```

At minimum, check the default flat layout, a `src` layout, a namespace layout,
documentation and Nox both enabled and disabled, and the optional Code of
Conduct. For generated projects, initialize Git, create a version tag,
and run:

```bash
uv build
uv run pytest
make lint
make typecheck
```

When changing a template filename or answer, inspect the generated tree and
the `.copier-answers.yml` file. A small filename expression can determine
whether an entire component exists in the output.
