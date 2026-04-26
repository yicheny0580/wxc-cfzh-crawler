from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOCS = [
    ROOT / "AGENTS.md",
    ROOT / "README.md",
    ROOT / "docs" / "index.md",
    ROOT / "docs" / "architecture.md",
    ROOT / "docs" / "operations.md",
    ROOT / "docs" / "quality.md",
    ROOT / "docs" / "exec-plans" / "index.md",
    ROOT / "docs" / "exec-plans" / "template.md",
    ROOT / "docs" / "design-docs" / "index.md",
    ROOT / "docs" / "design-docs" / "agent-workflow.md",
    ROOT / "docs" / "design-docs" / "project-invariants.md",
    ROOT / "docs" / "design-docs" / "harness.md",
    ROOT / "docs" / "design-docs" / "code-unit-design.md",
    ROOT / "docs" / "product-specs" / "index.md",
    ROOT / "docs" / "product-specs" / "product-principles.md",
    ROOT / "docs" / "product-specs" / "crawler-inspector-workflows.md",
    ROOT / "docs" / "references" / "index.md",
    ROOT / "docs" / "references" / "wenxuecity-cfzh.md",
    ROOT / "crawler" / "README.md",
    ROOT / "crawler" / "docs" / "index.md",
    ROOT / "inspector" / "docs" / "index.md",
]

SOURCE_OF_TRUTH_LINKS = [
    "design-docs/index.md",
    "design-docs/agent-workflow.md",
    "product-specs/index.md",
    "references/index.md",
    "exec-plans/index.md",
]

EXEC_PLAN_DIRS = [
    ROOT / "docs" / "exec-plans" / "active",
    ROOT / "docs" / "exec-plans" / "completed",
]

RETIRED_COMMAND = "w" + "xc"
RETIRED_WXC_DOC_PHRASES = [
    f"uv run {RETIRED_COMMAND}",
    f"{RETIRED_COMMAND} --help",
    f"{RETIRED_COMMAND} inspect",
    f"{RETIRED_COMMAND} crawl",
    f"{RETIRED_COMMAND} export",
]

CENTRALIZED_AGENT_PHRASES = [
    "humans and codex",
    "future agent",
    "future agents",
    "agent legibility",
]

AGENT_WORKFLOW_DOC = ROOT / "docs" / "design-docs" / "agent-workflow.md"
EXEC_PLANS_DOC = ROOT / "docs" / "exec-plans" / "index.md"
HARNESS_DOC = ROOT / "docs" / "design-docs" / "harness.md"
OPERATIONS_DOC = ROOT / "docs" / "operations.md"
JUSTFILE = ROOT / "justfile"
AGENTS_DOC = ROOT / "AGENTS.md"
README_DOC = ROOT / "README.md"
DOCS_INDEX_DOC = ROOT / "docs" / "index.md"
DESIGN_DOCS_INDEX_DOC = ROOT / "docs" / "design-docs" / "index.md"
PRODUCT_SPECS_INDEX_DOC = ROOT / "docs" / "product-specs" / "index.md"
REFERENCES_INDEX_DOC = ROOT / "docs" / "references" / "index.md"
PROJECT_INVARIANTS_DOC = ROOT / "docs" / "design-docs" / "project-invariants.md"
THIN_MAP_DOCS = [
    AGENTS_DOC,
    README_DOC,
    DOCS_INDEX_DOC,
    DESIGN_DOCS_INDEX_DOC,
    PRODUCT_SPECS_INDEX_DOC,
    REFERENCES_INDEX_DOC,
]
MAX_THIN_MAP_LINES = 120


def normalized_doc_text(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8").lower())


def test_doc_map_files_exist() -> None:
    missing = [path for path in DOCS if not path.is_file()]

    assert missing == []


def test_exec_plan_lifecycle_dirs_exist() -> None:
    missing = [path for path in EXEC_PLAN_DIRS if not path.is_dir()]

    assert missing == []


def test_root_index_links_source_of_truth_sections() -> None:
    content = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    missing_links = [target for target in SOURCE_OF_TRUTH_LINKS if target not in content]

    assert missing_links == []


def test_thin_index_layer_map_pattern() -> None:
    for path in THIN_MAP_DOCS:
        content = normalized_doc_text(path)
        line_count = len(path.read_text(encoding="utf-8").splitlines())

        assert "map" in content or "index" in content
        assert line_count <= MAX_THIN_MAP_LINES

    assert "table-of-contents map" in normalized_doc_text(AGENTS_DOC)
    assert "thin index" in normalized_doc_text(DOCS_INDEX_DOC)
    assert "source of truth" in normalized_doc_text(DOCS_INDEX_DOC)


def test_agent_workflow_requires_stable_doc_promotion() -> None:
    content = AGENT_WORKFLOW_DOC.read_text(encoding="utf-8").lower()

    assert "promote" in content
    assert "stable doc" in content


def test_agent_workflow_requires_review_before_commit() -> None:
    content = AGENT_WORKFLOW_DOC.read_text(encoding="utf-8").lower()

    assert "approval to implement is not approval to commit" in content
    assert "stop for human review" in content
    assert "explicit good-to-commit signal" in content


def test_agent_workflow_requires_active_exec_plan_for_substantial_work() -> None:
    content = normalized_doc_text(AGENT_WORKFLOW_DOC)

    assert "docs/exec-plans/active/" in content
    assert "substantial" in content
    assert "exec-plan gate decision" in content
    assert "first tracked implementation artifact" in content
    assert "after implementation approval" in content
    assert "before stable docs" in content
    assert "just exec-plan-new" in content
    assert "just exec-plan-complete" in content
    assert "before continuing implementation" in content


def test_exec_plans_are_mandatory_execution_records() -> None:
    workflow = normalized_doc_text(AGENT_WORKFLOW_DOC)
    exec_plans = normalized_doc_text(EXEC_PLANS_DOC)
    template = normalized_doc_text(ROOT / "docs" / "exec-plans" / "template.md")

    assert "mandatory execution and resume state" in workflow
    assert "execution records" in exec_plans
    assert "not optional for qualifying work" in exec_plans
    assert "not the long-term home" in exec_plans
    assert "durable design choices" in exec_plans
    assert "execution records" in template
    assert "durable design choices" in template


def test_project_invariants_require_focused_docs() -> None:
    content = normalized_doc_text(PROJECT_INVARIANTS_DOC)

    assert "thin maps" in content
    assert "small focused docs" in content
    assert "split docs by domain, responsibility, or layer" in content
    assert "long-term ideas, design choices" in content


def test_agent_workflow_documents_canonical_order() -> None:
    content = normalized_doc_text(AGENT_WORKFLOW_DOC)

    ordered_phrases = [
        "plan conversation",
        "user implementation approval",
        "first tracked implementation",
        "stable docs, code, or tests",
        "run validation",
        "stop for human review",
        "explicit good-to-commit signal",
        "complete the exec-plan",
    ]

    positions = [content.index(phrase) for phrase in ordered_phrases]
    assert positions == sorted(positions)


def test_harness_documents_exec_plan_helpers() -> None:
    contents = [
        JUSTFILE.read_text(encoding="utf-8"),
        HARNESS_DOC.read_text(encoding="utf-8"),
        EXEC_PLANS_DOC.read_text(encoding="utf-8"),
        OPERATIONS_DOC.read_text(encoding="utf-8"),
    ]

    for content in contents:
        assert "exec-plan-new" in content
        assert "exec-plan-complete" in content


def test_related_agent_workflow_notes_reference_canonical_lifecycle() -> None:
    docs = [
        AGENTS_DOC,
        README_DOC,
        EXEC_PLANS_DOC,
        HARNESS_DOC,
        OPERATIONS_DOC,
        PROJECT_INVARIANTS_DOC,
    ]

    for path in docs:
        content = normalized_doc_text(path)
        assert "agent-workflow.md" in content

    lifecycle_docs = [
        AGENTS_DOC,
        EXEC_PLANS_DOC,
        HARNESS_DOC,
        OPERATIONS_DOC,
        PROJECT_INVARIANTS_DOC,
    ]
    for path in lifecycle_docs:
        content = normalized_doc_text(path)
        assert "first tracked implementation artifact" in content
        assert "before stable docs" in content


def test_doc_map_relative_links_point_to_files() -> None:
    bad_links: list[str] = []
    for path in DOCS:
        content = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            relative_target = target.split("#", 1)[0]
            if not relative_target:
                continue
            resolved = (path.parent / relative_target).resolve()
            if not resolved.exists():
                bad_links.append(f"{path.relative_to(ROOT)} -> {target}")

    assert bad_links == []


def test_docs_do_not_advertise_retired_wxc_cli() -> None:
    findings: list[str] = []
    for path in DOCS:
        content = path.read_text(encoding="utf-8")
        for phrase in RETIRED_WXC_DOC_PHRASES:
            if phrase in content:
                findings.append(f"{path.relative_to(ROOT)} contains {phrase!r}")

    assert findings == []


def test_agent_notes_stay_centralized() -> None:
    findings: list[str] = []
    for path in DOCS:
        if path == AGENT_WORKFLOW_DOC:
            continue
        content = path.read_text(encoding="utf-8")
        lower_content = content.lower()
        for phrase in CENTRALIZED_AGENT_PHRASES:
            if phrase in lower_content:
                findings.append(f"{path.relative_to(ROOT)} contains {phrase!r}")

    assert findings == []
