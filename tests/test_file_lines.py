from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from check_file_lines import FileLineConfig, find_violations, main  # noqa: E402


def write_lines(path: Path, line_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x = 1\n" * line_count, encoding="utf-8")


def test_production_file_over_limit_fails(tmp_path: Path) -> None:
    write_lines(tmp_path / "src" / "too_large.py", 401)
    config = FileLineConfig(max_lines=400, include=("src/*.py",))

    violations = find_violations(tmp_path, config, tracked_only=False)

    assert len(violations) == 1
    assert violations[0].path == "src/too_large.py"
    assert violations[0].lines == 401


def test_file_at_limit_passes(tmp_path: Path) -> None:
    write_lines(tmp_path / "src" / "at_limit.py", 400)
    config = FileLineConfig(max_lines=400, include=("src/*.py",))

    assert find_violations(tmp_path, config, tracked_only=False) == []


def test_ignored_paths_do_not_fail(tmp_path: Path) -> None:
    write_lines(tmp_path / "src" / "ok.py", 12)
    write_lines(tmp_path / "tests" / "large_test.py", 401)
    write_lines(tmp_path / "docs" / "large.md", 401)
    config = FileLineConfig(
        max_lines=400,
        include=("**/*.py", "**/*.md"),
        exclude=("tests/**", "docs/**"),
    )

    assert find_violations(tmp_path, config, tracked_only=False) == []


def test_main_output_includes_remediation(tmp_path: Path, capsys) -> None:
    write_lines(tmp_path / "src" / "too_large.py", 401)
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.wxc.file_lines]
max_lines = 400
include = ["src/*.py"]
exclude = []
""".lstrip(),
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "--all-files"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "src/too_large.py: 401 lines (max 400)" in output
    assert "Split by responsibility instead of raising the cap." in output
