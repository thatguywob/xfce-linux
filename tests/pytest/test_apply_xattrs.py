"""Unit tests for scripts/apply-xattrs.py.

Tests the main() function logic with mocked os.setxattr and file I/O.
"""

import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Load apply-xattrs.py as a module (filename has hyphen, so importlib is needed)
MODULE_PATH = PROJECT_ROOT / "scripts" / "apply-xattrs.py"
spec = importlib.util.spec_from_file_location("apply_xattrs", MODULE_PATH)
apply_xattrs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apply_xattrs)


class TestApplyXattrs:
    def test_main_requires_rootfs_arg(self):
        """Should return error code 1 when no arguments provided."""
        with patch.object(sys, "argv", ["apply-xattrs.py"]):
            result = apply_xattrs.main()
            assert result == 1, f"Expected exit code 1, got {result}"

    def test_main_usage_message(self, capsys):
        """Should print usage message to stderr when no args."""
        with patch.object(sys, "argv", ["apply-xattrs.py"]):
            apply_xattrs.main()
            captured = capsys.readouterr()
            assert "usage:" in captured.err.lower(), "Should print usage message"

    def test_main_sets_xattrs(self, tmp_path, capsys):
        """Should set xattrs for files that exist in the rootfs."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir()
        (rootfs / "usr").mkdir()
        (rootfs / "usr" / "bin").mkdir()
        (rootfs / "usr" / "share").mkdir()
        (rootfs / "usr" / "share" / "icons").mkdir()

        # Create target files
        bin_file = rootfs / "usr" / "bin" / "xfce4-session"
        bin_file.write_text("binary")
        icon_file = rootfs / "usr" / "share" / "icons" / "index.theme"
        icon_file.write_text("theme")

        # Create filemap
        filemap = {
            "xfce-linux/xfce4-session.bst": {
                "interval": "weekly",
                "files": ["/usr/bin/xfce4-session", "/usr/share/icons/index.theme"],
            }
        }
        filemap_path = tmp_path / "filemap.json"
        filemap_path.write_text(json.dumps(filemap))

        with patch.object(os, "setxattr") as mock_setxattr:
            with patch.object(sys, "argv", ["apply-xattrs.py", str(rootfs), str(filemap_path)]):
                result = apply_xattrs.main()
                assert result == 0, f"Expected exit code 0, got {result}"

            # Should have set two xattrs per file
            assert mock_setxattr.call_count >= 2, (
                f"Expected at least 2 setxattr calls, got {mock_setxattr.call_count}"
            )

    def test_main_skips_missing_files(self, tmp_path, capsys):
        """Should skip files that don't exist in the rootfs and report count."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir()

        filemap = {
            "test/element.bst": {
                "interval": "daily",
                "files": ["/nonexistent/file.bin"],
            }
        }
        filemap_path = tmp_path / "filemap.json"
        filemap_path.write_text(json.dumps(filemap))

        with patch.object(os, "setxattr") as mock_setxattr:
            with patch.object(sys, "argv", ["apply-xattrs.py", str(rootfs), str(filemap_path)]):
                result = apply_xattrs.main()
                assert result == 0, f"Expected exit code 0, got {result}"
            mock_setxattr.assert_not_called()

    def test_main_handles_setxattr_errors(self, tmp_path, capsys):
        """Should handle OSError from setxattr gracefully."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir()
        target = rootfs / "test.txt"
        target.write_text("content")

        filemap = {
            "test/element.bst": {
                "interval": "weekly",
                "files": ["/test.txt"],
            }
        }
        filemap_path = tmp_path / "filemap.json"
        filemap_path.write_text(json.dumps(filemap))

        with patch.object(os, "setxattr", side_effect=OSError("Permission denied")):
            with patch.object(sys, "argv", ["apply-xattrs.py", str(rootfs), str(filemap_path)]):
                result = apply_xattrs.main()
                assert result == 0, f"Expected exit code 0 (non-fatal), got {result}"
