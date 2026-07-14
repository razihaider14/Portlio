"""
Registry of every metadata analyzer.

To add a new metadata analyzer: write a class with an
`analyze(input: AnalysisInput) -> list[Finding]` method (see
app.metadata.models.Analyzer) in its own module here, then add an instance
to ANALYZERS below. No other code needs to change, app.metadata.engine
iterates this list generically.
"""

from app.metadata.analyzers.build_system import BuildSystemAnalyzer
from app.metadata.analyzers.ci_cd import CICDPresenceAnalyzer
from app.metadata.analyzers.containerization import ContainerizationAnalyzer
from app.metadata.analyzers.documentation import DocumentationQualityAnalyzer
from app.metadata.analyzers.hardware_platform import HardwarePlatformAnalyzer
from app.metadata.analyzers.license import LicenseAnalyzer
from app.metadata.analyzers.maturity import MaturityAnalyzer
from app.metadata.analyzers.package_manager import PackageManagerAnalyzer
from app.metadata.analyzers.project_type import ProjectTypeAnalyzer
from app.metadata.analyzers.size_metrics import SizeMetricsAnalyzer
from app.metadata.analyzers.testing import TestPresenceAnalyzer
from app.metadata.models import Analyzer

ANALYZERS: list[Analyzer] = [
    ProjectTypeAnalyzer(),
    HardwarePlatformAnalyzer(),
    DocumentationQualityAnalyzer(),
    TestPresenceAnalyzer(),
    CICDPresenceAnalyzer(),
    ContainerizationAnalyzer(),
    PackageManagerAnalyzer(),
    BuildSystemAnalyzer(),
    LicenseAnalyzer(),
    MaturityAnalyzer(),
    SizeMetricsAnalyzer(),
]
