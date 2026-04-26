from __future__ import annotations

import os

from wxc_cfzh_crawler.paths import default_data_dir, default_database_url

BOT_NAME = "wxc_cfzh_crawler"

SPIDER_MODULES = ["wxc_cfzh_crawler.spiders"]
NEWSPIDER_MODULE = "wxc_cfzh_crawler.spiders"

# Admin-authorized crawler: ignore robots, but keep conservative crawl pressure.
ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = True

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 3.0

RETRY_ENABLED = True
RETRY_TIMES = 3
DOWNLOAD_TIMEOUT = 30

USER_AGENT = os.getenv(
    "WXC_CRAWLER_USER_AGENT",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
)
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

TELNETCONSOLE_ENABLED = False

WXC_DATA_DIR = str(default_data_dir())
DATABASE_URL = default_database_url()

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
LOG_LEVEL = os.getenv("WXC_LOG_LEVEL", "INFO")
WXC_PROGRESS = os.getenv("WXC_PROGRESS", "live")
