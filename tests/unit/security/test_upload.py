"""
@test_registry:
    suite: security-unit
    component: security.upload
    covers: [src/aiflow/security/upload.py]
    phase: 5
    priority: critical
    estimated_duration_ms: 100
    requires_services: []
    tags: [security, upload, path-traversal, filename]
"""

import pytest

from aiflow.security.upload import secure_filename, validate_upload_path


class TestSecureFilename:
    def test_normal_filename(self):
        assert secure_filename("report.pdf") == "report.pdf"

    def test_strips_directory_unix(self):
        assert secure_filename("/etc/passwd") == "passwd"

    def test_strips_directory_windows(self):
        assert secure_filename("C:\\Windows\\system32\\evil.exe") == "evil.exe"

    def test_strips_traversal(self):
        assert secure_filename("../../etc/passwd") == "passwd"

    def test_removes_null_bytes(self):
        assert secure_filename("file\x00name.pdf") == "filename.pdf"

    def test_removes_special_chars(self):
        result = secure_filename("file<>name|with:bad*chars?.pdf")
        assert "<" not in result
        assert ">" not in result
        assert "|" not in result
        assert ":" not in result

    def test_collapses_double_dots(self):
        assert secure_filename("file..name.pdf") == "file.name.pdf"

    def test_empty_filename_fallback(self):
        assert secure_filename("") == "unnamed"

    def test_only_dots_fallback(self):
        assert secure_filename("...") == "unnamed"

    def test_unicode_filename(self):
        result = secure_filename("dokumentum_v2.pdf")
        assert result == "dokumentum_v2.pdf"

    def test_spaces_preserved(self):
        result = secure_filename("my report 2024.pdf")
        assert "my report 2024" in result


class TestValidateUploadPath:
    def test_valid_path(self, tmp_path):
        target = tmp_path / "uploads" / "file.pdf"
        result = validate_upload_path(target, tmp_path)
        assert result.is_relative_to(tmp_path.resolve())

    def test_traversal_rejected(self, tmp_path):
        target = tmp_path / "uploads" / ".." / ".." / "etc" / "passwd"
        with pytest.raises(ValueError, match="Path traversal detected"):
            validate_upload_path(target, tmp_path / "uploads")

    def test_exact_base_is_ok(self, tmp_path):
        result = validate_upload_path(tmp_path, tmp_path)
        assert result == tmp_path.resolve()

    def test_sibling_directory_rejected(self, tmp_path):
        base = tmp_path / "uploads"
        base.mkdir()
        sibling = tmp_path / "secrets" / "key.pem"
        with pytest.raises(ValueError, match="Path traversal detected"):
            validate_upload_path(sibling, base)
