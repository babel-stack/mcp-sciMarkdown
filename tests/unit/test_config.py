import yaml
from pathlib import Path
from scimarkdown.config import SciMarkdownConfig, load_config


def test_default_config():
    config = SciMarkdownConfig()
    assert config.latex_style == "standard"
    assert config.images_output_dir == "same"
    assert config.images_dpi == 300
    assert config.images_counter_digits == 5
    assert config.math_heuristic is True
    assert config.math_ocr_engine == "auto"
    assert config.math_confidence_threshold == 0.75
    assert config.llm_enabled is False
    assert config.references_generate_index is True
    assert config.performance_total_timeout == 1800


def test_config_from_dict():
    config = SciMarkdownConfig.from_dict({
        "latex": {"style": "github"},
        "images": {"dpi": 150, "counter_digits": 5},
        "math": {"ocr_engine": "pix2tex"},
        "performance": {"total_timeout_seconds": 600},
    })
    assert config.latex_style == "github"
    assert config.images_dpi == 150
    assert config.math_ocr_engine == "pix2tex"
    assert config.performance_total_timeout == 600


def test_config_from_yaml_file(tmp_path):
    config_file = tmp_path / "scimarkdown.yaml"
    config_file.write_text(yaml.dump({
        "latex": {"style": "github"},
        "images": {"output_dir": "/tmp/images"},
    }))
    config = load_config(config_file)
    assert config.latex_style == "github"
    assert config.images_output_dir == "/tmp/images"


def test_config_override():
    base = SciMarkdownConfig()
    overrides = {"latex": {"style": "github"}}
    config = base.with_overrides(overrides)
    assert config.latex_style == "github"
    assert config.images_dpi == 300  # unchanged


def test_filters_config_defaults():
    config = SciMarkdownConfig()
    assert config.filters_enabled is True
    assert config.filters_repeated_text is True
    assert config.filters_page_numbers is True
    assert config.filters_decorative_images is True
    assert config.filters_min_repeat_pages == 3
    assert config.filters_max_header_length == 100
    assert config.filters_position_tolerance == 5.0
    assert config.filters_min_image_size == 30
    assert config.filters_max_image_aspect_ratio == 8.0
    assert config.filters_min_image_repeat == 3


def test_filters_config_from_dict():
    config = SciMarkdownConfig.from_dict({
        "filters": {
            "enabled": False,
            "min_repeat_pages": 5,
        }
    })
    assert config.filters_enabled is False
    assert config.filters_min_repeat_pages == 5


def test_reference_patterns_default():
    config = SciMarkdownConfig()
    assert len(config.references_patterns) == 5
    assert any("Fig" in p for p in config.references_patterns)


# --- Embeddings configuration ---

def test_embeddings_defaults():
    config = SciMarkdownConfig()
    assert config.embeddings_enabled is False
    assert config.embeddings_provider == "gemini"
    assert config.embeddings_model == "gemini-embedding-2-preview"
    assert config.embeddings_api_key_env == "GEMINI_API_KEY"
    assert config.embeddings_dimensions == 768
    assert config.embeddings_classify_math is True
    assert config.embeddings_semantic_linking is True
    assert config.embeddings_classify_document is True
    assert config.embeddings_content_indexing is False
    assert config.embeddings_cache_enabled is True
    assert config.embeddings_cache_dir == ".scimarkdown_cache"
    assert config.embeddings_cache_ttl_days == 30
    assert config.embeddings_math_similarity_threshold == 0.75
    assert config.embeddings_image_link_threshold == 0.60
    assert config.embeddings_max_per_document == 500
    assert config.embeddings_batch_size == 100


def test_embeddings_from_dict():
    config = SciMarkdownConfig.from_dict({
        "embeddings": {
            "enabled": True,
            "provider": "gemini",
            "model": "custom-model",
            "api_key_env": "MY_GEMINI_KEY",
            "dimensions": 1024,
            "classify_math": False,
            "semantic_linking": False,
            "classify_document": False,
            "content_indexing": True,
            "cache_enabled": False,
            "cache_dir": "/tmp/emb_cache",
            "cache_ttl_days": 7,
            "math_similarity_threshold": 0.80,
            "image_link_threshold": 0.70,
            "max_per_document": 200,
            "batch_size": 50,
        }
    })
    assert config.embeddings_enabled is True
    assert config.embeddings_model == "custom-model"
    assert config.embeddings_api_key_env == "MY_GEMINI_KEY"
    assert config.embeddings_dimensions == 1024
    assert config.embeddings_classify_math is False
    assert config.embeddings_content_indexing is True
    assert config.embeddings_cache_enabled is False
    assert config.embeddings_cache_dir == "/tmp/emb_cache"
    assert config.embeddings_cache_ttl_days == 7
    assert config.embeddings_math_similarity_threshold == 0.80
    assert config.embeddings_image_link_threshold == 0.70
    assert config.embeddings_max_per_document == 200
    assert config.embeddings_batch_size == 50


def test_embeddings_override():
    base = SciMarkdownConfig()
    config = base.with_overrides({"embeddings": {"enabled": True, "cache_ttl_days": 14}})
    assert config.embeddings_enabled is True
    assert config.embeddings_cache_ttl_days == 14
    assert config.embeddings_model == "gemini-embedding-2-preview"  # unchanged
