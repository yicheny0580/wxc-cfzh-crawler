from __future__ import annotations

import os
import sys
from typing import TextIO

from wxc_cfzh_crawler._db_progress import CrawlProgress, format_live_crawl_progress


class CrawlProgressReporter:
    def __init__(self, *, mode: str | None = None, stream: TextIO | None = None) -> None:
        self.mode = normalize_progress_mode(mode)
        self.stream = stream or sys.stderr
        self.enabled = self.mode == "live" and self.stream.isatty()
        self.has_line = False
        self.scheduled: int | None = None
        self.max_requests: int | None = None

    def update_progress(
        self,
        progress: CrawlProgress,
        *,
        scheduled: int | None = None,
        max_requests: int | None = None,
    ) -> None:
        if scheduled is not None:
            self.scheduled = scheduled
            self.max_requests = max_requests
        self.update(
            format_live_crawl_progress(
                progress,
                scheduled=self.scheduled,
                max_requests=self.max_requests,
            )
        )

    def update(self, text: str) -> None:
        if not self.enabled:
            return
        self.stream.write(f"\r\x1b[K{text}")
        self.stream.flush()
        self.has_line = True

    def clear(self) -> None:
        if not self.enabled or not self.has_line:
            return
        self.stream.write("\r\x1b[K")
        self.stream.flush()
        self.has_line = False

    def close(self) -> None:
        if not self.enabled or not self.has_line:
            return
        self.stream.write("\n")
        self.stream.flush()
        self.has_line = False


_reporter: CrawlProgressReporter | None = None


def normalize_progress_mode(mode: str | None) -> str:
    value = (mode or os.getenv("WXC_PROGRESS") or "live").strip().lower()
    if value in {"0", "false", "no", "off"}:
        return "off"
    return "live"


def configure_crawl_progress_reporter(
    *,
    mode: str | None = None,
    stream: TextIO | None = None,
) -> CrawlProgressReporter:
    global _reporter
    _reporter = CrawlProgressReporter(mode=mode, stream=stream)
    return _reporter


def get_crawl_progress_reporter(*, mode: str | None = None) -> CrawlProgressReporter:
    global _reporter
    if _reporter is None:
        _reporter = CrawlProgressReporter(mode=mode)
    return _reporter


def reset_crawl_progress_reporter() -> None:
    global _reporter
    _reporter = None
