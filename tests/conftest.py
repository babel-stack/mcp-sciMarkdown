import pytest
import shutil
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXPECTED_DIR = FIXTURES_DIR / "expected"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def tmp_output_dir(tmp_path):
    return tmp_path


def has_pix2tex():
    try:
        import pix2tex
        return True
    except ImportError:
        return False


def has_nougat():
    try:
        import nougat
        return True
    except ImportError:
        return False


skip_no_ocr = pytest.mark.skipif(not has_pix2tex(), reason="pix2tex not installed")
skip_no_nougat = pytest.mark.skipif(not has_nougat(), reason="nougat not installed")
