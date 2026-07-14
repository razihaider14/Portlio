"""
Infers hardware platforms (microcontrollers, SBCs) from deterministic
filesystem, dependency, and config-content markers.

A repository can target more than one platform (a PlatformIO project with
multiple [env:] boards), so this emits one Finding per detected platform.
PlatformIO's platformio.ini board IDs are matched by exact substring against
a small, well-known mapping table, not fuzzy guessing, since PlatformIO's
`board = <id>` line format and board ID vocabulary are stable and documented.

Important caveat about .ino files: the Arduino *sketch format* (.ino) is not
exclusive to classic AVR Arduino boards, the ESP32 and ESP8266 Arduino
cores also compile .ino files, and are extremely common in IoT/WiFi/
Bluetooth projects. So ".ino present" alone is only evidence of "the Arduino
framework/IDE is used", not of which chip. This analyzer therefore looks for
chip-specific evidence first (ESP32/ESP8266-exclusive library includes,
scanned from every downloaded .ino, .cpp, and .h file, since a
professionally structured sketch often puts the actual board-API usage in
companion source files rather than the .ino entry point itself; see
app.github.content_targets' companion-file selection), an "esp32"/"esp8266"
path segment or repo name, and only falls back to a generic, lower-confidence
"Arduino" platform label when no chip-specific signal is available.
"""

from app.metadata.dependency_utils import has_dependency
from app.metadata.models import AnalysisInput, Finding
from app.metadata.tree_utils import get_content, has_extension, has_filename

# PlatformIO board-id substrings that unambiguously identify a platform.
# Checked against the *board* line content of platformio.ini, not free text.
_PLATFORMIO_BOARD_MARKERS: tuple[tuple[str, str], ...] = (
    ("esp32", "ESP32"),
    ("esp8266", "ESP8266"),
    ("d1_mini", "ESP8266"),
    ("nodemcuv2", "ESP8266"),
    ("rpipico", "RP2040"),
    ("pico", "RP2040"),
    ("uno", "Arduino"),
    ("nano", "Arduino"),
    ("mega", "Arduino"),
    ("leonardo", "Arduino"),
    ("stm32", "STM32"),
    ("bluepill", "STM32"),
)

# Firmware source extensions worth scanning for chip-exclusive markers.
# Sketch (.ino) plus the companion C/C++ files a multi-file sketch typically
# splits its real logic into.
_FIRMWARE_SOURCE_EXTENSIONS = (".ino", ".cpp", ".h", ".hpp", ".c")

# Library #include names and API calls that only exist in the ESP32 Arduino
# core (not in classic AVR Arduino, and not shared with the ESP8266 core).
_ESP32_INO_MARKERS = (
    "bluetoothserial.h",
    "esp_now.h",
    "esp_wifi.h",
    "esp_camera.h",
    "esp_task_wdt.h",
    "esp_sleep.h",
    "esp_system.h",
    "espmdns.h",
    "preferences.h",
    "ledcwrite(",
    "ledcsetup(",
)

# Library #include names that only exist in the ESP8266 Arduino core.
_ESP8266_INO_MARKERS = (
    "esp8266wifi.h",
    "esp8266mdns.h",
    "esp8266httpclient.h",
    "esp8266webserver.h",
)


def _firmware_content_markers(input: AnalysisInput) -> list[Finding]:
    """
    Scan every downloaded firmware source file (.ino and its companion
    .cpp/.h/.c files) for chip-exclusive library includes.
    """
    findings = []
    for entry in input.entries:
        if entry.get("type") != "file":
            continue
        if not entry.get("name", "").lower().endswith(_FIRMWARE_SOURCE_EXTENSIONS):
            continue
        content = input.file_contents.get(entry["path"])
        if not content:
            continue
        lowered = content.lower()
        esp32_hit = [m for m in _ESP32_INO_MARKERS if m in lowered]
        if esp32_hit:
            findings.append(
                Finding(
                    "hardware_platforms",
                    "ESP32",
                    0.9,
                    tuple(f"{entry['path']} includes/uses {m}" for m in esp32_hit),
                )
            )
        esp8266_hit = [m for m in _ESP8266_INO_MARKERS if m in lowered]
        if esp8266_hit:
            findings.append(
                Finding(
                    "hardware_platforms",
                    "ESP8266",
                    0.9,
                    tuple(f"{entry['path']} includes {m}" for m in esp8266_hit),
                )
            )
    return findings


# (path/name substring, platform), checked against every entry's path and
# against the repository name itself. A path segment or repo name literally
# naming the chip (e.g. a folder called "ESP32/", or a repo named
# "ESP32-Weather-Station") is exact, checkable text, not a guess; but it's
# still just a naming convention rather than code evidence, so it's used at
# a lower confidence and only as a supplement, never overriding stronger
# in-content evidence for the same platform.
_NAME_HINT_MARKERS: tuple[tuple[str, str], ...] = (
    ("esp32", "ESP32"),
    ("esp8266", "ESP8266"),
    ("stm32", "STM32"),
    ("rp2040", "RP2040"),
)


def _path_and_repo_name_hints(input: AnalysisInput) -> list[Finding]:
    findings = []
    repo_name = (input.repo_metadata.get("name") or "").lower()
    for marker, platform in _NAME_HINT_MARKERS:
        path_hits = sorted(
            {e["path"] for e in input.entries if marker in e.get("path", "").lower()}
        )
        evidence = [f'found path containing "{marker}": {p}' for p in path_hits[:3]]
        if marker in repo_name:
            evidence.append(f'repository name contains "{marker}"')
        if evidence:
            findings.append(
                Finding("hardware_platforms", platform, 0.6, tuple(evidence))
            )
    return findings


def _platformio_platforms(input: AnalysisInput) -> list[Finding]:
    content = get_content(input.file_contents, input.entries, "platformio.ini")
    if not content:
        return []
    lowered = content.lower()
    found: dict[str, list[str]] = {}
    for marker, platform in _PLATFORMIO_BOARD_MARKERS:
        for line in lowered.splitlines():
            stripped = line.strip()
            if stripped.startswith("board") and marker in stripped:
                found.setdefault(platform, []).append(stripped)
                break
    return [
        Finding(
            "hardware_platforms",
            platform,
            0.85,
            tuple(f"platformio.ini: {line}" for line in lines),
        )
        for platform, lines in found.items()
    ]


def _esp_idf(input: AnalysisInput) -> Finding | None:
    evidence = []
    if has_filename(input.entries, "sdkconfig"):
        evidence.append("found sdkconfig (ESP-IDF)")
    if has_filename(input.entries, "sdkconfig.defaults"):
        evidence.append("found sdkconfig.defaults (ESP-IDF)")
    if has_filename(input.entries, "idf_component.yml"):
        evidence.append("found idf_component.yml (ESP-IDF)")
    if not evidence:
        return None
    return Finding("hardware_platforms", "ESP32", 0.9, tuple(evidence))


def _generic_arduino(input: AnalysisInput) -> Finding | None:
    # Only a fallback: .ino files exist, but nothing else in this analyzer
    # identified a specific chip. Lower confidence than the chip-specific
    # findings above, since "uses the Arduino framework" and "is a classic
    # AVR board" are not the same claim, ESP32/ESP8266 sketches are also
    # .ino files.
    if has_extension(input.entries, ".ino"):
        return Finding(
            "hardware_platforms",
            "Arduino",
            0.6,
            ("found .ino sketch file(s); no chip-specific markers found",),
        )
    return None


def _stm32(input: AnalysisInput) -> Finding | None:
    if has_extension(input.entries, ".ioc"):
        return Finding(
            "hardware_platforms",
            "STM32",
            0.9,
            ("found .ioc file (STM32CubeMX project)",),
        )
    return None


def _rp2040_pico_sdk(input: AnalysisInput) -> Finding | None:
    content = get_content(input.file_contents, input.entries, "CMakeLists.txt")
    if content and "pico_sdk_import.cmake" in content:
        return Finding(
            "hardware_platforms",
            "RP2040",
            0.85,
            (
                "CMakeLists.txt references pico_sdk_import.cmake (Raspberry Pi Pico SDK)",
            ),
        )
    return None


_RASPBERRY_PI_PACKAGES = ("rpi.gpio", "gpiozero", "picamera", "picamera2")


def _raspberry_pi(input: AnalysisInput) -> Finding | None:
    matched = [p for p in _RASPBERRY_PI_PACKAGES if has_dependency(input, p)]
    if not matched:
        return None
    return Finding(
        "hardware_platforms",
        "Raspberry Pi",
        0.85,
        tuple(f'declares dependency on "{p}"' for p in matched),
    )


class HardwarePlatformAnalyzer:
    """Infers one or more target hardware platforms from deterministic markers."""

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        findings = [
            f
            for f in (
                _esp_idf(input),
                _stm32(input),
                _rp2040_pico_sdk(input),
                _raspberry_pi(input),
            )
            if f is not None
        ]
        findings.extend(_platformio_platforms(input))
        findings.extend(_firmware_content_markers(input))
        findings.extend(_path_and_repo_name_hints(input))

        # De-duplicate by platform name, several signals can independently
        # fire for the same platform (e.g. both a "ESP32/" path hint and a
        # BluetoothSerial.h include); keep the higher-confidence Finding,
        # merging evidence from both when confidence ties.
        best: dict[str, Finding] = {}
        for finding in findings:
            existing = best.get(finding.value)
            if existing is None or finding.confidence > existing.confidence:
                best[finding.value] = finding
            elif finding.confidence == existing.confidence:
                merged_evidence = existing.evidence + tuple(
                    e for e in finding.evidence if e not in existing.evidence
                )
                best[finding.value] = Finding(
                    existing.field, existing.value, existing.confidence, merged_evidence
                )

        # The generic Arduino fallback only applies if no specific chip
        # platform was found at all, if ESP32/ESP8266/STM32/RP2040 was
        # identified, that's strictly more informative and the vague
        # "Arduino" label would just be noise.
        if not best:
            generic = _generic_arduino(input)
            if generic is not None:
                best[generic.value] = generic

        return list(best.values())
