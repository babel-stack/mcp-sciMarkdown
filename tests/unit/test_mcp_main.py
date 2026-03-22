"""Tests for scimarkdown.mcp.__main__ CLI entry point."""

import sys
from unittest.mock import patch, MagicMock

# create_mcp_server is imported *inside* main(), so we patch at its origin.
_SERVER_PATH = "scimarkdown.mcp.server.create_mcp_server"


class TestMcpMain:
    def test_mcp_main_stdio_transport(self):
        """Default (no --http flag) uses stdio transport."""
        mock_mcp = MagicMock()

        with patch(_SERVER_PATH, return_value=mock_mcp):
            with patch("sys.argv", ["scimarkdown-mcp"]):
                from scimarkdown.mcp.__main__ import main
                main()

        mock_mcp.run.assert_called_once_with(transport="stdio")

    def test_mcp_main_http_transport(self):
        """--http flag uses sse transport with default host/port."""
        mock_mcp = MagicMock()

        with patch(_SERVER_PATH, return_value=mock_mcp):
            with patch("sys.argv", ["scimarkdown-mcp", "--http"]):
                from scimarkdown.mcp.__main__ import main
                main()

        mock_mcp.run.assert_called_once_with(
            transport="sse",
            host="127.0.0.1",
            port=8000,
        )

    def test_mcp_main_http_custom_port(self):
        """--http with --port uses the custom port."""
        mock_mcp = MagicMock()

        with patch(_SERVER_PATH, return_value=mock_mcp):
            with patch("sys.argv", ["scimarkdown-mcp", "--http", "--port", "4000"]):
                from scimarkdown.mcp.__main__ import main
                main()

        mock_mcp.run.assert_called_once_with(
            transport="sse",
            host="127.0.0.1",
            port=4000,
        )

    def test_mcp_main_http_custom_host(self):
        """--http with --host uses the custom host."""
        mock_mcp = MagicMock()

        with patch(_SERVER_PATH, return_value=mock_mcp):
            with patch("sys.argv", ["scimarkdown-mcp", "--http", "--host", "0.0.0.0"]):
                from scimarkdown.mcp.__main__ import main
                main()

        mock_mcp.run.assert_called_once_with(
            transport="sse",
            host="0.0.0.0",
            port=8000,
        )

    def test_mcp_main_creates_server(self):
        """create_mcp_server is called exactly once."""
        mock_mcp = MagicMock()

        with patch(_SERVER_PATH, return_value=mock_mcp) as mock_create:
            with patch("sys.argv", ["scimarkdown-mcp"]):
                from scimarkdown.mcp.__main__ import main
                main()

        mock_create.assert_called_once()
