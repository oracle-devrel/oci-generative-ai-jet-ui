"""Every language: the files each is detected for, and the fixture files that must not parse."""

import pytest

from golestan_code_mcp.parsing import chunks as parsing_chunks

from parsing.languages.helpers import parsed


# --- TypeScript, TSX, C and C++ (US2) ---


@pytest.mark.parametrize(("path", "language"), [
    ("a.ts", "typescript"), ("a.mts", "typescript"), ("a.cts", "typescript"), ("App.tsx", "tsx"), ("a.c", "c"),
    ("a.h", "cpp"), ("a.cpp", "cpp"), ("a.cc", "cpp"), ("a.cxx", "cpp"), ("a.c++", "cpp"), ("a.hpp", "cpp"),
    ("a.hh", "cpp"), ("a.hxx", "cpp"),
])
def test_us2_files(path, language):
    assert parsing_chunks.detect_language(path) == language


@pytest.mark.parametrize(("language", "rel"), [
    ("typescript", "typescript/src/broken.ts"), ("tsx", "tsx/Bad.tsx"), ("c", "c/broken.c"), ("cpp", "cpp/broken.cpp")])
def test_us2_files_that_do_not_parse(language, rel):
    assert parsed(language, rel) is None


@pytest.mark.parametrize(("path", "language"), [
    ("Order.java", "java"), ("Order.kt", "kotlin"), ("build.gradle.kts", "kotlin"), ("lib.rs", "rust")])
def test_us4_files(path, language):
    assert parsing_chunks.detect_language(path) == language


@pytest.mark.parametrize(("language", "rel"), [
    ("java", "java/Broken.java"), ("kotlin", "kotlin/OneLine.kt"), ("rust", "rust/src/broken.rs")])
def test_us4_files_that_do_not_parse(language, rel):
    assert parsed(language, rel) is None  # OneLine.kt: the grammar's known one-line-body limit (research R1)


# --- PHP, Ruby and Swift (US5) ---


@pytest.mark.parametrize(("path", "language"), [
    ("Repo.php", "php"), ("parser.rb", "ruby"), ("tasks.rake", "ruby"), ("Rakefile", "ruby"), ("app/Gemfile", "ruby"),
    ("Shapes.swift", "swift")])
def test_us5_files(path, language):
    assert parsing_chunks.detect_language(path) == language


@pytest.mark.parametrize(("language", "rel"), [
    ("php", "php/broken.php"), ("ruby", "ruby/broken.rb"), ("swift", "swift/Broken.swift")])
def test_us5_files_that_do_not_parse(language, rel):
    assert parsed(language, rel) is None
