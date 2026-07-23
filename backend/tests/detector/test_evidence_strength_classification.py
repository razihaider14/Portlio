"""
Phase 6: sanity checks over the evidence_strength classification applied
to the entire production RULES table in app.detector.rules.

These are deliberately coarse, structural checks (every rule has a valid
EvidenceStrength; a Rule whose only matcher is HasDependency is never
DEMONSTRATED) rather than an assertion pinning every one of the 172 rules'
exact classification -- that would be a change-detector test, breaking on
every future rule addition/edit rather than actually guarding the
methodology described in app.detector.rules' module docstring (see also
the Phase 6 execution notes: classification was applied via a per-matcher-
type default plus a small, reviewed override list, not rule-by-rule by
hand).
"""

from app.detector.matchers import AllOf, AnyOf, HasDependency
from app.detector.models import EvidenceStrength
from app.detector.rules import RULES


def _flatten_matchers(matcher):
    if isinstance(matcher, (AnyOf, AllOf)):
        flattened = []
        for sub in matcher.matchers:
            flattened.extend(_flatten_matchers(sub))
        return flattened
    return [matcher]


class TestEvidenceStrengthClassificationCoverage:
    def test_every_rule_has_a_valid_evidence_strength(self):
        for rule in RULES:
            assert isinstance(
                rule.evidence_strength, EvidenceStrength
            ), f"Rule '{rule.name}' has no valid evidence_strength"

    def test_rule_names_are_unique(self):
        # Not new behavior, but a precondition the classification script
        # (and the detectability validator, see app.validation.detectability)
        # both implicitly rely on: names index the table.
        names = [rule.name for rule in RULES]
        assert len(names) == len(set(names))


class TestEvidenceStrengthClassificationSpotChecks:
    """
    A handful of specific, human-reviewed classifications from the actual
    Phase 6 rollout, kept as regression guards against an accidental
    reclassification (e.g. someone "simplifying" the FreeRTOS rule back to
    a plain DEMONSTRATED default without re-reading why it isn't one).
    """

    def _rule(self, name: str):
        matches = [rule for rule in RULES if rule.name == name]
        assert matches, f"no rule named '{name}' found in RULES"
        return matches[0]

    def test_pure_dependency_only_rules_are_declared(self):
        # A representative sample of rules whose only matcher is
        # HasDependency -- listing a package is not proof it's used.
        for name in ("React", "Flask", "pytest", "TensorFlow", "pandas"):
            rule = self._rule(name)
            flat = _flatten_matchers(rule.matchers[0])
            assert all(isinstance(m, HasDependency) for m in flat), (
                f"expected '{name}' to be pure-HasDependency for this test's "
                "assumption to hold"
            )
            assert rule.evidence_strength is EvidenceStrength.DECLARED

    def test_freertos_is_configured_not_demonstrated(self):
        # FreeRTOS is detected via a vendored config header or kernel
        # directory -- real setup, but not proof the surrounding code
        # actually calls the RTOS API (see the rule's own comment in
        # app.detector.rules for the full rationale, including why
        # symbol-level DEMONSTRATED detection isn't attempted yet).
        assert self._rule("FreeRTOS").evidence_strength is EvidenceStrength.CONFIGURED

    def test_build_file_mentions_are_declared_despite_content_matcher(self):
        # JUnit/Quarkus/Micronaut are matched via HasFileContent (a
        # substring check inside pom.xml/build.gradle), which defaults to
        # DEMONSTRATED under the generic per-matcher-type rule -- but
        # semantically these are build-file dependency mentions, exactly
        # equivalent to a manifest entry, just detected differently. The
        # override list corrects this; this test guards the correction.
        for name in ("JUnit", "Quarkus", "Micronaut"):
            assert self._rule(name).evidence_strength is EvidenceStrength.DECLARED

    def test_a_dedicated_config_file_signal_is_at_least_configured(self):
        # Ruff is detected via a dedicated ruff.toml OR a pyproject.toml
        # [tool.ruff] section -- real, deliberate setup, not a bare
        # dependency line.
        rule = self._rule("Ruff")
        assert rule.evidence_strength in (
            EvidenceStrength.CONFIGURED,
            EvidenceStrength.DEMONSTRATED,
        )
