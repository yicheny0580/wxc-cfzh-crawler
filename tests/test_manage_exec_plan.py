from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from manage_exec_plan import ExecPlanError, complete_plan, create_plan, parse_options  # noqa: E402


def write_template(root: Path) -> None:
    template_path = root / "docs" / "exec-plans" / "template.md"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(
        "# Execution Plan Template\n\n## Goal\n\n## Progress\n",
        encoding="utf-8",
    )


def test_create_plan_uses_template_with_title(tmp_path: Path) -> None:
    write_template(tmp_path)

    path = create_plan(tmp_path, "sample-plan", "Sample Plan")

    assert path == tmp_path / "docs" / "exec-plans" / "active" / "sample-plan.md"
    assert path.read_text(encoding="utf-8").startswith("# Sample Plan\n\n## Goal")


@pytest.mark.parametrize("slug", ["Upper", "two--hyphens", "../escape", "trailing-"])
def test_create_plan_rejects_invalid_slugs(tmp_path: Path, slug: str) -> None:
    write_template(tmp_path)

    with pytest.raises(ExecPlanError, match="slug"):
        create_plan(tmp_path, slug, "Bad Slug")


def test_create_plan_refuses_existing_active_plan(tmp_path: Path) -> None:
    write_template(tmp_path)
    create_plan(tmp_path, "sample-plan", "Sample Plan")

    with pytest.raises(ExecPlanError, match="already exists"):
        create_plan(tmp_path, "sample-plan", "Sample Plan")


def test_create_plan_refuses_existing_completed_plan(tmp_path: Path) -> None:
    write_template(tmp_path)
    completed = tmp_path / "docs" / "exec-plans" / "completed" / "sample-plan.md"
    completed.parent.mkdir(parents=True, exist_ok=True)
    completed.write_text("# Sample Plan\n", encoding="utf-8")

    with pytest.raises(ExecPlanError, match="already exists"):
        create_plan(tmp_path, "sample-plan", "Sample Plan")


def test_complete_plan_moves_active_plan_to_completed(tmp_path: Path) -> None:
    write_template(tmp_path)
    active = create_plan(tmp_path, "sample-plan", "Sample Plan")

    completed = complete_plan(tmp_path, "sample-plan")

    assert completed == tmp_path / "docs" / "exec-plans" / "completed" / "sample-plan.md"
    assert not active.exists()
    assert completed.read_text(encoding="utf-8").startswith("# Sample Plan")


def test_complete_plan_refuses_to_overwrite_completed_plan(tmp_path: Path) -> None:
    write_template(tmp_path)
    create_plan(tmp_path, "sample-plan", "Sample Plan")
    completed = tmp_path / "docs" / "exec-plans" / "completed" / "sample-plan.md"
    completed.parent.mkdir(parents=True, exist_ok=True)
    completed.write_text("# Existing\n", encoding="utf-8")

    with pytest.raises(ExecPlanError, match="already exists"):
        complete_plan(tmp_path, "sample-plan")


def test_complete_plan_requires_active_plan(tmp_path: Path) -> None:
    write_template(tmp_path)

    with pytest.raises(ExecPlanError, match="does not exist"):
        complete_plan(tmp_path, "sample-plan")


def test_parse_options_rejects_unknown_options() -> None:
    with pytest.raises(ExecPlanError, match="Unknown option"):
        parse_options(["slug=sample-plan", "owner=agent"], {"slug"})
