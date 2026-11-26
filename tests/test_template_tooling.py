"""Regression tests for generated development and release tooling."""

from __future__ import annotations

import importlib.util
import os
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
from packaging.version import Version

MIN_COVERAGE = 90
DEFERRED_ANNOTATIONS_MINOR = 14  # PEP 649
LAZY_IMPORTS_MINOR = 15  # PEP 810


def assert_git_ignores(project: Path, ignored: list[str], allowed: list[str]) -> None:
    """Check ignore rules independently of the user's Git configuration."""
    git = shutil.which("git")
    assert git is not None
    subprocess.run([git, "init", "-q", str(project)], check=True)  # noqa: S603
    result = subprocess.run(  # noqa: S603
        [
            git,
            "-C",
            str(project),
            "-c",
            f"core.excludesFile={os.devnull}",
            "check-ignore",
            "--no-index",
            "--stdin",
        ],
        input="\n".join([*ignored, *allowed]) + "\n",
        capture_output=True,
        check=True,
        text=True,
    )
    assert result.stdout.splitlines() == ignored


@pytest.fixture(scope="module")
def template_source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copy the working template without Git so uncommitted changes are tested."""
    project = Path(__file__).resolve().parents[1]
    source = tmp_path_factory.mktemp("template-source")
    shutil.copy(project / "copier.yaml", source)
    for name in ("extensions", "licenses", "template"):
        shutil.copytree(project / name, source / name)
    return source


def test_repository_ignores_tool_artifacts(tmp_path: Path) -> None:
    """Keep local tox, test, and packaging output out of the repository."""
    source = Path(__file__).resolve().parents[1]
    shutil.copy(source / ".gitignore", tmp_path)
    assert_git_ignores(
        tmp_path,
        [
            ".tox/py/log",
            ".testmondata",
            ".testmondata-journal",
            "build/temp",
            "dist/package.whl",
            "extensions/example.egg-info/PKG-INFO",
        ],
        ["uv.lock", "extensions/source.py"],
    )


@pytest.mark.parametrize("testmon", ["no", "manual", "automatic"])
def test_generated_projects_ignore_tool_artifacts(
    tmp_path: Path, template_source: Path, testmon: str
) -> None:
    """Ignore local artifacts regardless of the testmon configuration."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "pytest_testmon": testmon,
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    assert_git_ignores(
        project,
        [
            ".testmondata",
            ".testmondata-journal",
            "build/temp",
            "dist/package.whl",
            "src/example.egg-info/PKG-INFO",
            "coverage-data",
            "coverage-data.host.123",
            "coverage.json",
        ],
        ["uv.lock", "pixi.lock", "coverage-data-source.py"],
    )


@pytest.fixture(
    params=[
        {},
        {"package_layout": "flat"},
        {
            "package_layout": "src",
            "features": [],
            "nox": False,
            "target_python": "py313",
        },
        {"minimum_python": "3.14", "target_python": "py314"},
        {"minimum_python": "3.15", "target_python": "py315", "features": []},
        {
            "package_layout": "flat",
            "package_type": "namespace",
            "namespace_name": "example_namespace",
        },
        {"package_layout": "src", "package_type": "namespace", "features": []},
        {
            "package_layout": "src",
            "package_type": "namespace",
            "namespace_name": "example_namespace",
            "entry_points": ["cli"],
            "cli": "click",
            "features": ["docs", "doctest"],
            "doctest": ["docstrings", "docs", "readme"],
        },
        {"entry_points": ["cli"], "cli": "click", "install": "uv pip"},
        {"features": ["docs"]},
        {"integration_branch": "develop", "changelog": False},
        {"integration_branch": "release/stable", "changelog": False, "features": []},
        {"pytest_testmon": "manual"},
        {"pytest_testmon": "automatic"},
        {
            "features": ["docs", "doctest"],
            "doctest": ["docstrings", "docs", "readme"],
        },
    ],
    ids=(
        "src-standard-default",
        "flat-standard",
        "src-standard-no-options",
        "minimum-and-target-314",
        "minimum-and-target-315",
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
    features = data.get("features", ["docs"])
    assert isinstance(features, list)
    has_nox = data.get("nox", True)
    has_docs = "docs" in features
    assert (project / "noxfile.py").exists() is has_nox
    assert (project / "docs").exists() is has_docs
    assert (project / ".github/workflows/pages.yaml").exists() is has_docs
    assert (project / "scripts/coverage_badge.py").exists() is has_docs
    assert (project / ".github/skills/update-readme/SKILL.md").is_file()
    for path in (project / ".github/workflows").glob("*.yaml"):
        contents = path.read_text()
        assert contents.endswith("\n")
        assert not contents.endswith("\n\n")
        assert isinstance(yaml.safe_load(contents), dict)
    for name in ("check", "distributions", "publish", "release", "typecheck"):
        py_compile.compile(str(project / "scripts" / f"{name}.py"), doraise=True)
    make = shutil.which("make")
    assert make is not None
    subprocess.run(  # noqa: S603
        [make, "--just-print", "check"], cwd=project, check=True, capture_output=True
    )
    with (project / "pyproject.toml").open("rb") as stream:
        config = tomllib.load(stream)
    assert config["tool"]["project-checks"] == {
        "typecheck_level": "basic",
        "typecheck_source_only": True,
        "require_typecheck": False,
    }
    assert "pytest-xdist>=3.8" in config["dependency-groups"]["test"]
    testmon = data.get("pytest_testmon", "no")
    assert any(
        dependency.startswith("pytest-testmon")
        for dependency in config["dependency-groups"]["test"]
    ) is (testmon != "no")
    assert ("--testmon" in config["tool"]["pytest"]["addopts"]) is (
        testmon == "automatic"
    )
    assert config["tool"]["pytest"].get("consider_namespace_packages") is (
        True if data.get("package_type") == "namespace" else None
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
    if "docstrings" in data.get("doctest", []):  # type: ignore
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


@pytest.mark.parametrize(
    "policy",
    [
        ({}, ["docs"], False),
        ({"require_typecheck": False, "nox": False}, [], False),
        ({"require_typecheck": True}, ["docs"], True),
        ({"require_typecheck": True, "nox": False}, [], True),
    ],
)
def test_typecheck_release_and_ci_policy(
    tmp_path: Path,
    template_source: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    policy: tuple[dict[str, bool], list[str], bool],
) -> None:
    """Keep typecheck advisory or required in both release and shared CI."""
    option, features, required = policy
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "features": features,
            **option,
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    workflow = yaml.safe_load((project / ".github/workflows/checks.yaml").read_text())
    steps = workflow["jobs"]["checks"]["steps"]
    typecheck = next(
        step for step in steps if step.get("run") == "make check-typecheck"
    )
    assert not typecheck.get("continue-on-error", False)

    spec = importlib.util.spec_from_file_location(
        "generated_typecheck", project / "scripts/typecheck.py"
    )
    assert spec is not None
    assert spec.loader is not None
    typecheck_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(typecheck_module)
    calls: list[list[str]] = []

    def run(command: list[str], *, check: bool) -> None:
        assert check
        calls.append(command)
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(typecheck_module.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["typecheck", "--policy"])
    config = project / "pyproject.toml"
    initial = config.read_text()
    for current in (required, not required):
        config.write_text(
            initial.replace(
                f"require_typecheck = {str(required).lower()}",
                f"require_typecheck = {str(current).lower()}",
            )
        )
        if current:
            with pytest.raises(subprocess.CalledProcessError):
                typecheck_module.main()
        else:
            typecheck_module.main()
            assert "Type checking failed" in capsys.readouterr().err
    assert all(command[1] == "_typecheck" for command in calls)
    monkeypatch.setattr(sys, "argv", ["typecheck"])
    config.write_text(
        initial.replace("require_typecheck = true", "require_typecheck = false")
    )
    with pytest.raises(subprocess.CalledProcessError):
        typecheck_module.main()

    assert_check_runs_policy(project, monkeypatch)


def assert_check_runs_policy(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify local validation uses the same policy-aware target as CI."""
    spec = importlib.util.spec_from_file_location(
        "generated_check", project / "scripts/check.py"
    )
    assert spec is not None
    assert spec.loader is not None
    check_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check_module)
    monkeypatch.setattr(check_module, "tracked_changes", lambda: (b"", b""))
    calls: list[list[str]] = []

    def run_successfully(command: list[str], *, check: bool) -> None:
        assert check
        calls.append(command)

    monkeypatch.setattr(check_module.subprocess, "run", run_successfully)
    check_module.main()
    assert ["make", "check-typecheck"] in calls


@pytest.mark.parametrize("level", ["none", "basic", "strict"])
def test_typecheck_level(
    tmp_path: Path, template_source: Path, level: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Apply generated and subsequently edited type-check levels."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "typecheck_level": level,
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    spec = importlib.util.spec_from_file_location(
        "generated_typecheck", project / "scripts/typecheck.py"
    )
    assert spec is not None
    assert spec.loader is not None
    typecheck = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(typecheck)
    config = project / "pyproject.toml"
    assert (
        tomllib.loads(config.read_text())["tool"]["project-checks"]["typecheck_level"]
        == level
    )
    commands: list[list[str]] = []

    def run_successfully(command: list[str], *, check: bool) -> None:
        assert check
        commands.append(command)

    monkeypatch.setattr(typecheck.subprocess, "run", run_successfully)
    for current in ("none", "basic", "strict"):
        config.write_text(
            config.read_text().replace(
                f'typecheck_level = "{level}"', f'typecheck_level = "{current}"'
            )
        )
        level = current
        commands.clear()
        typecheck.main()
        if current == "none":
            assert not commands
        else:
            assert len(commands) == 1
            assert ("--strict" in commands[0][2]) is (current == "strict")
    config.write_text(
        config.read_text().replace(
            'typecheck_level = "strict"', 'typecheck_level = "invalid"'
        )
    )
    with pytest.raises(ValueError, match="Invalid"):
        typecheck.main()


@pytest.mark.parametrize(
    "options",
    [
        {},
        {
            "package_layout": "src",
            "package_type": "namespace",
            "features": [],
            "nox": False,
        },
        {"package_manager": "pixi", "typecheck_source_only": False},
    ],
)
def test_typecheck_source_scope(
    tmp_path: Path,
    template_source: Path,
    monkeypatch: pytest.MonkeyPatch,
    options: dict[str, object],
) -> None:
    """Apply the source-only option at generation and after editing settings."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            **options,
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    spec = importlib.util.spec_from_file_location(
        "generated_typecheck", project / "scripts/typecheck.py"
    )
    assert spec is not None
    assert spec.loader is not None
    typecheck = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(typecheck)
    config = project / "pyproject.toml"
    initial = config.read_text()
    initial_scope = options.get("typecheck_source_only", True)
    assert tomllib.loads(initial)["tool"]["project-checks"][
        "typecheck_source_only"
    ] is (initial_scope)
    commands: list[list[str]] = []

    def run_successfully(command: list[str], *, check: bool) -> None:
        assert check
        commands.append(command)

    monkeypatch.setattr(typecheck.subprocess, "run", run_successfully)
    for source_only in (True, False):
        config.write_text(
            initial.replace(
                f"typecheck_source_only = {str(initial_scope).lower()}",
                f"typecheck_source_only = {str(source_only).lower()}",
            )
        )
        source, _ = package_locations(options)
        expected = [source]
        if not source_only:
            expected += ["tests", "scripts"]
            if options.get("nox", True):
                expected.append("noxfile.py")
        assert typecheck.mypy_paths() == expected
        typecheck.main()
        assert commands[-1][3] == f"TYPECHECK_PATHS={' '.join(expected)}"

    config.write_text(
        initial.replace(
            "typecheck_source_only = true", 'typecheck_source_only = "true"'
        ).replace("typecheck_source_only = false", 'typecheck_source_only = "false"')
    )
    with pytest.raises(ValueError, match="Invalid"):
        typecheck.mypy_paths()


@pytest.mark.parametrize(("strict", "expected"), [(True, "strict"), (False, "basic")])
def test_legacy_typecheck_answers_migrate_on_recopy(
    tmp_path: Path,
    template_source: Path,
    strict: bool,  # noqa: FBT001
    expected: str,
) -> None:
    """Keep the project's own mypy strictness when no level was saved."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={"project_name": "example-package", "project_description": "Example"},
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    answer_file = project / ".copier-answers.yml"
    answers = yaml.safe_load(answer_file.read_text())
    del answers["typecheck_level"]
    answer_file.write_text(yaml.safe_dump(answers))
    if strict:
        config = project / "pyproject.toml"
        config.write_text(
            config.read_text().replace("[tool.mypy]\n", "[tool.mypy]\nstrict = true\n")
        )
    copier.run_recopy(project, defaults=True, overwrite=True, unsafe=True, quiet=True)
    assert yaml.safe_load(answer_file.read_text())["typecheck_level"] == expected
    assert (
        tomllib.loads((project / "pyproject.toml").read_text())["tool"][
            "project-checks"
        ]["typecheck_level"]
        == expected
    )


def test_generated_python_versions(
    generated: tuple[Path, dict[str, object]],
) -> None:
    """Keep the supported versions, default interpreter, and tools in sync."""
    project, data = generated
    with (project / "pyproject.toml").open("rb") as stream:
        config = tomllib.load(stream)
    target_python = data.get("target_python", "py315")
    minimum_python = data.get("minimum_python", "3.13")
    assert isinstance(target_python, str)
    assert isinstance(minimum_python, str)
    python_versions = [f"3.{minor}" for minor in range(int(minimum_python[2:]), 16)]
    assert config["tool"]["ruff"]["target-version"] == target_python
    assert config["tool"]["mypy"]["python_version"] == f"3.{target_python[3:]}"
    assert (project / ".python-version").read_text() == f"3.{target_python[3:]}\n"
    assert config["project"]["requires-python"] == f">={minimum_python}"
    classifiers = config["project"]["classifiers"]
    for minor in range(12, 16):
        classifier = f"Programming Language :: Python :: 3.{minor}"
        assert (classifier in classifiers) is (f"3.{minor}" in python_versions)
    checks_workflow = yaml.safe_load(
        (project / ".github/workflows/checks.yaml").read_text()
    )
    tests_job = checks_workflow["jobs"]["tests"]
    assert tests_job["strategy"]["matrix"]["python_version"] == python_versions
    if "docs" in data.get("features", ["docs"]):  # type: ignore
        coverage_step = next(
            step
            for step in tests_job["steps"]
            if step.get("name") == "Store coverage data for documentation"
        )
        assert (
            coverage_step["if"]
            == f"${{{{ matrix.python_version == '{minimum_python}' }}}}"
        )
    if data.get("nox", True):
        assert (
            f'# requires-python = ">={minimum_python}"'
            in (project / "noxfile.py").read_text()
        )
        assert f"tests-{minimum_python}" in (project / "README.md").read_text()


def test_generated_annotation_policy(
    generated: tuple[Path, dict[str, object]],
) -> None:
    """Postpone annotations before 3.14 and use lazy imports from 3.15."""
    project, data = generated
    minimum_python = data.get("minimum_python", "3.13")
    assert isinstance(minimum_python, str)
    minor = int(minimum_python[2:])
    with (project / "pyproject.toml").open("rb") as stream:
        lint = tomllib.load(stream)["tool"]["ruff"]["lint"]
    banned = lint.get("flake8-tidy-imports", {}).get("banned-api", {})
    postponed = [
        path
        for path in project.rglob("*.py")
        if "from __future__ import annotations" in path.read_text()
    ]
    deferred = minor >= DEFERRED_ANNOTATIONS_MINOR
    assert bool(postponed) is not deferred
    assert lint.get("future-annotations", False) is not deferred
    assert ("TID251" in lint["select"]) is deferred
    assert ("__future__.annotations" in banned) is deferred
    assert ("typing.TYPE_CHECKING" in banned) is (minor >= LAZY_IMPORTS_MINOR)


def test_target_below_minimum_is_rejected(
    tmp_path: Path, template_source: Path
) -> None:
    """The default interpreter must satisfy the project's minimum version."""
    with pytest.raises(ValueError, match="at least the minimum supported version"):
        copier.run_copy(
            str(template_source),
            tmp_path / "project",
            data={
                "project_name": "example-package",
                "project_description": "Example package",
                "minimum_python": "3.15",
                "target_python": "py314",
            },
            defaults=True,
            unsafe=True,
            quiet=True,
        )


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
    if "docs" in data.get("features", ["docs"]):  # type: ignore
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
    guide = (project / "AGENTS.md").read_text()
    assert f"branch into `{branch}`" in guide
    assert "Work on the user's current branch" in guide
    assert "clearly required by the task; do not create a branch by default." in guide
    assert f"merging into `{branch}`" in merge_skill
    for guidance in (guide, merge_skill):
        assert "git merge --squash" in guidance
        assert "their rationale, and validation" in guidance
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
    root = "." if data.get("package_layout") == "flat" else "src"
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
            [] if data.get("package_layout") == "flat" else ["src"]
        )
        assert config["tool"]["mypy"]["explicit_package_bases"]
        assert config["tool"]["mypy"]["mypy_path"] == (
            "." if data.get("package_layout") == "flat" else "src"
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
    if "cli" in data.get("entry_points", []):  # type: ignore
        assert config["project"]["scripts"]["example-package"].startswith(
            f"{import_name}.cli:"
        )
        assert (
            f"from {import_name}.cli import "
            in (project / "tests/test_cli.py").read_text()
        )
    if "docs" in data.get("features", ["docs"]):  # type: ignore
        assert f"::: {import_name}" in (project / "docs/reference/api.md").read_text()


@pytest.mark.parametrize(
    ("distribution_name", "package_manager"),
    [(None, "uv"), ("montec-common", "uv"), ("montec-common", "pixi")],
)
def test_namespace_distribution_name(
    tmp_path: Path,
    template_source: Path,
    monkeypatch: pytest.MonkeyPatch,
    distribution_name: str | None,
    package_manager: str,
) -> None:
    """Keep the saved distribution name distinct from the namespace import."""
    project = tmp_path / "project"
    data: dict[str, object] = {
        "project_name": "common",
        "project_description": "Example package",
        "package_layout": "src",
        "package_type": "namespace",
        "namespace_name": "montec",
        "package_manager": package_manager,
        "features": [],
        "entry_points": ["cli"],
        "cli": "argparse",
    }
    if distribution_name is not None:
        data["distribution_name"] = distribution_name
    expected_name = distribution_name or "common"
    copier.run_copy(
        str(template_source),
        project,
        data=data,
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    copier.run_recopy(project, defaults=True, overwrite=True, unsafe=True, quiet=True)
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    assert answers["distribution_name"] == expected_name
    config = tomllib.loads((project / "pyproject.toml").read_text())
    assert config["project"]["name"] == expected_name
    assert config["project"]["scripts"][expected_name] == "montec.common.cli:main"
    if package_manager == "pixi":
        assert expected_name in config["tool"]["pixi"]["pypi-dependencies"]
    assert (project / "src/montec/common/__init__.py").is_file()
    assert not (project / "src/montec/__init__.py").exists()

    monkeypatch.setenv("SETUPTOOLS_SCM_PRETEND_VERSION", "1.2.3")
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "hatchling", "build", "-t", "wheel"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    (wheel,) = (project / "dist").glob("*.whl")
    installed = project / "installed"
    shutil.unpack_archive(wheel, installed, "zip")
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import importlib.metadata, sys; sys.path.insert(0, sys.argv[1]); "
                "import montec.common; "
                "assert montec.common.__version__ == '1.2.3'; "
                "assert importlib.metadata.metadata(sys.argv[2])['Name'] == sys.argv[2]"
            ),
            str(installed),
            expected_name,
        ],
        cwd=project.parent,
        check=True,
        capture_output=True,
        text=True,
    )


def test_distribution_keys_match_pyproject_fmt(
    tmp_path: Path, template_source: Path
) -> None:
    """Write distribution-name keys bare, as pyproject-fmt does.

    pyproject-fmt rewrites quoted keys that are valid bare TOML keys, which would
    make the generated pre-commit hook change ``pyproject.toml`` and fail checks.
    """
    distribution_name = "example-package"
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "distribution_name": distribution_name,
            "package_manager": "pixi",
            "entry_points": ["cli"],
            "cli": "argparse",
            "features": [],
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    lines = (project / "pyproject.toml").read_text().splitlines()
    assert f'scripts.{distribution_name} = "example_package.cli:main"' in lines
    assert (
        f'pypi-dependencies.{distribution_name} = {{ path = ".", editable = true }}'
        in lines
    )
    config = tomllib.loads("\n".join(lines))
    assert distribution_name in config["project"]["scripts"]
    assert distribution_name in config["tool"]["pixi"]["pypi-dependencies"]


@pytest.mark.parametrize(
    "name",
    [
        "",
        ".bad",
        "bad-",
        "bad/name",
        "bad name",
        '"bad"',
        "montec.common",
        "montec_common",
        "Montec-Common",
        "montec--common",
    ],
)
def test_invalid_distribution_name_is_rejected(
    tmp_path: Path, template_source: Path, name: str
) -> None:
    """Reject distribution names that are invalid or not normalized."""
    with pytest.raises(ValueError, match="Enter a normalized distribution name"):
        copier.run_copy(
            str(template_source),
            tmp_path / "project",
            data={
                "project_name": "common",
                "project_description": "Example package",
                "distribution_name": name,
            },
            defaults=True,
            unsafe=True,
            quiet=True,
        )


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
    monkeypatch.setenv("SETUPTOOLS_SCM_PRETEND_VERSION", "1.2.3")
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


@pytest.mark.parametrize(
    ("annotated_tags_only", "expected"), [(True, "1.0.1"), (False, "2.0.0")]
)
def test_version_ignores_lightweight_tags(
    tmp_path: Path,
    template_source: Path,
    monkeypatch: pytest.MonkeyPatch,
    annotated_tags_only: bool,  # noqa: FBT001
    expected: str,
) -> None:
    """Derive versions from annotated tags only when the option is enabled."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "annotated_tags_only": annotated_tags_only,
            "features": [],
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    git = shutil.which("git")
    assert git is not None
    monkeypatch.delenv("SETUPTOOLS_SCM_PRETEND_VERSION", raising=False)
    identity = [
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.invalid",
        "-c",
        "commit.gpgSign=false",
        "-c",
        "tag.gpgSign=false",
    ]

    def run_git(*args: str) -> None:
        subprocess.run(  # noqa: S603
            [git, "-C", str(project), *identity, *args],
            check=True,
            capture_output=True,
        )

    run_git("init", "-q")
    run_git("add", "-A")
    run_git("commit", "-q", "-m", "Initial commit")
    run_git("tag", "--annotate", "v1.0.0", "--message", "Release 1.0.0")
    run_git("commit", "-q", "--allow-empty", "-m", "Next change")
    run_git("tag", "v2.0.0")
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "hatchling", "build", "-t", "wheel"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    (wheel,) = (project / "dist").glob("*.whl")
    assert Version(wheel.name.split("-")[1]).base_version == expected


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
    del answers["distribution_name"]
    answer_file.write_text(yaml.safe_dump(answers))
    data = {"package_layout": layout} if layout == "src" else None
    copier.run_recopy(
        project, data=data, defaults=True, overwrite=True, unsafe=True, quiet=True
    )
    migrated = yaml.safe_load(answer_file.read_text())
    assert migrated["package_layout"] == layout
    assert migrated["package_type"] == "namespace"
    assert migrated["namespace_name"] == "example_namespace"
    assert migrated["distribution_name"] == "example-package"
    prefix = "src/" if layout == "src" else ""
    assert (
        project / f"{prefix}example_namespace/example_package/__init__.py"
    ).is_file()


@pytest.mark.parametrize("old_nox", [False, True])
def test_legacy_nox_answers_migrate_on_recopy(
    tmp_path: Path,
    template_source: Path,
    old_nox: bool,  # noqa: FBT001
) -> None:
    """Preserve whether legacy task automation enabled Nox."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "nox": old_nox,
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    answer_file = project / ".copier-answers.yml"
    answers = yaml.safe_load(answer_file.read_text())
    del answers["nox"]
    answers["features"] = ["tasks", "docs"] if old_nox else ["docs"]
    answer_file.write_text(yaml.safe_dump(answers))
    copier.run_recopy(project, defaults=True, overwrite=True, unsafe=True, quiet=True)
    assert yaml.safe_load(answer_file.read_text())["nox"] is old_nox
    assert (project / "noxfile.py").exists() is old_nox


@pytest.mark.parametrize("package_manager", ["uv", "pixi", "mamba"])
@pytest.mark.parametrize("nox", [False, True])
@pytest.mark.parametrize("github_actions", [False, True])
def test_nox_and_ci_are_independent(
    tmp_path: Path,
    template_source: Path,
    package_manager: str,
    nox: bool,  # noqa: FBT001
    github_actions: bool,  # noqa: FBT001
) -> None:
    """Nox works without CI, and CI can run tests without Nox."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "minimum_python": "3.15",
            "target_python": "py315",
            "package_manager": package_manager,
            "nox": nox,
            "github_actions": github_actions,
            "features": [],
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    assert (project / "noxfile.py").exists() is nox
    assert ("\nnox:\n" in (project / "Makefile").read_text()) is nox
    config = tomllib.loads((project / "pyproject.toml").read_text())
    assert (
        any(
            dependency.startswith("nox")
            for dependency in config["dependency-groups"]["test"]
        )
        is nox
    )
    workflow = project / ".github/workflows/checks.yaml"
    assert workflow.exists() is github_actions
    if github_actions:
        jobs = yaml.safe_load(workflow.read_text())["jobs"]
        steps = jobs["tests"]["steps"]
        commands = "\n".join(step.get("run", "") for step in steps)
        assert (" -s tests-${{ matrix.python_version }}" in commands) is nox
        if not nox:
            assert "coverage run -m pytest" in commands


@pytest.mark.parametrize(
    "options",
    [
        {},
        {"public_github": False},
        {"public_github": False, "github_actions": True, "pypi_publish": False},
        {"public_github": False, "github_actions": True, "pypi_publish": True},
        {"public_github": False, "pypi_publish": True, "license": "none"},
        {"github_actions": False, "pypi_publish": True, "package_manager": "pixi"},
        {
            "pypi_publish": False,
            "license": "none",
            "package_manager": "pixi",
            "changelog": False,
            "features": [],
        },
        {"package_manager": "pixi", "features": ["docs"]},
        {"package_manager": "mamba", "mamba_environment_name": "example-dev"},
        {
            "package_manager": "mamba",
            "target_python": "py313",
            "public_github": False,
            "pypi_publish": True,
            "license": "none",
            "changelog": False,
            "features": [],
        },
        {"package_manager": "mamba", "features": ["docs"], "nox": False},
    ],
)
def test_optional_integrations(
    tmp_path: Path, template_source: Path, options: dict[str, object]
) -> None:
    """Render independent integration choices without stale generated references."""
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
            **options,
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    public = options.get("public_github", True)
    actions = options.get("github_actions", public)
    publishing = options.get("pypi_publish", public)
    licensed = options.get("license", "MIT") != "none"
    docs = "docs" in options.get("features", ["docs"])  # type: ignore
    pixi = options.get("package_manager", "uv") == "pixi"
    mamba = options.get("package_manager", "uv") == "mamba"
    config = tomllib.loads((project / "pyproject.toml").read_text())
    assert (project / "LICENSE").exists() is licensed
    assert ("license" in config["project"]) is licensed
    assert (project / ".github/workflows/ci.yaml").exists() is actions
    assert (project / ".github/workflows/release.yaml").exists() is (
        actions and publishing
    )
    assert (project / ".github/workflows/pages.yaml").exists() is (
        actions and public and docs
    )
    assert (project / "scripts/publish.py").exists() is publishing
    assert (project / "docs/license.md").exists() is (docs and licensed)
    assert ("pixi" in config["tool"]) is pixi
    assert (project / "environment.yaml").exists() is mamba
    if mamba:
        environment = yaml.safe_load((project / "environment.yaml").read_text())
        assert environment == {
            "name": options.get("mamba_environment_name", "example-package"),
            "channels": ["conda-forge"],
            "dependencies": [
                f"python=3.{str(options.get('target_python', 'py315'))[3:]}",
                "pip>=25.1",
            ],
        }
        for path in [
            project / "Makefile",
            project / ".pre-commit-config.yaml",
            project / "scripts/release.py",
        ]:
            text = path.read_text()
            assert "pixi run" not in text
            assert "uv run" not in text
            assert "mamba.lock" not in text
        if actions and not options.get("nox", True):
            workflow = (project / ".github/workflows/checks.yaml").read_text()
            assert '"python=$PYTHON_VERSION"' in workflow
    assert ("urls" in config["project"]) is public
    if not public:
        for path in (project / "README.md", project / "pyproject.toml"):
            assert "github.com/example/example-package" not in path.read_text()
    for path in project.rglob("*.py"):
        py_compile.compile(str(path), doraise=True)
    for path in (project / ".github/workflows").glob("*.yaml"):
        assert isinstance(yaml.safe_load(path.read_text()), dict)
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
    "name", ["", "base", "BASE", "-bad", "../bad", "bad/name", "bad name", "bad;name"]
)
def test_invalid_mamba_environment_name_is_rejected(
    tmp_path: Path, template_source: Path, name: str
) -> None:
    """Reject names that could target the base environment or escape commands."""
    with pytest.raises(ValueError, match="non-reserved environment name"):
        copier.run_copy(
            str(template_source),
            tmp_path / "project",
            data={
                "project_name": "example-package",
                "project_description": "Example package",
                "package_manager": "mamba",
                "mamba_environment_name": name,
            },
            defaults=True,
            unsafe=True,
            quiet=True,
        )


def test_recopy_disables_public_integrations(
    tmp_path: Path, template_source: Path
) -> None:
    """Saved default projects can explicitly switch off public integrations."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "github_user": "example",
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    copier.run_recopy(
        project,
        data={"public_github": False, "github_actions": False, "pypi_publish": False},
        defaults=True,
        overwrite=True,
        unsafe=True,
        quiet=True,
    )
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    assert answers["public_github"] is False
    assert answers["github_actions"] is False
    assert answers["pypi_publish"] is False
    assert (
        "github.com/example/example-package" not in (project / "README.md").read_text()
    )


def test_recopy_can_switch_to_mamba(tmp_path: Path, template_source: Path) -> None:
    """Keep existing project answers when adding a named Mamba environment."""
    project = tmp_path / "project"
    copier.run_copy(
        str(template_source),
        project,
        data={
            "project_name": "example-package",
            "project_description": "Example package",
            "github_user": "example",
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    copier.run_recopy(
        project,
        data={"package_manager": "mamba", "mamba_environment_name": "example-dev"},
        defaults=True,
        overwrite=True,
        unsafe=True,
        quiet=True,
    )
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    assert answers["project_name"] == "example-package"
    assert answers["package_manager"] == "mamba"
    assert answers["mamba_environment_name"] == "example-dev"
    assert yaml.safe_load((project / "environment.yaml").read_text())["name"] == (
        "example-dev"
    )
