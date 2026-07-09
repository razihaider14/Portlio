"""
Unit tests for the content-target selection registry.

select_content_targets() decides which already-known tree entries are worth
downloading; it never makes network calls itself.
"""

from app.github.content_targets import (
    CONTENT_TARGET_FILENAMES,
    MAX_CONTENT_FILE_SIZE_BYTES,
    select_content_targets,
)


def entry(path: str, type_: str = "file", size: int | None = None) -> dict:
    d = {"path": path, "name": path.rsplit("/", 1)[-1], "type": type_}
    if size is not None:
        d["size"] = size
    return d


class TestContentTargetFilenames:
    def test_includes_common_manifest_files(self):
        for name in (
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "cargo.toml",
            "go.mod",
            "composer.json",
            "readme.md",
        ):
            assert name in CONTENT_TARGET_FILENAMES

    def test_all_entries_are_lowercase(self):
        assert all(name == name.lower() for name in CONTENT_TARGET_FILENAMES)

    def test_excludes_generated_lockfiles(self):
        # Lockfiles are large, machine-generated, and their mere presence is
        # already a strong filename-based signal; content isn't needed.
        assert "poetry.lock" not in CONTENT_TARGET_FILENAMES
        assert "package-lock.json" not in CONTENT_TARGET_FILENAMES


class TestSelectContentTargets:
    def test_selects_matching_files(self):
        entries = [entry("requirements.txt"), entry("main.py")]
        selected = select_content_targets(entries)
        assert [e["path"] for e in selected] == ["requirements.txt"]

    def test_matching_is_case_insensitive(self):
        entries = [entry("REQUIREMENTS.TXT")]
        selected = select_content_targets(entries)
        assert len(selected) == 1

    def test_excludes_directories_even_with_matching_name(self):
        entries = [entry("package.json", type_="dir")]
        assert select_content_targets(entries) == []

    def test_excludes_files_not_in_registry(self):
        entries = [entry("main.py"), entry("README.rst")]
        assert select_content_targets(entries) == []

    def test_selects_multiple_targets_across_ecosystems(self):
        entries = [
            entry("requirements.txt"),
            entry("package.json"),
            entry("Cargo.toml"),
            entry("src/main.py"),
        ]
        selected = select_content_targets(entries)
        assert {e["path"] for e in selected} == {
            "requirements.txt",
            "package.json",
            "Cargo.toml",
        }

    def test_selects_nested_matching_files(self):
        entries = [entry("backend/requirements.txt")]
        selected = select_content_targets(entries)
        assert [e["path"] for e in selected] == ["backend/requirements.txt"]

    def test_skips_oversized_files(self):
        entries = [entry("README.md", size=MAX_CONTENT_FILE_SIZE_BYTES + 1)]
        assert select_content_targets(entries) == []

    def test_keeps_files_at_exact_size_limit(self):
        entries = [entry("README.md", size=MAX_CONTENT_FILE_SIZE_BYTES)]
        assert len(select_content_targets(entries)) == 1

    def test_keeps_files_with_unknown_size(self):
        entries = [entry("README.md")]  # no "size" key
        assert len(select_content_targets(entries)) == 1

    def test_empty_entries_returns_empty(self):
        assert select_content_targets([]) == []

    def test_custom_filenames_argument_overrides_default(self):
        entries = [entry("requirements.txt"), entry("special.cfg")]
        selected = select_content_targets(entries, filenames=frozenset({"special.cfg"}))
        assert [e["path"] for e in selected] == ["special.cfg"]

    def test_custom_max_size_argument_overrides_default(self):
        entries = [entry("requirements.txt", size=10)]
        assert select_content_targets(entries, max_size_bytes=5) == []
