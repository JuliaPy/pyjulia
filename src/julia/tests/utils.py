import os

import pytest

only_in_ci = pytest.mark.skipif(
    os.environ.get("CI", "false").lower() != "true", reason="CI=true not set"
)
"""
Tests that are too destructive or slow to run with casual `tox` call.
"""

skip_in_appveyor = pytest.mark.skipif(
    os.environ.get("APPVEYOR", "false").lower() == "true", reason="APPVEYOR=true is set"
)
"""
Tests that are known to fail in AppVeyor.
"""
