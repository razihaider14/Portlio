"""
Infers the project's type(s) from deterministic filesystem and dependency
markers.

A repository can genuinely be more than one type at once (an API backend
that's also Dockerized and ships a CLI admin tool), so this analyzer emits
one Finding per matched type rather than forcing a single label, callers
that want just the top candidate can sort by confidence.

Every check here is either an unambiguous, tool-exclusive config filename or
a declared dependency (which is why AnalysisInput.file_contents matters for
several of these); nothing is inferred from prose, naming conventions, or
directory layout alone.
"""

import json
import tomllib

from app.metadata.dependency_utils import has_dependency
from app.metadata.models import AnalysisInput, Finding
from app.metadata.tree_utils import has_directory, has_extension, has_filename, has_glob


def _is_embedded_firmware(input: AnalysisInput) -> Finding | None:
    markers = {
        "platformio.ini": has_filename(input.entries, "platformio.ini"),
        "sdkconfig": has_filename(input.entries, "sdkconfig"),
        "west.yml": has_filename(input.entries, "west.yml"),
        "mbed_app.json": has_filename(input.entries, "mbed_app.json"),
        ".ino file": has_extension(input.entries, ".ino"),
        ".ioc file": has_extension(input.entries, ".ioc"),
    }
    hit = [name for name, matched in markers.items() if matched]
    if not hit:
        return None
    return Finding(
        "project_types", "embedded_firmware", 0.9, tuple(f"found {h}" for h in hit)
    )


def _is_pcb_hardware(input: AnalysisInput) -> Finding | None:
    markers = {
        ".kicad_pro": has_extension(input.entries, ".kicad_pro"),
        ".kicad_pcb": has_extension(input.entries, ".kicad_pcb"),
        ".sch": has_extension(input.entries, ".sch"),
        ".brd": has_extension(input.entries, ".brd"),
        # Extended Gerber (RS-274X) layer extensions, as exported by KiCad,
        # EasyEDA, Eagle, and PCB fab houses (JLCPCB/PCBWay convention):
        # copper (.gtl/.gbl), soldermask (.gts/.gbs), silkscreen (.gto/.gbo),
        # keep-out/outline (.gko), mechanical (.gml), and drill (.drl).
        # ".gbr" is also checked as the generic/ambiguous fallback name some
        # tools use instead of per-layer extensions.
        "Gerber layer files": any(
            has_extension(input.entries, ext)
            for ext in (
                ".gbr",
                ".gtl",
                ".gbl",
                ".gts",
                ".gbs",
                ".gto",
                ".gbo",
                ".gko",
                ".gml",
                ".drl",
            )
        ),
        # A directory literally named "gerber" is a strong, common
        # convention for a folder of exported manufacturing files.
        "gerber/ directory": has_directory(input.entries, "gerber"),
    }
    hit = [name for name, matched in markers.items() if matched]
    if not hit:
        return None
    return Finding(
        "project_types", "pcb_hardware", 0.9, tuple(f"found {h}" for h in hit)
    )


def _is_mobile_app(input: AnalysisInput) -> Finding | None:
    markers = {
        "AndroidManifest.xml": has_filename(input.entries, "AndroidManifest.xml"),
        "pubspec.yaml + .dart files": has_filename(input.entries, "pubspec.yaml")
        and has_extension(input.entries, ".dart"),
        "metro.config.*": has_glob(input.entries, "metro.config.*"),
        "Xcode project.pbxproj": has_glob(input.entries, "*.pbxproj"),
    }
    hit = [name for name, matched in markers.items() if matched]
    if not hit:
        return None
    return Finding(
        "project_types", "mobile_app", 0.85, tuple(f"found {h}" for h in hit)
    )


def _is_desktop_app(input: AnalysisInput) -> Finding | None:
    markers = {
        "electron-builder config": has_glob(input.entries, "electron-builder.*"),
        "tauri.conf.json": has_filename(input.entries, "tauri.conf.json"),
    }
    hit = [name for name, matched in markers.items() if matched]
    if not hit:
        return None
    return Finding(
        "project_types", "desktop_app", 0.9, tuple(f"found {h}" for h in hit)
    )


def _is_browser_extension(input: AnalysisInput) -> Finding | None:
    if not has_filename(input.entries, "manifest.json"):
        return None
    for entry in input.entries:
        if entry.get("type") == "file" and entry["name"].lower() == "manifest.json":
            content = input.file_contents.get(entry["path"])
            if not content:
                continue
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(data, dict) and "manifest_version" in data:
                return Finding(
                    "project_types",
                    "browser_extension",
                    0.85,
                    ('manifest.json declares "manifest_version"',),
                )
    return None


_BACKEND_FRAMEWORK_PACKAGES = (
    "flask",
    "fastapi",
    "django",
    "express",
    "@nestjs/core",
    "gin",
    "echo",
    "fiber",
    "actix-web",
    "rocket",
    "symfony/framework-bundle",
    "laravel/framework",
    "sinatra",
    "rails",
)


def _is_api_backend(input: AnalysisInput) -> Finding | None:
    evidence = []
    if has_filename(input.entries, "manage.py"):
        evidence.append("found manage.py (Django)")
    if has_filename(input.entries, "artisan"):
        evidence.append("found artisan (Laravel)")
    if has_filename(input.entries, "routes.rb"):
        evidence.append("found routes.rb (Rails)")
    matched_packages = [
        p for p in _BACKEND_FRAMEWORK_PACKAGES if has_dependency(input, p)
    ]
    evidence.extend(f'declares dependency on "{p}"' for p in matched_packages)
    if not evidence:
        return None
    return Finding("project_types", "api_backend", 0.85, tuple(evidence))


def _has_npm_bin_entry(input: AnalysisInput) -> bool:
    for entry in input.entries:
        if entry.get("type") == "file" and entry["name"].lower() == "package.json":
            content = input.file_contents.get(entry["path"])
            if not content:
                continue
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(data, dict) and "bin" in data:
                return True
    return False


def _has_python_console_scripts(input: AnalysisInput) -> bool:
    for entry in input.entries:
        if entry.get("type") == "file" and entry["name"].lower() == "pyproject.toml":
            content = input.file_contents.get(entry["path"])
            if not content:
                continue
            try:
                data = tomllib.loads(content)
            except tomllib.TOMLDecodeError:
                continue
            if data.get("project", {}).get("scripts") or data.get("tool", {}).get(
                "poetry", {}
            ).get("scripts"):
                return True
    return False


def _has_cargo_bin_target(input: AnalysisInput) -> bool:
    for entry in input.entries:
        if entry.get("type") == "file" and entry["name"].lower() == "cargo.toml":
            content = input.file_contents.get(entry["path"])
            if content and "[[bin]]" in content:
                return True
    return False


def _is_cli_tool(input: AnalysisInput) -> Finding | None:
    evidence = []
    if _has_npm_bin_entry(input):
        evidence.append('package.json declares a "bin" entry')
    if _has_python_console_scripts(input):
        evidence.append("pyproject.toml declares console scripts")
    if _has_cargo_bin_target(input):
        evidence.append("Cargo.toml declares a [[bin]] target")
    if not evidence:
        return None
    return Finding("project_types", "cli_tool", 0.85, tuple(evidence))


def _is_website(input: AnalysisInput) -> Finding | None:
    if has_filename(input.entries, "index.html"):
        return Finding(
            "project_types", "website", 0.75, ("found index.html at repository root",)
        )
    return None


def _is_dashboard(input: AnalysisInput) -> Finding | None:
    evidence = []

    matched_deps = [p for p in ("streamlit", "dash") if has_dependency(input, p)]
    evidence.extend(f'declares dependency on "{p}"' for p in matched_deps)

    # A directory or HTML file literally named "dashboard" is a strong,
    # exact-text naming convention, common for Node-RED / IoT projects
    # that ship a hand-built HTML control panel rather than a Python
    # dashboard framework. Checked as a path substring so it also catches
    # "Dashboard/Dashboard.html" and "dashboard/admin_dashboard.html".
    dashboard_paths = sorted(
        {
            e["path"]
            for e in input.entries
            if e.get("type") == "file"
            and e["name"].lower().endswith(".html")
            and "dashboard" in e["path"].lower()
        }
    )
    evidence.extend(f"found dashboard HTML file: {p}" for p in dashboard_paths[:3])

    if not evidence:
        return None
    return Finding("project_types", "dashboard", 0.75, tuple(evidence))


_LIBRARY_MANIFESTS = ("package.json", "pyproject.toml", "setup.py", "Cargo.toml")


def _is_library(input: AnalysisInput, app_like_types: set[str]) -> Finding | None:
    # Only offered as a fallback: a package manifest exists, but none of the
    # more specific, higher-confidence "this is a runnable app" signals
    # matched. Lower confidence because this is inferred by absence, not by
    # a positive marker, honestly reflected in the reduced confidence.
    if app_like_types:
        return None
    if not has_filename(input.entries, *_LIBRARY_MANIFESTS):
        return None
    return Finding(
        "project_types",
        "library",
        0.6,
        ("found a package manifest with no CLI, API, or app entrypoint markers",),
    )


class ProjectTypeAnalyzer:
    """Infers one or more project types from deterministic markers."""

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        findings = [
            f
            for f in (
                _is_embedded_firmware(input),
                _is_pcb_hardware(input),
                _is_mobile_app(input),
                _is_desktop_app(input),
                _is_browser_extension(input),
                _is_api_backend(input),
                _is_cli_tool(input),
                _is_website(input),
                _is_dashboard(input),
            )
            if f is not None
        ]
        app_like = {f.value for f in findings}
        library_finding = _is_library(input, app_like)
        if library_finding is not None:
            findings.append(library_finding)
        return findings
