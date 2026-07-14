"""Unit tests for app.metadata.models."""

import pytest

from app.metadata.models import AnalysisInput, Finding


class TestAnalysisInput:
    def test_defaults_to_empty_file_contents_and_repo_metadata(self):
        input_ = AnalysisInput(
            entries=[{"path": "a.py", "name": "a.py", "type": "file"}]
        )
        assert input_.file_contents == {}
        assert input_.repo_metadata == {}

    def test_accepts_all_fields(self):
        input_ = AnalysisInput(
            entries=[{"path": "a.py", "name": "a.py", "type": "file"}],
            file_contents={"a.py": "print(1)"},
            repo_metadata={"stargazers_count": 5},
        )
        assert input_.file_contents == {"a.py": "print(1)"}
        assert input_.repo_metadata == {"stargazers_count": 5}


class TestFinding:
    def test_constructs_with_valid_confidence(self):
        finding = Finding(field="has_tests", value=True, confidence=0.9)
        assert finding.field == "has_tests"
        assert finding.value is True
        assert finding.confidence == 0.9
        assert finding.evidence == ()

    def test_accepts_evidence_tuple(self):
        finding = Finding(
            field="has_tests", value=True, confidence=1.0, evidence=("found tests/",)
        )
        assert finding.evidence == ("found tests/",)

    def test_rejects_confidence_above_one(self):
        with pytest.raises(ValueError):
            Finding(field="x", value=1, confidence=1.1)

    def test_rejects_confidence_below_zero(self):
        with pytest.raises(ValueError):
            Finding(field="x", value=1, confidence=-0.1)

    def test_accepts_confidence_boundary_values(self):
        Finding(field="x", value=1, confidence=0.0)
        Finding(field="x", value=1, confidence=1.0)
