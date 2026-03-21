"""Tests for link_references and build_figure_index MCP tools."""

import json

import pytest

from scimarkdown.mcp.server import create_mcp_server


def _get_tool_fn(name):
    _server = create_mcp_server()
    for tool in _server._tool_manager._tools.values():
        if tool.name == name:
            return tool.fn
    raise KeyError(f"Tool {name!r} not found")


def _make_images_json(n: int = 1) -> str:
    images = [
        {
            "position": i,
            "file_path": f"/tmp/doc_img{i:05d}.png",
            "original_format": "png",
            "width": 100,
            "height": 80,
            "caption": None,
            "reference_label": None,
            "ordinal": None,
        }
        for i in range(n)
    ]
    return json.dumps(images)


class TestLinkReferences:
    def test_links_figure_reference(self):
        fn = _get_tool_fn("link_references")
        text = "See Figure 1 for details."
        images = _make_images_json(2)
        result = fn(text=text, images=images)
        refs = json.loads(result)
        assert refs[0]["reference_label"] is not None
        assert refs[0]["ordinal"] == 1

    def test_unmatched_image_stays_none(self):
        fn = _get_tool_fn("link_references")
        text = "No figures mentioned."
        images = _make_images_json(1)
        result = fn(text=text, images=images)
        refs = json.loads(result)
        assert refs[0]["reference_label"] is None

    def test_returns_json_array(self):
        fn = _get_tool_fn("link_references")
        result = fn(text="Figure 1.", images=_make_images_json(1))
        refs = json.loads(result)
        assert isinstance(refs, list)

    def test_custom_patterns(self):
        fn = _get_tool_fn("link_references")
        text = "Panel 1 shows the result."
        images = _make_images_json(2)
        result = fn(text=text, images=images, patterns=[r"Panel\s*(\d+)"])
        refs = json.loads(result)
        assert refs[0]["reference_label"] is not None

    def test_empty_images_list(self):
        fn = _get_tool_fn("link_references")
        result = fn(text="Figure 1.", images="[]")
        refs = json.loads(result)
        assert refs == []

    def test_result_keys(self):
        fn = _get_tool_fn("link_references")
        result = fn(text="Figure 1.", images=_make_images_json(1))
        refs = json.loads(result)
        keys = {"position", "file_path", "original_format", "width", "height",
                "caption", "reference_label", "ordinal"}
        assert keys.issubset(refs[0].keys())


class TestBuildFigureIndex:
    def test_returns_markdown_string(self):
        fn = _get_tool_fn("build_figure_index")
        images_with_ref = json.dumps([{
            "position": 0,
            "file_path": "/tmp/img.png",
            "original_format": "png",
            "width": 100,
            "height": 80,
            "caption": "A test figure",
            "reference_label": "Figure 1",
            "ordinal": 1,
        }])
        result = fn(images=images_with_ref)
        assert isinstance(result, str)
        assert "## Figure Index" in result
        assert "Figure 1" in result
        assert "img.png" in result

    def test_empty_list_returns_empty_string(self):
        fn = _get_tool_fn("build_figure_index")
        result = fn(images="[]")
        assert result == ""

    def test_no_reference_label(self):
        fn = _get_tool_fn("build_figure_index")
        images = _make_images_json(1)
        result = fn(images=images)
        assert "(no reference)" in result

    def test_caption_in_output(self):
        fn = _get_tool_fn("build_figure_index")
        images = json.dumps([{
            "position": 0,
            "file_path": "/tmp/img.png",
            "original_format": "png",
            "width": 100,
            "height": 80,
            "caption": "Spectral analysis",
            "reference_label": None,
            "ordinal": None,
        }])
        result = fn(images=images)
        assert "Spectral analysis" in result

    def test_not_json(self):
        fn = _get_tool_fn("build_figure_index")
        images = _make_images_json(3)
        result = fn(images=images)
        # Should be markdown, not a JSON array
        assert not result.startswith("[")
        assert "## Figure Index" in result
