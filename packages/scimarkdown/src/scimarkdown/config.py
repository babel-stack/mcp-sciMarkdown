"""Configuration system for SciMarkdown."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


_DEFAULT_PATTERNS = [
    r'Fig(?:ura|ure|\.)\s*(\d+)',
    r'Tab(?:la|le|\.)\s*(\d+)',
    r'Gr[aA]f(?:ico|h)\s*(\d+)',
    r'Im(?:agen|age|g\.?)\s*(\d+)',
    r'Chart\s*(\d+)',
]


@dataclass
class SciMarkdownConfig:
    # LaTeX
    latex_style: str = "standard"

    # Images
    images_output_dir: str = "same"
    images_format: str = "png"
    images_dpi: int = 300
    images_margin_px: int = 10
    images_counter_digits: int = 5
    images_autocrop_whitespace: bool = True

    # Math
    math_heuristic: bool = True
    math_ocr_engine: str = "auto"
    math_nougat_model: str = "0.1.0-base"
    math_confidence_threshold: float = 0.75

    # LLM
    llm_enabled: bool = False
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_api_key_env: str = "LLM_API_KEY"

    # References
    references_patterns: list[str] = field(default_factory=lambda: list(_DEFAULT_PATTERNS))
    references_languages: list[str] = field(default_factory=lambda: ["es", "en"])
    references_generate_index: bool = True

    # Performance
    performance_total_timeout: int = 1800
    performance_max_images: int = 10000
    performance_max_image_file_size_mb: int = 50
    performance_max_total_images_size_mb: int = 500
    performance_ocr_timeout: int = 30
    performance_nougat_timeout: int = 120
    performance_llm_timeout: int = 60
    performance_unload_models: bool = False

    # Sync
    sync_remote: str = "https://github.com/microsoft/markitdown.git"
    sync_branch: str = "main"
    sync_check_interval_days: int = 14

    # Filters
    filters_enabled: bool = True
    filters_repeated_text: bool = True
    filters_page_numbers: bool = True
    filters_decorative_images: bool = True
    filters_min_repeat_pages: int = 3       # Pages text must repeat to be considered noise
    filters_max_header_length: int = 100    # Max chars for a header candidate
    filters_position_tolerance: float = 5.0 # Y-coordinate tolerance in points
    filters_min_image_size: int = 30        # Min width/height to keep (px)
    filters_max_image_aspect_ratio: float = 8.0  # Max aspect ratio before flagging as decorative
    filters_min_image_repeat: int = 3       # Pages image must repeat to be filtered

    # Embeddings
    embeddings_enabled: bool = False
    embeddings_provider: str = "gemini"
    embeddings_model: str = "gemini-embedding-2-preview"
    embeddings_api_key_env: str = "GEMINI_API_KEY"
    embeddings_dimensions: int = 768
    embeddings_classify_math: bool = True
    embeddings_semantic_linking: bool = True
    embeddings_classify_document: bool = True
    embeddings_content_indexing: bool = False
    embeddings_cache_enabled: bool = True
    embeddings_cache_dir: str = ".scimarkdown_cache"
    embeddings_cache_ttl_days: int = 30
    embeddings_math_similarity_threshold: float = 0.75
    embeddings_image_link_threshold: float = 0.60
    embeddings_max_per_document: int = 500
    embeddings_batch_size: int = 100

    @classmethod
    def from_dict(cls, data: dict) -> "SciMarkdownConfig":
        config = cls()
        config._apply_dict(data)
        return config

    def with_overrides(self, overrides: dict) -> "SciMarkdownConfig":
        import copy
        config = copy.deepcopy(self)
        config._apply_dict(overrides)
        return config

    def _apply_dict(self, data: dict) -> None:
        mapping = {
            ("latex", "style"): "latex_style",
            ("images", "output_dir"): "images_output_dir",
            ("images", "format"): "images_format",
            ("images", "dpi"): "images_dpi",
            ("images", "margin_px"): "images_margin_px",
            ("images", "counter_digits"): "images_counter_digits",
            ("images", "autocrop_whitespace"): "images_autocrop_whitespace",
            ("math", "heuristic"): "math_heuristic",
            ("math", "ocr_engine"): "math_ocr_engine",
            ("math", "nougat_model"): "math_nougat_model",
            ("math", "confidence_threshold"): "math_confidence_threshold",
            ("llm", "enabled"): "llm_enabled",
            ("llm", "provider"): "llm_provider",
            ("llm", "model"): "llm_model",
            ("llm", "api_key_env"): "llm_api_key_env",
            ("references", "patterns"): "references_patterns",
            ("references", "languages"): "references_languages",
            ("references", "generate_index"): "references_generate_index",
            ("performance", "total_timeout_seconds"): "performance_total_timeout",
            ("performance", "max_images"): "performance_max_images",
            ("performance", "max_image_file_size_mb"): "performance_max_image_file_size_mb",
            ("performance", "max_total_images_size_mb"): "performance_max_total_images_size_mb",
            ("performance", "ocr_timeout_seconds"): "performance_ocr_timeout",
            ("performance", "nougat_timeout_seconds"): "performance_nougat_timeout",
            ("performance", "llm_timeout_seconds"): "performance_llm_timeout",
            ("performance", "unload_models_after_conversion"): "performance_unload_models",
            ("sync", "remote"): "sync_remote",
            ("sync", "branch"): "sync_branch",
            ("sync", "check_interval_days"): "sync_check_interval_days",
            ("filters", "enabled"): "filters_enabled",
            ("filters", "repeated_text"): "filters_repeated_text",
            ("filters", "page_numbers"): "filters_page_numbers",
            ("filters", "decorative_images"): "filters_decorative_images",
            ("filters", "min_repeat_pages"): "filters_min_repeat_pages",
            ("filters", "max_header_length"): "filters_max_header_length",
            ("filters", "position_tolerance"): "filters_position_tolerance",
            ("filters", "min_image_size"): "filters_min_image_size",
            ("filters", "max_image_aspect_ratio"): "filters_max_image_aspect_ratio",
            ("filters", "min_image_repeat"): "filters_min_image_repeat",
            ("embeddings", "enabled"): "embeddings_enabled",
            ("embeddings", "provider"): "embeddings_provider",
            ("embeddings", "model"): "embeddings_model",
            ("embeddings", "api_key_env"): "embeddings_api_key_env",
            ("embeddings", "dimensions"): "embeddings_dimensions",
            ("embeddings", "classify_math"): "embeddings_classify_math",
            ("embeddings", "semantic_linking"): "embeddings_semantic_linking",
            ("embeddings", "classify_document"): "embeddings_classify_document",
            ("embeddings", "content_indexing"): "embeddings_content_indexing",
            ("embeddings", "cache_enabled"): "embeddings_cache_enabled",
            ("embeddings", "cache_dir"): "embeddings_cache_dir",
            ("embeddings", "cache_ttl_days"): "embeddings_cache_ttl_days",
            ("embeddings", "math_similarity_threshold"): "embeddings_math_similarity_threshold",
            ("embeddings", "image_link_threshold"): "embeddings_image_link_threshold",
            ("embeddings", "max_per_document"): "embeddings_max_per_document",
            ("embeddings", "batch_size"): "embeddings_batch_size",
        }
        for (section, key), attr in mapping.items():
            if section in data and key in data[section]:
                setattr(self, attr, data[section][key])


def load_config(path: Optional[Path] = None) -> SciMarkdownConfig:
    if path is None:
        path = Path("scimarkdown.yaml")
    if not path.exists():
        return SciMarkdownConfig()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return SciMarkdownConfig.from_dict(data)
