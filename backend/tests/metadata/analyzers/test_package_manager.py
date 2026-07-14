"""Tests for app.metadata.analyzers.package_manager.PackageManagerAnalyzer."""

from app.metadata.analyzers.package_manager import PackageManagerAnalyzer
from app.metadata.models import AnalysisInput

analyzer = PackageManagerAnalyzer()


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def managers_of(input_: AnalysisInput) -> set[str]:
    return {finding.value for finding in analyzer.analyze(input_)}


class TestEachPackageManager:
    def test_poetry(self):
        assert "Poetry" in managers_of(AnalysisInput(entries=[f("poetry.lock")]))

    def test_pipenv(self):
        assert "Pipenv" in managers_of(AnalysisInput(entries=[f("Pipfile.lock")]))

    def test_uv(self):
        assert "uv" in managers_of(AnalysisInput(entries=[f("uv.lock")]))

    def test_pip(self):
        assert "pip" in managers_of(AnalysisInput(entries=[f("requirements.txt")]))

    def test_npm(self):
        assert "npm" in managers_of(AnalysisInput(entries=[f("package-lock.json")]))

    def test_yarn(self):
        assert "Yarn" in managers_of(AnalysisInput(entries=[f("yarn.lock")]))

    def test_pnpm(self):
        assert "pnpm" in managers_of(AnalysisInput(entries=[f("pnpm-lock.yaml")]))

    def test_bun(self):
        assert "Bun" in managers_of(AnalysisInput(entries=[f("bun.lockb")]))

    def test_cargo(self):
        assert "Cargo" in managers_of(AnalysisInput(entries=[f("Cargo.lock")]))

    def test_go_modules(self):
        assert "Go Modules" in managers_of(AnalysisInput(entries=[f("go.sum")]))

    def test_composer(self):
        assert "Composer" in managers_of(AnalysisInput(entries=[f("composer.lock")]))

    def test_bundler(self):
        assert "Bundler" in managers_of(AnalysisInput(entries=[f("Gemfile.lock")]))

    def test_cocoapods(self):
        assert "CocoaPods" in managers_of(AnalysisInput(entries=[f("Podfile.lock")]))

    def test_nuget(self):
        assert "NuGet" in managers_of(AnalysisInput(entries=[f("nuget.config")]))

    def test_conan(self):
        assert "Conan" in managers_of(AnalysisInput(entries=[f("conanfile.txt")]))

    def test_vcpkg(self):
        assert "vcpkg" in managers_of(AnalysisInput(entries=[f("vcpkg.json")]))


class TestNoPackageManager:
    def test_empty_when_no_markers_present(self):
        assert managers_of(AnalysisInput(entries=[f("main.py")])) == set()


class TestMultiplePackageManagers:
    def test_detects_several_simultaneously(self):
        entries = [f("poetry.lock"), f("yarn.lock")]
        managers = managers_of(AnalysisInput(entries=entries))
        assert "Poetry" in managers
        assert "Yarn" in managers
