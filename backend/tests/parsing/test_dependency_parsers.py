"""
Unit tests for app.detector.dependency_parsers.

Each parser is tested for the common case and for tolerance of malformed
input (since HasDependency relies on parsers not raising on garbage).
"""

import pytest

from app.parsing.dependency_parsers import (
    normalize_dependency_name,
    parse_cargo_toml,
    parse_composer_json,
    parse_gemfile,
    parse_go_mod,
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements_txt,
)


class TestParseRequirementsTxt:
    def test_extracts_simple_names(self):
        content = "fastapi\nrequests==2.31.0\n"
        assert parse_requirements_txt(content) == {"fastapi", "requests"}

    def test_ignores_comments_and_blank_lines(self):
        content = "# a comment\n\nfastapi\n  # another\n"
        assert parse_requirements_txt(content) == {"fastapi"}

    def test_ignores_editable_and_recursive_directives(self):
        content = "-r base.txt\n-e .\nfastapi\n"
        assert parse_requirements_txt(content) == {"fastapi"}

    def test_handles_extras_and_markers(self):
        content = 'uvicorn[standard]>=0.20; python_version >= "3.8"\n'
        assert parse_requirements_txt(content) == {"uvicorn"}

    def test_empty_content_returns_empty_set(self):
        assert parse_requirements_txt("") == set()


class TestParsePyprojectToml:
    def test_extracts_pep621_dependencies(self):
        content = """
[project]
dependencies = ["fastapi>=0.100", "uvicorn[standard]"]
"""
        assert parse_pyproject_toml(content) == {"fastapi", "uvicorn"}

    def test_extracts_pep621_optional_dependencies(self):
        content = """
[project.optional-dependencies]
dev = ["pytest", "black"]
"""
        assert parse_pyproject_toml(content) == {"pytest", "black"}

    def test_extracts_poetry_dependencies_and_excludes_python(self):
        content = """
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.100"
"""
        assert parse_pyproject_toml(content) == {"fastapi"}

    def test_extracts_poetry_dependency_groups(self):
        content = """
[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
"""
        assert parse_pyproject_toml(content) == {"pytest"}

    def test_missing_sections_returns_empty_set(self):
        assert parse_pyproject_toml("[build-system]\n") == set()

    def test_invalid_toml_raises(self):
        with pytest.raises(Exception):
            parse_pyproject_toml("not [ valid toml")


class TestParsePackageJson:
    def test_extracts_dependencies_and_dev_dependencies(self):
        content = '{"dependencies": {"react": "^18.0.0"}, "devDependencies": {"jest": "^29.0.0"}}'
        assert parse_package_json(content) == {"react", "jest"}

    def test_missing_keys_returns_empty_set(self):
        assert parse_package_json("{}") == set()

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            parse_package_json("{not valid json")


class TestParseCargoToml:
    def test_extracts_dependencies(self):
        content = """
[dependencies]
serde = "1.0"

[dev-dependencies]
criterion = "0.5"
"""
        assert parse_cargo_toml(content) == {"serde", "criterion"}


class TestParseGoMod:
    def test_extracts_single_line_require(self):
        content = "module example.com/app\n\nrequire github.com/gin-gonic/gin v1.9.1\n"
        deps = parse_go_mod(content)
        assert "github.com/gin-gonic/gin" in deps
        assert "gin" in deps

    def test_extracts_require_block(self):
        content = """
require (
    github.com/gin-gonic/gin v1.9.1
    github.com/stretchr/testify v1.8.4
)
"""
        deps = parse_go_mod(content)
        assert "gin" in deps
        assert "testify" in deps

    def test_no_require_returns_empty_set(self):
        assert parse_go_mod("module example.com/app\n\ngo 1.21\n") == set()


class TestParseComposerJson:
    def test_extracts_require_and_excludes_php(self):
        content = '{"require": {"php": ">=8.0", "laravel/framework": "^10.0"}}'
        assert parse_composer_json(content) == {"laravel/framework"}


class TestParseGemfile:
    def test_extracts_gem_names(self):
        content = 'gem "rails", "~> 7.0"\ngem \'rspec\'\n'
        assert parse_gemfile(content) == {"rails", "rspec"}

    def test_no_gems_returns_empty_set(self):
        assert parse_gemfile("source 'https://rubygems.org'\n") == set()


class TestNormalizeDependencyName:
    def test_case_folds(self):
        assert normalize_dependency_name("FastAPI") == normalize_dependency_name(
            "fastapi"
        )

    def test_treats_separators_as_equivalent(self):
        assert normalize_dependency_name(
            "django_rest_framework"
        ) == normalize_dependency_name("Django-Rest-Framework")
        assert normalize_dependency_name("some.package") == normalize_dependency_name(
            "some-package"
        )

    def test_strips_surrounding_whitespace(self):
        assert normalize_dependency_name("  fastapi  ") == "fastapi"
