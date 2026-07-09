"""
Integration tests for the production RULES list.

Each test class represents one technology and covers:
  - A minimal positive case (should detect)
  - A negative case (should NOT detect for a plausible near-miss)

Tests use the public detect_technologies() API so they catch regressions
across the entire stack: matchers, engine, rules, and public interface.
"""

import pytest
from tests.conftest import d, f, repo
from app.detector.detector import detect_technologies


def has(technology: str, repository: dict) -> bool:
    return technology in detect_technologies(repository)


# Python ecosystem


class TestPython:
    def test_detected_by_py_extension(self):
        assert has("Python", repo(f("app/main.py")))

    def test_not_detected_without_py_files(self):
        assert not has("Python", repo(f("index.html"), f("style.css")))


class TestDjango:
    def test_detected_by_manage_py(self):
        assert has("Django", repo(f("manage.py"), f("myapp/models.py")))

    def test_not_detected_without_manage_py(self):
        assert not has("Django", repo(f("myapp/models.py"), f("requirements.txt")))


class TestPoetry:
    def test_detected_by_poetry_lock(self):
        assert has("Poetry", repo(f("poetry.lock"), f("pyproject.toml")))

    def test_not_detected_from_pyproject_toml_alone(self):
        # pyproject.toml is shared with setuptools, Hatch, uv — not Poetry-specific
        assert not has("Poetry", repo(f("pyproject.toml")))


class TestPipenv:
    def test_detected_by_pipfile(self):
        assert has("Pipenv", repo(f("Pipfile"), f("Pipfile.lock")))

    def test_not_detected_without_pipfile(self):
        assert not has("Pipenv", repo(f("requirements.txt")))


class TestUv:
    def test_detected_by_uv_lock(self):
        assert has("uv", repo(f("uv.lock"), f("pyproject.toml")))

    def test_not_detected_without_uv_lock(self):
        assert not has("uv", repo(f("pyproject.toml")))


class TestSetuptools:
    def test_detected_by_setup_py(self):
        assert has("setuptools", repo(f("setup.py"), f("mypackage/__init__.py")))

    def test_detected_by_setup_cfg(self):
        assert has("setuptools", repo(f("setup.cfg")))

    def test_not_detected_without_setup_files(self):
        assert not has("setuptools", repo(f("pyproject.toml")))


# JavaScript / TypeScript


class TestNodeJs:
    def test_detected_by_package_json(self):
        assert has("Node.js", repo(f("package.json"), f("index.js")))

    def test_not_detected_without_package_json(self):
        assert not has("Node.js", repo(f("index.js")))


class TestTypeScript:
    def test_detected_by_ts_extension(self):
        assert has("TypeScript", repo(f("src/app.ts")))

    def test_detected_by_tsx_extension(self):
        assert has("TypeScript", repo(f("src/App.tsx")))

    def test_not_detected_without_ts_files(self):
        assert not has("TypeScript", repo(f("src/app.js")))


class TestNextJs:
    def test_detected_by_next_config_js(self):
        assert has("Next.js", repo(f("next.config.js"), f("package.json")))

    def test_detected_by_next_config_ts(self):
        assert has("Next.js", repo(f("next.config.ts")))

    def test_not_detected_without_next_config(self):
        assert not has("Next.js", repo(f("package.json"), f("pages/index.js")))


class TestVue:
    def test_detected_by_vue_extension(self):
        assert has("Vue", repo(f("src/App.vue"), f("package.json")))

    def test_not_detected_without_vue_files(self):
        assert not has("Vue", repo(f("package.json"), f("src/App.js")))


class TestNuxt:
    def test_detected_by_nuxt_config(self):
        assert has("Nuxt", repo(f("nuxt.config.ts"), f("package.json")))

    def test_not_detected_without_nuxt_config(self):
        assert not has("Nuxt", repo(f("package.json"), f("pages/index.vue")))


class TestAngular:
    def test_detected_by_angular_json(self):
        assert has("Angular", repo(f("angular.json"), f("src/app/app.component.ts")))

    def test_not_detected_without_angular_json(self):
        assert not has("Angular", repo(f("package.json"), f("src/app.ts")))


class TestVite:
    def test_detected_by_vite_config_js(self):
        assert has("Vite", repo(f("vite.config.js")))

    def test_detected_by_vite_config_ts(self):
        assert has("Vite", repo(f("vite.config.ts")))

    def test_not_detected_without_vite_config(self):
        assert not has("Vite", repo(f("package.json"), f("index.html")))


class TestWebpack:
    def test_detected_by_webpack_config(self):
        assert has("Webpack", repo(f("webpack.config.js")))

    def test_not_detected_without_webpack_config(self):
        assert not has("Webpack", repo(f("package.json")))


# Mobile


class TestFlutter:
    def test_detected_with_pubspec_and_dart(self):
        assert has("Flutter", repo(f("pubspec.yaml"), f("lib/main.dart")))

    def test_not_detected_with_pubspec_alone(self):
        # Pure Dart packages also use pubspec.yaml; require .dart files
        assert not has("Flutter", repo(f("pubspec.yaml")))

    def test_not_detected_with_dart_alone(self):
        assert not has("Flutter", repo(f("lib/main.dart")))


class TestReactNative:
    def test_detected_by_metro_config(self):
        assert has("React Native", repo(f("metro.config.js"), f("package.json")))

    def test_detected_by_metro_config_ts(self):
        assert has("React Native", repo(f("metro.config.ts")))

    def test_not_detected_without_metro_config(self):
        assert not has("React Native", repo(f("package.json"), f("App.js")))


class TestAndroid:
    def test_detected_by_android_manifest(self):
        assert has(
            "Android",
            repo(
                f("app/src/main/AndroidManifest.xml"),
                f("build.gradle"),
            ),
        )

    def test_not_detected_without_manifest(self):
        assert not has("Android", repo(f("build.gradle"), f("src/Main.java")))


class TestSwift:
    def test_detected_by_swift_extension(self):
        assert has("Swift", repo(f("Sources/App/main.swift")))

    def test_not_detected_without_swift_files(self):
        assert not has("Swift", repo(f("Package.json")))


class TestKotlin:
    def test_detected_by_kt_extension(self):
        assert has("Kotlin", repo(f("src/main/kotlin/App.kt")))

    def test_detected_by_kts_extension(self):
        assert has("Kotlin", repo(f("build.gradle.kts")))

    def test_not_detected_without_kotlin_files(self):
        assert not has("Kotlin", repo(f("src/Main.java")))


# Java / JVM


class TestJavaMaven:
    def test_detected_by_pom_xml(self):
        assert has("Java Maven", repo(f("pom.xml"), f("src/main/java/App.java")))

    def test_not_detected_without_pom_xml(self):
        assert not has("Java Maven", repo(f("build.gradle")))


class TestGradle:
    def test_detected_by_build_gradle(self):
        assert has("Gradle", repo(f("build.gradle"), f("settings.gradle")))

    def test_detected_by_kotlin_dsl(self):
        assert has("Gradle", repo(f("build.gradle.kts")))

    def test_not_detected_without_gradle_files(self):
        assert not has("Gradle", repo(f("pom.xml")))


class TestSpringBoot:
    def test_detected_with_maven_and_application_properties(self):
        assert has(
            "Spring Boot",
            repo(
                f("pom.xml"),
                f("src/main/resources/application.properties"),
            ),
        )

    def test_detected_with_gradle_and_application_yml(self):
        assert has(
            "Spring Boot",
            repo(
                f("build.gradle"),
                f("src/main/resources/application.yml"),
            ),
        )

    def test_not_detected_with_pom_xml_alone(self):
        # Any Maven project has pom.xml, not enough on its own
        assert not has(
            "Spring Boot",
            repo(
                f("pom.xml"),
                f("src/main/java/App.java"),
            ),
        )

    def test_not_detected_with_application_properties_alone(self):
        # application.properties without a JVM build file, not Spring Boot
        assert not has(
            "Spring Boot",
            repo(
                f("src/main/resources/application.properties"),
            ),
        )

    def test_not_detected_with_src_main_resources_alone(self):
        # Previous (weaker) rule : src/main/resources without application file
        assert not has(
            "Spring Boot",
            repo(
                f("pom.xml"),
                f("src/main/resources/logback.xml"),
            ),
        )


# .NET


class TestDotNet:
    def test_detected_by_csproj(self):
        assert has(".NET", repo(f("MyApp/MyApp.csproj")))

    def test_detected_by_fsproj(self):
        assert has(".NET", repo(f("MyLib/MyLib.fsproj")))

    def test_not_detected_without_project_file(self):
        assert not has(".NET", repo(f("src/Program.cs")))


class TestDotNetSolution:
    def test_detected_by_sln(self):
        assert has(".NET Solution", repo(f("MyApp.sln")))

    def test_not_detected_without_sln(self):
        assert not has(".NET Solution", repo(f("MyApp.csproj")))


# Systems languages


class TestRust:
    def test_detected_by_cargo_toml(self):
        assert has("Rust", repo(f("Cargo.toml"), f("src/main.rs")))

    def test_not_detected_without_cargo_toml(self):
        assert not has("Rust", repo(f("src/main.rs")))


class TestGo:
    def test_detected_by_go_mod(self):
        assert has("Go", repo(f("go.mod"), f("main.go")))

    def test_not_detected_without_go_mod(self):
        assert not has("Go", repo(f("main.go")))


class TestC:
    def test_detected_by_c_extension(self):
        assert has("C", repo(f("src/main.c"), f("src/util.h")))

    def test_not_detected_from_h_files_alone(self):
        # .h files are shared with C++, should not trigger C alone
        assert not has("C", repo(f("include/mylib.h")))

    def test_not_detected_without_c_files(self):
        assert not has("C", repo(f("src/main.cpp")))


class TestCpp:
    def test_detected_by_cpp_extension(self):
        assert has("C++", repo(f("src/main.cpp"), f("include/app.hpp")))

    def test_detected_by_cc_extension(self):
        assert has("C++", repo(f("src/main.cc")))

    def test_not_detected_from_h_files_alone(self):
        assert not has("C++", repo(f("include/mylib.h")))


class TestCMake:
    def test_detected_by_cmakelists(self):
        assert has("CMake", repo(f("CMakeLists.txt"), f("src/main.c")))

    def test_not_detected_without_cmakelists(self):
        assert not has("CMake", repo(f("Makefile"), f("src/main.c")))


class TestMake:
    def test_detected_by_makefile(self):
        assert has("Make", repo(f("Makefile")))

    def test_detected_case_insensitive(self):
        assert has("Make", repo(f("makefile")))

    def test_detected_by_makefile_am(self):
        assert has("Make", repo(f("Makefile.am")))

    def test_not_detected_without_makefile(self):
        assert not has("Make", repo(f("CMakeLists.txt"), f("src/main.c")))


# PHP


class TestPhp:
    def test_detected_by_php_extension(self):
        assert has("PHP", repo(f("index.php"), f("src/App.php")))

    def test_not_detected_without_php_files(self):
        assert not has("PHP", repo(f("composer.json")))


class TestComposer:
    def test_detected_by_composer_json(self):
        assert has("Composer", repo(f("composer.json"), f("src/App.php")))

    def test_not_detected_without_composer_json(self):
        assert not has("Composer", repo(f("index.php")))


class TestLaravel:
    def test_detected_by_artisan(self):
        assert has(
            "Laravel",
            repo(
                f("artisan"),
                f("composer.json"),
                f("app/Http/Controllers/HomeController.php"),
            ),
        )

    def test_not_detected_without_artisan(self):
        assert not has("Laravel", repo(f("composer.json"), f("index.php")))


# Ruby


class TestRuby:
    def test_detected_by_rb_extension(self):
        assert has("Ruby", repo(f("lib/app.rb")))

    def test_not_detected_without_rb_files(self):
        assert not has("Ruby", repo(f("Gemfile")))


class TestBundler:
    def test_detected_by_gemfile(self):
        assert has("Bundler", repo(f("Gemfile"), f("Gemfile.lock")))

    def test_not_detected_without_gemfile(self):
        assert not has("Bundler", repo(f("lib/app.rb")))


class TestRubyOnRails:
    def test_detected_by_routes_rb(self):
        assert has(
            "Ruby on Rails",
            repo(
                f("config/routes.rb"),
                f("app/controllers/application_controller.rb"),
            ),
        )

    def test_not_detected_without_routes_rb(self):
        assert not has("Ruby on Rails", repo(f("Gemfile"), f("lib/app.rb")))


# Embedded systems


class TestArduino:
    def test_detected_by_ino_extension(self):
        assert has("Arduino", repo(f("firmware/sketch.ino"), f("firmware/motors.cpp")))

    def test_detected_even_when_html_is_primary_language(self):
        # Regression: HTML-heavy repos must still detect Arduino via .ino
        assert has(
            "Arduino",
            repo(
                f("dashboard/index.html"),
                f("dashboard/style.css"),
                f("firmware/sketch.ino"),
            ),
        )

    def test_not_detected_without_ino_files(self):
        assert not has("Arduino", repo(f("src/main.cpp"), f("platformio.ini")))


class TestPlatformIO:
    def test_detected_by_platformio_ini(self):
        assert has("PlatformIO", repo(f("platformio.ini"), f("src/main.cpp")))

    def test_not_detected_without_platformio_ini(self):
        assert not has("PlatformIO", repo(f("src/main.cpp")))


class TestEspIdf:
    def test_detected_by_sdkconfig(self):
        assert has("ESP-IDF", repo(f("sdkconfig"), f("main/main.c")))

    def test_detected_by_idf_component_yml(self):
        assert has("ESP-IDF", repo(f("idf_component.yml"), f("main/main.c")))

    def test_not_detected_without_esp_idf_files(self):
        assert not has("ESP-IDF", repo(f("CMakeLists.txt"), f("main/main.c")))


class TestStm32:
    def test_detected_by_ioc_extension(self):
        assert has("STM32CubeIDE", repo(f("MyProject.ioc"), f("Core/Src/main.c")))

    def test_not_detected_without_ioc_file(self):
        assert not has("STM32CubeIDE", repo(f("Core/Src/main.c")))


# Containers & Orchestration


class TestDocker:
    def test_detected_by_dockerfile(self):
        assert has("Docker", repo(f("Dockerfile"), f("src/main.py")))

    def test_detected_case_insensitive(self):
        assert has("Docker", repo(f("dockerfile")))

    def test_not_detected_without_dockerfile(self):
        assert not has("Docker", repo(f("docker-compose.yml")))


class TestDockerCompose:
    def test_detected_by_docker_compose_yml(self):
        assert has("Docker Compose", repo(f("docker-compose.yml")))

    def test_detected_by_compose_yaml(self):
        assert has("Docker Compose", repo(f("compose.yaml")))

    def test_not_detected_without_compose_file(self):
        assert not has("Docker Compose", repo(f("Dockerfile")))


class TestHelm:
    def test_detected_by_chart_yaml(self):
        assert has(
            "Helm",
            repo(
                f("Chart.yaml"),
                f("templates/deployment.yaml"),
            ),
        )

    def test_not_detected_without_chart_yaml(self):
        assert not has("Helm", repo(f("templates/deployment.yaml")))


class TestKubernetes:
    def test_detected_by_k8s_directory(self):
        assert has(
            "Kubernetes",
            repo(
                d("k8s"),
                f("k8s/deployment.yaml"),
            ),
        )

    def test_detected_by_kubernetes_directory(self):
        assert has(
            "Kubernetes",
            repo(
                d("kubernetes"),
                f("kubernetes/service.yaml"),
            ),
        )

    def test_not_detected_without_k8s_directory(self):
        assert not has("Kubernetes", repo(f("deployment.yaml")))


# Infrastructure as Code


class TestTerraform:
    def test_detected_by_tf_extension(self):
        assert has("Terraform", repo(f("main.tf"), f("variables.tf")))

    def test_not_detected_without_tf_files(self):
        assert not has("Terraform", repo(f("ansible.cfg")))


class TestAnsible:
    def test_detected_by_ansible_cfg(self):
        assert has("Ansible", repo(f("ansible.cfg"), f("playbook.yml")))

    def test_not_detected_without_ansible_cfg(self):
        assert not has("Ansible", repo(f("playbook.yml")))


# CI/CD


class TestGitHubActions:
    def test_detected_by_workflows_path(self):
        assert has(
            "GitHub Actions",
            repo(
                d(".github"),
                d(".github/workflows"),
                f(".github/workflows/ci.yml"),
            ),
        )

    def test_not_detected_with_github_dir_only(self):
        # .github alone is not enough, workflows/ must exist inside it
        assert not has(
            "GitHub Actions",
            repo(
                d(".github"),
                f(".github/CODEOWNERS"),
            ),
        )


class TestGitLabCi:
    def test_detected_by_gitlab_ci_yml(self):
        assert has("GitLab CI", repo(f(".gitlab-ci.yml"), f("src/main.py")))

    def test_not_detected_without_gitlab_ci_yml(self):
        assert not has("GitLab CI", repo(f(".github/workflows/ci.yml")))


class TestCircleCi:
    def test_detected_by_circleci_directory(self):
        assert has("CircleCI", repo(d(".circleci"), f(".circleci/config.yml")))

    def test_not_detected_without_circleci_directory(self):
        assert not has("CircleCI", repo(f("circle.yml")))


class TestTravisCi:
    def test_detected_by_travis_yml(self):
        assert has("Travis CI", repo(f(".travis.yml"), f("src/main.py")))

    def test_not_detected_without_travis_yml(self):
        assert not has("Travis CI", repo(f(".github/workflows/ci.yml")))


class TestJenkins:
    def test_detected_by_jenkinsfile(self):
        assert has("Jenkins", repo(f("Jenkinsfile")))

    def test_detected_by_jenkinsfile_groovy(self):
        assert has("Jenkins", repo(f("Jenkinsfile.groovy")))

    def test_detected_case_insensitive(self):
        assert has("Jenkins", repo(f("jenkinsfile")))

    def test_not_detected_without_jenkinsfile(self):
        assert not has("Jenkins", repo(f(".travis.yml")))


class TestAzurePipelines:
    def test_detected_by_azure_pipelines_yml(self):
        assert has("Azure Pipelines", repo(f("azure-pipelines.yml")))

    def test_not_detected_without_azure_pipelines_yml(self):
        assert not has("Azure Pipelines", repo(f(".travis.yml")))


# Web Technologies


class TestHtml:
    def test_detected_by_html_extension(self):
        assert has("HTML", repo(f("index.html"), f("about.html")))

    def test_detected_by_htm_extension(self):
        assert has("HTML", repo(f("index.htm")))

    def test_not_detected_without_html_files(self):
        assert not has("HTML", repo(f("style.css")))


class TestCss:
    def test_detected_by_css_extension(self):
        assert has("CSS", repo(f("styles/main.css")))

    def test_not_detected_without_css_files(self):
        assert not has("CSS", repo(f("index.html")))


class TestSass:
    def test_detected_by_scss_extension(self):
        assert has("Sass", repo(f("styles/main.scss")))

    def test_detected_by_sass_extension(self):
        assert has("Sass", repo(f("styles/main.sass")))

    def test_not_detected_without_sass_files(self):
        assert not has("Sass", repo(f("styles/main.css")))


class TestTailwind:
    def test_detected_by_tailwind_config_js(self):
        assert has("Tailwind CSS", repo(f("tailwind.config.js")))

    def test_detected_by_tailwind_config_ts(self):
        assert has("Tailwind CSS", repo(f("tailwind.config.ts")))

    def test_not_detected_without_tailwind_config(self):
        assert not has("Tailwind CSS", repo(f("package.json"), f("styles/main.css")))


# Data Science


class TestJupyter:
    def test_detected_by_ipynb_extension(self):
        assert has("Jupyter Notebook", repo(f("analysis/explore.ipynb")))

    def test_not_detected_without_ipynb_files(self):
        assert not has("Jupyter Notebook", repo(f("analysis/explore.py")))


# Database tooling


class TestAlembic:
    def test_detected_by_alembic_ini(self):
        assert has("Alembic", repo(f("alembic.ini"), f("alembic/env.py")))

    def test_not_detected_without_alembic_ini(self):
        assert not has("Alembic", repo(f("alembic/env.py")))


class TestPrisma:
    def test_detected_by_schema_prisma(self):
        assert has("Prisma", repo(f("prisma/schema.prisma"), f("package.json")))

    def test_not_detected_without_schema_prisma(self):
        assert not has("Prisma", repo(f("package.json")))


# Cross-ecosystem regression tests


class TestNoFalsePositives:
    def test_empty_repo_detects_nothing(self):
        assert detect_technologies(repo()) == []

    def test_c_header_only_does_not_trigger_c(self):
        # A C++ header-only library should not be detected as C
        result = detect_technologies(repo(f("include/mylib.h"), f("include/util.h")))
        assert "C" not in result

    def test_src_main_resources_alone_not_spring_boot(self):
        result = detect_technologies(
            repo(
                f("pom.xml"),
                f("src/main/resources/logback.xml"),
            )
        )
        assert "Spring Boot" not in result

    def test_generic_yaml_not_kubernetes(self):
        result = detect_technologies(repo(f("config.yaml"), f("values.yaml")))
        assert "Kubernetes" not in result

    def test_pubspec_yaml_without_dart_not_flutter(self):
        result = detect_technologies(repo(f("pubspec.yaml")))
        assert "Flutter" not in result


class TestRealWorldScenarios:
    def test_arduino_iot_dashboard(self):
        """Firmware repo where HTML byte-count exceeds C++; still detects Arduino."""
        result = detect_technologies(
            repo(
                f("firmware/sketch.ino"),
                f("firmware/sensors.cpp"),
                f("firmware/sensors.h"),
                f("platformio.ini"),
                f("dashboard/index.html"),
                f("dashboard/app.js"),
                f("dashboard/style.css"),
                d(".github"),
                d(".github/workflows"),
                f(".github/workflows/build.yml"),
            )
        )
        assert "Arduino" in result
        assert "PlatformIO" in result
        assert "HTML" in result
        assert "CSS" in result
        assert "C++" in result
        assert "GitHub Actions" in result

    def test_fullstack_nextjs_project(self):
        result = detect_technologies(
            repo(
                f("package.json"),
                f("next.config.ts"),
                f("tailwind.config.ts"),
                f("src/app/page.tsx"),
                f("src/app/layout.tsx"),
                f("prisma/schema.prisma"),
                f(".github/workflows/ci.yml"),
            )
        )
        assert "Node.js" in result
        assert "TypeScript" in result
        assert "Next.js" in result
        assert "Tailwind CSS" in result
        assert "Prisma" in result
        assert "GitHub Actions" in result

    def test_python_data_science_project(self):
        result = detect_technologies(
            repo(
                f("pyproject.toml"),
                f("poetry.lock"),
                f("notebooks/explore.ipynb"),
                f("src/train.py"),
                f("Dockerfile"),
                f(".github/workflows/train.yml"),
            )
        )
        assert "Python" in result
        assert "Poetry" in result
        assert "Jupyter Notebook" in result
        assert "Docker" in result
        assert "GitHub Actions" in result

    def test_rust_cli_with_ci(self):
        result = detect_technologies(
            repo(
                f("Cargo.toml"),
                f("src/main.rs"),
                f("Dockerfile"),
                f(".github/workflows/release.yml"),
                f(".travis.yml"),
            )
        )
        assert "Rust" in result
        assert "Docker" in result
        assert "GitHub Actions" in result
        assert "Travis CI" in result

    def test_rails_api(self):
        result = detect_technologies(
            repo(
                f("Gemfile"),
                f("Gemfile.lock"),
                f("config/routes.rb"),
                f("app/controllers/application_controller.rb"),
                f(".gitlab-ci.yml"),
                f("docker-compose.yml"),
            )
        )
        assert "Ruby" in result
        assert "Bundler" in result
        assert "Ruby on Rails" in result
        assert "GitLab CI" in result
        assert "Docker Compose" in result


class TestFastAPI:
    def test_detected_by_dependency_in_requirements_txt(self):
        result = detect_technologies(
            repo(
                f("main.py"),
                f("requirements.txt"),
                file_contents={"requirements.txt": "fastapi==0.100\nuvicorn\n"},
            )
        )
        assert "FastAPI" in result

    def test_not_detected_without_file_contents(self):
        # Same tree, but content wasn't downloaded (include_content=False),
        # must not false-positive just because requirements.txt exists.
        result = detect_technologies(repo(f("main.py"), f("requirements.txt")))
        assert "FastAPI" not in result

    def test_not_detected_when_dependency_absent(self):
        result = detect_technologies(
            repo(
                f("requirements.txt"),
                file_contents={"requirements.txt": "flask==2.0\n"},
            )
        )
        assert "FastAPI" not in result


class TestReact:
    def test_detected_by_dependency_in_package_json(self):
        result = detect_technologies(
            repo(
                f("package.json"),
                file_contents={
                    "package.json": '{"dependencies": {"react": "^18.0.0"}}'
                },
            )
        )
        assert "React" in result

    def test_not_detected_without_file_contents(self):
        result = detect_technologies(repo(f("package.json")))
        assert "React" not in result

    def test_not_detected_when_dependency_absent(self):
        result = detect_technologies(
            repo(
                f("package.json"),
                file_contents={"package.json": '{"dependencies": {"vue": "^3.0.0"}}'},
            )
        )
        assert "React" not in result
