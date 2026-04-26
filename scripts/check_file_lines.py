from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class FileLineConfig:
    max_lines: int
    include: tuple[str, ...]
    exclude: tuple[str, ...] = ()


@dataclass(frozen=True)
class FileLineViolation:
    path: str
    lines: int
    max_lines: int


def load_config(config_path: Path) -> FileLineConfig:
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    raw_config = payload.get("tool", {}).get("wxc", {}).get("file_lines")
    if not isinstance(raw_config, dict):
        raise ValueError(f"{config_path} is missing [tool.wxc.file_lines]")

    max_lines = raw_config.get("max_lines")
    include = raw_config.get("include")
    exclude = raw_config.get("exclude", [])
    if not isinstance(max_lines, int) or max_lines < 1:
        raise ValueError("[tool.wxc.file_lines].max_lines must be a positive integer")
    if not isinstance(include, list) or not all(isinstance(item, str) for item in include):
        raise ValueError("[tool.wxc.file_lines].include must be a list of strings")
    if not isinstance(exclude, list) or not all(isinstance(item, str) for item in exclude):
        raise ValueError("[tool.wxc.file_lines].exclude must be a list of strings")

    return FileLineConfig(
        max_lines=max_lines,
        include=tuple(include),
        exclude=tuple(exclude),
    )


def git_visible_files(root: Path) -> set[str] | None:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return {item.decode("utf-8") for item in result.stdout.split(b"\0") if item}


def path_matches(path: str, patterns: Iterable[str]) -> bool:
    posix_path = PurePosixPath(path)
    return any(posix_path.match(pattern) for pattern in patterns)


def candidate_files(
    root: Path,
    config: FileLineConfig,
    *,
    tracked_only: bool = True,
) -> list[Path]:
    tracked = git_visible_files(root) if tracked_only else None
    candidates: set[str] = set()

    for pattern in config.include:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if tracked is not None and relative not in tracked:
                continue
            if path_matches(relative, config.exclude):
                continue
            candidates.add(relative)

    return [root / relative for relative in sorted(candidates)]


def count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def find_violations(
    root: Path,
    config: FileLineConfig,
    *,
    tracked_only: bool = True,
) -> list[FileLineViolation]:
    violations = []
    for path in candidate_files(root, config, tracked_only=tracked_only):
        line_count = count_lines(path)
        if line_count > config.max_lines:
            violations.append(
                FileLineViolation(
                    path=path.relative_to(root).as_posix(),
                    lines=line_count,
                    max_lines=config.max_lines,
                )
            )
    return violations


def print_violations(violations: Sequence[FileLineViolation]) -> None:
    if not violations:
        print("File length lint passed.")
        return

    print(
        f"File length lint failed: {len(violations)} production file(s) exceed "
        f"{violations[0].max_lines} lines."
    )
    for violation in violations:
        print(f"- {violation.path}: {violation.lines} lines (max {violation.max_lines})")
        print("  Split by responsibility instead of raising the cap.")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enforce production source file length limits.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the parent of scripts/.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to pyproject.toml. Defaults to ROOT/pyproject.toml.",
    )
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Check matching files even when they are not tracked by git.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = args.root.resolve()
    config_path = (args.config or root / "pyproject.toml").resolve()
    config = load_config(config_path)
    violations = find_violations(root, config, tracked_only=not args.all_files)
    print_violations(violations)
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
