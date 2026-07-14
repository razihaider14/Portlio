"""Tests for app.metadata.analyzers.hardware_platform.HardwarePlatformAnalyzer."""

from app.metadata.analyzers.hardware_platform import HardwarePlatformAnalyzer
from app.metadata.models import AnalysisInput

analyzer = HardwarePlatformAnalyzer()


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def d(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "dir"}


def platforms_of(input_: AnalysisInput) -> set[str]:
    return {finding.value for finding in analyzer.analyze(input_)}


class TestESPIDF:
    def test_detected_by_sdkconfig(self):
        input_ = AnalysisInput(entries=[f("sdkconfig")])
        assert "ESP32" in platforms_of(input_)

    def test_detected_by_idf_component_yml(self):
        input_ = AnalysisInput(entries=[f("idf_component.yml")])
        assert "ESP32" in platforms_of(input_)

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(entries=[f("main.py")])
        assert "ESP32" not in platforms_of(input_)


class TestArduino:
    def test_detected_by_ino_file(self):
        input_ = AnalysisInput(entries=[f("sketch.ino")])
        assert "Arduino" in platforms_of(input_)

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(entries=[f("main.py")])
        assert "Arduino" not in platforms_of(input_)


class TestSTM32:
    def test_detected_by_ioc_file(self):
        input_ = AnalysisInput(entries=[f("project.ioc")])
        assert "STM32" in platforms_of(input_)

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(entries=[f("main.py")])
        assert "STM32" not in platforms_of(input_)


class TestRP2040:
    def test_detected_by_pico_sdk_cmake_reference(self):
        content = "include(pico_sdk_import.cmake)\nproject(myapp)\n"
        input_ = AnalysisInput(
            entries=[f("CMakeLists.txt")], file_contents={"CMakeLists.txt": content}
        )
        assert "RP2040" in platforms_of(input_)

    def test_not_detected_without_pico_sdk_reference(self):
        input_ = AnalysisInput(
            entries=[f("CMakeLists.txt")],
            file_contents={"CMakeLists.txt": "project(myapp)\n"},
        )
        assert "RP2040" not in platforms_of(input_)

    def test_not_detected_without_file_contents(self):
        input_ = AnalysisInput(entries=[f("CMakeLists.txt")])
        assert "RP2040" not in platforms_of(input_)


class TestRaspberryPi:
    def test_detected_by_rpi_gpio_dependency(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "RPi.GPIO==0.7.1\n"},
        )
        assert "Raspberry Pi" in platforms_of(input_)

    def test_detected_by_gpiozero_dependency(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "gpiozero\n"},
        )
        assert "Raspberry Pi" in platforms_of(input_)

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(
            entries=[f("requirements.txt")],
            file_contents={"requirements.txt": "flask\n"},
        )
        assert "Raspberry Pi" not in platforms_of(input_)


class TestPlatformIOBoardDetection:
    def test_detects_esp32_board(self):
        content = "[env:esp32dev]\nplatform = espressif32\nboard = esp32dev\n"
        input_ = AnalysisInput(
            entries=[f("platformio.ini")], file_contents={"platformio.ini": content}
        )
        assert "ESP32" in platforms_of(input_)

    def test_detects_uno_as_arduino(self):
        content = "[env:uno]\nplatform = atmelavr\nboard = uno\n"
        input_ = AnalysisInput(
            entries=[f("platformio.ini")], file_contents={"platformio.ini": content}
        )
        assert "Arduino" in platforms_of(input_)

    def test_detects_pico_as_rp2040(self):
        content = "[env:pico]\nplatform = raspberrypi\nboard = pico\n"
        input_ = AnalysisInput(
            entries=[f("platformio.ini")], file_contents={"platformio.ini": content}
        )
        assert "RP2040" in platforms_of(input_)

    def test_no_platforms_without_file_contents(self):
        input_ = AnalysisInput(entries=[f("platformio.ini")])
        assert platforms_of(input_) == set()

    def test_detects_multiple_boards_across_environments(self):
        content = "[env:esp32dev]\nboard = esp32dev\n\n[env:uno]\nboard = uno\n"
        input_ = AnalysisInput(
            entries=[f("platformio.ini")], file_contents={"platformio.ini": content}
        )
        platforms = platforms_of(input_)
        assert "ESP32" in platforms
        assert "Arduino" in platforms


class TestMultiplePlatformsAndDeduplication:
    def test_repo_can_target_multiple_platforms(self):
        input_ = AnalysisInput(entries=[f("sdkconfig"), f("project.ioc")])
        platforms = platforms_of(input_)
        assert "ESP32" in platforms
        assert "STM32" in platforms

    def test_no_duplicate_findings_for_same_platform(self):
        # Both ESP-IDF's sdkconfig marker and a platformio.ini esp32 board
        # independently indicate ESP32; the analyzer should report it once.
        content = "[env:esp32dev]\nboard = esp32dev\n"
        input_ = AnalysisInput(
            entries=[f("sdkconfig"), f("platformio.ini")],
            file_contents={"platformio.ini": content},
        )
        findings = analyzer.analyze(input_)
        esp32_findings = [x for x in findings if x.value == "ESP32"]
        assert len(esp32_findings) == 1


class TestChipSpecificInoContentMarkers:
    def test_bluetoothserial_identifies_esp32(self):
        content = "#include <BluetoothSerial.h>\nvoid setup() {}\n"
        input_ = AnalysisInput(
            entries=[f("sketch.ino")], file_contents={"sketch.ino": content}
        )
        assert "ESP32" in platforms_of(input_)

    def test_esp_now_identifies_esp32(self):
        content = "#include <esp_now.h>\n"
        input_ = AnalysisInput(
            entries=[f("sketch.ino")], file_contents={"sketch.ino": content}
        )
        assert "ESP32" in platforms_of(input_)

    def test_preferences_h_identifies_esp32(self):
        content = "#include <Preferences.h>\n"
        input_ = AnalysisInput(
            entries=[f("sketch.ino")], file_contents={"sketch.ino": content}
        )
        assert "ESP32" in platforms_of(input_)

    def test_espmdns_identifies_esp32(self):
        content = "#include <ESPmDNS.h>\n"
        input_ = AnalysisInput(
            entries=[f("sketch.ino")], file_contents={"sketch.ino": content}
        )
        assert "ESP32" in platforms_of(input_)

    def test_esp8266wifi_identifies_esp8266(self):
        content = "#include <ESP8266WiFi.h>\n"
        input_ = AnalysisInput(
            entries=[f("sketch.ino")], file_contents={"sketch.ino": content}
        )
        assert "ESP8266" in platforms_of(input_)

    def test_plain_wifi_h_does_not_claim_a_specific_chip(self):
        # <WiFi.h> is used by both the ESP32 Arduino core AND the classic
        # Arduino WiFi shield library, the header name alone is ambiguous
        # and must not be treated as ESP32-exclusive evidence.
        content = "#include <WiFi.h>\n#include <PubSubClient.h>\n"
        input_ = AnalysisInput(
            entries=[f("sketch.ino")], file_contents={"sketch.ino": content}
        )
        platforms = platforms_of(input_)
        assert "ESP32" not in platforms
        assert "ESP8266" not in platforms

    def test_no_ino_content_falls_back_to_generic_arduino(self):
        # .ino exists but wasn't downloaded (no include_content), must
        # still report *something* (generic Arduino), just at lower
        # confidence, rather than reporting nothing.
        input_ = AnalysisInput(entries=[f("sketch.ino")])
        assert platforms_of(input_) == {"Arduino"}


class TestCompanionFileContentMarkers:
    def test_chip_marker_found_in_companion_cpp_file_not_ino_itself(self):
        # Mirrors a realistic multi-file sketch: the thin .ino has no
        # chip-specific evidence, but a companion .cpp file (e.g. an
        # mqtt/bluetooth handler) does.
        input_ = AnalysisInput(
            entries=[f("firmware/firmware.ino"), f("firmware/bt_handler.cpp")],
            file_contents={
                "firmware/firmware.ino": "void setup() {}\nvoid loop() {}\n",
                "firmware/bt_handler.cpp": "#include <BluetoothSerial.h>\n",
            },
        )
        assert "ESP32" in platforms_of(input_)

    def test_chip_marker_found_in_companion_header_file(self):
        input_ = AnalysisInput(
            entries=[f("firmware/firmware.ino"), f("firmware/wifi_handler.h")],
            file_contents={
                "firmware/firmware.ino": "void setup() {}\n",
                "firmware/wifi_handler.h": "#include <ESP8266WiFi.h>\n",
            },
        )
        assert "ESP8266" in platforms_of(input_)

    def test_unrelated_cpp_file_without_ino_sibling_is_still_scanned_if_downloaded(
        self,
    ):
        # The analyzer itself scans whatever content it's given; it's
        # content_targets' job (not this analyzer's) to decide which files
        # get downloaded in the first place.
        input_ = AnalysisInput(
            entries=[f("lib/esp_stuff.cpp")],
            file_contents={"lib/esp_stuff.cpp": "#include <esp_now.h>\n"},
        )
        assert "ESP32" in platforms_of(input_)


class TestPathAndRepoNameHints:
    def test_esp32_named_directory_is_evidence(self):
        input_ = AnalysisInput(entries=[d("ESP32"), f("ESP32/ESP32.ino")])
        assert "ESP32" in platforms_of(input_)

    def test_esp32_in_repo_name_is_evidence(self):
        input_ = AnalysisInput(
            entries=[f("firmware.ino")], repo_metadata={"name": "ESP32-Weather-Station"}
        )
        assert "ESP32" in platforms_of(input_)

    def test_generic_arduino_not_used_when_name_hint_available(self):
        input_ = AnalysisInput(
            entries=[f("firmware.ino")], repo_metadata={"name": "ESP32-Weather-Station"}
        )
        platforms = platforms_of(input_)
        assert platforms == {"ESP32"}

    def test_no_hint_from_unrelated_repo_name(self):
        input_ = AnalysisInput(
            entries=[f("sketch.ino")], repo_metadata={"name": "my-cool-bot"}
        )
        assert platforms_of(input_) == {"Arduino"}


class TestGenericArduinoFallbackOnlyWhenNoSpecificChipFound:
    def test_generic_arduino_confidence_is_lower_than_specific_chip(self):
        input_ = AnalysisInput(entries=[f("sketch.ino")])
        findings = analyzer.analyze(input_)
        assert findings[0].value == "Arduino"
        assert findings[0].confidence == 0.6

    def test_specific_chip_confidence_higher_than_generic(self):
        content = "#include <BluetoothSerial.h>\n"
        input_ = AnalysisInput(
            entries=[f("sketch.ino")], file_contents={"sketch.ino": content}
        )
        findings = analyzer.analyze(input_)
        assert findings[0].value == "ESP32"
        assert findings[0].confidence == 0.9

    def test_generic_arduino_suppressed_when_specific_chip_found(self):
        content = "#include <BluetoothSerial.h>\n"
        input_ = AnalysisInput(
            entries=[f("sketch.ino")], file_contents={"sketch.ino": content}
        )
        platforms = platforms_of(input_)
        assert platforms == {"ESP32"}
