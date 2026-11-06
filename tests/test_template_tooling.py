"""Regression tests for generated development and release tooling."""

from __future__ import annotations

import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

import copier
import pytest
import yaml

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

MIN_COVERAGE = 90


@pytest.fixture(scope="module")
def template_source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copy the working template without Git so uncommitted changes are tested."""
    project = Path(__file__).resolve().parents[1]
    source = tmp_path_factory.mktemp("template-source")
    shutil.copy(project / "copier.yaml", source)
    for name in ("extensions", "licenses", "template"):
        shutil.copytree(project / name, source / name)
    return source


@pytest.fixture(
    params=[
        {"package_layout": "flat"},
        {"package_layout": "src", "features": []},
        {"package_layout": "namespace", "namespace_name": "example_namespace"},
        {"entry_points": ["cli"], "cli": "click", "install": "uv pip"},
        {"features": ["docs"]},
        {
            "features": ["tasks", "docs", "doctest"],
            "doctest": ["docstrings", "docs", "readme"],
        },
    ],
    ids=("flat", "src-no-options", "namespace", "click", "docs-only", "doctests"),
)
def generated(
    tmp_path: Path, template_source: Path, request: pytest.FixtureRequest
) -> tuple[Path, dict[str, object]]:
    """Render representative package layouts and optional features."""
    data: dict[str, object] = {
        "project_name": "example-package",
        "project_description": "Example package",
        "user_name": "Test User",
        "user_email": "test@example.invalid",
        "github_user": "example",
    }
    data.update(request.param)
    destination = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        destination,
        data=data,
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    return destination, data


def test_rendered_tooling_is_complete(
    generated: tuple[Path, dict[str, object]],
) -> None:
    """Check optional files, configuration, commands, and generated Python syntax."""
    project, data = generated
    features = data.get("features", ["tasks", "docs"])
    assert isinstance(features, list)
    has_tasks = "tasks" in features
    has_docs = "docs" in features
    assert (project / "noxfile.py").exists() is has_tasks
    assert (project / "docs").exists() is has_docs
    assert (project / ".github/workflows/pages.yaml").exists() is has_docs
    assert (project / "scripts/coverage_badge.py").exists() is has_docs
    for path in (project / ".github/workflows").glob("*.yaml"):
        contents = path.read_text()
        assert contents.endswith("\n")
        assert not contents.endswith("\n\n")
        assert isinstance(yaml.safe_load(contents), dict)
    for name in ("check", "distributions", "publish", "release"):
        py_compile.compile(str(project / "scripts" / f"{name}.py"), doraise=True)
    make = shutil.which("make")
    assert make is not None
    subprocess.run(  # noqa: S603
        [make, "--just-print", "check"], cwd=project, check=True, capture_output=True
    )
    with (project / "pyproject.toml").open("rb") as stream:
        config = tomllib.load(stream)
    assert "pytest-xdist>=3.8" in config["dependency-groups"]["test"]
    assert "twine>=6.1" in config["dependency-groups"]["release"]
    assert config["tool"]["coverage"]["report"]["fail_under"] == MIN_COVERAGE
    if "doctest" in features:
        assert "./example_package" in config["tool"]["pytest"]["testpaths"]
        assert "." not in config["tool"]["pytest"]["testpaths"]
    release_workflow = yaml.safe_load(
        (project / ".github/workflows/release.yaml").read_text()
    )
    events = release_workflow[True]  # PyYAML treats "on" as a YAML 1.1 boolean.
    assert "workflow_dispatch" in events
    assert "branches" not in events["push"]
    assert "scripts.release --dry-run" in (project / "RELEASING.md").read_text()


def test_generated_agent_guide_uses_selected_layout(
    generated: tuple[Path, dict[str, object]],
) -> None:
    """The rendered agent guide must not contain unresolved Jinja expressions."""
    project, data = generated
    guide = (project / "AGENTS.md").read_text()
    assert "{{" not in guide
    assert "{%" not in guide
    layout = data.get("package_layout", "flat")
    source = {
        "flat": "./example_package/",
        "src": "src/example_package/",
        "namespace": "example_namespace/example_package/",
    }[layout]
    assert source in guide
