"""Verify that original MarkItDown tests still pass after our fork changes."""

import subprocess
import sys
import pytest


@pytest.mark.skip(reason="Upstream tests require full markitdown dependencies")
def test_upstream_tests_pass():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "packages/markitdown/tests/", "-x", "-q"],
        capture_output=True,
        text=True,
        cwd="/home/u680912/2-Munera/claude/mcp/microsoft_markitdown",
    )
    assert result.returncode == 0, f"Upstream tests failed:\n{result.stdout}\n{result.stderr}"
