"""
Unit tests which can be done without loading `libjulia`.
"""

from julia.find_libpython import finding_libpython


def test_smoke_finding_libpython():
    paths = list(finding_libpython())
    assert set(map(type, paths)) == {str}
