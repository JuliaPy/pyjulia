import os

import pytest

only_in_ci = pytest.mark.skipif(
    os.environ.get("CI", "false").lower() != "true", reason="CI=true not set"
)
"""
Tests that are too destructive or slow to run with casual `tox` call.
"""
