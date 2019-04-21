"""
Bridge Python and Julia by initializing the Julia runtime inside Python.
"""

#-----------------------------------------------------------------------------
# Copyright (C) 2013 The IPython and Julia Development Teams.
#
# Distributed under the terms of the BSD License. The full license is in
# the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
from __future__ import print_function, absolute_import

from logging import getLogger
# Not importing `logging` module here so that using `logging.debug`
# instead of `logger.debug` becomes an error.

import atexit
import ctypes
import ctypes.util
import os
import sys
import subprocess
import textwrap
import warnings

from ctypes import c_void_p as void_p
from ctypes import c_char_p as char_p
from ctypes import py_object, c_int, c_char_p, POINTER, pointer

try:
    from shutil import which
except ImportError:
    # For Python < 3.3; it should behave more-or-less similar to
    # shutil.which when used with single argument.
    from distutils.spawn import find_executable as which

try:
    from os.path import samefile
except ImportError:
    # For Python < 3.2 in Windows:
    def samefile(f1, f2):
        a = os.path.realpath(os.path.normcase(f1))
        b = os.path.realpath(os.path.normcase(f2))
        return a == b


# this is python 3.3 specific
from types import ModuleType

from .find_libpython import find_libpython, linked_libpython
from .options import JuliaOptions, options_docs, parse_jl_options
from .release import __version__
from .utils import is_windows

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)

#-----------------------------------------------------------------------------
# Classes and funtions
#-----------------------------------------------------------------------------
python_version = sys.version_info


logger = getLogger("julia")
_loghandler = None


def get_loghandler():
    """
    Get `logging.StreamHandler` private to PyJulia.
    """
    global _loghandler
    if _loghandler is None:
        import logging

        formatter = logging.Formatter("%(levelname)s %(message)s")

        _loghandler = logging.StreamHandler()
        _loghandler.setFormatter(formatter)

        logger.addHandler(_loghandler)
    return _loghandler


def set_loglevel(level):
    import logging

    get_loghandler()
    logger.setLevel(getattr(logging, level, level))


def enable_debug():
    set_loglevel("DEBUG")
    logger.debug("")  # flush whatever in the line
    logger.debug("Debug-level logging is enabled for PyJulia.")
    logger.debug("PyJulia version: %s", __version__)


# As setting up Julia modifies os.environ, we need to cache it for
# launching subprocesses later in the original environment.
_enviorn = os.environ.copy()


class JuliaError(Exception):
    """
    Wrapper for Julia exceptions.
    """


class JuliaNotFound(RuntimeError):
    def __init__(self, executable, kwargname):
        self.executable = executable
        self.kwargname = kwargname

    def __str__(self):
        return """\
Julia executable `{}` cannot be found.

If you have installed Julia, make sure Julia executable is in the
system PATH.  Alternatively, specify file path to the Julia executable
using `{}` keyword argument.

If you have not installed Julia, download Julia from
https://julialang.org/downloads/ and install it.
""".format(self.executable, self.kwargname)


def remove_prefix(string, prefix):
    return string[len(prefix):] if string.startswith(prefix) else string


def jl_name(name):
    if name.endswith('_b'):
        return name[:-2] + '!'
    return name


def py_name(name):
    if name.endswith('!'):
        return name[:-1] + '_b'
    return name


class JuliaModule(ModuleType):

    def __init__(self, loader, *args, **kwargs):
        super(JuliaModule, self).__init__(*args, **kwargs)
        self._julia = loader.julia
        self.__loader__ = loader

    @property
    def __all__(self):
        juliapath = remove_prefix(self.__name__, "julia.")
        names = set(self._julia.eval("names({})".format(juliapath)))
        names.discard(juliapath.rsplit('.', 1)[-1])
        return [py_name(n) for n in names if is_accessible_name(n)]

    def __dir__(self):
        if python_version.major == 2:
            names = set()
        else:
            names = set(super(JuliaModule, self).__dir__())
        names.update(self.__all__)
        return list(names)
    # Override __dir__ method so that completing member names work
    # well in Python REPLs like IPython.

    __path__ = ()
    # Declare that `JuliaModule` is a Python module since any Julia
    # module can have sub-modules.
    # See: https://docs.python.org/3/reference/import.html#package-path-rules

    def __getattr__(self, name):
        try:
            return self.__try_getattr(name)
        except AttributeError:
            if name.endswith("_b"):
                try:
                    return self.__try_getattr(jl_name(name))
                except AttributeError:
                    pass
            raise

    def __try_getattr(self, name):
        jl_module = remove_prefix(self.__name__, "julia.")
        jl_fullname = ".".join((jl_module, name))

        if isamodule(self._julia, jl_fullname):
            realname = self._julia.fullname(self._julia.eval(jl_fullname))
            if self._julia.isdefined(realname):
                return self.__loader__.load_module("julia." + realname)
            # Otherwise, it may be, e.g., "Main.anonymous", created by
            # Module().

        if isdefined(self._julia, jl_module, name):
            return self._julia.eval(jl_fullname)

        raise AttributeError(name)


class JuliaMainModule(JuliaModule):

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super(JuliaMainModule, self).__setattr__(name, value)
        else:
            juliapath = remove_prefix(self.__name__, "julia.")
            setter = '''
            PyCall.pyfunctionret(
                (x) -> Base.eval({}, :({} = $x)),
                Any,
                PyCall.PyAny)
            '''.format(juliapath, jl_name(name))
            self._julia.eval(setter)(value)

    help = property(lambda self: self._julia.help)
    eval = property(lambda self: self._julia.eval)
    using = property(lambda self: self._julia.using)


# add custom import behavior for the julia "module"
class JuliaImporter(object):

    # find_module was deprecated in v3.4
    def find_module(self, fullname, path=None):
        if fullname.startswith("julia."):
            filename = fullname.split(".", 2)[1]
            filepath = os.path.join(os.path.dirname(__file__), filename)
            if os.path.isfile(filepath + ".py") or os.path.isdir(filepath):
                return
            return JuliaModuleLoader()


class JuliaModuleLoader(object):

    @property
    def julia(self):
        self.__class__.julia = julia = Julia()
        return julia

    # load module was deprecated in v3.4
    def load_module(self, fullname):
        juliapath = remove_prefix(fullname, "julia.")
        if juliapath == 'Main':
            return sys.modules.setdefault(fullname,
                                          JuliaMainModule(self, fullname))
        elif isafunction(self.julia, juliapath):
            return self.julia.eval(juliapath)

        try:
            self.julia.eval("import {}".format(juliapath.split(".", 1)[0]))
        except JuliaError:
            pass
        else:
            if isamodule(self.julia, juliapath):
                return sys.modules.setdefault(fullname,
                                              JuliaModule(self, fullname))

        raise ImportError("{} not found".format(juliapath))


def ismacro(name):
    """ Is the name a macro?

    >>> ismacro('@time')
    True
    >>> ismacro('sum')
    False
    """
    return name.startswith("@")


def isoperator(name):
    return not name[0].isalpha()


def isprotected(name):
    return name.startswith("_")


def notascii(name):
    try:
        name.encode("ascii")
        return False
    except:
        return True


def is_accessible_name(name):
    """
    Check if a Julia variable `name` is (easily) accessible from Python.

    Return `True` if `name` can be safely converted to a Python
    identifier using `py_name` function.  For example,

    >>> is_accessible_name('A_mul_B!')
    True

    Since it can be accessed as `A_mul_B_b` in Python.
    """
    return not (ismacro(name) or
                isoperator(name) or
                isprotected(name) or
                notascii(name))


def isdefined(julia, parent, member):
    return julia.eval("isdefined({}, :({}))".format(parent, member))


def isamodule(julia, julia_name):
    try:
        return julia.eval("isa({}, Module)".format(julia_name))
    except JuliaError:
        return False  # assuming this is an `UndefVarError`


def isafunction(julia, julia_name, mod_name=""):
    code = "isa({}, Function)".format(julia_name)
    if mod_name:
        code = "isa({}.{}, Function)".format(mod_name, julia_name)
    try:
        return julia.eval(code)
    except:
        return False


def determine_if_statically_linked():
    """Determines if this python executable is statically linked"""
    return linked_libpython() is None


juliainfo_script = """
println(VERSION < v"0.7.0-DEV.3073" ? JULIA_HOME : Base.Sys.BINDIR)
if VERSION >= v"0.7.0-DEV.3630"
    using Libdl
    using Pkg
end
println(Libdl.dlpath(string("lib", splitext(Base.julia_exename())[1])))
println(unsafe_string(Base.JLOptions().image_file))

println(VERSION)
println(VERSION.major)
println(VERSION.minor)
println(VERSION.patch)

if VERSION < v"0.7.0"
    PyCall_depsfile = Pkg.dir("PyCall","deps","deps.jl")
else
    pkg = Base.PkgId(Base.UUID(0x438e738f_606a_5dbb_bf0a_cddfbfd45ab0), "PyCall")
    modpath = Base.locate_package(pkg)
    if modpath == nothing
        PyCall_depsfile = nothing
    else
        PyCall_depsfile = joinpath(dirname(modpath),"..","deps","deps.jl")
    end
end
if PyCall_depsfile !== nothing && isfile(PyCall_depsfile)
    include(PyCall_depsfile)
    println(pyprogramname)
    println(libpython)
end
"""


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

        # Use the original environment variables to avoid a cryptic
        # error "fake-julia/../lib/julia/sys.so: cannot open shared
        # object file: No such file or directory":
        popen_kwargs.setdefault("env", _enviorn)

        proc = subprocess.Popen(
            [julia, "--startup-file=no", "-e", juliainfo_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            **popen_kwargs)

        stdout, stderr = proc.communicate()
        retcode = proc.wait()
        if retcode != 0:
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

    def __init__(self, julia, bindir, libjulia_path, sysimage,
                 version_raw, version_major, version_minor, version_patch,
                 python=None, libpython_path=None):
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


def setup_libjulia(libjulia):
    # Store the running interpreter reference so we can start using it via self.call
    libjulia.jl_.argtypes = [void_p]
    libjulia.jl_.restype = None

    # Set the return types of some of the bridge functions in ctypes terminology
    libjulia.jl_eval_string.argtypes = [char_p]
    libjulia.jl_eval_string.restype = void_p

    libjulia.jl_exception_occurred.restype = void_p
    libjulia.jl_typeof_str.argtypes = [void_p]
    libjulia.jl_typeof_str.restype = char_p
    libjulia.jl_call2.argtypes = [void_p, void_p, void_p]
    libjulia.jl_call2.restype = void_p
    libjulia.jl_get_field.argtypes = [void_p, char_p]
    libjulia.jl_get_field.restype = void_p
    libjulia.jl_typename_str.restype = char_p
    libjulia.jl_unbox_voidpointer.argtypes = [void_p]
    libjulia.jl_unbox_voidpointer.restype = py_object

    for c_type in UNBOXABLE_TYPES:
        jl_unbox = getattr(libjulia, "jl_unbox_{}".format(c_type))
        jl_unbox.argtypes = [void_p]
        jl_unbox.restype = getattr(ctypes, "c_{}".format({
            "float32": "float",
            "float64": "double",
        }.get(c_type, c_type)))

    libjulia.jl_typeof.argtypes = [void_p]
    libjulia.jl_typeof.restype = void_p

    libjulia.jl_exception_clear.restype = None
    libjulia.jl_stderr_obj.argtypes = []
    libjulia.jl_stderr_obj.restype = void_p
    libjulia.jl_stderr_stream.argtypes = []
    libjulia.jl_stderr_stream.restype = void_p
    libjulia.jl_printf.restype = ctypes.c_int

    libjulia.jl_parse_opts.argtypes = [POINTER(c_int),
                                       POINTER(POINTER(c_char_p))]
    libjulia.jl_set_ARGS.argtypes = [c_int, POINTER(c_char_p)]
    libjulia.jl_is_initialized.argtypes = []
    libjulia.jl_is_initialized.restype = ctypes.c_int
    libjulia.jl_atexit_hook.argtypes = [ctypes.c_int]


try:
    # A hack to make `_LIBJULIA` survive reload:
    _LIBJULIA
except NameError:
    _LIBJULIA = None
# Ugly hack to register the julia interpreter globally so we can reload
# this extension without trying to re-open the shared lib, which kills
# the python interpreter. Nasty but useful while debugging


def set_libjulia(libjulia):
    # Flag process-wide that Julia is initialized and store the actual
    # runtime interpreter, so we can reuse it across calls and module
    # reloads.
    global _LIBJULIA
    _LIBJULIA = libjulia


def get_libjulia():
    return _LIBJULIA


class BaseLibJulia(object):

    def __getattr__(self, name):
        return getattr(self.libjulia, name)


class LibJulia(BaseLibJulia):
    """
    Low-level interface to `libjulia` C-API.

    Examples
    --------
    >>> from julia.api import LibJulia, JuliaInfo

    An easy way to create a `LibJulia` object is `LibJulia.load`:

    >>> api = LibJulia.load()                              # doctest: +SKIP

    Or, equivalently,

    >>> api = LibJulia.load(julia="julia")                 # doctest: +SKIP
    >>> api = LibJulia.from_juliainfo(JuliaInfo.load())    # doctest: +SKIP

    You can pass a path to the Julia executable using `julia` keyword
    argument:

    >>> api = LibJulia.load(julia="PATH/TO/CUSTOM/julia")  # doctest: +SKIP

    .. Do not run doctest with non-default libjulia.so.
       >>> _ = getfixture("julia")
       >>> api = get_libjulia()

    Path to the system image can be configured before initializing Julia:

    >>> api.sysimage                                       # doctest: +SKIP
    '/home/user/julia/lib/julia/sys.so'
    >>> api.sysimage = "PATH/TO/CUSTOM/sys.so"             # doctest: +SKIP

    Finally, the Julia runtime can be initialized using `LibJulia.init_julia`.
    Note that only the first call to this function in the current Python
    process takes effect.

    >>> api.init_julia()

    Any command-line options supported by Julia can be passed to
    `init_julia`:

    >>> api.init_julia(["--compiled-modules=no", "--optimize=3"])

    Once `init_julia` is called, any subsequent use of `Julia` API
    (thus also ``from julia import <JuliaModule>`` etc.) uses this
    initialized Julia runtime.

    `LibJulia` can be used to access Julia's C-API:

    >>> ret = api.jl_eval_string(b"Int64(1 + 2)")
    >>> int(api.jl_unbox_int64(ret))
    3

    However, a proper use of the C-API is more involved and presumably
    very challenging without C macros.  See also:
    https://docs.julialang.org/en/latest/manual/embedding/

    Attributes
    ----------
    libjulia_path : str
        Path to libjulia.
    bindir : str
        ``Sys.BINDIR`` of `julia`.  This is passed to
        `jl_init_with_image` unless overridden by argument ``option``
        to `init_julia`.
    sysimage : str
        Path to system image.  This is passed to `jl_init_with_image`
        unless overridden by argument ``option`` to `init_julia`.

        If `sysimage` is a relative path, it is interpreted relative
        to the current directory (rather than relative to the Julia
        `bindir` as in the `jl_init_with_image` C API).
    """

    @classmethod
    def load(cls, **kwargs):
        """
        Create `LibJulia` based on information retrieved with `JuliaInfo.load`.

        This classmethod runs `JuliaInfo.load` to retrieve information about
        `julia` runtime.  This information is used to intialize `LibJulia`.
        """
        return cls.from_juliainfo(JuliaInfo.load(**kwargs))

    @classmethod
    def from_juliainfo(cls, juliainfo):
        return cls(
            libjulia_path=juliainfo.libjulia_path,
            bindir=juliainfo.bindir,
            sysimage=juliainfo.sysimage,
        )

    def __init__(self, libjulia_path, bindir, sysimage):
        self.libjulia_path = libjulia_path
        self.bindir = bindir
        self.sysimage = sysimage

        if not os.path.exists(libjulia_path):
            raise RuntimeError("Julia library (\"libjulia\") not found! {}".format(libjulia_path))

        # fixes a specific issue with python 2.7.13
        # ctypes.windll.LoadLibrary refuses unicode argument
        # http://bugs.python.org/issue29294
        if sys.version_info >= (2, 7, 13) and sys.version_info < (2, 7, 14):
            libjulia_path = libjulia_path.encode("ascii")

        self.libjulia = ctypes.PyDLL(libjulia_path, ctypes.RTLD_GLOBAL)
        setup_libjulia(self.libjulia)

    @property
    def jl_init_with_image(self):
        try:
            return self.libjulia.jl_init_with_image
        except AttributeError:
            return self.libjulia.jl_init_with_image__threading

    def init_julia(self, options=None):
        """
        Initialize `libjulia`.  Calling this method twice is a no-op.

        It calls `jl_init_with_image` (or `jl_init_with_image__threading`)
        but makes sure that it is called only once for each process.

        Parameters
        ----------
        options : sequence of `str` or `JuliaOptions`
            This is passed as command line options to the Julia runtime.

            .. warning::

                Any invalid command line option terminates the entire
                Python process.
        """
        if get_libjulia():
            return

        if hasattr(options, "as_args"):  # JuliaOptions
            options = options.as_args()
        if options:
            # Let's materialize it here in case it's an iterator.
            options = list(options)
        # Record `options`.  It's not used anywhere at the moment but
        # may be useful for debugging.
        self.options = options

        if options:
            ns = parse_jl_options(options)
            if ns.home:
                self.bindir = ns.home
            if ns.sysimage:
                self.sysimage = ns.sysimage

        # Julia tries to interpret `sysimage` as a relative path and
        # aborts if not found.  Turning it to absolute path here.
        # Mutating `self.sysimage` so that the actual path used can be
        # retrieved later.
        if not os.path.isabs(self.sysimage):
            self.sysimage = os.path.realpath(self.sysimage)

        jl_init_path = self.bindir
        sysimage = self.sysimage

        if not os.path.isdir(jl_init_path):
            raise RuntimeError("jl_init_path (bindir) {} is not a directory".format(jl_init_path))
        if not os.path.exists(sysimage):
            raise RuntimeError("System image {} does not exist".format(sysimage))

        if options:
            assert not isinstance(options, str)
            # It seems that `argv_list[0]` is ignored and
            # `sys.executable` is used anyway:
            argv_list = [sys.executable]
            argv_list.extend(options)
            if sys.version_info[0] >= 3:
                argv_list = [s.encode('utf-8') for s in argv_list]

            argc = c_int(len(argv_list))
            argv = POINTER(char_p)((char_p * len(argv_list))(*argv_list))

            logger.debug("argv_list = %r", argv_list)
            logger.debug("argc = %r", argc)
            self.libjulia.jl_parse_opts(pointer(argc), pointer(argv))
            logger.debug("jl_parse_opts called")
            logger.debug("argc = %r", argc)
            for i in range(argc.value):
                logger.debug("argv[%d] = %r", i, argv[i])

        logger.debug("calling jl_init_with_image(%s, %s)", jl_init_path, sysimage)
        self.jl_init_with_image(jl_init_path.encode("utf-8"), sysimage.encode("utf-8"))
        logger.debug("seems to work...")

        set_libjulia(self)

        self.libjulia.jl_exception_clear()

        if options:
            # This doesn't seem to be working.
            self.libjulia.jl_set_ARGS(argc, argv)


class InProcessLibJulia(BaseLibJulia):

    def __init__(self):
        # we're assuming here we're fully inside a running Julia process,
        # so we're fishing for symbols in our own process table
        self.libjulia = ctypes.PyDLL(None)

        setup_libjulia(self.libjulia)
        set_libjulia(self)


_separate_cache_error_common_header = """\
It seems your Julia and PyJulia setup are not supported.

Julia executable:
    {runtime}
Python interpreter and libpython used by PyCall.jl:
    {jlinfo.python}
    {jl_libpython}
Python interpreter used to import PyJulia and its libpython.
    {sys.executable}
    {py_libpython}
"""


_separate_cache_error_common_footer = """
For more information, see:

    https://pyjulia.readthedocs.io/en/latest/troubleshooting.html
"""


_separate_cache_error_statically_linked = """
Your Python interpreter "{sys.executable}"
is statically linked to libpython.  Currently, PyJulia does not fully
support such Python interpreter.

The easiest workaround is to pass `compiled_modules=False` to `Julia`
constructor.  To do so, first *reboot* your Python REPL (if this happened
inside an interactive session) and then evaluate:

    >>> from julia.api import Julia
    >>> jl = Julia(compiled_modules=False)

Another workaround is to run your Python script with `python-jl`
command bundled in PyJulia.  You can simply do:

    $ python-jl PATH/TO/YOUR/SCRIPT.py

See `python-jl --help` for more information.
"""


_separate_cache_error_incompatible_libpython = """
In Julia >= 0.7, above two paths to `libpython` have to match exactly
in order for PyJulia to work out-of-the-box.  To configure PyCall.jl to use
Python interpreter "{sys.executable}",
run the following code in the Python REPL:

    >>> import julia
    >>> julia.install()
"""


def raise_separate_cache_error(
        runtime, jlinfo,
        # For test:
        _determine_if_statically_linked=determine_if_statically_linked):
    template = _separate_cache_error_common_header
    if _determine_if_statically_linked():
        template += _separate_cache_error_statically_linked
    else:
        template += _separate_cache_error_incompatible_libpython
    template += _separate_cache_error_common_footer
    message = template.format(
        runtime=runtime,
        jlinfo=jlinfo,
        py_libpython=find_libpython(),
        jl_libpython=jlinfo.libpython_path,
        sys=sys)
    raise RuntimeError(message)


UNBOXABLE_TYPES = (
    'bool',
    'int8',
    'uint8',
    'int16',
    'uint16',
    'int32',
    'uint32',
    'int64',
    'uint64',
    'float32',
    'float64',
)


class Julia(object):
    """
    Implements a bridge to the Julia runtime.
    This uses the Julia PyCall module to perform type conversions and allow
    full access to the entire Julia runtime.
    """

    def __init__(self, init_julia=True, jl_init_path=None, runtime=None,
                 jl_runtime_path=None, debug=False, **julia_options):
        """
        Create a Python object that represents a live Julia runtime.

        Note: Use `LibJulia` to fully control the initialization of
        the Julia runtime.

        Parameters
        ==========

        init_julia : bool
            If True, try to initialize the Julia runtime. If this code is
            being called from inside an already running Julia, the flag should
            be passed as False so the interpreter isn't re-initialized.

            Note that it is safe to call this class constructor twice in the
            same process with `init_julia` set to True, as a global reference
            is kept to avoid re-initializing it. The purpose of the flag is
            only to manage situations when Julia was initialized from outside
            this code.

        runtime : str
            Custom Julia binary, e.g. "/usr/local/bin/julia" or "julia-1.0.0".

        debug : bool
            If True, print some debugging information to STDERR
        """
        # Note: `options_docs` is appended below (top level)

        if debug:
            enable_debug()

        if jl_runtime_path is not None:
            warnings.warn(
                "`jl_runtime_path` is deprecated. Please use `runtime`.",
                DeprecationWarning)

        if not init_julia and runtime is None and is_windows:
            warnings.warn(
                "It is recommended to pass `runtime` when `init_julia=False` in Windows"
            )

        if runtime is None:
            if jl_runtime_path is None:
                runtime = "julia"
            else:
                runtime = jl_runtime_path
        else:
            if jl_runtime_path is None:
                jl_runtime_path = which(runtime)
                if jl_runtime_path is None:
                    raise JuliaNotFound(runtime, kwargname="runtime")
            else:
                raise TypeError(
                    "Both `runtime` and `jl_runtime_path` are specified.")

        if jl_init_path:
            warnings.warn(
                "`jl_init_path` is deprecated. Please use `bindir`.",
                DeprecationWarning)
            if "bindir" in julia_options:
                raise TypeError("Both `jl_init_path` and `bindir` are specified.")

        logger.debug("")  # so that debug message is shown nicely w/ pytest

        if get_libjulia():
            # Use pre-existing `LibJulia`.
            self.api = get_libjulia()
        elif init_julia:
            jlinfo = JuliaInfo.load(runtime)
            self.api = LibJulia.from_juliainfo(jlinfo)

            if jl_init_path:
                self.api.bindir = jl_init_path

            options = JuliaOptions(**julia_options)

            use_separate_cache = not (
                options.compiled_modules == "no" or jlinfo.is_compatible_python()
            )
            logger.debug("use_separate_cache = %s", use_separate_cache)
            if use_separate_cache:
                PYCALL_JULIA_HOME = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)), "fake-julia").replace("\\", "\\\\")
                os.environ["JULIA_HOME"] = PYCALL_JULIA_HOME  # TODO: this line can be removed when dropping Julia v0.6
                os.environ["JULIA_BINDIR"] = PYCALL_JULIA_HOME
                self.api.bindir = PYCALL_JULIA_HOME

            was_initialized = self.api.jl_is_initialized()
            if was_initialized:
                set_libjulia(self.api)
            else:
                self.api.init_julia(options)

            if use_separate_cache:
                if jlinfo.version_info < (0, 6):
                    raise RuntimeError(
                        "PyJulia does not support Julia < 0.6 anymore")
                elif jlinfo.version_info >= (0, 7):
                    raise_separate_cache_error(runtime, jlinfo)
                # Intercept precompilation
                os.environ["PYCALL_PYTHON_EXE"] = sys.executable
                os.environ["PYCALL_JULIA_HOME"] = PYCALL_JULIA_HOME
                os.environ["PYJULIA_IMAGE_FILE"] = jlinfo.sysimage
                os.environ["PYCALL_LIBJULIA_PATH"] = os.path.dirname(jlinfo.libjulia_path)
                # Add a private cache directory. PyCall needs a different
                # configuration and so do any packages that depend on it.
                self._call(u"unshift!(Base.LOAD_CACHE_PATH, abspath(Pkg.Dir._pkgroot()," +
                    "\"lib\", \"pyjulia%s-v$(VERSION.major).$(VERSION.minor)\"))" % sys.version_info[0])

                # If PyCall.jl is already pre-compiled, for the global
                # environment, hide it while we are loading PyCall.jl
                # for PyJulia which has to compile a new cache if it
                # does not exist.  However, Julia does not compile a
                # new cache if it exists in Base.LOAD_CACHE_PATH[2:end].
                # https://github.com/JuliaPy/pyjulia/issues/92#issuecomment-289303684
                self._call(u"""
                for path in Base.LOAD_CACHE_PATH[2:end]
                    cache = joinpath(path, "PyCall.ji")
                    backup = joinpath(path, "PyCall.ji.backup")
                    if isfile(cache)
                        mv(cache, backup; remove_destination=true)
                    end
                end
                """)

            # This is mainly for initiating the precompilation:
            self._call(u"using PyCall")

            if use_separate_cache:
                self._call(u"""
                for path in Base.LOAD_CACHE_PATH[2:end]
                    cache = joinpath(path, "PyCall.ji")
                    backup = joinpath(path, "PyCall.ji.backup")
                    if !isfile(cache) && isfile(backup)
                        mv(backup, cache)
                    end
                    rm(backup; force=true)
                end
                """)

            # We are assuming that `jl_is_initialized()` was true only
            # if this process was a Julia process (hence PyCall had
            # already called `atexit(Py_Finalize)`).  This is not true
            # if `libjulia` is initialized in a Python process with
            # other mechanisms.  Julia's atexit hooks will not be
            # called if this happens.  As it's not clear what should
            # be done for such cases (the other mechanisms may or may
            # not register the atexit hook), let's play on the safer
            # side for now.
            if not was_initialized:
                atexit.register(self.api.jl_atexit_hook, 0)
        else:
            if is_windows:
                # `InProcessLibJulia` does not work on Windows at the
                # moment.  See:
                # https://github.com/JuliaPy/pyjulia/issues/287
                self.api = LibJulia.load(julia=runtime)
                set_libjulia(self.api)
            else:
                self.api = InProcessLibJulia()

        # Currently, PyJulia assumes that `Main.PyCall` exsits.  Thus, we need
        # to import `PyCall` again here in case `init_julia=False` is passed:
        self._call(u"using PyCall")

        # Whether we initialized Julia or not, we MUST create at least one
        # instance of PyObject and the convert function. Since these will be
        # needed on every call, we hold them in the Julia object itself so
        # they can survive across reinitializations.
        self._PyObject = self._call("PyCall.PyObject")
        self._convert = self._call("convert")

        self.sprint = self.eval('sprint')
        self.showerror = self.eval('showerror')

        if self.eval('VERSION >= v"0.7-"'):
            self.eval("@eval Main import Base.MainInclude: eval, include")
            # https://github.com/JuliaLang/julia/issues/28825

        if not isdefined(self, "Main", "_PyJuliaHelper"):
            self.eval("include")(
                os.path.join(
                    os.path.dirname(os.path.realpath(__file__)), "pyjulia_helper.jl"
                )
            )

    def _call(self, src):
        """
        Low-level call to execute a snippet of Julia source.

        This only raises an exception if Julia itself throws an error, but it
        does NO type conversion into usable Python objects nor any memory
        management. It should never be used for returning the result of Julia
        expressions, only to execute statements.
        """
        # logger.debug("_call(%s)", src)
        ans = self.api.jl_eval_string(src.encode('utf-8'))
        self.check_exception(src)

        return ans

    @staticmethod
    def _check_unboxable(c_type):
        if c_type not in UNBOXABLE_TYPES:
            raise ValueError("Julia value cannot be unboxed as c_type={!r}.\n"
                             "c_type supported by PyJulia are:\n"
                             "{}".format(c_type, "\n".join(UNBOXABLE_TYPES)))

    def _is_unboxable_as(self, pointer, c_type):
        self._check_unboxable(c_type)
        jl_type = getattr(self.api, 'jl_{}_type'.format(c_type))
        desired = ctypes.cast(jl_type, ctypes.POINTER(ctypes.c_void_p))[0]
        actual = self.api.jl_typeof(pointer)
        return actual == desired

    def _unbox_as(self, pointer, c_type):
        self._check_unboxable(c_type)
        jl_unbox = getattr(self.api, 'jl_unbox_{}'.format(c_type))
        if self._is_unboxable_as(pointer, c_type):
            return jl_unbox(pointer)
        else:
            raise TypeError("Cannot unbox pointer {} as {}"
                            .format(pointer, c_type))

    def check_exception(self, src="<unknown code>"):
        exoc = self.api.jl_exception_occurred()
        logger.debug("exception occured? %s", str(exoc))
        if not exoc:
            # logger.debug("No Exception")
            self.api.jl_exception_clear()
            return

        # If, theoretically, an exception happens in early stage of
        # self.__init__, showerror and sprint as below does not work.
        # Let's use jl_typeof_str in such case.
        try:
            sprint = self.sprint
            showerror = self.showerror
        except AttributeError:
            res = None
        else:
            res = self.api.jl_call2(self._convert, self._PyObject, exoc)
        if res is None:
            exception = self.api.jl_typeof_str(exoc).decode('utf-8')
        else:
            exception = sprint(showerror, self._as_pyobj(res))
        raise JuliaError(u'Exception \'{}\' occurred while calling julia code:\n{}'
                         .format(exception, src))

    def _typeof_julia_exception_in_transit(self):
        exception = void_p.in_dll(self.api, 'jl_exception_in_transit')
        msg = self.api.jl_typeof_str(exception)
        return char_p(msg).value

    def help(self, name):
        """ Return help string for function by name. """
        if name is None:
            return None
        return self.eval('Markdown.plain(@doc("{}"))'.format(name))

    def eval(self, src):
        """ Execute code in Julia, then pull some results back to Python. """
        if src is None:
            return None
        ans = self._call(src)
        if not ans:
            return None
        res = self.api.jl_call2(self._convert, self._PyObject, ans)

        if res is None:
            self.check_exception("convert(PyCall.PyObject, {})".format(src))
        return self._as_pyobj(res)

    def _as_pyobj(self, res):
        if res == 0:
            return None
        boxed_obj = self.api.jl_get_field(res, b'o')
        pyobj = self.api.jl_unbox_voidpointer(boxed_obj)
        # make sure we incref it before returning it,
        # as this is a borrowed reference
        ctypes.pythonapi.Py_IncRef(ctypes.py_object(pyobj))
        return pyobj

    def using(self, module):
        """Load module in Julia by calling the `using module` command"""
        self.eval("using %s" % module)

    def fullname(self, module):
        if isinstance(module, JuliaModule):
            assert module.__name__.startswith("julia.")
            return module.__name__[len("julia.") :]

        from .Main._PyJuliaHelper import fullnamestr

        return fullnamestr(module)

    def isdefined(self, parent, member=None):
        from .Main._PyJuliaHelper import isdefinedstr

        if member is None:
            if not isinstance(parent, string_types):
                raise ValueError("`julia.isdefined(name)` requires string `name`")
            if "." not in parent:
                raise ValueError(
                    "`julia.isdefined(name)` requires at least one dot in `name`."
                )
            parent, member = parent.rsplit(".", 1)
        if isinstance(parent, string_types):
            parent = self.eval(parent)
        return isdefinedstr(parent, member)


if sys.version_info[0] > 2:
    Julia.__init__.__doc__ = textwrap.dedent(Julia.__init__.__doc__) + options_docs


class LegacyJulia(object):
    __doc__ = Julia.__doc__

    def __init__(self, *args, **kwargs):
        self.__julia = Julia(*args, **kwargs)
    __init__.__doc__ = Julia.__init__.__doc__

    def __getattr__(self, name):
        from julia import Main
        warnings.warn(
            "Accessing `Julia().<name>` to obtain Julia objects is"
            " deprecated.  Use `from julia import Main; Main.<name>` or"
            " `jl = Julia(); jl.eval('<name>')`.",
            DeprecationWarning)
        try:
            return getattr(self.__julia, name)
        except AttributeError:
            return getattr(Main, name)


sys.meta_path.append(JuliaImporter())
