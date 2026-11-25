"""An extension to inspect an existing project's ``pyproject.toml``."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2.ext import Extension

if TYPE_CHECKING:
    from os import PathLike

    from jinja2.environment import Environment


def mypy_strict(project: str | PathLike[str]) -> bool:
    """Check whether an existing project enables strict mypy in its config.

    Projects generated before the ``typecheck_level`` question configured strict
    checking directly under ``[tool.mypy]``; this recovers that setting on update,
    including when it was removed locally. Missing or unreadable files count as
    not strict.
    """
    try:
        with (Path(project) / "pyproject.toml").open("rb") as stream:
            config = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError):
        return False
    return config.get("tool", {}).get("mypy", {}).get("strict") is True


class PyprojectExtension(Extension):
    """An extension to inspect an existing project's ``pyproject.toml``."""

    def __init__(self, environment: Environment) -> None:
        """Initialize the extension."""
        super().__init__(environment)
        environment.filters["mypy_strict"] = mypy_strict
