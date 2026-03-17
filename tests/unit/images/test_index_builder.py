"""Tests for IndexBuilder — markdown table generation."""

import pytest
from scimarkdown.images import IndexBuilder
from scimarkdown.models import ImageRef


def _make_image(
    position: int = 0,
    file_path: str = "/tmp/doc_img00001.png",
    reference_label: str | None = None,
    caption: str | None = None,
    ordinal: int | None = None,
) -> ImageRef:
    return ImageRef(
        position=position,
        file_path=file_path,
        original_format="png",
        reference_label=reference_label,
        caption=caption,
        ordinal=ordinal,
    )


class TestBuildIndexTable:
    def test_returns_string(self):
        builder = IndexBuilder()
        images = [_make_image(reference_label="Figure 1")]
        result = builder.build(images)
        assert isinstance(result, str)

    def test_header_present(self):
        builder = IndexBuilder()
        images = [_make_image(reference_label="Figure 1")]
        result = builder.build(images)
        assert "## Figure Index" in result

    def test_column_headers(self):
        builder = IndexBuilder()
        images = [_make_image(reference_label="Figure 1")]
        result = builder.build(images)
        assert "# |" in result or "| #" in result
        assert "Figure" in result
        assert "Description" in result
        assert "File" in result

    def test_two_images_with_references(self):
        builder = IndexBuilder()
        images = [
            _make_image(position=0, file_path="/out/doc_img00001.png",
                        reference_label="Figure 1", caption="Introduction chart",
                        ordinal=1),
            _make_image(position=1, file_path="/out/doc_img00002.png",
                        reference_label="Figure 2", caption="Results graph",
                        ordinal=2),
        ]
        result = builder.build(images)
        assert "Figure 1" in result
        assert "Figure 2" in result
        assert "Introduction chart" in result
        assert "Results graph" in result
        assert "doc_img00001.png" in result
        assert "doc_img00002.png" in result

    def test_row_numbering(self):
        builder = IndexBuilder()
        images = [
            _make_image(reference_label="Figure 1"),
            _make_image(reference_label="Figure 2"),
        ]
        result = builder.build(images)
        lines = result.splitlines()
        # Find data rows (after header and separator)
        data_rows = [l for l in lines if l.startswith("| ") and "---" not in l and "#" not in l]
        assert data_rows[0].startswith("| 1 |")
        assert data_rows[1].startswith("| 2 |")


class TestUnmatchedImageInIndex:
    def test_no_reference_shows_placeholder(self):
        """Image without reference_label shows '(no reference)'."""
        builder = IndexBuilder()
        images = [_make_image(file_path="/out/doc_img00001.png")]
        result = builder.build(images)
        assert "(no reference)" in result

    def test_mixed_matched_and_unmatched(self):
        builder = IndexBuilder()
        images = [
            _make_image(file_path="/out/doc_img00001.png", reference_label="Figure 1"),
            _make_image(file_path="/out/doc_img00002.png"),  # no label
        ]
        result = builder.build(images)
        assert "Figure 1" in result
        assert "(no reference)" in result

    def test_no_caption_leaves_description_blank(self):
        builder = IndexBuilder()
        images = [_make_image(reference_label="Figure 1", caption=None)]
        result = builder.build(images)
        lines = [l for l in result.splitlines() if "Figure 1" in l]
        assert len(lines) == 1
        # Description column should be empty (two consecutive pipes with nothing between)
        assert "||" in lines[0].replace(" ", "")


class TestEmptyImages:
    def test_empty_list_returns_empty_string(self):
        builder = IndexBuilder()
        result = builder.build([])
        assert result == ""

    def test_empty_does_not_include_header(self):
        builder = IndexBuilder()
        result = builder.build([])
        assert "## Figure Index" not in result
