#!/usr/bin/env python3
"""Common utilities for search scripts."""

import socket
import ssl
import time
import urllib.error


def join_api_url(base: str, path: str, *, api_version: str = "v1") -> str:
    """Join API base URL with path, ensuring /v1 is present exactly once.

    Normalizes inputs: trailing slashes on base are stripped, and path is
    prefixed with a leading slash if missing. Passing ``api_version=""``
    skips the version segment entirely.

    Examples:
        https://host        + /responses  → https://host/v1/responses
        https://host/       + /responses  → https://host/v1/responses
        https://host/v1     + /responses  → https://host/v1/responses
        https://host/v1/    + /responses  → https://host/v1/responses
        https://host        + responses   → https://host/v1/responses
        https://host        + /x, api_version="" → https://host/x
    """
    base = base.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    if not api_version:
        return f"{base}{path}"
    if base.endswith(f"/{api_version}"):
        return f"{base}{path}"
    return f"{base}/{api_version}{path}"


def bearer_headers(token: str, *, extra: dict | None = None) -> dict:
    """Build Authorization: Bearer headers with optional extras."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def with_retry(
    fn, *, attempts: int = 3, base_delay: float = 1.0, retryable: tuple = ()
):
    """Exponential backoff retry wrapper for urllib calls.

    Default retryable: ``URLError``, ``SSLError``, ``socket.timeout``. Note
    that ``urllib.error.HTTPError`` subclasses ``URLError`` but is always
    excluded from the default set — HTTP 4xx/5xx responses are generally
    not transient (404/401/403 retries are wasted; 5xx deserves its own
    policy). Callers who really want HTTP-error retries must pass an
    explicit ``retryable`` tuple containing ``HTTPError``.

    Non-retryable exceptions propagate immediately, as do ``BaseException``
    subclasses like ``KeyboardInterrupt`` / ``SystemExit``.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    use_default = not retryable
    if not retryable:
        retryable = (urllib.error.URLError, ssl.SSLError, socket.timeout)
    for attempt in range(attempts):
        try:
            return fn()
        except urllib.error.HTTPError:
            # HTTPError is a subclass of URLError; skip retry under default
            # policy. If the caller opted in by listing HTTPError explicitly,
            # fall through to the retry branch below.
            if use_default:
                raise
            if attempt == attempts - 1:
                raise
            time.sleep(base_delay * (2**attempt))
        except retryable:
            if attempt == attempts - 1:
                raise
            time.sleep(base_delay * (2**attempt))
    raise RuntimeError("with_retry: unreachable")
