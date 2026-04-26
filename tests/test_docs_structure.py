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
    ROOT / "docs" / "design-docs" / "index.md",
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
    "product-specs/index.md",
    "references/index.md",
]

RETIRED_COMMAND = "w" + "xc"
RETIRED_WXC_DOC_PHRASES = [
    f"uv run {RETIRED_COMMAND}",
    f"{RETIRED_COMMAND} --help",
    f"{RETIRED_COMMAND} inspect",
    f"{RETIRED_COMMAND} crawl",
    f"{RETIRED_COMMAND} export",
]


def test_doc_map_files_exist() -> None:
    missing = [path for path in DOCS if not path.is_file()]

    assert missing == []


def test_root_index_links_source_of_truth_sections() -> None:
    content = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    missing_links = [target for target in SOURCE_OF_TRUTH_LINKS if target not in content]

    assert missing_links == []


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
