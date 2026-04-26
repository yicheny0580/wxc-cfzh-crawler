from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NoReturn

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ACTIVE_DIR = Path("docs/exec-plans/active")
COMPLETED_DIR = Path("docs/exec-plans/completed")
TEMPLATE_PATH = Path("docs/exec-plans/template.md")
TEMPLATE_HEADING = "# Execution Plan Template"


class ExecPlanError(ValueError):
    pass


def validate_slug(slug: str) -> str:
    if not SLUG_PATTERN.fullmatch(slug):
        raise ExecPlanError(
            "Exec-plan slug must use lowercase letters, numbers, and single hyphens."
        )
    return slug


def validate_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        raise ExecPlanError("Exec-plan title must not be empty.")
    if "\n" in cleaned or "\r" in cleaned:
        raise ExecPlanError("Exec-plan title must be a single line.")
    return cleaned


def plan_path(root: Path, directory: Path, slug: str) -> Path:
    return root / directory / f"{validate_slug(slug)}.md"


def render_plan(root: Path, title: str) -> str:
    template = (root / TEMPLATE_PATH).read_text(encoding="utf-8")
    heading = TEMPLATE_HEADING
    if not template.startswith(heading):
        raise ExecPlanError(f"{TEMPLATE_PATH} must start with {heading!r}.")
    return template.replace(heading, f"# {validate_title(title)}", 1)


def create_plan(root: Path, slug: str, title: str) -> Path:
    active_path = plan_path(root, ACTIVE_DIR, slug)
    completed_path = plan_path(root, COMPLETED_DIR, slug)
    if active_path.exists():
        raise ExecPlanError(f"Active exec-plan already exists: {active_path.relative_to(root)}")
    if completed_path.exists():
        relative_path = completed_path.relative_to(root)
        raise ExecPlanError(f"Completed exec-plan already exists: {relative_path}")

    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(render_plan(root, title), encoding="utf-8")
    return active_path


def complete_plan(root: Path, slug: str) -> Path:
    active_path = plan_path(root, ACTIVE_DIR, slug)
    completed_path = plan_path(root, COMPLETED_DIR, slug)
    if not active_path.is_file():
        raise ExecPlanError(f"Active exec-plan does not exist: {active_path.relative_to(root)}")
    if completed_path.exists():
        relative_path = completed_path.relative_to(root)
        raise ExecPlanError(f"Completed exec-plan already exists: {relative_path}")

    completed_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.rename(completed_path)
    return completed_path


def parse_options(values: list[str], allowed: set[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ExecPlanError(f"Expected key=value option, got: {value}")
        key, option_value = value.split("=", 1)
        if key not in allowed:
            allowed_options = ", ".join(sorted(allowed))
            raise ExecPlanError(f"Unknown option {key!r}. Expected one of: {allowed_options}.")
        if key in parsed:
            raise ExecPlanError(f"Duplicate option: {key}")
        if not option_value:
            raise ExecPlanError(f"Option {key!r} must not be empty.")
        parsed[key] = option_value
    return parsed


def require_option(options: dict[str, str], key: str) -> str:
    try:
        return options[key]
    except KeyError as exc:
        raise ExecPlanError(f"Missing required option: {key}") from exc


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or complete checked-in exec-plans.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Create an active exec-plan.")
    new_parser.add_argument("options", nargs="*", help="Use slug=... title=... options.")

    complete_parser = subparsers.add_parser(
        "complete",
        help="Move an active exec-plan to completed.",
    )
    complete_parser.add_argument("options", nargs="*", help="Use slug=... option.")

    return parser


def fail(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    root = repository_root()
    try:
        if args.command == "new":
            options = parse_options(args.options, {"slug", "title"})
            path = create_plan(
                root,
                require_option(options, "slug"),
                require_option(options, "title"),
            )
            print(f"Created {path.relative_to(root)}")
            return 0
        if args.command == "complete":
            options = parse_options(args.options, {"slug"})
            path = complete_plan(root, require_option(options, "slug"))
            print(f"Moved to {path.relative_to(root)}")
            return 0
    except ExecPlanError as exc:
        fail(str(exc))

    fail(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
