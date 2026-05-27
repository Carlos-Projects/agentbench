"""Tests for HTTP utilities."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agentbench.utils.http import check_endpoint_health, send_mcp_request, send_prompt


@pytest.mark.asyncio
async def test_send_prompt_success() -> None:
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.text = "Test response"
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        resp = await send_prompt("http://test:8080", "hello")
        assert resp.text == "Test response"


@pytest.mark.asyncio
async def test_send_prompt_custom_headers() -> None:
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.text = "ok"
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        await send_prompt("http://test:8080", "hello", headers={"Authorization": "Bearer test"})
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer test"


@pytest.mark.asyncio
async def test_send_mcp_request() -> None:
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = {"jsonrpc": "2.0", "result": "ok"}
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        result = await send_mcp_request("http://test:8080", method="tools/list")
        assert result["result"] == "ok"


@pytest.mark.asyncio
async def test_send_mcp_request_with_params() -> None:
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = {"jsonrpc": "2.0", "result": "ok"}
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        await send_mcp_request("http://test:8080", params={"name": "test"})
        call_kwargs = mock_post.call_args[1]
        assert "params" in call_kwargs["json"]


@pytest.mark.asyncio
async def test_check_endpoint_health_success() -> None:
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.is_success = True
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        assert await check_endpoint_health("http://test:8080") is True


@pytest.mark.asyncio
async def test_check_endpoint_health_failure() -> None:
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.is_success = False
    mock_response.status_code = 500

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        assert await check_endpoint_health("http://test:8080") is False
