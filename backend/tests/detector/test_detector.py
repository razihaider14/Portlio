"""
Tests for the detector's public API handling of the optional
"file_contents" key on the repository dict.

Rule-level behavior is covered in test_rules.py; these tests exercise
detect_technologies()/detect_technologies_detailed() directly against a
hand-crafted rule so they don't depend on the production RULES list.
"""

from tests.conftest import f, repo

from app.detector import detector as detector_module
from app.detector.detector import detect_technologies, detect_technologies_detailed
from app.detector.matchers import HasDependency
from app.detector.models import EvidenceStrength, Rule, RuleCategory

CUSTOM_RULE = Rule(
    name="Custom Content Rule",
    matchers=[HasDependency("some-package")],
    category=RuleCategory.FRAMEWORK,
    evidence_strength=EvidenceStrength.DECLARED,
    confidence=0.9,
    priority=30,
)


class TestDetectTechnologiesFileContents:
    def test_ignores_missing_file_contents_key(self):
        repository = repo(f("requirements.txt"))
        assert "file_contents" not in repository
        result = detect_technologies(repository)
        assert isinstance(result, list)

    def test_empty_file_contents_behaves_like_absent(self):
        repository = repo(f("requirements.txt"), file_contents={})
        result_empty = detect_technologies(repository)
        repository_absent = repo(f("requirements.txt"))
        result_absent = detect_technologies(repository_absent)
        assert result_empty == result_absent

    def test_detailed_results_also_receive_file_contents(self, monkeypatch):
        monkeypatch.setattr(detector_module, "RULES", [CUSTOM_RULE])
        repository = repo(
            f("requirements.txt"),
            file_contents={"requirements.txt": "some-package==1.0\n"},
        )
        results = detect_technologies_detailed(repository)
        assert [r.name for r in results] == ["Custom Content Rule"]

    def test_sorted_list_form_also_receives_file_contents(self, monkeypatch):
        monkeypatch.setattr(detector_module, "RULES", [CUSTOM_RULE])
        repository = repo(
            f("requirements.txt"),
            file_contents={"requirements.txt": "some-package==1.0\n"},
        )
        assert detect_technologies(repository) == ["Custom Content Rule"]

    def test_no_match_without_file_contents(self, monkeypatch):
        monkeypatch.setattr(detector_module, "RULES", [CUSTOM_RULE])
        repository = repo(f("requirements.txt"))
        assert detect_technologies(repository) == []
