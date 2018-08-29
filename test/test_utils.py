"""
Unit tests which can be done without loading `libjulia`.
"""

from julia.find_libpython import finding_libpython


def test_finding_libpython_yield_type():
    paths = list(finding_libpython())
    assert set(map(type, paths)) <= {str}
# In a statically linked Python executable, no paths may be found.  So
# let's just check returned type of finding_libpython.
