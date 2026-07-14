"""Unit tests for app.metadata.dependency_utils."""

from app.metadata.dependency_utils import has_dependency
from app.metadata.models import AnalysisInput


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


class TestHasDependency:
    def test_true_when_dependency_declared(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "flask==3.0\n"},
        )
        assert has_dependency(input_, "flask")

    def test_false_when_dependency_absent(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "django\n"},
        )
        assert not has_dependency(input_, "flask")

    def test_false_without_file_contents(self):
        input_ = AnalysisInput(entries=[f("requirements.txt")])
        assert not has_dependency(input_, "flask")

    def test_matches_any_of_multiple_package_names(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "streamlit\n"},
        )
        assert has_dependency(input_, "streamlit", "dash")

    def test_false_on_malformed_manifest(self):
        input_ = AnalysisInput(
            entries=[f("package.json")],
            file_contents={"package.json": "{not json"},
        )
        assert not has_dependency(input_, "react")

    def test_ignores_files_with_no_known_parser(self):
        input_ = AnalysisInput(
            entries=[f("notes.txt")],
            file_contents={"notes.txt": "flask"},
        )
        assert not has_dependency(input_, "flask")
