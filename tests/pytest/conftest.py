"""Shared fixtures for xfce-linux Python tests."""

import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to sys.path for direct script imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def mock_filemap(temp_dir):
    """Create a minimal filemap.json in a temp directory."""
    filemap = {
        "xfce-linux/file.bst": {
            "interval": "weekly",
            "files": ["/usr/bin/xfce4-session", "/usr/share/icons/hicolor/index.theme"],
        },
        "gnome/shell.bst": {
            "interval": "monthly",
            "files": ["/usr/bin/gnome-shell", "/usr/lib/libmutter.so"],
        },
    }
    import json
    path = temp_dir / "filemap.json"
    path.write_text(json.dumps(filemap, indent=2))
    return path
