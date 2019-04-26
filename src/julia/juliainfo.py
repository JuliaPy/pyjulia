from __future__ import absolute_import, print_function

import os
import subprocess
import sys
import warnings
from logging import getLogger  # see `.core.logger`

from .find_libpython import linked_libpython

try:
    from os.path import samefile
except ImportError:
    # For Python < 3.2 in Windows:
    def samefile(f1, f2):
        a = os.path.realpath(os.path.normcase(f1))
        b = os.path.realpath(os.path.normcase(f2))
        return a == b


logger = getLogger("julia")


class JuliaInfo(object):
    """
    Information required for initializing Julia runtime.

    Examples
    --------
    >>> from julia.api import JuliaInfo
    >>> info = JuliaInfo.load()
    >>> info = JuliaInfo.load(julia="julia")  # equivalent
    >>> info = JuliaInfo.load(julia="PATH/TO/julia")       # doctest: +SKIP
    >>> info.julia
    'julia'
    >>> info.sysimage                                      # doctest: +SKIP
    '/home/user/julia/lib/julia/sys.so'
    >>> info.python                                        # doctest: +SKIP
    '/usr/bin/python3'
    >>> info.is_compatible_python()                        # doctest: +SKIP
    True

    Attributes
    ----------
    julia : str
        Path to a Julia executable from which information was retrieved.
    bindir : str
        ``Sys.BINDIR`` of `julia`.
    libjulia_path : str
        Path to libjulia.
    sysimage : str
        Path to system image.
    python : str
        Python executable with which PyCall.jl is configured.
    libpython_path : str
        libpython path used by PyCall.jl.
    """

    @classmethod
    def load(cls, julia="julia", **popen_kwargs):
        """
        Get basic information from `julia`.
        """

        juliainfo_script = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "juliainfo.jl"
        )
        proc = subprocess.Popen(
            [julia, "--startup-file=no", juliainfo_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            **popen_kwargs
        )

        stdout, stderr = proc.communicate()
        retcode = proc.wait()
        if retcode != 0:
            logger.debug("STDOUT from %s:\n%s", julia, stdout)
            logger.debug("STDERR from %s:\n%s", julia, stderr)
            if sys.version_info[0] < 3:
                output = "\n".join(["STDOUT:", stdout, "STDERR:", stderr])
                raise subprocess.CalledProcessError(
                    retcode, [julia, "-e", "..."], output
                )
            else:
                raise subprocess.CalledProcessError(
                    retcode, [julia, "-e", "..."], stdout, stderr
                )

        stderr = stderr.strip()
        if stderr:
            warnings.warn("{} warned:\n{}".format(julia, stderr))

        args = stdout.rstrip().split("\n")

        return cls(julia, *args)

    def __init__(
        self,
        julia,
        version_raw,
        version_major,
        version_minor,
        version_patch,
        bindir=None,
        libjulia_path=None,
        sysimage=None,
        python=None,
        libpython_path=None,
    ):
        self.julia = julia
        self.bindir = bindir
        self.libjulia_path = libjulia_path
        self.sysimage = sysimage

        version_major = int(version_major)
        version_minor = int(version_minor)
        version_patch = int(version_patch)
        self.version_raw = version_raw
        self.version_major = version_major
        self.version_minor = version_minor
        self.version_patch = version_patch
        self.version_info = (version_major, version_minor, version_patch)

        self.python = python
        self.libpython_path = libpython_path

        logger.debug("pyprogramname = %s", python)
        logger.debug("sys.executable = %s", sys.executable)
        logger.debug("bindir = %s", bindir)
        logger.debug("libjulia_path = %s", libjulia_path)

    def is_pycall_built(self):
        return bool(self.libpython_path)

    def is_compatible_python(self):
        """
        Check if python used by PyCall.jl is compatible with `sys.executable`.
        """
        return self.libpython_path and is_compatible_exe(self.libpython_path)


def is_compatible_exe(jl_libpython):
    """
    Determine if `libpython` is compatible with this Python.

    Current Python executable is considered compatible if it is dynamically
    linked to libpython and both of them are using identical libpython.  If
    this function returns `True`, PyJulia use the same precompilation cache
    of PyCall.jl used by Julia itself.
    """
    py_libpython = linked_libpython()
    logger.debug("py_libpython = %s", py_libpython)
    logger.debug("jl_libpython = %s", jl_libpython)
    dynamically_linked = py_libpython is not None
    return dynamically_linked and samefile(py_libpython, jl_libpython)
    # `py_libpython is not None` here for checking if this Python
    # executable is dynamically linked or not (`py_libpython is None`
    # if it's statically linked).  `jl_libpython` may be `None` if
    # libpython used for PyCall is removed so we can't expect
    # `jl_libpython` to be a `str` always.
