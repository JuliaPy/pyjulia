import subprocess
import sys

from julia.find_libpython import finding_libpython, linked_libpython

try:
    unicode
except NameError:
    unicode = str  # for Python 3


def test_finding_libpython_yield_type():
    paths = list(finding_libpython())
    assert set(map(type, paths)) <= {str, unicode}


# In a statically linked Python executable, no paths may be found.  So
# let's just check returned type of finding_libpython.


def determine_if_statically_linked():
    """Determines if this python executable is statically linked"""
    if not sys.platform.startswith("linux"):
        # Assuming that Windows and OS X are generally always
        # dynamically linked.  Note that this is not the case in
        # Python installed via conda:
        # https://github.com/JuliaPy/pyjulia/issues/150#issuecomment-432912833
        # However, since we do not use conda in our CI, this function
        # is OK to use in tests.
        return False
    lddoutput = subprocess.check_output(["ldd", sys.executable])
    return not (b"libpython" in lddoutput)


def test_linked_libpython():
    # TODO: Special-case conda (check `sys.version`).  See the above
    # comments in `determine_if_statically_linked.
    if not determine_if_statically_linked():
        assert linked_libpython() is not None
