from __future__ import print_function

import os
import sys
import traceback
from functools import wraps

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


def _retry_on_failure(*fargs, **kwargs):
    f = fargs[0]
    args = fargs[1:]
    for i in range(10):
        try:
            return f(*args, **kwargs)
        except Exception:
            print()
            print("{}-th try of {} failed".format(i, f))
            traceback.print_exc()
    return f(*args, **kwargs)


def retry_failing_if_windows(test):
    """
    Retry upon test failure if in Windows.

    This is an ugly workaround for occasional STATUS_ACCESS_VIOLATION failures
    in Windows: https://github.com/JuliaPy/pyjulia/issues/462
    """
    if not is_windows:
        return test

    @wraps(test)
    def repeater(*args, **kwargs):
        _retry_on_failure(test, *args, **kwargs)

    return repeater
