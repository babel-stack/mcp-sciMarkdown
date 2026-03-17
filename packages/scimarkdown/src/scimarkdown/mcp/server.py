"""MCP server for SciMarkdown with two conversion tools."""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from markitdown import MarkItDown
from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
from scimarkdown.config import SciMarkdownConfig


def create_mcp_server() -> FastMCP:
    """Create and return a configured FastMCP server instance."""
    mcp = FastMCP("scimarkdown")

    @mcp.tool()
    def convert_to_markdown(uri: str) -> str:
        """Convert a file or URL to plain Markdown using base MarkItDown.

        Args:
            uri: File path or URL to convert.

        Returns:
            Markdown text of the converted document.
        """
        converter = MarkItDown()
        result = converter.convert(uri)
        return result.markdown or ""

    @mcp.tool()
    def convert_to_scimarkdown(uri: str, config: Optional[dict] = None) -> str:
        """Convert a file or URL to enriched SciMarkdown with LaTeX and image support.

        Args:
            uri: File path or URL to convert.
            config: Optional configuration overrides as a dict.
                    Supports the same keys as scimarkdown.yaml (nested dicts).

        Returns:
            Enriched Markdown text with LaTeX formulas and image references.
        """
        sci_config = SciMarkdownConfig()
        if config:
            sci_config = sci_config.with_overrides(config)

        converter = EnhancedMarkItDown(sci_config=sci_config)
        result = converter.convert(uri)
        return result.markdown or ""

    return mcp
