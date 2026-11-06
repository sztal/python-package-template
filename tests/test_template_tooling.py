"""Regression tests for generated development and release tooling."""

from __future__ import annotations

import py_compile
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import copier
import pytest
import yaml

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
        {},
        {"package_layout": "src", "features": [], "target_python": "py315"},
        {"package_type": "namespace", "namespace_name": "example_namespace"},
        {"package_layout": "src", "package_type": "namespace", "features": []},
        {
            "package_layout": "src",
            "package_type": "namespace",
            "namespace_name": "example_namespace",
            "entry_points": ["cli"],
            "cli": "click",
            "features": ["tasks", "docs", "doctest"],
            "doctest": ["docstrings", "docs", "readme"],
        },
        {"entry_points": ["cli"], "cli": "click", "install": "uv pip"},
        {"features": ["docs"]},
        {"integration_branch": "develop", "changelog": False},
        {"integration_branch": "release/stable", "changelog": False, "features": []},
        {"pytest_testmon": "manual"},
        {"pytest_testmon": "automatic"},
        {
            "features": ["tasks", "docs", "doctest"],
            "doctest": ["docstrings", "docs", "readme"],
        },
    ],
    ids=(
        "flat-standard-default",
        "src-standard-no-options",
        "flat-namespace",
        "src-namespace-default-name",
        "src-namespace-cli-doctests",
        "click",
        "docs-only",
        "no-changelog-docs",
        "no-changelog-no-docs",
        "testmon-manual",
        "testmon-automatic",
        "doctests",
    ),
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
    target_python = data.get("target_python", "py314")
    assert isinstance(target_python, str)
    assert config["tool"]["ruff"]["target-version"] == target_python
    assert config["tool"]["mypy"]["python_version"] == f"3.{target_python[3:]}"
    assert config["project"]["requires-python"] == ">=3.13"
    assert "Programming Language :: Python :: 3.15" in config["project"]["classifiers"]
    assert (
        "Programming Language :: Python :: 3.12" not in config["project"]["classifiers"]
    )
    checks_workflow = yaml.safe_load(
        (project / ".github/workflows/checks.yaml").read_text()
    )
    assert checks_workflow["jobs"]["tests"]["strategy"]["matrix"]["python_version"] == [
        "3.13",
        "3.14",
        "3.15",
    ]
    assert "pytest-xdist>=3.8" in config["dependency-groups"]["test"]
    testmon = data.get("pytest_testmon", "no")
    assert ("pytest-testmon>=2.3.0" in config["dependency-groups"]["test"]) is (
        testmon != "no"
    )
    assert ("--testmon" in config["tool"]["pytest"]["addopts"]) is (
        testmon == "automatic"
    )
    for target in ("coverage", "coverage-html"):
        result = subprocess.run(  # noqa: S603
            [make, "--just-print", target],
            cwd=project,
            check=True,
            capture_output=True,
            text=True,
        )
        command = next(
            line for line in result.stdout.splitlines() if "coverage run" in line
        )
        assert ("--no-testmon" in command.split()) is (testmon != "no")
    assert "twine>=6.1" in config["dependency-groups"]["release"]
    assert config["tool"]["coverage"]["report"]["fail_under"] == MIN_COVERAGE
    if "docstrings" in data.get("doctest", []):
        source, _ = package_locations(data)
        assert source in config["tool"]["pytest"]["testpaths"]
        assert "." not in config["tool"]["pytest"]["testpaths"]
    release_workflow = yaml.safe_load(
        (project / ".github/workflows/release.yaml").read_text()
    )
    events = release_workflow[True]  # PyYAML treats "on" as a YAML 1.1 boolean.
    assert "workflow_dispatch" in events
    assert "branches" not in events["push"]
    assert "scripts.release --dry-run" in (project / "RELEASING.md").read_text()


def test_generated_branch_and_changelog(
    generated: tuple[Path, dict[str, object]],
) -> None:
    """Keep changelog support and branch references consistent."""
    project, data = generated
    with (project / "pyproject.toml").open("rb") as stream:
        config = tomllib.load(stream)
    has_changelog = data.get("changelog", True)
    assert (project / "CHANGELOG.md").exists() is has_changelog
    assert (project / "changelog.d").exists() is has_changelog
    assert ("towncrier" in config["tool"]) is has_changelog
    assert (
        "towncrier>=25.8" in config["dependency-groups"]["release"]
    ) is has_changelog
    assert ("Changelog" in config["project"]["urls"]) is has_changelog
    if "docs" in data.get("features", ["tasks", "docs"]):
        assert (project / "docs/changelog.md").exists() is has_changelog
    release_workflow = yaml.safe_load(
        (project / ".github/workflows/release.yaml").read_text()
    )
    branch = data.get("integration_branch", "master")
    ci = yaml.safe_load((project / ".github/workflows/ci.yaml").read_text())
    assert ci[True]["push"]["branches"] == [branch]
    assert release_workflow["jobs"]["resolve"]["steps"][0]["with"]["ref"] == branch
    assert (
        f'INTEGRATION_BRANCH = "{branch}"'
        in (project / "scripts/release.py").read_text()
    )
    assert "INTEGRATION_BRANCH" in (project / "scripts/publish.py").read_text()
    merge_skill = (project / ".github/skills/merge-branch/SKILL.md").read_text()
    if has_changelog:
        assert f"merge into `{branch}`" in merge_skill
        assert "commit messages and Git history" in merge_skill
        assert (
            "--notes-file" in (project / ".github/workflows/release.yaml").read_text()
        )
    else:
        assert "do not create fragments" in merge_skill
        assert (
            "--generate-notes"
            in (project / ".github/workflows/release.yaml").read_text()
        )


@pytest.mark.parametrize("changelog", [True, False])
def test_generated_release_tools(
    tmp_path: Path, template_source: Path, *, changelog: bool
) -> None:
    """Exercise release preparation with and without Towncrier on a custom branch."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "user_name": "Test User",
            "user_email": "test@example.invalid",
            "integration_branch": "release/stable",
            "changelog": changelog,
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            "/dev/null",
            "tests/test_release_tools.py",
            "-q",
        ],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "branch",
    ["", "HEAD", "-bad", "bad..branch", "bad/.hidden", "bad.lock", "bad'branch"],
)
def test_invalid_integration_branch_is_rejected(
    tmp_path: Path, template_source: Path, branch: str
) -> None:
    """Reject names that cannot safely be used as Git refs and workflow input."""
    with pytest.raises(ValueError, match="valid Git branch name"):
        copier.run_copy(
            str(template_source),
            tmp_path / "project",
            data={
                "project_name": "example-package",
                "project_description": "Example package",
                "user_name": "Test User",
                "user_email": "test@example.invalid",
                "integration_branch": branch,
            },
            defaults=True,
            unsafe=True,
            quiet=True,
        )


def package_locations(data: dict[str, object]) -> tuple[str, str]:
    """Return the expected source path and import name for a generated project."""
    root = "src" if data.get("package_layout") == "src" else "."
    if data.get("package_type") == "namespace":
        namespace = data.get("namespace_name", "example_package")
        return f"{root}/{namespace}/example_package", f"{namespace}.example_package"
    return f"{root}/example_package", "example_package"


def test_generated_package_layout(generated: tuple[Path, dict[str, object]]) -> None:
    """Keep package paths, imports, and build settings consistent."""
    project, data = generated
    source, import_name = package_locations(data)
    assert (project / source / "__init__.py").is_file()
    assert (project / source / "py.typed").is_file()
    if data.get("package_type") == "namespace":
        assert not (project / Path(source).parent / "__init__.py").exists()
    with (project / "pyproject.toml").open("rb") as stream:
        config = tomllib.load(stream)
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]
    if data.get("package_type") == "namespace":
        assert wheel["only-include"] == [source.removeprefix("./")]
        assert wheel.get("sources", []) == (
            ["src"] if data.get("package_layout") == "src" else []
        )
        assert config["tool"]["mypy"]["explicit_package_bases"]
        assert config["tool"]["mypy"]["mypy_path"] == (
            "src" if data.get("package_layout") == "src" else "."
        )
    else:
        assert wheel["packages"] == [source]
    assert config["tool"]["coverage"]["run"]["source_pkgs"] == [import_name]
    assert (
        f"from {import_name} import __version__"
        in (project / "tests/test_version.py").read_text()
    )
    assert (
        f'IMPORT_NAME = "{import_name}"'
        in (project / "scripts/distributions.py").read_text()
    )
    if "cli" in data.get("entry_points", []):
        assert config["project"]["scripts"]["example-package"].startswith(
            f"{import_name}.cli:"
        )
        assert (
            f"from {import_name}.cli import "
            in (project / "tests/test_cli.py").read_text()
        )
    if "docs" in data.get("features", ["tasks", "docs"]):
        assert f"::: {import_name}" in (project / "docs/reference/api.md").read_text()


def test_built_wheel_preserves_import_path(
    generated: tuple[Path, dict[str, object]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Build and import the actual wheel without leaking namespace siblings."""
    project, data = generated
    source, import_name = package_locations(data)
    if data.get("package_type") == "namespace":
        sibling = project / Path(source).parent / "unrelated_package"
        sibling.mkdir()
        (sibling / "__init__.py").write_text("")
    monkeypatch.setenv("UV_DYNAMIC_VERSIONING_BYPASS", "1.2.3")
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "hatchling", "build", "-t", "wheel"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    (wheel,) = (project / "dist").glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    wheel_path = import_name.replace(".", "/")
    assert f"{wheel_path}/__init__.py" in names
    assert f"{wheel_path}/py.typed" in names
    if data.get("package_type") == "namespace":
        namespace = data.get("namespace_name", "example_package")
        assert f"{namespace}/__init__.py" not in names
        assert f"{namespace}/unrelated_package/__init__.py" not in names
    installed = project / "installed"
    shutil.unpack_archive(wheel, installed, "zip")
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import importlib, sys; sys.path.insert(0, sys.argv[1]); "
                "module = importlib.import_module(sys.argv[2]); "
                "assert module.__version__ == '1.2.3'"
            ),
            str(installed),
            import_name,
        ],
        cwd=project.parent,
        check=True,
        capture_output=True,
        text=True,
    )
    if data.get("package_type") == "namespace":
        namespace = data.get("namespace_name", "example_package")
        other_install = project / "other-install"
        other_package = other_install / str(namespace) / "other_package"
        other_package.mkdir(parents=True)
        (other_package / "__init__.py").write_text("")
        subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-I",
                "-c",
                (
                    "import importlib, sys; sys.path[:0] = sys.argv[1:3]; "
                    "importlib.import_module(sys.argv[3]); "
                    "importlib.import_module(sys.argv[4])"
                ),
                str(installed),
                str(other_install),
                import_name,
                f"{namespace}.other_package",
            ],
            cwd=project.parent,
            check=True,
            capture_output=True,
            text=True,
        )


def test_generated_agent_guide_uses_selected_layout(
    generated: tuple[Path, dict[str, object]],
) -> None:
    """The rendered agent guide must not contain unresolved Jinja expressions."""
    project, data = generated
    guide = (project / "AGENTS.md").read_text()
    assert "{{" not in guide
    assert "{%" not in guide
    source, import_name = package_locations(data)
    assert f"{source}/" in guide
    assert f"Import package: `{import_name}`" in guide


@pytest.mark.parametrize("cli", ["argparse", "click", "typer", "cyclopts"])
def test_namespaced_cli_imports(
    tmp_path: Path, template_source: Path, cli: str
) -> None:
    """Every CLI framework uses the qualified namespace import."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "user_name": "Test User",
            "user_email": "test@example.invalid",
            "github_user": "example",
            "package_layout": "src",
            "package_type": "namespace",
            "namespace_name": "example_namespace",
            "entry_points": ["cli"],
            "cli": cli,
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    py_compile.compile(str(project / "tests/test_cli.py"), doraise=True)
    assert (
        "from example_namespace.example_package.cli import"
        in (project / "tests/test_cli.py").read_text()
    )
    with (project / "pyproject.toml").open("rb") as stream:
        config = tomllib.load(stream)
    assert config["project"]["scripts"]["example-package"].startswith(
        "example_namespace.example_package.cli:"
    )
    if cli == "click":
        source = project / "src/example_namespace/example_package/cli.py"
        assert '@click.version_option(package_name="example-package")' in (
            source.read_text()
        )


@pytest.mark.parametrize("namespace", ["", "not-valid", "a.b", "123", "class"])
def test_invalid_namespace_is_rejected(
    tmp_path: Path, template_source: Path, namespace: str
) -> None:
    """Reject namespace names that cannot appear in Python import statements."""
    with pytest.raises(ValueError, match="valid Python identifier"):
        copier.run_copy(
            str(template_source),
            tmp_path / "project",
            data={
                "project_name": "example-package",
                "project_description": "Example package",
                "user_name": "Test User",
                "user_email": "test@example.invalid",
                "github_user": "example",
                "package_type": "namespace",
                "namespace_name": namespace,
            },
            defaults=True,
            unsafe=True,
            quiet=True,
        )


@pytest.mark.parametrize("layout", ["flat", "src"])
@pytest.mark.parametrize("namespace", ["tests", "scripts"])
def test_namespace_cannot_shadow_generated_packages(
    tmp_path: Path, template_source: Path, namespace: str, layout: str
) -> None:
    """Namespaces must not collide with generated regular packages."""
    with pytest.raises(ValueError, match="conflicts with a generated"):
        copier.run_copy(
            str(template_source),
            tmp_path / "project",
            data={
                "project_name": "example-package",
                "project_description": "Example package",
                "user_name": "Test User",
                "user_email": "test@example.invalid",
                "github_user": "example",
                "package_layout": layout,
                "package_type": "namespace",
                "namespace_name": namespace,
            },
            defaults=True,
            unsafe=True,
            quiet=True,
        )


@pytest.mark.parametrize("layout", ["flat", "src"])
def test_legacy_namespace_answers_migrate_on_recopy(
    tmp_path: Path, template_source: Path, layout: str
) -> None:
    """Preserve the old namespace choice while splitting the two questions."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "user_name": "Test User",
            "user_email": "test@example.invalid",
            "github_user": "example",
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    answer_file = project / ".copier-answers.yml"
    answers = yaml.safe_load(answer_file.read_text())
    answers["package_layout"] = "namespace"
    answers["namespace_name"] = "example_namespace"
    del answers["package_type"]
    answer_file.write_text(yaml.safe_dump(answers))
    data = {"package_layout": layout} if layout == "src" else None
    copier.run_recopy(
        project, data=data, defaults=True, overwrite=True, unsafe=True, quiet=True
    )
    migrated = yaml.safe_load(answer_file.read_text())
    assert migrated["package_layout"] == layout
    assert migrated["package_type"] == "namespace"
    assert migrated["namespace_name"] == "example_namespace"
    prefix = "src/" if layout == "src" else ""
    assert (
        project / f"{prefix}example_namespace/example_package/__init__.py"
    ).is_file()
