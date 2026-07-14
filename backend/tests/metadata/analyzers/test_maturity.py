"""Tests for app.metadata.analyzers.maturity.MaturityAnalyzer."""

from datetime import datetime, timedelta, timezone

from app.metadata.analyzers.maturity import MaturityAnalyzer
from app.metadata.models import AnalysisInput

analyzer = MaturityAnalyzer()


def maturity_value(repo_metadata: dict) -> dict:
    input_ = AnalysisInput(entries=[], repo_metadata=repo_metadata)
    findings = analyzer.analyze(input_)
    assert len(findings) == 1
    assert findings[0].field == "maturity"
    return findings[0].value


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TestExactMetrics:
    def test_pulls_stars_forks_issues_directly(self):
        value = maturity_value(
            {"stargazers_count": 100, "forks_count": 10, "open_issues_count": 3}
        )
        assert value["stars"] == 100
        assert value["forks"] == 10
        assert value["open_issues"] == 3

    def test_defaults_to_zero_when_fields_missing(self):
        value = maturity_value({})
        assert value["stars"] == 0
        assert value["forks"] == 0
        assert value["open_issues"] == 0


class TestArchivedAndForkFlags:
    def test_archived_tier(self):
        value = maturity_value({"archived": True})
        assert value["is_archived"] is True
        assert value["maturity_tier"] == "archived"

    def test_fork_tier(self):
        value = maturity_value({"fork": True})
        assert value["is_fork"] is True
        assert value["maturity_tier"] == "fork"

    def test_archived_takes_priority_over_fork(self):
        value = maturity_value({"archived": True, "fork": True})
        assert value["maturity_tier"] == "archived"


class TestAgeAndActivityTiers:
    def test_experimental_tier_for_new_repo(self):
        now = datetime.now(timezone.utc)
        value = maturity_value(
            {"created_at": iso(now - timedelta(days=5)), "pushed_at": iso(now)}
        )
        assert value["maturity_tier"] == "experimental"

    def test_stale_tier_for_long_untouched_repo(self):
        now = datetime.now(timezone.utc)
        value = maturity_value(
            {
                "created_at": iso(now - timedelta(days=1000)),
                "pushed_at": iso(now - timedelta(days=800)),
            }
        )
        assert value["maturity_tier"] == "stale"

    def test_mature_tier_for_old_actively_maintained_repo(self):
        now = datetime.now(timezone.utc)
        value = maturity_value(
            {
                "created_at": iso(now - timedelta(days=800)),
                "pushed_at": iso(now - timedelta(days=30)),
            }
        )
        assert value["maturity_tier"] == "mature"

    def test_active_tier_for_recent_but_not_yet_mature_repo(self):
        now = datetime.now(timezone.utc)
        value = maturity_value(
            {
                "created_at": iso(now - timedelta(days=100)),
                "pushed_at": iso(now - timedelta(days=10)),
            }
        )
        assert value["maturity_tier"] == "active"

    def test_unknown_tier_without_timestamps(self):
        value = maturity_value({})
        assert value["maturity_tier"] == "unknown"
        assert value["age_days"] is None
        assert value["days_since_last_push"] is None


class TestConfidence:
    def test_lower_confidence_without_timestamps(self):
        input_ = AnalysisInput(entries=[], repo_metadata={})
        findings = analyzer.analyze(input_)
        assert findings[0].confidence < 0.85

    def test_higher_confidence_with_timestamps(self):
        now = datetime.now(timezone.utc)
        input_ = AnalysisInput(
            entries=[],
            repo_metadata={"created_at": iso(now), "pushed_at": iso(now)},
        )
        findings = analyzer.analyze(input_)
        assert findings[0].confidence >= 0.8

    def test_handles_malformed_timestamp_gracefully(self):
        value = maturity_value(
            {"created_at": "not-a-date", "pushed_at": "also-not-a-date"}
        )
        assert value["age_days"] is None
        assert value["maturity_tier"] == "unknown"
