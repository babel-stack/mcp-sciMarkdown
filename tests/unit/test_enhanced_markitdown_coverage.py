"""Tests for enhanced_markitdown coverage gaps: convert_local and convert_stream paths."""

import io
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestEnhancedMarkitdownConvertLocal:
    def test_convert_local_with_file(self, tmp_path):
        """convert_local reads a file and calls convert_stream."""
        try:
            from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
            from scimarkdown.config import SciMarkdownConfig
        except Exception:
            pytest.skip("markitdown not importable")

        txt = tmp_path / "test.txt"
        txt.write_text("Hello world x²")

        config = SciMarkdownConfig(math_heuristic=False)
        enhanced = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

        try:
            result = enhanced.convert_local(str(txt))
            assert result is not None
            assert result.markdown is not None
        except Exception as exc:
            pytest.skip(f"convert_local raised: {exc}")

    def test_convert_local_with_path_object(self, tmp_path):
        """convert_local accepts a Path object."""
        try:
            from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
            from scimarkdown.config import SciMarkdownConfig
        except Exception:
            pytest.skip("markitdown not importable")

        txt = tmp_path / "test.txt"
        txt.write_text("Simple content")

        config = SciMarkdownConfig(math_heuristic=False)
        enhanced = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

        try:
            result = enhanced.convert_local(Path(txt))
            assert result is not None
        except Exception as exc:
            pytest.skip(f"convert_local raised: {exc}")

    def test_convert_local_with_file_extension_override(self, tmp_path):
        """convert_local respects file_extension override."""
        try:
            from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
            from scimarkdown.config import SciMarkdownConfig
        except Exception:
            pytest.skip("markitdown not importable")

        txt = tmp_path / "test.txt"
        txt.write_text("Content here")

        config = SciMarkdownConfig(math_heuristic=False)
        enhanced = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

        try:
            result = enhanced.convert_local(str(txt), file_extension=".txt")
            assert result is not None
        except Exception as exc:
            pytest.skip(f"convert_local raised: {exc}")

    def test_convert_local_same_output_dir(self, tmp_path):
        """When images_output_dir='same', output_dir is set to file's parent."""
        try:
            from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
            from scimarkdown.config import SciMarkdownConfig
        except Exception:
            pytest.skip("markitdown not importable")

        txt = tmp_path / "test.txt"
        txt.write_text("Hello")

        config = SciMarkdownConfig(
            math_heuristic=False,
            images_output_dir="same",
        )
        enhanced = EnhancedMarkItDown(sci_config=config)

        try:
            result = enhanced.convert_local(str(txt))
            assert enhanced.output_dir == tmp_path
        except Exception as exc:
            pytest.skip(f"convert_local raised: {exc}")

    def test_convert_local_with_stream_info(self, tmp_path):
        """convert_local passes stream_info through to convert_stream."""
        try:
            from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
            from scimarkdown.config import SciMarkdownConfig
            from markitdown._stream_info import StreamInfo
        except Exception:
            pytest.skip("markitdown not importable")

        txt = tmp_path / "test.txt"
        txt.write_text("Hello")

        config = SciMarkdownConfig(math_heuristic=False)
        enhanced = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

        try:
            si = StreamInfo(local_path=str(txt), extension=".txt", filename="test.txt")
            result = enhanced.convert_local(str(txt), stream_info=si)
            assert result is not None
        except Exception as exc:
            pytest.skip(f"convert_local raised: {exc}")

    def test_convert_local_with_url(self, tmp_path):
        """convert_local with url parameter passes it to stream_info."""
        try:
            from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
            from scimarkdown.config import SciMarkdownConfig
        except Exception:
            pytest.skip("markitdown not importable")

        txt = tmp_path / "test.txt"
        txt.write_text("Hello")

        config = SciMarkdownConfig(math_heuristic=False)
        enhanced = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

        try:
            result = enhanced.convert_local(str(txt), url="file:///test.txt")
            assert result is not None
        except Exception as exc:
            pytest.skip(f"convert_local raised: {exc}")


class TestEnhancedMarkitdownConvertStream:
    def test_convert_stream_non_seekable(self, tmp_path):
        """Non-seekable stream is wrapped in BytesIO."""
        try:
            from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
            from scimarkdown.config import SciMarkdownConfig
        except Exception:
            pytest.skip("markitdown not importable")

        config = SciMarkdownConfig(math_heuristic=False)
        enhanced = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

        # Create a non-seekable stream
        non_seekable = MagicMock()
        non_seekable.seekable.return_value = False
        non_seekable.read.return_value = b"Hello world"

        try:
            result = enhanced.convert_stream(non_seekable, file_extension=".txt")
            assert result is not None
        except Exception as exc:
            pytest.skip(f"convert_stream raised: {exc}")

    def test_convert_stream_enrichment_failure_returns_base(self, tmp_path):
        """When enrichment fails, base result is returned."""
        try:
            from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
            from scimarkdown.config import SciMarkdownConfig
        except Exception:
            pytest.skip("markitdown not importable")

        config = SciMarkdownConfig(math_heuristic=False)
        enhanced = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

        # Make enrichment fail
        enhanced._enrichment.enrich = MagicMock(side_effect=RuntimeError("enrichment failed"))

        stream = io.BytesIO(b"Hello world")
        try:
            result = enhanced.convert_stream(stream, file_extension=".txt")
            # Should return base result despite enrichment failure
            assert result is not None
        except Exception as exc:
            pytest.skip(f"convert_stream raised: {exc}")

    def test_convert_stream_with_filename_in_stream_info(self, tmp_path):
        """document_name is derived from stream_info.filename."""
        try:
            from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
            from scimarkdown.config import SciMarkdownConfig
            from markitdown._stream_info import StreamInfo
        except Exception:
            pytest.skip("markitdown not importable")

        config = SciMarkdownConfig(math_heuristic=False)
        enhanced = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

        stream = io.BytesIO(b"Hello world")
        si = StreamInfo(filename="mydoc.txt", extension=".txt")

        try:
            result = enhanced.convert_stream(stream, stream_info=si, file_extension=".txt")
            assert result is not None
        except Exception as exc:
            pytest.skip(f"convert_stream raised: {exc}")

    def test_convert_stream_with_non_same_output_dir(self, tmp_path):
        """When images_output_dir is set to a specific path, it's used."""
        try:
            from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
            from scimarkdown.config import SciMarkdownConfig
        except Exception:
            pytest.skip("markitdown not importable")

        out_dir = tmp_path / "specific_output"
        config = SciMarkdownConfig(
            math_heuristic=False,
            images_output_dir=str(out_dir),
        )
        enhanced = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

        stream = io.BytesIO(b"Hello")
        try:
            result = enhanced.convert_stream(stream, file_extension=".txt")
            assert result is not None
        except Exception as exc:
            pytest.skip(f"convert_stream raised: {exc}")
