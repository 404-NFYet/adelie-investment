from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}
ALLOWED_SCHEMES = {"http", "https"}


class UrlValidationError(ValueError):
    pass


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _has_public_resolution(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True

    has_public = False
    for info in infos:
        ip_str = info[4][0]
        ip_obj = ipaddress.ip_address(ip_str)
        if _is_public_ip(ip_obj):
            has_public = True
    return has_public


def validate_public_article_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UrlValidationError("Only http/https URLs are allowed")

    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise UrlValidationError("URL host is missing")

    if host in BLOCKED_HOSTS or host.endswith(".local"):
        raise UrlValidationError("Local/internal hosts are not allowed")

    try:
        ip_obj = ipaddress.ip_address(host)
        if not _is_public_ip(ip_obj):
            raise UrlValidationError("Private/internal IP URLs are not allowed")
    except ValueError:
        if not _has_public_resolution(host):
            raise UrlValidationError("Private/internal resolved host is not allowed")

    return parsed.geturl()
