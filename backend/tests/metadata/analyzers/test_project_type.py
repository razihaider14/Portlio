"""Tests for app.metadata.analyzers.project_type.ProjectTypeAnalyzer."""

from app.metadata.analyzers.project_type import ProjectTypeAnalyzer
from app.metadata.models import AnalysisInput

analyzer = ProjectTypeAnalyzer()


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def d(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "dir"}


def types_of(input_: AnalysisInput) -> set[str]:
    return {finding.value for finding in analyzer.analyze(input_)}


class TestEmbeddedFirmware:
    def test_detected_by_platformio_ini(self):
        input_ = AnalysisInput(entries=[f("platformio.ini")])
        assert "embedded_firmware" in types_of(input_)

    def test_detected_by_ino_file(self):
        input_ = AnalysisInput(entries=[f("sketch.ino")])
        assert "embedded_firmware" in types_of(input_)

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(entries=[f("main.py")])
        assert "embedded_firmware" not in types_of(input_)


class TestPCBHardware:
    def test_detected_by_kicad_pcb(self):
        input_ = AnalysisInput(entries=[f("board.kicad_pcb")])
        assert "pcb_hardware" in types_of(input_)

    def test_detected_by_top_copper_gerber_extension(self):
        input_ = AnalysisInput(entries=[f("Gerber_TopLayer.GTL")])
        assert "pcb_hardware" in types_of(input_)

    def test_detected_by_bottom_copper_gerber_extension(self):
        input_ = AnalysisInput(entries=[f("Gerber_BottomLayer.GBL")])
        assert "pcb_hardware" in types_of(input_)

    def test_detected_by_drill_file_extension(self):
        input_ = AnalysisInput(entries=[f("Drill_PTH_Through.DRL")])
        assert "pcb_hardware" in types_of(input_)

    def test_detected_by_gerber_directory(self):
        input_ = AnalysisInput(entries=[d("Gerber"), f("Gerber/anything.txt")])
        assert "pcb_hardware" in types_of(input_)

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(entries=[f("main.py")])
        assert "pcb_hardware" not in types_of(input_)


class TestMobileApp:
    def test_detected_by_android_manifest(self):
        input_ = AnalysisInput(entries=[f("AndroidManifest.xml")])
        assert "mobile_app" in types_of(input_)

    def test_detected_by_pbxproj(self):
        input_ = AnalysisInput(entries=[f("App.xcodeproj/project.pbxproj")])
        assert "mobile_app" in types_of(input_)

    def test_detected_by_flutter_pubspec_and_dart(self):
        input_ = AnalysisInput(entries=[f("pubspec.yaml"), f("lib/main.dart")])
        assert "mobile_app" in types_of(input_)

    def test_not_detected_by_pubspec_alone_without_dart(self):
        input_ = AnalysisInput(entries=[f("pubspec.yaml")])
        assert "mobile_app" not in types_of(input_)


class TestDesktopApp:
    def test_detected_by_tauri_config(self):
        input_ = AnalysisInput(entries=[f("tauri.conf.json")])
        assert "desktop_app" in types_of(input_)

    def test_detected_by_electron_builder_config(self):
        input_ = AnalysisInput(entries=[f("electron-builder.yml")])
        assert "desktop_app" in types_of(input_)

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(entries=[f("main.py")])
        assert "desktop_app" not in types_of(input_)


class TestBrowserExtension:
    def test_detected_by_manifest_version_key(self):
        input_ = AnalysisInput(
            entries=[f("manifest.json")],
            file_contents={"manifest.json": '{"manifest_version": 3, "name": "x"}'},
        )
        assert "browser_extension" in types_of(input_)

    def test_not_detected_without_manifest_version_key(self):
        input_ = AnalysisInput(
            entries=[f("manifest.json")],
            file_contents={"manifest.json": '{"name": "not-an-extension"}'},
        )
        assert "browser_extension" not in types_of(input_)

    def test_not_detected_without_file_contents(self):
        input_ = AnalysisInput(entries=[f("manifest.json")])
        assert "browser_extension" not in types_of(input_)

    def test_not_detected_on_malformed_json(self):
        input_ = AnalysisInput(
            entries=[f("manifest.json")], file_contents={"manifest.json": "{not json"}
        )
        assert "browser_extension" not in types_of(input_)


class TestAPIBackend:
    def test_detected_by_manage_py(self):
        input_ = AnalysisInput(entries=[f("manage.py")])
        assert "api_backend" in types_of(input_)

    def test_detected_by_artisan(self):
        input_ = AnalysisInput(entries=[f("artisan")])
        assert "api_backend" in types_of(input_)

    def test_detected_by_flask_dependency(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "flask\n"},
        )
        assert "api_backend" in types_of(input_)

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(entries=[f("main.py")])
        assert "api_backend" not in types_of(input_)


class TestCLITool:
    def test_detected_by_npm_bin_entry(self):
        input_ = AnalysisInput(
            entries=[f("package.json")],
            file_contents={"package.json": '{"bin": {"mytool": "./cli.js"}}'},
        )
        assert "cli_tool" in types_of(input_)

    def test_not_detected_without_bin_entry(self):
        input_ = AnalysisInput(
            entries=[f("package.json")],
            file_contents={"package.json": '{"main": "index.js"}'},
        )
        assert "cli_tool" not in types_of(input_)

    def test_detected_by_python_console_scripts(self):
        content = '[project.scripts]\nmytool = "mytool:main"\n'
        input_ = AnalysisInput(
            entries=[f("pyproject.toml")], file_contents={"pyproject.toml": content}
        )
        assert "cli_tool" in types_of(input_)

    def test_detected_by_cargo_bin_target(self):
        content = '[[bin]]\nname = "mytool"\npath = "src/main.rs"\n'
        input_ = AnalysisInput(
            entries=[f("Cargo.toml")], file_contents={"Cargo.toml": content}
        )
        assert "cli_tool" in types_of(input_)

    def test_not_detected_without_evidence(self):
        input_ = AnalysisInput(entries=[f("main.py")])
        assert "cli_tool" not in types_of(input_)


class TestWebsite:
    def test_detected_by_root_index_html(self):
        input_ = AnalysisInput(entries=[f("index.html")])
        assert "website" in types_of(input_)

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(entries=[f("main.py")])
        assert "website" not in types_of(input_)


class TestDashboard:
    def test_detected_by_streamlit_dependency(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "streamlit\n"},
        )
        assert "dashboard" in types_of(input_)

    def test_detected_by_dash_dependency(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "dash\n"},
        )
        assert "dashboard" in types_of(input_)

    def test_detected_by_dashboard_named_html_file(self):
        input_ = AnalysisInput(entries=[f("Dashboard/Dashboard.html")])
        assert "dashboard" in types_of(input_)

    def test_detected_by_dashboard_named_html_file_lowercase(self):
        input_ = AnalysisInput(entries=[f("dashboard/admin_dashboard.html")])
        assert "dashboard" in types_of(input_)

    def test_not_detected_by_unrelated_html_file(self):
        input_ = AnalysisInput(entries=[f("index.html")])
        assert "dashboard" not in types_of(input_)

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "flask\n"},
        )
        assert "dashboard" not in types_of(input_)


class TestLibraryFallback:
    def test_detected_when_manifest_present_with_no_app_markers(self):
        input_ = AnalysisInput(entries=[f("pyproject.toml")])
        assert "library" in types_of(input_)

    def test_not_detected_without_any_manifest(self):
        input_ = AnalysisInput(entries=[f("README.md")])
        assert "library" not in types_of(input_)

    def test_not_detected_when_a_more_specific_type_matched(self):
        # manage.py makes this an api_backend; "library" should not also
        # fire just because pyproject.toml happens to exist alongside it.
        input_ = AnalysisInput(entries=[f("manage.py"), f("pyproject.toml")])
        types = types_of(input_)
        assert "api_backend" in types
        assert "library" not in types


class TestMultipleSimultaneousTypes:
    def test_repo_can_have_several_types_at_once(self):
        input_ = AnalysisInput(
            entries=[f("manage.py"), f("index.html")],
        )
        types = types_of(input_)
        assert "api_backend" in types
        assert "website" in types

    def test_confidence_and_evidence_are_populated(self):
        input_ = AnalysisInput(entries=[f("manage.py")])
        findings = analyzer.analyze(input_)
        assert len(findings) == 1
        assert findings[0].confidence == 0.85
        assert findings[0].evidence
