"""Shared test fixtures."""

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def tmp_cases_dir(tmp_path):
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    return cases_dir
