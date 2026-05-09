from __future__ import annotations

from wxc_cfzh_crawler._db_progress import CrawlProgress, format_live_crawl_progress
from wxc_cfzh_crawler.progress import CrawlProgressReporter


class StreamBuffer:
    def __init__(self, *, tty: bool) -> None:
        self.tty = tty
        self.writes: list[str] = []
        self.flushes = 0

    def isatty(self) -> bool:
        return self.tty

    def write(self, value: str) -> int:
        self.writes.append(value)
        return len(value)

    def flush(self) -> None:
        self.flushes += 1

    @property
    def text(self) -> str:
        return "".join(self.writes)


def progress_snapshot() -> CrawlProgress:
    return CrawlProgress(
        saved_posts=1,
        saved_replies=2,
        frontier={
            "post": {
                "pending": 3,
                "in_progress": 1,
                "done": 1,
                "failed": 0,
                "suppressed": 1,
            },
            "reply": {
                "pending": 5,
                "in_progress": 2,
                "done": 2,
                "failed": 1,
                "suppressed": 0,
            },
        },
    )


def test_format_live_crawl_progress_is_compact() -> None:
    text = format_live_crawl_progress(progress_snapshot(), scheduled=4, max_requests=10)

    assert text == (
        "CFZH saved posts=1 replies=2 | pending posts=3 replies=5 | "
        "active=3 | failed=1 | suppressed=1 | scheduled=4/10"
    )


def test_live_reporter_rewrites_one_terminal_line() -> None:
    stream = StreamBuffer(tty=True)
    reporter = CrawlProgressReporter(mode="live", stream=stream)

    reporter.update_progress(progress_snapshot(), scheduled=4, max_requests=10)
    reporter.update_progress(progress_snapshot())
    reporter.clear()
    reporter.close()

    assert stream.writes[0].startswith("\r\x1b[KCFZH saved posts=1 replies=2")
    assert "scheduled=4/10" in stream.writes[1]
    assert stream.writes[2] == "\r\x1b[K"
    assert stream.writes[-1] != "\n"


def test_non_tty_reporter_suppresses_live_updates() -> None:
    stream = StreamBuffer(tty=False)
    reporter = CrawlProgressReporter(mode="live", stream=stream)

    reporter.update_progress(progress_snapshot(), scheduled=4, max_requests=10)
    reporter.clear()
    reporter.close()

    assert stream.writes == []


def test_live_reporter_close_adds_newline_after_visible_line() -> None:
    stream = StreamBuffer(tty=True)
    reporter = CrawlProgressReporter(mode="live", stream=stream)

    reporter.update_progress(progress_snapshot(), scheduled=4, max_requests=None)
    reporter.close()

    assert stream.writes[-1] == "\n"
