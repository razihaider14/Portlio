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

    def test_includes_documentation_files(self):
        for name in (
            "readme.md",
            "license",
            "license.md",
            "changelog.md",
            "contributing.md",
            "code_of_conduct.md",
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
        entries = [entry("main.py"), entry("notes.txt")]
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


class TestExtensionBasedSelection:
    def test_selects_file_matching_extension_regardless_of_name(self):
        entries = [entry("MySketch.ino")]
        selected = select_content_targets(entries)
        assert [e["path"] for e in selected] == ["MySketch.ino"]

    def test_extension_matching_is_case_insensitive(self):
        entries = [entry("Sketch.INO")]
        selected = select_content_targets(entries)
        assert len(selected) == 1

    def test_caps_matches_per_extension(self):
        entries = [entry(f"sketch{i}.ino") for i in range(10)]
        selected = select_content_targets(entries, max_matches_per_extension=3)
        assert len(selected) == 3

    def test_prefers_shallower_paths_when_capping(self):
        entries = [
            entry("deep/nested/path/sketch.ino"),
            entry("root.ino"),
        ]
        selected = select_content_targets(entries, max_matches_per_extension=1)
        assert selected[0]["path"] == "root.ino"

    def test_respects_size_limit_for_extension_matches(self):
        entries = [entry("big.ino", size=MAX_CONTENT_FILE_SIZE_BYTES + 1)]
        assert select_content_targets(entries) == []

    def test_directories_with_matching_extension_are_excluded(self):
        entries = [entry("weird.ino", type_="dir")]
        assert select_content_targets(entries) == []

    def test_custom_extensions_argument_overrides_default(self):
        entries = [entry("main.cpp")]
        selected = select_content_targets(entries, extensions=frozenset({".cpp"}))
        assert [e["path"] for e in selected] == ["main.cpp"]

    def test_no_extension_matches_by_default_outside_registry(self):
        entries = [entry("main.cpp")]
        assert select_content_targets(entries) == []


class TestCompanionFileSelection:
    def test_selects_companion_h_and_cpp_files_next_to_ino(self):
        entries = [
            entry("firmware/firmware.ino"),
            entry("firmware/mqtt_handler.cpp"),
            entry("firmware/mqtt_handler.h"),
        ]
        selected = select_content_targets(entries)
        paths = {e["path"] for e in selected}
        assert paths == {
            "firmware/firmware.ino",
            "firmware/mqtt_handler.cpp",
            "firmware/mqtt_handler.h",
        }

    def test_does_not_select_companion_files_from_other_directories(self):
        entries = [
            entry("firmware/firmware.ino"),
            entry("other/unrelated.cpp"),
        ]
        selected = select_content_targets(entries)
        paths = {e["path"] for e in selected}
        assert "other/unrelated.cpp" not in paths

    def test_no_companions_selected_without_an_extension_match(self):
        entries = [entry("src/main.cpp"), entry("src/main.h")]
        assert select_content_targets(entries) == []

    def test_caps_companion_files_per_directory(self):
        entries = [entry("firmware/firmware.ino")] + [
            entry(f"firmware/module{i}.cpp") for i in range(15)
        ]
        selected = select_content_targets(entries, max_companion_files_per_directory=3)
        companions = [e for e in selected if e["path"] != "firmware/firmware.ino"]
        assert len(companions) == 3

    def test_companion_selection_respects_size_limit(self):
        entries = [
            entry("firmware/firmware.ino"),
            entry("firmware/big.cpp", size=MAX_CONTENT_FILE_SIZE_BYTES + 1),
        ]
        selected = select_content_targets(entries)
        paths = {e["path"] for e in selected}
        assert "firmware/big.cpp" not in paths

    def test_no_duplicate_entries_when_filename_and_companion_overlap(self):
        # A companion-matching file that's also independently a
        # CONTENT_TARGET_FILENAMES match (unlikely in practice, but the
        # dedup logic should still hold) must only appear once.
        entries = [entry("firmware/firmware.ino"), entry("firmware/setup.h")]
        selected = select_content_targets(entries)
        paths = [e["path"] for e in selected]
        assert len(paths) == len(set(paths))

    def test_custom_companion_extensions_argument(self):
        entries = [entry("firmware/firmware.ino"), entry("firmware/data.txt")]
        selected = select_content_targets(
            entries, companion_extensions=frozenset({".txt"})
        )
        paths = {e["path"] for e in selected}
        assert "firmware/data.txt" in paths

    def test_disabling_companion_extensions(self):
        entries = [entry("firmware/firmware.ino"), entry("firmware/helper.h")]
        selected = select_content_targets(entries, companion_extensions=frozenset())
        paths = {e["path"] for e in selected}
        assert paths == {"firmware/firmware.ino"}
