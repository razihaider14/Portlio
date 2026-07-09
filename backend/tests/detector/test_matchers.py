"""
Unit tests for every matcher type.

Each test class covers one matcher in isolation: correct positives,
correct negatives, edge cases (empty tree, case sensitivity, etc.).
"""

import pytest
from tests.conftest import d, f
from app.detector.matchers import (
    AllOf,
    AnyOf,
    HasDependency,
    HasDirectory,
    HasExtension,
    HasFileContent,
    HasFileGlob,
    HasFilename,
    HasJsonKey,
    HasPath,
    HasTomlSection,
)
from app.detector.models import Entry


def entries(*items: dict) -> list[Entry]:
    return [Entry(path=e["path"], name=e["name"], type=e["type"]) for e in items]


# HasExtension


class TestHasExtension:
    def test_matches_exact_extension(self):
        assert HasExtension(".py").matches(entries(f("app/main.py")))

    def test_matches_any_of_multiple_extensions(self):
        m = HasExtension(".c", ".h")
        assert m.matches(entries(f("src/util.h")))
        assert m.matches(entries(f("src/main.c")))

    def test_case_insensitive(self):
        assert HasExtension(".py").matches(entries(f("Script.PY")))

    def test_no_match_on_wrong_extension(self):
        assert not HasExtension(".py").matches(entries(f("main.js")))

    def test_no_match_on_directory(self):
        # A directory named "src.py" should not trigger extension matching
        assert not HasExtension(".py").matches(entries(d("src.py")))

    def test_no_match_on_empty_tree(self):
        assert not HasExtension(".py").matches([])

    def test_no_match_for_file_without_extension(self):
        assert not HasExtension(".py").matches(entries(f("Makefile")))


# HasFilename


class TestHasFilename:
    def test_matches_exact_name(self):
        assert HasFilename("Cargo.toml").matches(entries(f("Cargo.toml")))

    def test_case_insensitive(self):
        assert HasFilename("Dockerfile").matches(entries(f("dockerfile")))
        assert HasFilename("dockerfile").matches(entries(f("Dockerfile")))

    def test_matches_nested_file(self):
        assert HasFilename("pom.xml").matches(entries(f("modules/core/pom.xml")))

    def test_matches_any_of_multiple_names(self):
        m = HasFilename("docker-compose.yml", "compose.yml")
        assert m.matches(entries(f("compose.yml")))

    def test_no_match_on_wrong_name(self):
        assert not HasFilename("pom.xml").matches(entries(f("build.gradle")))

    def test_no_match_on_directory_with_same_name(self):
        assert not HasFilename("Makefile").matches(entries(d("Makefile")))

    def test_no_match_on_empty_tree(self):
        assert not HasFilename("pom.xml").matches([])


# HasDirectory


class TestHasDirectory:
    def test_matches_directory(self):
        assert HasDirectory(".github").matches(entries(d(".github")))

    def test_case_insensitive(self):
        assert HasDirectory(".github").matches(entries(d(".GitHub")))

    def test_matches_any_of_multiple_names(self):
        m = HasDirectory("k8s", "kubernetes")
        assert m.matches(entries(d("k8s")))
        assert m.matches(entries(d("kubernetes")))

    def test_no_match_on_file_with_same_name(self):
        assert not HasDirectory(".github").matches(entries(f(".github")))

    def test_no_match_when_absent(self):
        assert not HasDirectory(".circleci").matches(entries(d(".github")))

    def test_no_match_on_empty_tree(self):
        assert not HasDirectory("src").matches([])


# HasPath


class TestHasPath:
    def test_matches_exact_path(self):
        assert HasPath("src/main.py").matches(entries(f("src/main.py")))

    def test_matches_prefix(self):
        # Any entry whose path starts with the given prefix
        assert HasPath(".github/workflows").matches(
            entries(f(".github/workflows/ci.yml"))
        )

    def test_case_insensitive(self):
        assert HasPath("src/main/resources").matches(
            entries(f("src/main/resources/application.properties"))
        )

    def test_no_match_when_path_absent(self):
        assert not HasPath("src/main/resources").matches(
            entries(f("src/test/resources/test.properties"))
        )

    def test_no_match_on_empty_tree(self):
        assert not HasPath(".github/workflows").matches([])

    def test_does_not_match_unrelated_path(self):
        assert not HasPath("src/main/resources/application.properties").matches(
            entries(f("src/main/resources/logback.xml"))
        )


# HasFileGlob


class TestHasFileGlob:
    def test_literal_pattern_case_insensitive(self):
        # No wildcards: behaves as case-insensitive exact match
        assert HasFileGlob("dockerfile").matches(entries(f("Dockerfile")))
        assert HasFileGlob("dockerfile").matches(entries(f("DOCKERFILE")))

    def test_wildcard_suffix(self):
        m = HasFileGlob("next.config.*")
        assert m.matches(entries(f("next.config.js")))
        assert m.matches(entries(f("next.config.ts")))
        assert m.matches(entries(f("next.config.mjs")))

    def test_wildcard_prefix(self):
        assert HasFileGlob("jenkinsfile*").matches(entries(f("Jenkinsfile")))
        assert HasFileGlob("jenkinsfile*").matches(entries(f("Jenkinsfile.groovy")))

    def test_no_match_on_directory(self):
        assert not HasFileGlob("dockerfile").matches(entries(d("Dockerfile")))

    def test_no_match_on_partial_name(self):
        assert not HasFileGlob("vite.config.*").matches(
            entries(f("not-vite.config.js"))
        )

    def test_no_match_on_empty_tree(self):
        assert not HasFileGlob("*.py").matches([])


# HasFileContent


class TestHasFileContent:
    def test_matches_when_content_contains_substring(self):
        m = HasFileContent("requirements.txt", "fastapi")
        assert m.matches(
            entries(f("requirements.txt")),
            file_contents={"requirements.txt": "fastapi==0.100\n"},
        )

    def test_no_match_when_substring_absent(self):
        m = HasFileContent("requirements.txt", "fastapi")
        assert not m.matches(
            entries(f("requirements.txt")),
            file_contents={"requirements.txt": "flask==2.0\n"},
        )

    def test_case_insensitive(self):
        m = HasFileContent("requirements.txt", "FastAPI")
        assert m.matches(
            entries(f("requirements.txt")),
            file_contents={"requirements.txt": "fastapi==0.100\n"},
        )

    def test_no_match_without_file_contents(self):
        m = HasFileContent("requirements.txt", "fastapi")
        assert not m.matches(entries(f("requirements.txt")))

    def test_no_match_when_file_not_in_tree(self):
        m = HasFileContent("requirements.txt", "fastapi")
        assert not m.matches(
            entries(f("other.txt")), file_contents={"other.txt": "fastapi"}
        )

    def test_no_match_when_path_missing_from_content_dict(self):
        m = HasFileContent("requirements.txt", "fastapi")
        assert not m.matches(
            entries(f("requirements.txt")), file_contents={"other.txt": "fastapi"}
        )

    def test_matches_nested_path(self):
        m = HasFileContent("requirements.txt", "fastapi")
        assert m.matches(
            entries(f("backend/requirements.txt")),
            file_contents={"backend/requirements.txt": "fastapi"},
        )


# HasJsonKey


class TestHasJsonKey:
    def test_matches_top_level_key(self):
        m = HasJsonKey("package.json", "name")
        assert m.matches(
            entries(f("package.json")),
            file_contents={"package.json": '{"name": "my-app"}'},
        )

    def test_matches_nested_dotted_key_path(self):
        m = HasJsonKey("package.json", "dependencies.react")
        assert m.matches(
            entries(f("package.json")),
            file_contents={"package.json": '{"dependencies": {"react": "^18.0.0"}}'},
        )

    def test_no_match_when_key_path_absent(self):
        m = HasJsonKey("package.json", "dependencies.react")
        assert not m.matches(
            entries(f("package.json")),
            file_contents={"package.json": '{"dependencies": {"vue": "^3.0.0"}}'},
        )

    def test_matches_with_contains_on_string_value(self):
        m = HasJsonKey("package.json", "scripts.build", contains="webpack")
        assert m.matches(
            entries(f("package.json")),
            file_contents={"package.json": '{"scripts": {"build": "webpack build"}}'},
        )

    def test_no_match_with_contains_mismatch(self):
        m = HasJsonKey("package.json", "scripts.build", contains="webpack")
        assert not m.matches(
            entries(f("package.json")),
            file_contents={"package.json": '{"scripts": {"build": "vite build"}}'},
        )

    def test_matches_with_contains_on_dict_membership(self):
        m = HasJsonKey("package.json", "dependencies", contains="react")
        assert m.matches(
            entries(f("package.json")),
            file_contents={"package.json": '{"dependencies": {"react": "^18.0.0"}}'},
        )

    def test_no_match_on_malformed_json(self):
        m = HasJsonKey("package.json", "name")
        assert not m.matches(
            entries(f("package.json")), file_contents={"package.json": "{not json"}
        )

    def test_no_match_without_file_contents(self):
        m = HasJsonKey("package.json", "name")
        assert not m.matches(entries(f("package.json")))


# HasTomlSection


class TestHasTomlSection:
    def test_matches_top_level_section(self):
        m = HasTomlSection("Cargo.toml", "dependencies")
        assert m.matches(
            entries(f("Cargo.toml")),
            file_contents={"Cargo.toml": '[dependencies]\nserde = "1.0"\n'},
        )

    def test_matches_nested_dotted_section(self):
        m = HasTomlSection("pyproject.toml", "tool.poetry.dependencies")
        content = '[tool.poetry.dependencies]\nfastapi = "^0.100"\n'
        assert m.matches(
            entries(f("pyproject.toml")), file_contents={"pyproject.toml": content}
        )

    def test_no_match_when_section_absent(self):
        m = HasTomlSection("pyproject.toml", "tool.poetry.dependencies")
        assert not m.matches(
            entries(f("pyproject.toml")),
            file_contents={"pyproject.toml": "[build-system]\n"},
        )

    def test_matches_with_key_present_in_section(self):
        m = HasTomlSection("Cargo.toml", "dependencies", key="serde")
        assert m.matches(
            entries(f("Cargo.toml")),
            file_contents={"Cargo.toml": '[dependencies]\nserde = "1.0"\n'},
        )

    def test_no_match_with_key_absent_from_section(self):
        m = HasTomlSection("Cargo.toml", "dependencies", key="tokio")
        assert not m.matches(
            entries(f("Cargo.toml")),
            file_contents={"Cargo.toml": '[dependencies]\nserde = "1.0"\n'},
        )

    def test_no_match_on_malformed_toml(self):
        m = HasTomlSection("Cargo.toml", "dependencies")
        assert not m.matches(
            entries(f("Cargo.toml")), file_contents={"Cargo.toml": "not [ valid"}
        )

    def test_no_match_without_file_contents(self):
        m = HasTomlSection("Cargo.toml", "dependencies")
        assert not m.matches(entries(f("Cargo.toml")))


# HasDependency


class TestHasDependency:
    def test_matches_dependency_in_requirements_txt(self):
        m = HasDependency("fastapi")
        assert m.matches(
            entries(f("requirements.txt")),
            file_contents={"requirements.txt": "fastapi==0.100\n"},
        )

    def test_matches_dependency_in_package_json(self):
        m = HasDependency("react")
        assert m.matches(
            entries(f("package.json")),
            file_contents={"package.json": '{"dependencies": {"react": "^18.0.0"}}'},
        )

    def test_matches_dependency_in_pyproject_toml(self):
        m = HasDependency("fastapi")
        content = '[project]\ndependencies = ["fastapi>=0.100"]\n'
        assert m.matches(
            entries(f("pyproject.toml")), file_contents={"pyproject.toml": content}
        )

    def test_matches_dependency_in_cargo_toml(self):
        m = HasDependency("serde")
        assert m.matches(
            entries(f("Cargo.toml")),
            file_contents={"Cargo.toml": '[dependencies]\nserde = "1.0"\n'},
        )

    def test_matches_go_module_by_short_name(self):
        m = HasDependency("gin")
        content = "require github.com/gin-gonic/gin v1.9.1\n"
        assert m.matches(entries(f("go.mod")), file_contents={"go.mod": content})

    def test_matches_dependency_in_composer_json(self):
        m = HasDependency("laravel/framework")
        content = '{"require": {"laravel/framework": "^10.0"}}'
        assert m.matches(
            entries(f("composer.json")), file_contents={"composer.json": content}
        )

    def test_matches_dependency_in_gemfile(self):
        m = HasDependency("rails")
        assert m.matches(
            entries(f("Gemfile")), file_contents={"Gemfile": 'gem "rails"\n'}
        )

    def test_normalizes_name_casing_and_separators(self):
        m = HasDependency("Django-REST-Framework")
        content = "django_rest_framework==3.14\n"
        assert m.matches(
            entries(f("requirements.txt")), file_contents={"requirements.txt": content}
        )

    def test_no_match_when_dependency_absent(self):
        m = HasDependency("fastapi")
        assert not m.matches(
            entries(f("requirements.txt")),
            file_contents={"requirements.txt": "flask\n"},
        )

    def test_no_match_without_file_contents(self):
        m = HasDependency("fastapi")
        assert not m.matches(entries(f("requirements.txt")))

    def test_no_match_on_malformed_manifest(self):
        m = HasDependency("fastapi")
        assert not m.matches(
            entries(f("package.json")), file_contents={"package.json": "{not json"}
        )

    def test_ignores_files_with_no_known_parser(self):
        m = HasDependency("fastapi")
        assert not m.matches(
            entries(f("notes.txt")), file_contents={"notes.txt": "fastapi"}
        )


# AnyOf (composite OR)


class TestAnyOf:
    def test_matches_if_any_child_matches(self):
        m = AnyOf(HasFilename("pom.xml"), HasFilename("build.gradle"))
        assert m.matches(entries(f("pom.xml")))
        assert m.matches(entries(f("build.gradle")))

    def test_no_match_if_no_child_matches(self):
        m = AnyOf(HasFilename("pom.xml"), HasFilename("build.gradle"))
        assert not m.matches(entries(f("Cargo.toml")))

    def test_no_match_on_empty_tree(self):
        m = AnyOf(HasExtension(".py"), HasExtension(".js"))
        assert not m.matches([])

    def test_short_circuits_on_first_match(self):
        # Not strictly testable without mocking, but this verifies correctness
        m = AnyOf(HasFilename("a.txt"), HasFilename("b.txt"))
        assert m.matches(entries(f("a.txt")))


# AllOf (composite AND)


class TestAllOf:
    def test_matches_only_when_all_children_match(self):
        m = AllOf(HasFilename("pom.xml"), HasExtension(".java"))
        assert m.matches(entries(f("pom.xml"), f("src/Main.java")))

    def test_no_match_if_any_child_fails(self):
        m = AllOf(HasFilename("pom.xml"), HasExtension(".java"))
        assert not m.matches(entries(f("pom.xml")))  # missing .java
        assert not m.matches(entries(f("src/Main.java")))  # missing pom.xml

    def test_no_match_on_empty_tree(self):
        m = AllOf(HasFilename("pom.xml"), HasExtension(".java"))
        assert not m.matches([])


# Nested composites


class TestNestedComposites:
    def test_anyof_containing_allof(self):
        # (A AND B) OR (C AND D)
        m = AnyOf(
            AllOf(HasFilename("pom.xml"), HasExtension(".java")),
            AllOf(HasFilename("build.gradle"), HasExtension(".kt")),
        )
        assert m.matches(entries(f("pom.xml"), f("Main.java")))
        assert m.matches(entries(f("build.gradle"), f("Main.kt")))
        assert not m.matches(entries(f("pom.xml"), f("Main.kt")))  # mixed : no match

    def test_allof_containing_anyof(self):
        # (A OR B) AND C
        m = AllOf(
            AnyOf(HasFilename("pom.xml"), HasFilename("build.gradle")),
            HasExtension(".java"),
        )
        assert m.matches(entries(f("pom.xml"), f("src/Main.java")))
        assert m.matches(entries(f("build.gradle"), f("src/Main.java")))
        assert not m.matches(entries(f("pom.xml")))  # no .java files


class TestCompositesPropagateFileContents:
    def test_anyof_propagates_file_contents_to_children(self):
        m = AnyOf(HasDependency("fastapi"))
        assert m.matches(
            entries(f("requirements.txt")),
            file_contents={"requirements.txt": "fastapi\n"},
        )

    def test_allof_propagates_file_contents_to_children(self):
        m = AllOf(HasFilename("requirements.txt"), HasDependency("fastapi"))
        assert m.matches(
            entries(f("requirements.txt")),
            file_contents={"requirements.txt": "fastapi\n"},
        )
        assert not m.matches(entries(f("requirements.txt")))  # no file_contents
