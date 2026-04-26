from __future__ import annotations

from pathlib import Path

from scrapy.http import TextResponse

from wxc_cfzh_crawler.parsing import (
    extract_comment_entries,
    extract_index_entries,
    extract_post_record,
    extract_reply_record,
    extract_root_index_entries,
    post_id_from_url,
)

FIXTURES = Path(__file__).parent / "fixtures"


def response_for(name: str, url: str) -> TextResponse:
    body = (FIXTURES / name).read_bytes()
    return TextResponse(url=url, body=body, encoding="utf-8")


def response_from_html(html: str, url: str) -> TextResponse:
    return TextResponse(url=url, body=html.encode(), encoding="utf-8")


def test_post_id_from_url() -> None:
    assert post_id_from_url("https://bbs.wenxuecity.com/cfzh/74854.html") == "74854"
    assert post_id_from_url("https://bbs.wenxuecity.com/cfzh/74854-print.html") == "74854"
    assert post_id_from_url("https://bbs.wenxuecity.com/cfzh/?page=1") is None


def test_extract_index_entries_preserves_nested_parentage_and_skips_sticky() -> None:
    response = response_for("forum_index.html", "https://bbs.wenxuecity.com/cfzh/")

    entries = extract_index_entries(response)
    by_id = {entry.post_id: entry for entry in entries}

    assert "70000" not in by_id
    assert by_id["100"].root_post_id == "100"
    assert by_id["101"].parent_id == "100"
    assert by_id["101"].root_post_id == "100"
    assert by_id["102"].parent_id == "101"
    assert by_id["102"].depth == 2
    assert by_id["200"].parent_id is None


def test_extract_index_entries_ignores_sticky_duplicates_before_real_rows() -> None:
    response = response_from_html(
        """
        <!doctype html>
        <html>
          <body>
            <div id="postlist">
              <a href="/cfzh/100.html" class="sticky">Root A sticky</a>
              <p style="margin:2px 0 17px 0px; width:705px">
                * <a href="/cfzh/200.html" class="post">Root B</a>
                - M (12 bytes) (3 reads) 04/26/2026 08:00:00
              </p>
              <p style="margin:2px 0 17px 0px; width:705px">
                * <a href="/cfzh/100.html" class="post">Root A</a>
                - M (12 bytes) (4 reads) 04/26/2026 08:01:00 (1)
              </p>
              <p style="margin:2px 0 2px 20px; width:683px">
                * <a href="/cfzh/101.html" class="post">Reply A1</a>
                - F (0 bytes) (1 reads) 04/26/2026 08:02:00
              </p>
            </div>
          </body>
        </html>
        """,
        "https://bbs.wenxuecity.com/cfzh/",
    )

    entries = extract_index_entries(response)
    by_id = {entry.post_id: entry for entry in entries}

    assert [entry.post_id for entry in entries] == ["200", "100", "101"]
    assert by_id["100"].root_post_id == "100"
    assert by_id["101"].parent_id == "100"
    assert by_id["101"].root_post_id == "100"


def test_extract_index_entries_reads_listing_metadata_and_children() -> None:
    response = response_from_html(
        """
        <!doctype html>
        <html>
          <body>
            <div id="postlist">
              <p style="margin:2px 0 17px 0px; width:705px">
                * <a href="/cfzh/100.html" class="post">Root A</a>
                - <a href="//passport.wenxuecity.com/profile.php?cid=author-a">
                  Author A
                </a>
                - M (1,007 bytes) (61 reads) 04/26/2026 08:21:05 (1)
              </p>
              <p style="margin:2px 0 2px 20px; width:683px">
                * <a href="/cfzh/101.html" class="post">Reply A1</a>
                - <a href="//passport.wenxuecity.com/profile.php?cid=author-b">
                  Author B
                </a>
                - F (0 bytes) (2 reads) 04/26/2026 08:22:05
              </p>
            </div>
          </body>
        </html>
        """,
        "https://bbs.wenxuecity.com/cfzh/",
    )

    entries = extract_index_entries(response)
    root, reply = entries

    assert root.byte_count == 1007
    assert root.read_count == 61
    assert root.reply_count == 1
    assert root.has_children is True
    assert root.author == "Author A"
    assert root.author_profile_url == "https://passport.wenxuecity.com/profile.php?cid=author-a"
    assert root.published_at is not None
    assert root.published_at.isoformat() == "2026-04-26T08:21:05"
    assert reply.byte_count == 0
    assert reply.has_children is False


def test_extract_root_index_entries_only_returns_thread_roots() -> None:
    response = response_for("forum_index.html", "https://bbs.wenxuecity.com/cfzh/")

    entries = extract_root_index_entries(response)

    assert [entry.post_id for entry in entries] == ["100", "200"]


def test_extract_comment_entries_are_relative_to_root_post() -> None:
    response = response_for("thread.html", "https://bbs.wenxuecity.com/cfzh/100.html")

    entries = extract_comment_entries(
        response,
        root_post_id="100",
        base_parent_id="100",
        base_depth=0,
    )
    by_id = {entry.post_id: entry for entry in entries}

    assert "999" not in by_id
    assert by_id["101"].parent_id == "100"
    assert by_id["101"].depth == 1
    assert by_id["102"].parent_id == "101"
    assert by_id["102"].depth == 2


def test_extract_comment_entries_reads_postreply_listing_datetime() -> None:
    response = response_from_html(
        """
        <!doctype html>
        <html>
          <body>
            <div id="comment">
              <div id="postlist">
                <p style="margin:2px 0 2px 0px;">
                  * <a href="/cfzh/101.html" class="post">Reply A1</a>
                  -<a href="//passport.wenxuecity.com/profile.php?cid=author-a">
                    Author A
                  </a>- F (0 bytes) () 04/26/2026 postreply 06:57:06
                </p>
              </div>
            </div>
          </body>
        </html>
        """,
        "https://bbs.wenxuecity.com/cfzh/100.html",
    )

    entries = extract_comment_entries(
        response,
        root_post_id="100",
        base_parent_id="100",
        base_depth=0,
    )

    assert entries[0].byte_count == 0
    assert entries[0].published_at is not None
    assert entries[0].published_at.isoformat() == "2026-04-26T06:57:06"


def test_extract_comment_entries_reads_current_nickname_author_links() -> None:
    response = response_from_html(
        """
        <!doctype html>
        <html>
          <body>
            <div id="comment">
              <div id="postlist">
                <p style="margin:2px 0 2px 0px;">
                  * <a href="/cfzh/75059.html" class="post">
                    我去年在这里说存储股领涨, 也问大家为什么领涨.
                  </a>
                  <span class="b"> -
                    <a class="nickname"
                      href="//passport.wenxuecity.com/members/index.php?act=profile&amp;cid=%E4%BD%8E%E6%89%8B">
                      低手只会用均线
                    </a>-
                  </span>
                  <a
                    href="//www.wenxuecity.com/qqh/index.php?act=write&amp;cid=%E4%BD%8E%E6%89%8B">
                  </a>
                  <small>(0 bytes) (<span>5 reads</span>) 04/26/2026&nbsp;postreply 10:05:01</small>
                </p>
              </div>
            </div>
          </body>
        </html>
        """,
        "https://bbs.wenxuecity.com/cfzh/75051.html",
    )

    entries = extract_comment_entries(
        response,
        root_post_id="75051",
        base_parent_id="75051",
        base_depth=0,
    )

    assert entries[0].post_id == "75059"
    assert entries[0].author == "低手只会用均线"
    assert entries[0].author_profile_url == (
        "https://passport.wenxuecity.com/members/index.php?act=profile&cid=%E4%BD%8E%E6%89%8B"
    )
    assert entries[0].byte_count == 0
    assert entries[0].read_count == 5
    assert entries[0].published_at is not None
    assert entries[0].published_at.isoformat() == "2026-04-26T10:05:01"


def test_extract_post_record_reads_metadata_and_body() -> None:
    response = response_for("thread.html", "https://bbs.wenxuecity.com/cfzh/100.html")

    record = extract_post_record(response, meta={})

    assert record["post_id"] == "100"
    assert record["title"] == "Root A"
    assert record["author"] == "Author A"
    assert record["byte_count"] == 570
    assert record["read_count"] == 1436
    assert record["body_text"] == "Root body text"
    assert record["edited_at"].isoformat() == "2026-04-25T10:01:34"


def test_extract_reply_record_uses_postparent() -> None:
    response = response_for("reply.html", "https://bbs.wenxuecity.com/cfzh/102.html")

    record = extract_reply_record(response, meta={"root_post_id": "100", "reply_depth": 2})

    assert record["item_type"] == "reply"
    assert record["reply_id"] == "102"
    assert record["parent_reply_id"] == "101"
    assert record["root_post_id"] == "100"
    assert record["depth"] == 2
    assert record["body_text"] == "Reply body text"
