"""
Unit tests for the detection engine.

Tests the engine in isolation using hand-crafted rules, independent of
the production RULES list. This ensures engine logic regressions are
caught regardless of rule changes.
"""

from app.detector.engine import detect
from app.detector.matchers import HasDependency, HasExtension, HasFilename
from app.detector.models import EvidenceStrength, Entry, MatchResult, Rule, RuleCategory

# Fixtures

PYTHON_RULE = Rule(
    name="Python",
    matchers=[HasExtension(".py")],
    category=RuleCategory.LANGUAGE,
    evidence_strength=EvidenceStrength.DEMONSTRATED,
    confidence=0.95,
    priority=10,
)

DJANGO_RULE = Rule(
    name="Django",
    matchers=[HasFilename("manage.py"), HasExtension(".py")],
    category=RuleCategory.FRAMEWORK,
    evidence_strength=EvidenceStrength.DEMONSTRATED,
    confidence=0.95,
    priority=30,
)

CARGO_RULE = Rule(
    name="Rust",
    matchers=[HasFilename("Cargo.toml")],
    category=RuleCategory.LANGUAGE,
    evidence_strength=EvidenceStrength.DEMONSTRATED,
    confidence=1.0,
    priority=10,
)


def make_entries(*paths: str) -> list[Entry]:
    return [Entry(path=p, name=p.rsplit("/", 1)[-1], type="file") for p in paths]


# Tests


class TestDetectEngine:
    def test_returns_match_for_satisfied_rule(self):
        entries = make_entries("app/main.py")
        results = detect(entries, [PYTHON_RULE])
        assert len(results) == 1
        assert results[0].name == "Python"

    def test_returns_empty_when_no_rules_match(self):
        entries = make_entries("main.js")
        results = detect(entries, [PYTHON_RULE, CARGO_RULE])
        assert results == []

    def test_returns_empty_on_empty_tree(self):
        results = detect([], [PYTHON_RULE, CARGO_RULE])
        assert results == []

    def test_returns_empty_on_empty_rules(self):
        entries = make_entries("main.py")
        results = detect(entries, [])
        assert results == []

    def test_multiple_rules_can_match(self):
        entries = make_entries("manage.py", "app/views.py")
        results = detect(entries, [PYTHON_RULE, DJANGO_RULE, CARGO_RULE])
        names = {r.name for r in results}
        assert names == {"Python", "Django"}

    def test_all_matchers_must_pass(self):
        # DJANGO_RULE requires both manage.py AND .py extension
        entries_no_manage = make_entries("app/views.py")
        results = detect(entries_no_manage, [DJANGO_RULE])
        assert results == []

        entries_with_manage = make_entries("manage.py", "app/views.py")
        results = detect(entries_with_manage, [DJANGO_RULE])
        assert len(results) == 1

    def test_match_result_carries_rule_metadata(self):
        entries = make_entries("Cargo.toml")
        results = detect(entries, [CARGO_RULE])
        assert len(results) == 1
        r = results[0]
        assert isinstance(r, MatchResult)
        assert r.name == "Rust"
        assert r.category == RuleCategory.LANGUAGE
        assert r.confidence == 1.0
        assert r.priority == 10

    def test_result_order_follows_rule_order(self):
        # Engine preserves rule definition order; sorting is the caller's job
        entries = make_entries("main.py", "manage.py", "Cargo.toml")
        rules = [PYTHON_RULE, DJANGO_RULE, CARGO_RULE]
        results = detect(entries, rules)
        assert [r.name for r in results] == ["Python", "Django", "Rust"]


class TestDetectWithFileContents:
    def test_passes_file_contents_through_to_matchers(self):
        rule = Rule(
            name="FastAPI",
            matchers=[HasDependency("fastapi")],
            category=RuleCategory.FRAMEWORK,
            evidence_strength=EvidenceStrength.DECLARED,
            confidence=0.95,
            priority=30,
        )
        entries = make_entries("requirements.txt")
        results = detect(
            entries, [rule], file_contents={"requirements.txt": "fastapi\n"}
        )
        assert [r.name for r in results] == ["FastAPI"]

    def test_content_rule_does_not_match_without_file_contents(self):
        rule = Rule(
            name="FastAPI",
            matchers=[HasDependency("fastapi")],
            category=RuleCategory.FRAMEWORK,
            evidence_strength=EvidenceStrength.DECLARED,
            confidence=0.95,
            priority=30,
        )
        entries = make_entries("requirements.txt")
        results = detect(entries, [rule])
        assert results == []

    def test_mixes_tree_and_content_matchers_in_same_rule(self):
        rule = Rule(
            name="Python FastAPI project",
            matchers=[HasExtension(".py"), HasDependency("fastapi")],
            category=RuleCategory.FRAMEWORK,
            evidence_strength=EvidenceStrength.DEMONSTRATED,
            confidence=0.9,
            priority=30,
        )
        entries = make_entries("main.py", "requirements.txt")
        results = detect(
            entries, [rule], file_contents={"requirements.txt": "fastapi\n"}
        )
        assert [r.name for r in results] == ["Python FastAPI project"]


class TestEvidenceStrengthPropagation:
    """Phase 6: Rule.evidence_strength must flow through detect() onto MatchResult unchanged."""

    def test_evidence_strength_copied_onto_match_result(self):
        rule = Rule(
            name="Django",
            matchers=[HasFilename("manage.py")],
            category=RuleCategory.FRAMEWORK,
            evidence_strength=EvidenceStrength.DEMONSTRATED,
            confidence=0.95,
            priority=30,
        )
        entries = make_entries("manage.py")
        results = detect(entries, [rule])
        assert results[0].evidence_strength is EvidenceStrength.DEMONSTRATED

    def test_declared_evidence_strength_copied_onto_match_result(self):
        rule = Rule(
            name="FastAPI",
            matchers=[HasDependency("fastapi")],
            category=RuleCategory.FRAMEWORK,
            evidence_strength=EvidenceStrength.DECLARED,
            confidence=0.9,
            priority=30,
        )
        entries = make_entries("requirements.txt")
        results = detect(
            entries, [rule], file_contents={"requirements.txt": "fastapi\n"}
        )
        assert results[0].evidence_strength is EvidenceStrength.DECLARED
