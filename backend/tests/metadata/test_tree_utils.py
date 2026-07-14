"""Unit tests for app.metadata.tree_utils."""

from app.metadata.tree_utils import (
    directory_names,
    filenames,
    get_content,
    has_directory,
    has_extension,
    has_filename,
    has_glob,
    matching_files,
)


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def d(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "dir"}


class TestFilenames:
    def test_returns_lowercase_file_names_only(self):
        entries = [f("Main.PY"), d("SRC")]
        assert filenames(entries) == {"main.py"}


class TestDirectoryNames:
    def test_returns_lowercase_dir_names_only(self):
        entries = [f("main.py"), d("SRC")]
        assert directory_names(entries) == {"src"}


class TestHasFilename:
    def test_matches_case_insensitively(self):
        assert has_filename([f("README.MD")], "readme.md")

    def test_no_match_for_directory_with_same_name(self):
        assert not has_filename([d("LICENSE")], "LICENSE")

    def test_no_match_when_absent(self):
        assert not has_filename([f("main.py")], "LICENSE")

    def test_matches_any_of_multiple_names(self):
        assert has_filename([f("COPYING")], "LICENSE", "COPYING")


class TestHasExtension:
    def test_matches_simple_extension(self):
        assert has_extension([f("main.py")], ".py")

    def test_matches_multi_part_extension_exactly(self):
        assert has_extension([f("template.pkr.hcl")], ".pkr.hcl")

    def test_does_not_confuse_multi_part_with_single_part(self):
        # A naive rpartition(".") split would see ".hcl" and match; this
        # must not match a plain ".hcl" query against a ".pkr.hcl" file
        # unless ".hcl" is explicitly passed (endswith is intentional).
        assert has_extension([f("template.pkr.hcl")], ".hcl")
        assert not has_extension([f("main.tf")], ".pkr.hcl")

    def test_no_match_when_absent(self):
        assert not has_extension([f("main.py")], ".rs")


class TestHasDirectory:
    def test_matches_case_insensitively(self):
        assert has_directory([d(".GitHub")], ".github")

    def test_no_match_for_file_with_same_name(self):
        assert not has_directory([f(".github")], ".github")


class TestHasGlob:
    def test_matches_pattern(self):
        assert has_glob([f("project.pbxproj")], "*.pbxproj")

    def test_no_match_for_directory(self):
        assert not has_glob([d("project.pbxproj")], "*.pbxproj")

    def test_no_match_when_absent(self):
        assert not has_glob([f("main.py")], "*.pbxproj")


class TestMatchingFiles:
    def test_returns_all_matching_entries(self):
        entries = [f("a.test.js"), f("b.test.js"), f("main.js")]
        result = matching_files(entries, "*.test.js")
        assert {e["name"] for e in result} == {"a.test.js", "b.test.js"}

    def test_returns_empty_list_when_no_match(self):
        assert matching_files([f("main.py")], "*.test.js") == []


class TestGetContent:
    def test_returns_content_for_matching_entry(self):
        entries = [f("README.md")]
        content_map = {"README.md": "# Hello"}
        assert get_content(content_map, entries, "README.md") == "# Hello"

    def test_returns_none_when_entry_absent(self):
        assert get_content({}, [f("main.py")], "README.md") is None

    def test_returns_none_when_content_not_downloaded(self):
        entries = [f("README.md")]
        assert get_content({}, entries, "README.md") is None

    def test_matches_any_of_multiple_names(self):
        entries = [f("README.rst")]
        content_map = {"README.rst": "Hello"}
        assert get_content(content_map, entries, "README.md", "README.rst") == "Hello"
