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
