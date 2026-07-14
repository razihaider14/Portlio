"""Unit tests for app.metadata.engine."""

from app.metadata.engine import analyze
from app.metadata.models import AnalysisInput, Finding


class _StubAnalyzer:
    def __init__(self, findings):
        self._findings = findings

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        return self._findings


class TestAnalyze:
    def test_empty_analyzer_list_returns_empty(self):
        input_ = AnalysisInput(entries=[])
        assert analyze(input_, []) == []

    def test_collects_findings_from_single_analyzer(self):
        finding = Finding("has_tests", True, 1.0)
        input_ = AnalysisInput(entries=[])
        result = analyze(input_, [_StubAnalyzer([finding])])
        assert result == [finding]

    def test_flattens_findings_from_multiple_analyzers(self):
        f1 = Finding("has_tests", True, 1.0)
        f2 = Finding("has_docker", False, 1.0)
        input_ = AnalysisInput(entries=[])
        result = analyze(input_, [_StubAnalyzer([f1]), _StubAnalyzer([f2])])
        assert result == [f1, f2]

    def test_analyzer_returning_empty_list_contributes_nothing(self):
        f1 = Finding("has_tests", True, 1.0)
        input_ = AnalysisInput(entries=[])
        result = analyze(input_, [_StubAnalyzer([]), _StubAnalyzer([f1])])
        assert result == [f1]

    def test_preserves_analyzer_order(self):
        f1 = Finding("a", 1, 1.0)
        f2 = Finding("b", 2, 1.0)
        input_ = AnalysisInput(entries=[])
        result = analyze(input_, [_StubAnalyzer([f2]), _StubAnalyzer([f1])])
        assert result == [f2, f1]

    def test_same_input_passed_to_every_analyzer(self):
        received = []

        class _RecordingAnalyzer:
            def analyze(self, input: AnalysisInput) -> list[Finding]:
                received.append(input)
                return []

        input_ = AnalysisInput(entries=[{"path": "a", "name": "a", "type": "file"}])
        analyze(input_, [_RecordingAnalyzer(), _RecordingAnalyzer()])
        assert received == [input_, input_]
