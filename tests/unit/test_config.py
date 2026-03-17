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


def test_reference_patterns_default():
    config = SciMarkdownConfig()
    assert len(config.references_patterns) == 5
    assert any("Fig" in p for p in config.references_patterns)
