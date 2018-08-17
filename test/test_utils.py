"""
Unit tests which can be done without loading `libjulia`.
"""

import sys

import pytest

from julia.core import is_different_exe


@pytest.mark.parametrize('pyprogramname, sys_executable, exe_differs', [
    (sys.executable, sys.executable, False),
    (None, sys.executable, True),
    ('/dev/null', sys.executable, True),
])
def test_is_different_exe(pyprogramname, sys_executable, exe_differs):
    assert is_different_exe(pyprogramname, sys_executable) == exe_differs
