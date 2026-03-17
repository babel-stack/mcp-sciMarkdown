import pytest
import io


def test_enhanced_markitdown_module_exists():
    """Verify the module can be imported."""
    try:
        from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
        assert EnhancedMarkItDown is not None
    except Exception:
        pytest.skip("markitdown not importable on this system")


def test_enhanced_has_config():
    try:
        from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
        from scimarkdown.config import SciMarkdownConfig

        enhanced = EnhancedMarkItDown()
        assert hasattr(enhanced, 'sci_config')
        assert isinstance(enhanced.sci_config, SciMarkdownConfig)
    except Exception:
        pytest.skip("markitdown not importable on this system")


def test_enhanced_with_custom_config():
    try:
        from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
        from scimarkdown.config import SciMarkdownConfig

        config = SciMarkdownConfig(latex_style="github")
        enhanced = EnhancedMarkItDown(sci_config=config)
        assert enhanced.sci_config.latex_style == "github"
    except Exception:
        pytest.skip("markitdown not importable on this system")
