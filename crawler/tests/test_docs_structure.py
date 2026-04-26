from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = [
    ROOT / "AGENTS.md",
    ROOT / "README.md",
    ROOT / "docs" / "index.md",
    ROOT / "docs" / "architecture.md",
    ROOT / "docs" / "operations.md",
    ROOT / "docs" / "quality.md",
    ROOT / "docs" / "exec-plans" / "index.md",
    ROOT / "crawler" / "README.md",
    ROOT / "crawler" / "docs" / "index.md",
    ROOT / "inspector" / "docs" / "index.md",
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
