import platform

import pytest

from julia.find_libpython import finding_libpython, linked_libpython
from julia.core import determine_if_statically_linked

try:
    unicode
except NameError:
    unicode = str  # for Python 3


def test_finding_libpython_yield_type():
    paths = list(finding_libpython())
    assert set(map(type, paths)) <= {str, unicode}
# In a statically linked Python executable, no paths may be found.  So
# let's just check returned type of finding_libpython.


@pytest.mark.xfail(platform.system() == "Windows",
                   reason="linked_libpython is not implemented for Windows")
def test_linked_libpython():
    if determine_if_statically_linked():
        assert linked_libpython() is not None
