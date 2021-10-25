"""
Bridge Python and Julia by initializing the Julia runtime inside Python.
"""

# ----------------------------------------------------------------------------
# Copyright (C) 2013 The IPython and Julia Development Teams.
#
# Distributed under the terms of the BSD License. The full license is in
# the file COPYING, distributed as part of this software.
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

from __future__ import absolute_import, print_function

import atexit
import ctypes
import ctypes.util
import logging as _logging  # see `.logger`
import os
import sys
import textwrap
import warnings
from ctypes import c_char_p, c_void_p
from logging import getLogger  # see `.logger`
from types import ModuleType  # this is python 3.3 specific

from .find_libpython import find_libpython, linked_libpython
from .juliainfo import JuliaInfo
from .libjulia import UNBOXABLE_TYPES, LibJulia, get_inprocess_libjulia, get_libjulia
from .options import JuliaOptions, options_docs
from .release import __version__
from .utils import PYCALL_PKGID, is_windows

try:
    from shutil import which
except ImportError:
    # For Python < 3.3; it should behave more-or-less similar to
    # shutil.which when used with single argument.
    from distutils.spawn import find_executable as which

try:
    FutureWarning
except NameError:
    # Python 2
    FutureWarning = DeprecationWarning

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)

# ----------------------------------------------------------------------------
# Classes and funtions
# ----------------------------------------------------------------------------
python_version = sys.version_info


logger = getLogger("julia")
"""
Implementation notes: We are not importing `logging` module at the top
level so that using `logging.debug` instead of `logger.debug` becomes
an error.
"""

_loghandler = None


def get_loghandler():
    """
    Get `logging.StreamHandler` private to PyJulia.
    """
    global _loghandler
    if _loghandler is None:
        formatter = _logging.Formatter("%(levelname)s %(message)s")

        _loghandler = _logging.StreamHandler()
        _loghandler.setFormatter(formatter)

        logger.addHandler(_loghandler)
    return _loghandler


def set_loglevel(level):
    get_loghandler()
    logger.setLevel(getattr(_logging, level, level))


def enable_debug():
    set_loglevel("DEBUG")

    handler = get_loghandler()
    handler.setFormatter(_logging.Formatter("%(levelname)s (%(process)d) %(message)s"))

    logger.debug("")  # flush whatever in the line
    logger.debug("Debug-level logging is enabled for PyJulia.")
    logger.debug("PyJulia version: %s", __version__)


class JuliaError(Exception):
    """
    Wrapper for Julia exceptions.
    """


# fmt: off


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

        if self._julia.isamodule(jl_fullname):
            realname = self._julia.fullname(self._julia.eval(jl_fullname))
            if self._julia.isdefined(realname):
                return self.__loader__.load_module("julia." + realname)
            # Otherwise, it may be, e.g., "Main.anonymous", created by
            # Module().

        if self._julia._isdefined(jl_module, name):
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
        elif self.julia.isafunction(juliapath):
            return self.julia.eval(juliapath)

        try:
            self.julia.eval("import {}".format(juliapath.split(".", 1)[0]))
        except JuliaError:
            pass
        else:
            if self.julia.isamodule(juliapath):
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

# fmt: on


def determine_if_statically_linked():
    """Determines if this python executable is statically linked"""
    return linked_libpython() is None


_unsupported_error_common_header = """\
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


_unsupported_error_common_footer = """
For more information, see:

    https://pyjulia.readthedocs.io/en/latest/troubleshooting.html
"""


_unsupported_error_statically_linked = """
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


_unsupported_error_incompatible_libpython = """
In Julia >= 0.7, above two paths to `libpython` have to match exactly
in order for PyJulia to work out-of-the-box.  To configure PyCall.jl to use
Python interpreter "{sys.executable}",
run the following code in the Python REPL:

    >>> import julia
    >>> julia.install()
"""


class UnsupportedPythonError(Exception):
    def __init__(self, jlinfo):
        self.jlinfo = jlinfo
        self.statically_linked = determine_if_statically_linked()

    def __str__(self):
        template = _unsupported_error_common_header
        if self.statically_linked:
            template += _unsupported_error_statically_linked
        else:
            template += _unsupported_error_incompatible_libpython
        template += _unsupported_error_common_footer
        return template.format(
            runtime=self.jlinfo.julia,
            jlinfo=self.jlinfo,
            py_libpython=find_libpython(),
            jl_libpython=self.jlinfo.libpython_path,
            sys=sys,
        )


class Julia(object):
    """
    Implements a bridge to the Julia runtime.
    This uses the Julia PyCall module to perform type conversions and allow
    full access to the entire Julia runtime.
    """

    # fmt: off

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
                "`jl_runtime_path` is deprecated. Please use `runtime`.", FutureWarning
            )

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
                "`jl_init_path` is deprecated. Please use `bindir`.", FutureWarning
            )
            if "bindir" in julia_options:
                raise TypeError("Both `jl_init_path` and `bindir` are specified.")

        logger.debug("")  # so that debug message is shown nicely w/ pytest

        if get_libjulia():
            # Use pre-existing `LibJulia`.
            self.api = get_libjulia()
        elif init_julia:
            jlinfo = JuliaInfo.load(runtime)
            if jlinfo.version_info < (0, 7):
                raise RuntimeError("PyJulia does not support Julia < 0.7 anymore")

            self.api = LibJulia.from_juliainfo(jlinfo)

            if jl_init_path:
                self.api.bindir = jl_init_path

            options = JuliaOptions(**julia_options)

            is_compatible_python = jlinfo.is_compatible_python()
            logger.debug("is_compatible_python = %r", is_compatible_python)
            logger.debug("compiled_modules = %r", options.compiled_modules)
            if not (options.compiled_modules == "no" or is_compatible_python):
                raise UnsupportedPythonError(jlinfo)

            self.api.init_julia(options)

            # We are assuming that `jl_is_initialized()` was true only
            # if this process was a Julia process (hence PyCall had
            # already called `atexit(Py_Finalize)`).  This is not true
            # if `libjulia` is initialized in a Python process with
            # other mechanisms.  Julia's atexit hooks will not be
            # called if this happens.  As it's not clear what should
            # be done for such cases (the other mechanisms may or may
            # not register the atexit hook), let's play on the safer
            # side for now.
            if not self.api.was_initialized:  # = jl_is_initialized()
                atexit.register(self.api.jl_atexit_hook, 0)
        else:
            self.api = get_inprocess_libjulia(julia=runtime)

        # Currently, PyJulia assumes that `Main.PyCall` exsits.  Thus, we need
        # to import `PyCall` again here in case `init_julia=False` is passed:
        if debug:
            self._call("""
            const PyCall = try
                Base.require({0})
            catch err
                @error "Failed to import PyCall" exception = (err, catch_backtrace())
                rethrow()
            end
            """.format(PYCALL_PKGID))
        else:
            self._call("const PyCall = Base.require({0})".format(PYCALL_PKGID))

        self._call(u"using .PyCall")

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

        if not self._isdefined("Main", "_PyJuliaHelper"):
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

    # `_unbox_as` was added for communicating with Julia runtime before
    # initializing PyCal:
    # * Fail with a helpful message if separate cache is not supported
    #   https://github.com/JuliaPy/pyjulia/pull/186
    # However, this is not used anymore at the moment. Maybe clean this up?
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
        exception = c_void_p.in_dll(self.api, 'jl_exception_in_transit')
        msg = self.api.jl_typeof_str(exception)
        return c_char_p(msg).value

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

    # fmt: on

    def using(self, module):
        """Load module in Julia by calling the `using module` command"""
        self.eval("using %s" % module)

    def fullname(self, module):
        if isinstance(module, JuliaModule):
            assert module.__name__.startswith("julia.")
            return module.__name__[len("julia.") :]

        from .Main._PyJuliaHelper import fullnamestr

        return fullnamestr(module)

    def isdefined(self, fullname):
        from .Main._PyJuliaHelper import isdefinedstr

        if not isinstance(fullname, string_types):
            raise ValueError("`julia.isdefined(name)` requires string `name`")
        if "." not in fullname:
            raise ValueError(
                "`julia.isdefined(name)` requires at least one dot in `name`."
            )
        parent, member = fullname.rsplit(".", 1)

        if isinstance(parent, string_types):
            parent = self.eval(parent)
        return isdefinedstr(parent, member)

    def _isdefined(self, parent, member):
        # `_isdefined` is used in context that `isdefined` is not available
        return self.eval("isdefined({}, :({}))".format(parent, member))

    def isamodule(self, julia_name):
        try:
            return self.eval("isa({}, Module)".format(julia_name))
        except JuliaError:
            return False  # assuming this is an `UndefVarError`

    def isafunction(self, julia_name):
        code = "isa({}, Function)".format(julia_name)
        try:
            return self.eval(code)
        except Exception:
            return False


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
            FutureWarning,
        )
        try:
            return getattr(self.__julia, name)
        except AttributeError:
            return getattr(Main, name)


sys.meta_path.append(JuliaImporter())
