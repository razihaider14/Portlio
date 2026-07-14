"""Tests for app.metadata.analyzers.testing.TestPresenceAnalyzer."""

from app.metadata.analyzers.testing import TestPresenceAnalyzer
from app.metadata.models import AnalysisInput

analyzer = TestPresenceAnalyzer()


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def d(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "dir"}


def has_tests(input_: AnalysisInput) -> bool:
    findings = analyzer.analyze(input_)
    assert len(findings) == 1
    assert findings[0].field == "has_tests"
    return findings[0].value


class TestDirectoryConventions:
    def test_detected_by_tests_directory(self):
        assert has_tests(AnalysisInput(entries=[d("tests")]))

    def test_detected_by_dunder_tests_directory(self):
        assert has_tests(AnalysisInput(entries=[d("__tests__")]))

    def test_not_detected_without_evidence(self):
        assert not has_tests(AnalysisInput(entries=[f("main.py")]))


class TestFilenameConventions:
    def test_detected_by_python_test_prefix(self):
        assert has_tests(AnalysisInput(entries=[f("test_main.py")]))

    def test_detected_by_python_test_suffix(self):
        assert has_tests(AnalysisInput(entries=[f("main_test.py")]))

    def test_detected_by_js_test_convention(self):
        assert has_tests(AnalysisInput(entries=[f("app.test.js")]))

    def test_detected_by_go_test_convention(self):
        assert has_tests(AnalysisInput(entries=[f("main_test.go")]))

    def test_detected_by_java_test_convention(self):
        assert has_tests(AnalysisInput(entries=[f("AppTest.java")]))


class TestFrameworkDependency:
    def test_detected_by_pytest_dependency(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "pytest\n"},
        )
        assert has_tests(input_)

    def test_detected_by_jest_dependency(self):
        content = '{"devDependencies": {"jest": "^29.0.0"}}'
        input_ = AnalysisInput(
            entries=[f("package.json")], file_contents={"package.json": content}
        )
        assert has_tests(input_)

    def test_not_detected_without_evidence(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "flask\n"},
        )
        assert not has_tests(input_)


class TestEvidenceAndConfidence:
    def test_evidence_populated_when_detected(self):
        findings = analyzer.analyze(AnalysisInput(entries=[d("tests")]))
        assert findings[0].evidence

    def test_high_confidence_regardless_of_outcome(self):
        positive = analyzer.analyze(AnalysisInput(entries=[d("tests")]))
        negative = analyzer.analyze(AnalysisInput(entries=[f("main.py")]))
        assert positive[0].confidence >= 0.9
        assert negative[0].confidence >= 0.9
