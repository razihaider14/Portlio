"""
Skill aggregation engine.

Mirrors app.detector.engine / app.metadata.engine: pure functions over
already-computed inputs, with no knowledge of GitHub, HTTP, application
state, or how RepositorySkillData was produced. No side effects, no AI,
fully deterministic, straightforward to test in isolation.

Pipeline:
    1. score_repository_practice() : one repository's metadata -> a 0-5
       RepositoryPractice score (see app.aggregator.rules).
    2. build_skill_profiles() : every repository's technologies +
       practice scores -> one SkillProfile per distinct technology,
       aggregated across the whole portfolio, plus one SkillProfile per
       COMPOSITE_SKILL_RULE with sufficient evidence (e.g. "ESP32").
    3. detect_strengths() / detect_weaknesses() : filter/derive
       PortfolioWeakness entries: shallow skills, portfolio-wide practice
       gaps, and narrow category breadth.
    4. generate_recommendations() : walk app.aggregator.rules.
       COMPLEMENT_RULES from every established skill, chaining up to
       MAX_RECOMMENDATION_CHAIN_DEPTH hops, to find missing pairings.
"""

import re
from collections import Counter, defaultdict
from statistics import mean

from app.aggregator.models import (
    PortfolioWeakness,
    ProficiencyTier,
    RepositoryPractice,
    RepositorySkillData,
    SkillProfile,
    SkillRecommendation,
    SkillTier,
    TechnologyObservation,
    WeaknessKind,
)
from app.aggregator.rules import (
    COMPLEMENT_RULES,
    COMPOSITE_SKILL_NAMES,
    COMPOSITE_SKILL_RULES,
    LIMITED_PRACTICE_THRESHOLD,
    MAX_RECOMMENDATION_CHAIN_DEPTH,
    MIN_REPOSITORIES_FOR_BREADTH_JUDGEMENT,
    MIN_REPOSITORIES_FOR_PRACTICE_JUDGEMENT,
    PRACTICE_FACTS,
    PRACTICE_MAX_SCORE,
    SKILL_MAX_SCORE,
    ComplementRule,
    CompositeSkillRule,
    breadth_points,
    confidence_points,
    detection_confidence,
    practice_points,
    proficiency_tier_for,
    tier_for_score,
)
from app.detector.models import EvidenceStrength, RuleCategory

_Occurrence = tuple[str, TechnologyObservation, RepositoryPractice]


def score_repository_practice(metadata: dict) -> RepositoryPractice:
    """
    Compute the 0-5 engineering-practice score for one repository from its
    app.metadata.metadata_analyzer.analyze_repository_metadata() output.
    See app.aggregator.rules.PRACTICE_FACTS for the point rubric. Missing
    keys degrade to "no evidence" (0 points for that line) rather than
    raising, since metadata may be partially unavailable (e.g. no
    repo_metadata fetched).
    """
    evidence: list[str] = []
    score = 0
    for label, check in PRACTICE_FACTS:
        if check(metadata):
            score += 1
            evidence.append(f"{label} evidence present")

    return RepositoryPractice(
        score=score, max_score=PRACTICE_MAX_SCORE, evidence=tuple(evidence)
    )


def _majority_category(categories: list[RuleCategory]) -> RuleCategory:
    """
    The most common category among a skill's occurrences. Ties are broken
    by the category's enum value (alphabetical), for a fully deterministic
    result. In practice a technology's category is fixed by a single
    detector Rule, so this only matters if RULES ever assigns the same
    name two different categories.
    """
    counts = Counter(categories)
    max_count = max(counts.values())
    candidates = sorted(
        (category for category, count in counts.items() if count == max_count),
        key=lambda category: category.value,
    )
    return candidates[0]


_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]")


def _normalize_repository_name(name: str) -> str:
    """Lowercase and strip everything but letters/digits, so 'ESP32-RPi-MQTT' and 'esp_32_rpi_mqtt' compare equal."""
    return _NON_ALPHANUMERIC.sub("", name.lower())


def _repository_name_matches(repository_name: str, keywords: tuple[str, ...]) -> bool:
    """True if any keyword (normalized the same way) is a substring of the normalized repository name."""
    normalized_name = _normalize_repository_name(repository_name)
    return any(
        _normalize_repository_name(keyword) in normalized_name for keyword in keywords
    )


def _composite_occurrences(
    rule: CompositeSkillRule, occurrences: dict[str, list[_Occurrence]]
) -> list[_Occurrence]:
    """
    Every (repository, technology, practice) entry that qualifies as
    evidence for one CompositeSkillRule: drawn from its base technologies'
    own occurrences, filtered by repository-name keyword if the rule has
    any. The composite's own TechnologyObservation reuses the contributing
    base technology's real detector confidence and evidence_strength
    (never invents either), so the composite's average_detector_confidence/
    detection_confidence stay an honest reflection of actual detection.
    """
    matches: list[_Occurrence] = []
    for base_name in rule.base_technologies:
        for repository_name, technology, practice in occurrences.get(base_name, ()):
            if rule.name_keywords and not _repository_name_matches(
                repository_name, rule.name_keywords
            ):
                continue
            composite_observation = TechnologyObservation(
                name=rule.name,
                category=rule.category,
                confidence=technology.confidence,
                evidence_strength=technology.evidence_strength,
            )
            matches.append((repository_name, composite_observation, practice))
    return matches


def _composite_evidence_line(rule: CompositeSkillRule, repository_count: int) -> str:
    base = " or ".join(rule.base_technologies)
    if rule.name_keywords:
        keywords = ", ".join(f"'{keyword}'" for keyword in rule.name_keywords)
        return (
            f"derived from {base} evidence in {repository_count} "
            f"repositor{'y' if repository_count == 1 else 'ies'} whose name "
            f"matches one of: {keywords}"
        )
    return f"derived by rolling up {base} evidence"


def build_skill_profiles(
    repositories: list[RepositorySkillData],
) -> list[SkillProfile]:
    """
    Aggregate every repository's detected technologies into one
    SkillProfile per distinct technology name, scored across the whole
    portfolio, plus one SkillProfile per composite skill in
    app.aggregator.rules.COMPOSITE_SKILL_RULES that has sufficient
    evidence. See app.aggregator.rules for the scoring rubric.

    Each profile carries both the legacy `score`/`tier`/
    `average_detector_confidence` (computed exactly as before Phase 6, for
    backward compatibility) and the newer, additive `detection_confidence`/
    `proficiency_tier` (evidence-strength-weighted; see
    app.aggregator.rules.detection_confidence()/.proficiency_tier_for()).

    Args:
        repositories: One RepositorySkillData per repository, combining
            the detector's and metadata analyzer's output for that repo.

    Returns:
        One SkillProfile per distinct technology name detected in any
        repository (plus qualifying composites), sorted by score
        descending then name ascending.
    """
    occurrences: dict[str, list[_Occurrence]] = defaultdict(list)
    for repo in repositories:
        practice = score_repository_practice(repo.metadata)
        for tech in repo.technologies:
            occurrences[tech.name].append((repo.name, tech, practice))

    composite_rule_by_name: dict[str, CompositeSkillRule] = {}
    for rule in COMPOSITE_SKILL_RULES:
        matches = _composite_occurrences(rule, occurrences)
        distinct_repos = {repository_name for repository_name, _, _ in matches}
        if len(distinct_repos) >= rule.min_repositories:
            occurrences[rule.name] = matches
            composite_rule_by_name[rule.name] = rule

    profiles: list[SkillProfile] = []
    for name, entries in occurrences.items():
        repo_names = tuple(sorted({repo_name for repo_name, _, _ in entries}))
        repository_count = len(repo_names)

        average_confidence = mean(tech.confidence for _, tech, _ in entries)
        average_practice = mean(practice.score for _, _, practice in entries)
        category = _majority_category([tech.category for _, tech, _ in entries])

        breadth = breadth_points(repository_count)
        confidence_score = confidence_points(average_confidence)
        practice_score = practice_points(average_practice)
        total_score = breadth + confidence_score + practice_score

        # Phase 6, additive: detection_confidence/proficiency_tier are
        # computed here from the SAME occurrences but via the
        # evidence-strength-weighted path (see app.aggregator.rules).
        # `average_confidence`/`confidence_score`/`total_score` above, and
        # `tier_for_score(total_score)` below, are left completely
        # untouched -- they keep feeding the legacy `average_detector_
        # confidence`/`score`/`tier` fields exactly as before Phase 6, so
        # no existing consumer of those fields sees any behavior change.
        weighted_confidence = detection_confidence(
            [(tech.confidence, tech.evidence_strength) for _, tech, _ in entries]
        )
        weighted_confidence_score = confidence_points(weighted_confidence)
        proficiency_raw_score = breadth + weighted_confidence_score + practice_score
        has_demonstrated_evidence = any(
            tech.evidence_strength == EvidenceStrength.DEMONSTRATED
            for _, tech, _ in entries
        )
        proficiency_tier = proficiency_tier_for(
            repository_count=repository_count,
            raw_score=proficiency_raw_score,
            has_demonstrated_evidence=has_demonstrated_evidence,
        )

        evidence = [
            f"detected in {repository_count} "
            f"repositor{'y' if repository_count == 1 else 'ies'} "
            f"({breadth} breadth point{'s' if breadth != 1 else ''})",
            f"average detection confidence {average_confidence:.2f} "
            f"({confidence_score} point{'s' if confidence_score != 1 else ''})",
            f"average engineering-practice score "
            f"{average_practice:.1f}/{PRACTICE_MAX_SCORE} "
            f"({practice_score} point{'s' if practice_score != 1 else ''})",
        ]
        is_composite = name in composite_rule_by_name
        if is_composite:
            evidence.append(
                _composite_evidence_line(composite_rule_by_name[name], repository_count)
            )

        profiles.append(
            SkillProfile(
                name=name,
                category=category,
                repository_count=repository_count,
                repositories=repo_names,
                average_detector_confidence=average_confidence,
                average_practice_score=average_practice,
                score=total_score,
                max_score=SKILL_MAX_SCORE,
                tier=tier_for_score(total_score),
                detection_confidence=weighted_confidence,
                proficiency_tier=proficiency_tier,
                evidence=tuple(evidence),
                is_composite=is_composite,
            )
        )

    return sorted(profiles, key=lambda profile: (-profile.score, profile.name))


def detect_strengths(profiles: list[SkillProfile]) -> list[SkillProfile]:
    """
    Skills tiered PROFICIENT or EXPERT: repeated, reliably-detected use
    backed by real engineering practice. Sorted by score descending then
    name.
    """
    strengths = [
        profile
        for profile in profiles
        if profile.tier in (SkillTier.EXPERT, SkillTier.PROFICIENT)
    ]
    return sorted(strengths, key=lambda profile: (-profile.score, profile.name))


def _detect_shallow_skill_weaknesses(
    profiles: list[SkillProfile],
) -> list[PortfolioWeakness]:
    """
    One PortfolioWeakness.SHALLOW_SKILL per skill tiered EXPOSURE: present
    in the portfolio, but with minimal supporting evidence (typically a
    single repository, low detection confidence, and/or no
    engineering-practice signals).
    """
    return [
        PortfolioWeakness(
            kind=WeaknessKind.SHALLOW_SKILL,
            name=profile.name,
            category=profile.category,
            description=(
                f"'{profile.name}' is detected but has minimal supporting "
                f"evidence (score {profile.score}/{profile.max_score})."
            ),
            evidence=profile.evidence,
        )
        for profile in profiles
        if profile.tier == SkillTier.EXPOSURE
    ]


def _detect_limited_practice_weaknesses(
    repositories: list[RepositorySkillData],
) -> list[PortfolioWeakness]:
    """
    One PortfolioWeakness.LIMITED_PRACTICE per app.aggregator.rules.
    PRACTICE_FACTS fact whose portfolio-wide adoption fraction falls below
    LIMITED_PRACTICE_THRESHOLD, provided there are enough repositories
    (MIN_REPOSITORIES_FOR_PRACTICE_JUDGEMENT) to judge fairly. Independent
    of any single skill's score: a portfolio can have zero shallow skills
    and still be missing CI/CD almost everywhere.
    """
    total = len(repositories)
    if total < MIN_REPOSITORIES_FOR_PRACTICE_JUDGEMENT:
        return []

    weaknesses = []
    for label, check in PRACTICE_FACTS:
        satisfying = [repo for repo in repositories if check(repo.metadata)]
        fraction = len(satisfying) / total
        if fraction < LIMITED_PRACTICE_THRESHOLD:
            missing = sorted(
                repo.name for repo in repositories if repo not in satisfying
            )
            weaknesses.append(
                PortfolioWeakness(
                    kind=WeaknessKind.LIMITED_PRACTICE,
                    name=label,
                    category=None,
                    description=(
                        f"Only {len(satisfying)} of {total} repositories "
                        f"({fraction:.0%}) show {label} evidence."
                    ),
                    evidence=tuple(missing),
                )
            )
    return weaknesses


def _detect_limited_breadth_weaknesses(
    profiles: list[SkillProfile],
) -> list[PortfolioWeakness]:
    """
    One PortfolioWeakness.LIMITED_BREADTH per ecosystem category
    represented by exactly one directly-detected technology (composite
    skills are excluded, see COMPOSITE_SKILL_NAMES) despite a combined
    repository footprint of at least
    MIN_REPOSITORIES_FOR_BREADTH_JUDGEMENT, e.g. "Limited Frontend
    Breadth" when every frontend repository only ever uses plain HTML.
    """
    base_profiles = [p for p in profiles if p.name not in COMPOSITE_SKILL_NAMES]
    by_category: dict[RuleCategory, list[SkillProfile]] = defaultdict(list)
    for profile in base_profiles:
        by_category[profile.category].append(profile)

    weaknesses = []
    for category, category_profiles in by_category.items():
        if len(category_profiles) != 1:
            continue
        repository_count = category_profiles[0].repository_count
        if repository_count < MIN_REPOSITORIES_FOR_BREADTH_JUDGEMENT:
            continue
        label = f"{category.value.replace('_', ' ').title()} Breadth"
        weaknesses.append(
            PortfolioWeakness(
                kind=WeaknessKind.LIMITED_BREADTH,
                name=label,
                category=category,
                description=(
                    f"Only 1 distinct {category.value.replace('_', ' ')} "
                    f"skill ('{category_profiles[0].name}') detected across "
                    f"{repository_count} repositories."
                ),
                evidence=category_profiles[0].repositories,
            )
        )
    return weaknesses


def detect_weaknesses(
    repositories: list[RepositorySkillData], profiles: list[SkillProfile]
) -> list[PortfolioWeakness]:
    """
    Every portfolio weakness: shallow skills, portfolio-wide
    engineering-practice gaps, and narrow category breadth. See
    WeaknessKind for what each represents and app.aggregator.rules for the
    exact, documented thresholds. Sorted by kind (shallow skills first,
    since they name a specific skill; then portfolio-wide practice gaps;
    then category breadth) then name.
    """
    weaknesses = (
        _detect_shallow_skill_weaknesses(profiles)
        + _detect_limited_practice_weaknesses(repositories)
        + _detect_limited_breadth_weaknesses(profiles)
    )
    kind_priority = {
        WeaknessKind.SHALLOW_SKILL: 0,
        WeaknessKind.LIMITED_PRACTICE: 1,
        WeaknessKind.LIMITED_BREADTH: 2,
    }
    return sorted(
        weaknesses, key=lambda weakness: (kind_priority[weakness.kind], weakness.name)
    )


def generate_recommendations(
    profiles: list[SkillProfile],
) -> list[SkillRecommendation]:
    """
    Recommend missing complementary skills for every established skill
    (tier above EXPOSURE), walking app.aggregator.rules.COMPLEMENT_RULES
    up to MAX_RECOMMENDATION_CHAIN_DEPTH hops to build multi-step learning
    paths (e.g. established "ESP32" -> missing "FreeRTOS" -> missing
    "ESP-IDF"). A single accidental, low-confidence, single-repository
    detection does not trigger a recommendation (it isn't yet
    "established"), avoiding noisy suggestions. Chain hops themselves are
    hypothetical (not established, not even detected) and are only used to
    look up the *next* rule, never to justify skipping app.aggregator.rules'
    "trigger must be established" check for the root.

    If multiple established root skills (or chains) recommend the same
    missing skill, the recommendation is merged (`based_on` lists every
    triggering root).

    Returns:
        Recommendations sorted by the strongest triggering root's score
        descending, then by recommended skill name.
    """
    scores_by_name = {profile.name: profile.score for profile in profiles}
    present = set(scores_by_name)
    established = {
        profile.name for profile in profiles if profile.tier != SkillTier.EXPOSURE
    }

    rules_by_trigger: dict[str, list[ComplementRule]] = defaultdict(list)
    for rule in COMPLEMENT_RULES:
        rules_by_trigger[rule.trigger].append(rule)

    based_on_by_skill: dict[str, set[str]] = defaultdict(set)
    chain_by_skill: dict[str, tuple[str, ...]] = {}
    rule_by_skill: dict[str, ComplementRule] = {}

    def walk(
        current_trigger: str, chain: tuple[str, ...], depth: int, root: str
    ) -> None:
        if depth > MAX_RECOMMENDATION_CHAIN_DEPTH:
            return
        for rule in rules_by_trigger.get(current_trigger, ()):
            if rule.recommended in chain or rule.recommended == root:
                continue  # cycle guard: never recommend something already on this path
            if any(complement in present for complement in rule.complements):
                continue  # pairing already satisfied; nothing to recommend, chain stops here
            based_on_by_skill[rule.recommended].add(root)
            # Prefer the shortest chain reaching this recommendation,
            # regardless of which root/order discovers it first: `walk` is
            # depth-first and `established` has no defined iteration
            # order, so without this comparison the result (e.g. whether
            # "GitHub Actions" shows chain=() because pytest reaches it
            # directly, or chain=("Ruff",) because Python -> Ruff reaches
            # it first) would depend on set ordering rather than being
            # deterministic.
            existing_chain = chain_by_skill.get(rule.recommended)
            if existing_chain is None or len(chain) < len(existing_chain):
                chain_by_skill[rule.recommended] = chain
                rule_by_skill[rule.recommended] = rule
            walk(rule.recommended, chain + (rule.recommended,), depth + 1, root)

    for skill in sorted(established):
        walk(skill, (), 1, skill)

    recommendations = [
        SkillRecommendation(
            skill=skill,
            category=rule_by_skill[skill].category,
            reason=rule_by_skill[skill].reason,
            based_on=tuple(sorted(roots)),
            chain=chain_by_skill[skill],
        )
        for skill, roots in based_on_by_skill.items()
    ]

    return sorted(
        recommendations,
        key=lambda rec: (
            -max(scores_by_name[root] for root in rec.based_on),
            rec.skill,
        ),
    )
