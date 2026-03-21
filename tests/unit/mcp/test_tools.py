"""Tests for granular MCP tools: detect_math and format_latex."""

import json

import pytest

from scimarkdown.mcp.server import create_mcp_server


def _get_tool_fn(name):
    _server = create_mcp_server()
    for tool in _server._tool_manager._tools.values():
        if tool.name == name:
            return tool.fn
    raise KeyError(f"Tool {name!r} not found")


class TestDetectMath:
    def test_detect_latex_inline(self):
        fn = _get_tool_fn("detect_math")
        text = r"The formula \(x^2 + y^2\) is a circle."
        result = fn(text=text)
        regions = json.loads(result)
        assert isinstance(regions, list)
        assert len(regions) >= 1
        assert regions[0]["source_type"] == "latex"
        assert regions[0]["latex"] == "x^2 + y^2"

    def test_detect_unicode(self):
        fn = _get_tool_fn("detect_math")
        text = "We know that α ∈ ℝ and β ≥ 0."
        result = fn(text=text)
        regions = json.loads(result)
        assert isinstance(regions, list)
        assert any(r["source_type"] == "unicode" for r in regions)

    def test_returns_json_array(self):
        fn = _get_tool_fn("detect_math")
        result = fn(text="no math here")
        regions = json.loads(result)
        assert isinstance(regions, list)

    def test_filter_by_methods(self):
        fn = _get_tool_fn("detect_math")
        text = r"Inline: \(x^2\) and unicode α ∈ ℝ and β ≥ 0."
        result = fn(text=text, methods=["latex"])
        regions = json.loads(result)
        assert all(r["source_type"] == "latex" for r in regions)

    def test_filter_returns_empty_for_no_match(self):
        fn = _get_tool_fn("detect_math")
        text = r"Only latex here: \(x^2\)."
        result = fn(text=text, methods=["mathml"])
        regions = json.loads(result)
        assert regions == []

    def test_region_dict_has_required_keys(self):
        fn = _get_tool_fn("detect_math")
        text = r"\(x^2\)"
        result = fn(text=text)
        regions = json.loads(result)
        assert len(regions) >= 1
        keys = {"position", "original_text", "latex", "source_type", "confidence", "is_inline"}
        assert keys.issubset(regions[0].keys())


class TestFormatLatex:
    def test_format_inline_standard(self):
        fn = _get_tool_fn("format_latex")
        formulas = json.dumps([{"latex": "x^2", "is_inline": True, "original_text": r"\(x^2\)"}])
        result = fn(formulas=formulas)
        items = json.loads(result)
        assert items[0]["formatted"] == "$x^2$"

    def test_format_block_standard(self):
        fn = _get_tool_fn("format_latex")
        formulas = json.dumps([{"latex": "E = mc^2", "is_inline": False, "original_text": r"\[E = mc^2\]"}])
        result = fn(formulas=formulas)
        items = json.loads(result)
        assert items[0]["formatted"] == "$$E = mc^2$$"

    def test_format_github_style(self):
        fn = _get_tool_fn("format_latex")
        formulas = json.dumps([{"latex": "x^2", "is_inline": True, "original_text": r"\(x^2\)"}])
        result = fn(formulas=formulas, style="github")
        items = json.loads(result)
        assert items[0]["formatted"] == "$`x^2`$"

    def test_returns_original_text(self):
        fn = _get_tool_fn("format_latex")
        formulas = json.dumps([{"latex": "x", "is_inline": True, "original_text": r"\(x\)"}])
        result = fn(formulas=formulas)
        items = json.loads(result)
        assert items[0]["original_text"] == r"\(x\)"

    def test_multiple_formulas(self):
        fn = _get_tool_fn("format_latex")
        formulas = json.dumps([
            {"latex": "a", "is_inline": True, "original_text": "a"},
            {"latex": "b", "is_inline": False, "original_text": "b"},
        ])
        result = fn(formulas=formulas)
        items = json.loads(result)
        assert len(items) == 2
        assert items[0]["formatted"] == "$a$"
        assert items[1]["formatted"] == "$$b$$"

    def test_empty_list(self):
        fn = _get_tool_fn("format_latex")
        result = fn(formulas="[]")
        items = json.loads(result)
        assert items == []
