"""Tests for app.metadata.analyzers.size_metrics.SizeMetricsAnalyzer."""

from app.metadata.analyzers.size_metrics import SizeMetricsAnalyzer
from app.metadata.models import AnalysisInput

analyzer = SizeMetricsAnalyzer()


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def d(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "dir"}


def metrics_value(input_: AnalysisInput) -> dict:
    findings = analyzer.analyze(input_)
    assert len(findings) == 1
    assert findings[0].field == "size_metrics"
    return findings[0].value


class TestFileAndDirectoryCounts:
    def test_counts_files_and_directories_separately(self):
        entries = [f("main.py"), f("utils.py"), d("src")]
        value = metrics_value(AnalysisInput(entries=entries))
        assert value["total_files"] == 2
        assert value["total_directories"] == 1

    def test_empty_repo(self):
        value = metrics_value(AnalysisInput(entries=[]))
        assert value["total_files"] == 0
        assert value["total_directories"] == 0


class TestExtensionBreakdown:
    def test_counts_files_by_extension(self):
        entries = [f("a.py"), f("b.py"), f("c.js")]
        value = metrics_value(AnalysisInput(entries=entries))
        assert value["file_count_by_extension"] == {".py": 2, ".js": 1}

    def test_files_without_extension_are_excluded(self):
        entries = [f("Makefile"), f("main.py")]
        value = metrics_value(AnalysisInput(entries=entries))
        assert value["file_count_by_extension"] == {".py": 1}

    def test_limits_to_top_n_extensions(self):
        entries = [f(f"file{i}.ext{i}") for i in range(15)]
        value = metrics_value(AnalysisInput(entries=entries))
        assert len(value["file_count_by_extension"]) <= 10


class TestMaxDirectoryDepth:
    def test_computes_deepest_nesting(self):
        entries = [f("a/b/c/deep.py"), f("shallow.py")]
        value = metrics_value(AnalysisInput(entries=entries))
        assert value["max_directory_depth"] == 3

    def test_zero_depth_for_root_only_files(self):
        entries = [f("main.py")]
        value = metrics_value(AnalysisInput(entries=entries))
        assert value["max_directory_depth"] == 0


class TestRepoSizeFromAPI:
    def test_pulls_size_from_repo_metadata(self):
        input_ = AnalysisInput(entries=[], repo_metadata={"size": 4096})
        value = metrics_value(input_)
        assert value["repo_size_kb"] == 4096

    def test_none_when_unavailable(self):
        value = metrics_value(AnalysisInput(entries=[]))
        assert value["repo_size_kb"] is None


class TestConfidenceIsAlwaysExact:
    def test_confidence_is_always_1(self):
        findings = analyzer.analyze(AnalysisInput(entries=[f("main.py")]))
        assert findings[0].confidence == 1.0
