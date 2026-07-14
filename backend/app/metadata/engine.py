"""
Repository metadata analysis engine.

Pure orchestration, mirroring app.detector.engine: given an AnalysisInput
and a list of Analyzers, run every analyzer and flatten their Findings into
one list. No knowledge of GitHub, HTTP, or the technology detector, and no
side effects, straightforward to test in isolation.
"""

from app.metadata.models import AnalysisInput, Analyzer, Finding


def analyze(input: AnalysisInput, analyzers: list[Analyzer]) -> list[Finding]:
    """
    Run every analyzer against `input` and collect all Findings.

    Analyzers are independent: each is given the full AnalysisInput and may
    return any number of Findings (including zero). There's no AND/OR logic
    between analyzers the way there is between a Rule's matchers in the
    detector, every analyzer always runs, and its Findings are simply
    appended to the result.

    Args:
        input: The repository data available for analysis.
        analyzers: The analyzers to run, in order. Findings are returned in
            the order their analyzer ran and, within an analyzer, in the
            order it produced them.

    Returns:
        A flat list of every Finding produced by every analyzer.
    """
    findings: list[Finding] = []
    for analyzer in analyzers:
        findings.extend(analyzer.analyze(input))
    return findings
