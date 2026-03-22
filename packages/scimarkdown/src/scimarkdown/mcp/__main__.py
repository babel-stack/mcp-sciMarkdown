"""CLI entry point for running the SciMarkdown MCP server."""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m scimarkdown.mcp",
        description="Run the SciMarkdown MCP server.",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        default=False,
        help="Serve over HTTP (SSE transport) instead of stdio.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind when using --http (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind when using --http (default: 8000).",
    )
    args = parser.parse_args()

    from scimarkdown.mcp.server import create_mcp_server

    mcp = create_mcp_server()

    if args.http:
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    main()
