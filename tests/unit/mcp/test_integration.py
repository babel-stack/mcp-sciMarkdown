"""Integration tests: tool listing, count, and pipeline chaining."""

import base64
import io
import json
from pathlib import Path

import pytest

from scimarkdown.mcp.server import create_mcp_server


def _get_server():
    return create_mcp_server()


def _get_tool_fn(server, name):
    for tool in server._tool_manager._tools.values():
        if tool.name == name:
            return tool.fn
    raise KeyError(f"Tool {name!r} not found")


def _make_minimal_png() -> bytes:
    """Return a minimal valid 2x2 white PNG as bytes."""
    from PIL import Image

    buf = io.BytesIO()
    img = Image.new("RGB", (2, 2), color=(200, 200, 200))
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestToolRegistration:
    def test_all_eight_tools_registered(self):
        server = _get_server()
        registered = set(server._tool_manager._tools.keys())
        expected = {
            "convert_to_markdown",
            "convert_to_scimarkdown",
            "detect_math",
            "format_latex",
            "extract_images",
            "link_references",
            "build_figure_index",
            "ocr_formula",
        }
        assert expected == registered

    def test_tool_count_is_eight(self):
        server = _get_server()
        assert len(server._tool_manager._tools) == 8

    def test_tool_names_list(self):
        server = _get_server()
        names = list(server._tool_manager._tools.keys())
        assert len(names) == 8
        assert "detect_math" in names
        assert "format_latex" in names
        assert "extract_images" in names
        assert "link_references" in names
        assert "build_figure_index" in names
        assert "ocr_formula" in names


class TestMathPipeline:
    """Pipeline: detect_math → format_latex."""

    def test_detect_then_format_inline(self):
        server = _get_server()
        detect_fn = _get_tool_fn(server, "detect_math")
        format_fn = _get_tool_fn(server, "format_latex")

        text = r"The energy equation is \(E = mc^2\)."
        detected_json = detect_fn(text=text)
        regions = json.loads(detected_json)
        assert len(regions) >= 1

        formatted_json = format_fn(formulas=detected_json)
        items = json.loads(formatted_json)
        assert len(items) >= 1
        assert items[0]["formatted"] == "$E = mc^2$"

    def test_detect_then_format_block(self):
        server = _get_server()
        detect_fn = _get_tool_fn(server, "detect_math")
        format_fn = _get_tool_fn(server, "format_latex")

        text = r"The display formula: \[x^2 + y^2 = r^2\]"
        detected_json = detect_fn(text=text)
        regions = json.loads(detected_json)
        block_regions = [r for r in regions if not r["is_inline"]]
        assert len(block_regions) >= 1

        formatted_json = format_fn(formulas=json.dumps(block_regions))
        items = json.loads(formatted_json)
        assert items[0]["formatted"] == "$$x^2 + y^2 = r^2$$"

    def test_detect_filter_then_format(self):
        server = _get_server()
        detect_fn = _get_tool_fn(server, "detect_math")
        format_fn = _get_tool_fn(server, "format_latex")

        text = r"Inline: \(a + b\) and unicode: α ∈ ℝ and β ≥ 0."
        detected_json = detect_fn(text=text, methods=["latex"])
        regions = json.loads(detected_json)
        assert all(r["source_type"] == "latex" for r in regions)

        formatted_json = format_fn(formulas=detected_json)
        items = json.loads(formatted_json)
        assert all("$" in item["formatted"] for item in items)


class TestImagePipeline:
    """Pipeline: extract_images → link_references → build_figure_index."""

    def _make_html_file(self, tmp_path) -> Path:
        png_bytes = _make_minimal_png()
        b64 = base64.b64encode(png_bytes).decode("ascii")
        html = f'<html><body><img src="data:image/png;base64,{b64}"/></body></html>'
        html_file = tmp_path / "doc.html"
        html_file.write_text(html)
        return html_file

    def test_extract_then_link_then_index(self, tmp_path):
        server = _get_server()
        extract_fn = _get_tool_fn(server, "extract_images")
        link_fn = _get_tool_fn(server, "link_references")
        index_fn = _get_tool_fn(server, "build_figure_index")

        html_file = self._make_html_file(tmp_path)
        out_dir = str(tmp_path / "images")

        # Step 1: extract images
        extracted_json = extract_fn(uri=str(html_file), output_dir=out_dir)
        refs = json.loads(extracted_json)
        assert len(refs) == 1

        # Step 2: link references
        text = "As shown in Figure 1, the result is clear."
        linked_json = link_fn(text=text, images=extracted_json)
        linked = json.loads(linked_json)
        assert linked[0]["reference_label"] is not None
        assert linked[0]["ordinal"] == 1

        # Step 3: build index
        index_md = index_fn(images=linked_json)
        assert "## Figure Index" in index_md
        assert "Figure 1" in index_md
        assert "doc_img" in index_md

    def test_extract_no_refs_then_index(self, tmp_path):
        server = _get_server()
        extract_fn = _get_tool_fn(server, "extract_images")
        link_fn = _get_tool_fn(server, "link_references")
        index_fn = _get_tool_fn(server, "build_figure_index")

        html_file = self._make_html_file(tmp_path)
        out_dir = str(tmp_path / "images2")

        extracted_json = extract_fn(uri=str(html_file), output_dir=out_dir)

        # No references in text
        linked_json = link_fn(text="Nothing here.", images=extracted_json)
        linked = json.loads(linked_json)
        assert linked[0]["reference_label"] is None

        index_md = index_fn(images=linked_json)
        assert "(no reference)" in index_md
