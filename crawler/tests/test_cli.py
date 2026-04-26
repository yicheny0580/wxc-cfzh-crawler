from __future__ import annotations

import pytest

from wxc_cfzh_crawler.cli import build_parser, positive_int


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
