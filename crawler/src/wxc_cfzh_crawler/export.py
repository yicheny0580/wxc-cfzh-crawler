from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from wxc_cfzh_crawler.db import connect, fetch_replies, fetch_root_posts
from wxc_cfzh_crawler.paths import default_database_url


def build_reply_trees(replies: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    nodes = [{**reply, "replies": []} for reply in replies]
    by_id = {str(node["reply_id"]): node for node in nodes}
    by_root: dict[str, list[dict[str, Any]]] = {}

    for node in nodes:
        root_post_id = str(node["root_post_id"])
        by_root.setdefault(root_post_id, [])
        parent_id = node.get("parent_reply_id")
        parent = by_id.get(str(parent_id)) if parent_id else None
        if parent is None or str(parent["root_post_id"]) != root_post_id:
            by_root[root_post_id].append(node)
        else:
            parent["replies"].append(node)

    return by_root


def build_posts_with_replies(
    posts: list[dict[str, Any]],
    replies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    replies_by_root = build_reply_trees(replies)
    return [
        {
            **post,
            "replies": replies_by_root.get(str(post["post_id"]), []),
        }
        for post in posts
    ]


def build_flat_records(
    posts: list[dict[str, Any]],
    replies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        *(
            {
                **post,
                "record_type": "post",
                "root_post_id": post["post_id"],
                "parent_reply_id": None,
                "depth": 0,
            }
            for post in posts
        ),
        *({"record_type": "reply", **reply} for reply in replies),
    ]


def write_records(records: list[dict[str, Any]], *, output_path: Path, output_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "json":
        output_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return

    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, default=str))
            handle.write("\n")


def export_records(
    *,
    database_url: str,
    output_path: Path,
    output_format: str,
    shape: str,
) -> None:
    try:
        conn = connect(database_url)
    except sqlite3.Error as exc:
        raise SystemExit(f"Could not open database: {exc}") from exc

    with conn:
        posts = fetch_root_posts(conn)
        replies = fetch_replies(conn)

    if shape == "flat":
        records = build_flat_records(posts, replies)
    else:
        records = build_posts_with_replies(posts, replies)
    write_records(records, output_path=output_path, output_format=output_format)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export crawled Wenxuecity cfzh posts.")
    parser.add_argument(
        "--database-url",
        default=default_database_url(),
        help="SQLite database URL. Defaults to DATABASE_URL or root data/crawler.sqlite3.",
    )
    parser.add_argument("--out", required=True, help="Output file path.")
    parser.add_argument("--format", choices=["json", "jsonl"], default="jsonl")
    parser.add_argument("--shape", choices=["reddit", "flat"], default="reddit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    export_records(
        database_url=args.database_url,
        output_path=Path(args.out),
        output_format=args.format,
        shape=args.shape,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
