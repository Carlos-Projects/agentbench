"""HTTP utility functions for benchmark target communication."""

from __future__ import annotations

from typing import Any

import httpx

from agentbench.logger import logger
from agentbench.utils.security import sanitize_url_for_log

DEFAULT_TIMEOUT = 30.0
MAX_REDIRECTS = 5


async def send_prompt(
    url: str,
    prompt: str,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    api_format: str = "generic",
) -> httpx.Response:
    """Send a prompt to an agent endpoint and return the response.

    Supports multiple API formats:
    - ``generic``: POST with ``{"prompt": ..., "messages": [...]}``
    - ``openai``: OpenAI chat completions format
    - ``anthropic``: Anthropic Claude API format
    - ``mcp``: MCP protocol format (use :func:`send_mcp_request` instead)

    Args:
        url: Target agent URL.
        prompt: Input prompt or payload.
        headers: Optional HTTP headers.
        timeout: Request timeout in seconds.
        api_format: API format (``generic``, ``openai``, or ``anthropic``).

    Returns:
        HTTP response from the target.

    Raises:
        httpx.RequestError: If the request fails.
    """
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, max_redirects=MAX_REDIRECTS) as client:
        headers = headers or {}

        if api_format == "openai":
            json_data = {
                "messages": [{"role": "user", "content": prompt}],
                "model": "default",
                "max_tokens": 1024,
            }
            headers.setdefault("Content-Type", "application/json")
        elif api_format == "anthropic":
            json_data = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            }
            headers.setdefault("Content-Type", "application/json")
            headers.setdefault("anthropic-version", "2023-06-01")
        else:
            json_data = {"prompt": prompt, "messages": [{"role": "user", "content": prompt}]}

        safe_url = sanitize_url_for_log(url)
        logger.debug("Sending prompt to %s (format=%s, prompt_len=%d)", safe_url, api_format, len(prompt))
        resp = await client.post(url, json=json_data, headers=headers)
        logger.debug("Response: status=%d, length=%d", resp.status_code, len(resp.text))
        return resp


async def send_mcp_request(
    url: str,
    method: str = "tools/call",
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Send an MCP protocol request to an agent.

    Args:
        url: MCP server URL.
        method: MCP method to call.
        params: Method parameters.
        headers: Optional HTTP headers.
        timeout: Request timeout in seconds.

    Returns:
        MCP response as a dictionary.
    """
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, max_redirects=MAX_REDIRECTS) as client:
        headers = headers or {"Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        safe_url = sanitize_url_for_log(url)
        logger.debug("Sending MCP request to %s (method=%s)", safe_url, method)
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        result = resp.json()
        logger.debug("MCP response received (method=%s)", method)
        return result


async def mcp_initialize(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Perform MCP protocol initialization handshake.

    Sends ``initialize`` request and ``notifications/initialized``
    notification as required by the MCP specification.

    Args:
        url: MCP server URL.
        headers: Optional HTTP headers.
        timeout: Request timeout in seconds.

    Returns:
        Server capabilities from the initialize response.

    Raises:
        httpx.RequestError: If initialization fails.
    """
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, max_redirects=MAX_REDIRECTS) as client:
        base_headers = headers or {"Content-Type": "application/json"}

        init_payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "agentbench", "version": "0.1.0"},
            },
        }
        safe_url = sanitize_url_for_log(url)
        logger.debug("MCP initialize handshake to %s", safe_url)
        init_resp = await client.post(url, json=init_payload, headers=base_headers)
        init_resp.raise_for_status()
        result = init_resp.json()

        notified_payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        await client.post(url, json=notified_payload, headers=base_headers)

        return result.get("result", {})


async def check_endpoint_health(url: str, timeout: float = 10.0) -> bool:
    """Check if an endpoint is reachable.

    Args:
        url: Target URL to check.
        timeout: Request timeout in seconds.

    Returns:
        True if the endpoint responds with a 2xx status.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            logger.debug("Health check %s: status=%d", url, resp.status_code)
            return resp.is_success
    except httpx.RequestError as exc:
        logger.warning("Health check %s failed: %s", url, exc)
        return False
