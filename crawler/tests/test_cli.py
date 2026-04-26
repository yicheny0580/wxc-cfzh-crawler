from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from wxc_cfzh_crawler import cli
from wxc_cfzh_crawler.cli import (
    build_parser,
    ensure_frontend_ready,
    frontend_manifest_hash,
    positive_int,
    write_frontend_sync_marker,
)


def create_frontend(repo_root: Path) -> Path:
    frontend_dir = repo_root / "inspector" / "frontend"
    frontend_dir.mkdir(parents=True)
    (frontend_dir / "package.json").write_text('{"scripts":{"build":"vite build"}}\n')
    (frontend_dir / "package-lock.json").write_text('{"lockfileVersion":3}\n')
    return frontend_dir


def test_cli_root_help_lists_primary_commands(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "crawl" in output
    assert "export" in output
    assert "inspect" in output


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("crawl", "--pages"),
        ("export", "--shape"),
        ("inspect", "--skip-ui-build"),
    ],
)
def test_cli_subcommand_help_is_discoverable(
    command: str,
    expected: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args([command, "--help"])

    assert exc_info.value.code == 0
    assert expected in capsys.readouterr().out


def test_crawl_args_use_standard_options() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "crawl",
            "--pages",
            "2",
            "--max-requests",
            "5",
            "--database-url",
            "sqlite:////tmp/crawler.sqlite3",
            "--log-level",
            "DEBUG",
        ]
    )

    assert args.command == "crawl"
    assert args.pages == 2
    assert args.max_requests == 5
    assert args.database_url == "sqlite:////tmp/crawler.sqlite3"
    assert args.log_level == "DEBUG"


def test_positive_int_rejects_zero() -> None:
    with pytest.raises(Exception, match="at least 1"):
        positive_int("0")


def test_inspect_refresh_help_is_discoverable(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["inspect", "--help"])

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "--skip-ui-build" in output
    assert "refresh or build inspector/frontend" in output


def test_frontend_ready_builds_even_when_dist_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frontend_dir = create_frontend(tmp_path)
    (frontend_dir / "dist").mkdir()
    (frontend_dir / "dist" / "index.html").write_text("<!doctype html>\n")
    write_frontend_sync_marker(frontend_dir, frontend_manifest_hash(frontend_dir))
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> None:
        assert check is True
        commands.append(command)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    ensure_frontend_ready(tmp_path, skip_build=False)

    assert commands == [["npm", "--prefix", str(frontend_dir), "run", "build"]]


def test_frontend_ready_runs_ci_when_marker_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frontend_dir = create_frontend(tmp_path)
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> None:
        assert check is True
        commands.append(command)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    ensure_frontend_ready(tmp_path, skip_build=False)

    assert commands == [
        ["npm", "--prefix", str(frontend_dir), "ci"],
        ["npm", "--prefix", str(frontend_dir), "run", "build"],
    ]
    assert cli.frontend_sync_marker_path(frontend_dir).exists()


def test_frontend_ready_runs_ci_when_marker_is_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frontend_dir = create_frontend(tmp_path)
    write_frontend_sync_marker(frontend_dir, "stale")
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> None:
        assert check is True
        commands.append(command)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    ensure_frontend_ready(tmp_path, skip_build=False)

    assert commands == [
        ["npm", "--prefix", str(frontend_dir), "ci"],
        ["npm", "--prefix", str(frontend_dir), "run", "build"],
    ]


def test_frontend_ready_skips_ci_when_marker_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frontend_dir = create_frontend(tmp_path)
    write_frontend_sync_marker(frontend_dir, frontend_manifest_hash(frontend_dir))
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> None:
        assert check is True
        commands.append(command)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    ensure_frontend_ready(tmp_path, skip_build=False)

    assert commands == [["npm", "--prefix", str(frontend_dir), "run", "build"]]


def test_frontend_ready_skip_build_skips_sync_and_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> None:
        commands.append(command)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    ensure_frontend_ready(tmp_path, skip_build=True)

    assert commands == []


def test_frontend_ready_reports_missing_npm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_frontend(tmp_path)

    def fake_run(command: list[str], *, check: bool) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    with pytest.raises(SystemExit, match="npm was not found"):
        ensure_frontend_ready(tmp_path, skip_build=False)


def test_frontend_ready_reports_failed_npm_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_frontend(tmp_path)

    def fake_run(command: list[str], *, check: bool) -> None:
        raise subprocess.CalledProcessError(returncode=1, cmd=command)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    with pytest.raises(SystemExit, match="dependency refresh failed"):
        ensure_frontend_ready(tmp_path, skip_build=False)


def test_frontend_ready_reports_failed_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frontend_dir = create_frontend(tmp_path)
    write_frontend_sync_marker(frontend_dir, frontend_manifest_hash(frontend_dir))

    def fake_run(command: list[str], *, check: bool) -> None:
        raise subprocess.CalledProcessError(returncode=1, cmd=command)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    with pytest.raises(SystemExit, match="UI build failed"):
        ensure_frontend_ready(tmp_path, skip_build=False)
