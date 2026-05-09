from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from http.client import HTTPResponse
from typing import Protocol

WXC_BASE_URL = "https://bbs.wenxuecity.com"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 8
USER_AGENT = "wxc-cfzh-inspector/0.1"


class ImageProxyInputError(ValueError):
    pass


class ImageProxyFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProxiedImage:
    content: bytes
    media_type: str


class ImageOpener(Protocol):
    def open(
        self,
        fullurl: urllib.request.Request,
        data: bytes | None = None,
        timeout: float | object = socket._GLOBAL_DEFAULT_TIMEOUT,
    ) -> HTTPResponse: ...


class _ImageSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        for name, value in attrs:
            if name.lower() == "src" and value:
                self.sources.append(value)


def normalize_image_url(value: str) -> str | None:
    raw_value = value.strip()
    if not raw_value:
        return None

    try:
        parsed = urllib.parse.urlsplit(urllib.parse.urljoin(WXC_BASE_URL, raw_value))
    except ValueError:
        return None

    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None

    return urllib.parse.urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            parsed.query,
            "",
        )
    )


def post_image_urls(body_html: str | None) -> set[str]:
    if not body_html:
        return set()

    parser = _ImageSrcParser()
    parser.feed(body_html)
    return {
        normalized
        for source in parser.sources
        if (normalized := normalize_image_url(source)) is not None
    }


def require_post_image_url(body_html: str | None, requested_src: str) -> str:
    requested_url = normalize_image_url(requested_src)
    if requested_url is None:
        raise ImageProxyInputError("Image URL must be an HTTP or HTTPS URL.")

    if requested_url not in post_image_urls(body_html):
        raise ImageProxyInputError("Image URL is not part of the requested post.")

    return requested_url


def _blocked_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return True
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_fetch_target(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ImageProxyInputError("Image URL must be an HTTP or HTTPS URL.")

    host = parsed.hostname
    if not host:
        raise ImageProxyInputError("Image URL must include a host.")
    if host.lower() in {"localhost", "localhost.localdomain"}:
        raise ImageProxyInputError("Image host is not allowed.")

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ImageProxyFetchError("Image host could not be resolved.") from exc

    if not addresses:
        raise ImageProxyFetchError("Image host could not be resolved.")

    for address in addresses:
        if _blocked_address(address[4][0]):
            raise ImageProxyInputError(
                "Image host resolves to a private or local network address."
            )


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: HTTPResponse,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> urllib.request.Request | None:
        normalized_url = normalize_image_url(newurl)
        if normalized_url is None:
            raise ImageProxyInputError("Redirected image URL must be HTTP or HTTPS.")
        validate_fetch_target(normalized_url)
        return super().redirect_request(req, fp, code, msg, headers, normalized_url)


def _read_limited(response: HTTPResponse) -> bytes:
    content = response.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise ImageProxyFetchError("Image is too large.")
    return content


def fetch_image_bytes(url: str, opener: ImageOpener | None = None) -> ProxiedImage:
    validate_fetch_target(url)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "image/*,*/*;q=0.8",
            "User-Agent": USER_AGENT,
        },
    )
    image_opener = opener or urllib.request.build_opener(_SafeRedirectHandler())

    try:
        with image_opener.open(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            media_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            media_type = media_type.strip()
            if not media_type.startswith("image/") or media_type == "image/svg+xml":
                raise ImageProxyFetchError("Response is not a supported image.")
            return ProxiedImage(content=_read_limited(response), media_type=media_type)
    except ImageProxyInputError:
        raise
    except ImageProxyFetchError:
        raise
    except urllib.error.HTTPError as exc:
        raise ImageProxyFetchError(f"Image fetch failed with HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise ImageProxyFetchError("Image fetch failed.") from exc
    except TimeoutError as exc:
        raise ImageProxyFetchError("Image fetch timed out.") from exc
