"""Tests for scimarkdown CLI (__main__.py)."""

import sys
from unittest.mock import patch, MagicMock
from scimarkdown.__main__ import main, _build_parser


class TestBuildParser:
    def test_parser_has_input_arg(self):
        parser = _build_parser()
        args = parser.parse_args(["somefile.txt"])
        assert args.input == "somefile.txt"

    def test_parser_has_output_arg(self):
        parser = _build_parser()
        args = parser.parse_args(["file.txt", "-o", "out.md"])
        assert args.output == "out.md"

    def test_parser_has_config_arg(self):
        parser = _build_parser()
        args = parser.parse_args(["file.txt", "-c", "config.yaml"])
        assert args.config == "config.yaml"

    def test_parser_has_latex_style_arg(self):
        parser = _build_parser()
        args = parser.parse_args(["file.txt", "--latex-style", "github"])
        assert args.latex_style == "github"

    def test_parser_has_output_dir_arg(self):
        parser = _build_parser()
        args = parser.parse_args(["file.txt", "--output-dir", "/tmp"])
        assert args.output_dir == "/tmp"

    def test_parser_defaults(self):
        parser = _build_parser()
        args = parser.parse_args(["file.txt"])
        assert args.output is None
        assert args.config is None
        assert args.latex_style is None
        assert args.output_dir is None


_ENHANCED_PATH = "scimarkdown._enhanced_markitdown.EnhancedMarkItDown"


def _mock_enhanced(mock_result):
    """Helper: create mock converter class and instance."""
    mock_converter = MagicMock()
    mock_converter.convert.return_value = mock_result
    mock_cls = MagicMock(return_value=mock_converter)
    return mock_cls, mock_converter


class TestMainCLI:
    def test_cli_with_file_stdout(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("Hello x² + y²")
        mock_result = MagicMock()
        mock_result.markdown = "Hello $x^{2}$ + $y^{2}$"
        mock_cls, _ = _mock_enhanced(mock_result)

        with patch(_ENHANCED_PATH, mock_cls):
            with patch("sys.stdout"):
                exit_code = main([str(txt)])
        assert exit_code == 0

    def test_cli_with_output_file(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("Hello")
        out = tmp_path / "out.md"

        mock_result = MagicMock()
        mock_result.markdown = "Hello"
        mock_cls, _ = _mock_enhanced(mock_result)

        with patch(_ENHANCED_PATH, mock_cls):
            exit_code = main([str(txt), "-o", str(out)])
        assert exit_code == 0
        assert out.read_text() == "Hello"

    def test_cli_with_latex_style(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("x²")

        mock_result = MagicMock()
        mock_result.markdown = "content"
        mock_cls, _ = _mock_enhanced(mock_result)

        with patch(_ENHANCED_PATH, mock_cls):
            exit_code = main([str(txt), "--latex-style", "github"])
        assert exit_code == 0

    def test_cli_with_config_file(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("Hello")
        cfg = tmp_path / "config.yaml"
        cfg.write_text("latex:\n  style: github\n")

        mock_result = MagicMock()
        mock_result.markdown = "Hello"
        mock_cls, _ = _mock_enhanced(mock_result)

        with patch(_ENHANCED_PATH, mock_cls):
            exit_code = main([str(txt), "-c", str(cfg)])
        assert exit_code == 0

    def test_cli_with_output_dir(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("Hello")

        mock_result = MagicMock()
        mock_result.markdown = "Hello"
        mock_cls, _ = _mock_enhanced(mock_result)

        with patch(_ENHANCED_PATH, mock_cls):
            exit_code = main([str(txt), "--output-dir", str(tmp_path)])
        assert exit_code == 0

    def test_cli_conversion_failure_returns_1(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("Hello")

        mock_converter = MagicMock()
        mock_converter.convert.side_effect = RuntimeError("Conversion error")
        mock_cls = MagicMock(return_value=mock_converter)

        with patch(_ENHANCED_PATH, mock_cls):
            exit_code = main([str(txt)])
        assert exit_code == 1

    def test_cli_import_error_returns_2(self, tmp_path):
        """When the import of core modules raises ImportError, exit code 2."""
        txt = tmp_path / "test.txt"
        txt.write_text("Hello")

        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "scimarkdown.config" in name:
                raise ImportError("no module")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            exit_code = main([str(txt)])
        assert exit_code == 2

    def test_cli_markdown_no_trailing_newline(self, tmp_path):
        """When markdown doesn't end in newline, stdout gets one appended."""
        txt = tmp_path / "test.txt"
        txt.write_text("Hello")

        mock_result = MagicMock()
        mock_result.markdown = "no newline"
        mock_cls, _ = _mock_enhanced(mock_result)

        written = []
        with patch(_ENHANCED_PATH, mock_cls):
            with patch("sys.stdout") as mock_stdout:
                mock_stdout.write.side_effect = lambda s: written.append(s)
                exit_code = main([str(txt)])
        assert exit_code == 0
        # Should write both the content and a trailing newline
        assert any("no newline" in s for s in written)
        assert "\n" in written

    def test_cli_empty_markdown(self, tmp_path):
        """Empty markdown: stdout.write called with empty string, no trailing newline."""
        txt = tmp_path / "test.txt"
        txt.write_text("")

        mock_result = MagicMock()
        mock_result.markdown = ""
        mock_cls, _ = _mock_enhanced(mock_result)

        with patch(_ENHANCED_PATH, mock_cls):
            with patch("sys.stdout"):
                exit_code = main([str(txt)])
        assert exit_code == 0

    def test_cli_output_creates_parent_dir(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("Hello")
        out = tmp_path / "subdir" / "nested" / "out.md"

        mock_result = MagicMock()
        mock_result.markdown = "Hello"
        mock_cls, _ = _mock_enhanced(mock_result)

        with patch(_ENHANCED_PATH, mock_cls):
            exit_code = main([str(txt), "-o", str(out)])
        assert exit_code == 0
        assert out.exists()

    def test_cli_with_all_overrides(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("content")

        mock_result = MagicMock()
        mock_result.markdown = "content"
        mock_cls, _ = _mock_enhanced(mock_result)

        with patch(_ENHANCED_PATH, mock_cls):
            exit_code = main([
                str(txt),
                "--latex-style", "standard",
                "--output-dir", str(tmp_path),
            ])
        assert exit_code == 0
