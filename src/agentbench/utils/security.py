"""Security utilities for safe file operations, URL validation, and input sanitization."""

from __future__ import annotations

import re
import socket
from ipaddress import ip_address, ip_network
from pathlib import Path
from urllib.parse import urlparse

from agentbench.logger import logger

PRIVATE_NETWORKS = [
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("127.0.0.0/8"),
    ip_network("169.254.0.0/16"),
    ip_network("::1/128"),
    ip_network("fc00::/7"),
    ip_network("fe80::/10"),
]

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def safe_resolve_path(path: str | Path, base: str | Path | None = None) -> Path:
    """Resolve a path, warning if it stays outside an allowed base directory.

    Allows system temp directories (/tmp, /var/tmp) and the base directory.
    Other paths outside the base emit a warning but are not blocked, since
    CLI tools legitimately write to arbitrary output paths.

    Args:
        path: The path to resolve.
        base: Optional base directory. If None, uses CWD.

    Returns:
        Resolved absolute Path.
    """
    resolved = Path(path).resolve()
    base_path = Path(base).resolve() if base else Path.cwd().resolve()

    # Allow paths within base directory OR system temp directories
    try:
        resolved.relative_to(base_path)
    except ValueError:
        resolved_str = str(resolved)
        if not resolved_str.startswith("/tmp") and not resolved_str.startswith("/var/tmp") and not resolved_str.startswith("/var/folders"):
            logger.debug("Output path %s is outside base %s", resolved, base_path)

    return resolved


def validate_file_size(path: str | Path) -> bool:
    """Validate that a file does not exceed the maximum allowed size.

    Args:
        path: Path to the file.

    Returns:
        True if file size is within limits.

    Raises:
        ValueError: If file exceeds MAX_FILE_SIZE.
    """
    size = Path(path).stat().st_size
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File {path} is {size} bytes, exceeds limit of {MAX_FILE_SIZE}")
    return True


def sanitize_url_for_log(url: str) -> str:
    """Remove sensitive query parameters from a URL for safe logging.

    Args:
        url: The URL to sanitize.

    Returns:
        URL with query parameters and credentials stripped.
    """
    try:
        parsed = urlparse(url)
        sanitized = f"{parsed.scheme}://{parsed.hostname or ''}"
        if parsed.port:
            sanitized += f":{parsed.port}"
        sanitized += parsed.path or "/"
        if parsed.query:
            sanitized += "?<redacted>"
        return sanitized
    except Exception:
        return "<invalid-url>"


def validate_webhook_url(url: str) -> bool:
    """Validate a webhook URL is safe to send requests to.

    Blocks:
    - Private IP ranges (RFC 1918, loopback, link-local)
    - URLs without a valid hostname

    Args:
        url: The webhook URL to validate.

    Returns:
        True if the URL is safe.

    Raises:
        ValueError: If the URL points to a private or loopback address.
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError("Webhook URL must start with http:// or https://")

    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    # Resolve hostname to IP
    try:
        ips = socket.getaddrinfo(hostname, None)
        for family, _type, _proto, _canon, sockaddr in ips:
            addr = ip_address(sockaddr[0])
            for network in PRIVATE_NETWORKS:
                if addr in network:
                    raise ValueError(f"Webhook URL resolves to private address {addr}")
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")

    return True


def sanitize_exception_message(exc: Exception, max_length: int = 200) -> str:
    """Sanitize an exception message to remove sensitive information.

    Strips file paths, IP addresses, and stack traces.

    Args:
        exc: The exception to sanitize.
        max_length: Maximum length of the returned message.

    Returns:
        Sanitized exception message.
    """
    msg = str(exc)[:max_length]

    # Strip file paths (e.g., /Users/foo/bar, C:\\Users\\foo)
    msg = re.sub(r"[/\\][A-Za-z0-9_\-\.]+([/\\][A-Za-z0-9_\-\.]+)+", "<path>", msg)

    # Strip IP addresses
    msg = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<ip>", msg)

    return msg[:max_length]


def validate_header_value(value: str) -> str:
    """Validate and sanitize an HTTP header value.

    Rejects headers containing CRLF or null bytes to prevent HTTP
    response splitting / header injection.

    Args:
        value: The header value to validate.

    Returns:
        The sanitized header value.

    Raises:
        ValueError: If the header contains CR, LF, or null bytes.
    """
    if any(c in value for c in ("\r", "\n", "\0")):
        raise ValueError(f"Header value contains invalid control characters: {value[:20]!r}")
    return value.strip()
