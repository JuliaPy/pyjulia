import os
import sys

import pytest

is_windows = os.name == "nt"
is_apple = sys.platform == "darwin"
in_github_actions = os.environ.get("GITHUB_ACTIONS", "false").lower() == "true"

only_in_ci = pytest.mark.skipif(
    os.environ.get("CI", "false").lower() != "true", reason="CI=true not set"
)
"""
Tests that are too destructive or slow to run with casual `tox` call.
"""

skip_in_windows = pytest.mark.skipif(is_windows, reason="Running in Windows")
"""
Tests that are known to fail in Windows.
"""

skip_in_apple = pytest.mark.skipif(is_apple, reason="Running in macOS")
"""
Tests that are known to fail in macOS.
"""

skip_in_github_actions_windows = pytest.mark.skipif(
    is_windows and in_github_actions, reason="Running in Windows in GitHub Actions"
)
"""
Tests that are known to fail in Windows in GitHub Actions.
"""
