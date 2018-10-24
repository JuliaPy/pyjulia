"""
Bridge Python and Julia by initializing the Julia interpreter inside Python.
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
import atexit
import ctypes
import ctypes.util
import os
import sys
import keyword
import subprocess
import time
import warnings

from collections import namedtuple
from ctypes import c_void_p as void_p
from ctypes import c_char_p as char_p
from ctypes import py_object

try:
    from shutil import which
except ImportError:
    # For Python < 3.3; it should behave more-or-less similar to
    # shutil.which when used with single argument.
    from distutils.spawn import find_executable as which

# this is python 3.3 specific
from types import ModuleType, FunctionType

from .find_libpython import find_libpython, linked_libpython, normalize_path

#-----------------------------------------------------------------------------
# Classes and funtions
#-----------------------------------------------------------------------------
python_version = sys.version_info

if python_version.major == 3:
    def iteritems(d): return iter(d.items())
else:
    iteritems = dict.iteritems


# As setting up Julia modifies os.environ, we need to cache it for
# launching subprocesses later in the original environment.
_enviorn = os.environ.copy()


class JuliaError(Exception):
    pass


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

        # If `name` is a top-level module, don't import it as a
        # submodule.  Note that it handles the case that `name` is
        # `Base` and `Core`.
        is_toplevel = isdefined(self._julia, 'Main', name)
        if not is_toplevel and isamodule(self._julia, jl_fullname):
            # FIXME: submodules from other modules still hit this code
            # path and they are imported as submodules.
            return self.__loader__.load_module(".".join((self.__name__, name)))

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
            pypath = os.path.join(os.path.dirname(__file__),
                                  "{}.py".format(fullname[len("julia."):]))
            if os.path.isfile(pypath):
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
            self.julia.eval("import {}".format(juliapath))
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


JuliaInfo = namedtuple(
    'JuliaInfo',
    ['JULIA_HOME', 'libjulia_path', 'image_file',
     # Variables in PyCall/deps/deps.jl:
     'pyprogramname', 'libpython'])


def juliainfo(runtime='julia', **popen_kwargs):
    # Use the original environment variables to avoid a cryptic
    # error "fake-julia/../lib/julia/sys.so: cannot open shared
    # object file: No such file or directory":
    popen_kwargs.setdefault("env", _enviorn)

    proc = subprocess.Popen(
        [runtime, "--startup-file=no", "-e",
         """
         println(VERSION < v"0.7.0-DEV.3073" ? JULIA_HOME : Base.Sys.BINDIR)
         if VERSION >= v"0.7.0-DEV.3630"
             using Libdl
             using Pkg
         end
         println(Libdl.dlpath(string("lib", splitext(Base.julia_exename())[1])))
         println(unsafe_string(Base.JLOptions().image_file))
         if VERSION < v"0.7.0"
             PyCall_depsfile = Pkg.dir("PyCall","deps","deps.jl")
         else
             modpath = Base.locate_package(Base.identify_package("PyCall"))
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
         """],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        **popen_kwargs)

    stdout, stderr = proc.communicate()
    retcode = proc.wait()
    if retcode != 0:
        raise subprocess.CalledProcessError(
            retcode,
            [runtime, "-e", "..."],
            stdout,
            stderr,
        )

    stderr = stderr.strip()
    if stderr:
        warnings.warn("{} warned:\n{}".format(runtime, stderr))

    args = stdout.rstrip().split("\n")
    args.extend([None] * (len(JuliaInfo._fields) - len(args)))
    return JuliaInfo(*args)


def is_same_path(a, b):
    a = os.path.realpath(os.path.normcase(a))
    b = os.path.realpath(os.path.normcase(b))
    return a == b


def is_compatible_exe(jlinfo, _debug=lambda *_: None):
    """
    Determine if Python used by PyCall.jl is compatible with this Python.

    Current Python executable is considered compatible if it is dynamically
    linked to libpython and both of them are using identical libpython.  If
    this function returns `True`, PyJulia use the same precompilation cache
    of PyCall.jl used by Julia itself.

    Parameters
    ----------
    jlinfo : JuliaInfo
        A `JuliaInfo` object returned by `juliainfo` function.
    """
    _debug("jlinfo.libpython =", jlinfo.libpython)
    py_libpython = linked_libpython()
    jl_libpython = normalize_path(jlinfo.libpython)
    _debug("py_libpython =", py_libpython)
    _debug("jl_libpython =", jl_libpython)
    dynamically_linked = py_libpython is not None
    return dynamically_linked and py_libpython == jl_libpython
    # `py_libpython is not None` here for checking if this Python
    # executable is dynamically linked or not (`py_libpython is None`
    # if it's statically linked).  `jl_libpython` may be `None` if
    # libpython used for PyCall is removed so we can't expect
    # `jl_libpython` to be a `str` always.


_separate_cache_error_common_header = """\
It seems your Julia and PyJulia setup are not supported.

Julia interpreter:
    {runtime}
Python interpreter and libpython used by PyCall.jl:
    {jlinfo.pyprogramname}
    {jl_libpython}
Python interpreter used to import PyJulia and its libpython.
    {sys.executable}
    {py_libpython}
"""


_separate_cache_error_common_footer = """
For more information, see:
    https://github.com/JuliaPy/pyjulia
    https://github.com/JuliaPy/PyCall.jl
"""


_separate_cache_error_statically_linked = """
Your Python interpreter "{sys.executable}"
is statically linked to libpython.  Currently, PyJulia does not support
such Python interpreter.  One easy workaround is to run your Python
script with `python-jl` command bundled in PyJulia.  You can simply do:

    python-jl PATH/TO/YOUR/SCRIPT.py

See `python-jl --help` for more information.

For other available workarounds, see:
    https://github.com/JuliaPy/pyjulia#troubleshooting
"""


_separate_cache_error_incompatible_libpython = """
In Julia >= 0.7, above two paths to `libpython` have to match exactly
in order for PyJulia to work.  To configure PyCall.jl to use Python
interpreter "{sys.executable}",
run the following commands in the Julia interpreter:

    ENV["PYTHON"] = "{sys.executable}"
    using Pkg
    Pkg.build("PyCall")
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
        jl_libpython=normalize_path(jlinfo.libpython),
        sys=sys)
    raise RuntimeError(message)


_julia_runtime = [False]


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
    Implements a bridge to the Julia interpreter or library.
    This uses the Julia PyCall module to perform type conversions and allow
    full access to the entire Julia interpreter.
    """

    def __init__(self, init_julia=True, jl_init_path=None, runtime=None,
                 jl_runtime_path=None, debug=False):
        """Create a Python object that represents a live Julia interpreter.

        Parameters
        ==========

        init_julia : bool
            If True, try to initialize the Julia interpreter. If this code is
            being called from inside an already running Julia, the flag should
            be passed as False so the interpreter isn't re-initialized.

        runtime : str (optional)
            Custom Julia binary, e.g. "/usr/local/bin/julia" or "julia-1.0.0".

        jl_init_path : str (optional)
            Path to give to jl_init relative to which we find sys.so,
            (defaults to jl_runtime_path or NULL)

        debug : bool
            If True, print some debugging information to STDERR

        Note that it is safe to call this class constructor twice in the same
        process with `init_julia` set to True, as a global reference is kept
        to avoid re-initializing it. The purpose of the flag is only to manage
        situations when Julia was initialized from outside this code.
        """
        self.is_debugging = debug

        # Ugly hack to register the julia interpreter globally so we can reload
        # this extension without trying to re-open the shared lib, which kills
        # the python interpreter. Nasty but useful while debugging
        if _julia_runtime[0]:
            self.api = _julia_runtime[0]
            return

        if jl_runtime_path is not None:
            warnings.warn(
                "`jl_runtime_path` is deprecated. Please use `runtime`.",
                DeprecationWarning)

        if runtime is None:
            if jl_runtime_path is None:
                runtime = "julia"
            else:
                runtime = jl_runtime_path
        else:
            if jl_runtime_path is None:
                jl_runtime_path = which(runtime)
                if jl_runtime_path is None:
                    raise RuntimeError("Julia runtime {} cannot be found"
                                       .format(runtime))
            else:
                raise TypeError(
                    "Both `runtime` and `jl_runtime_path` are specified.")

        self._debug()  # so that debug message is shown nicely w/ pytest

        if init_julia:
            jlinfo = juliainfo(runtime)
            JULIA_HOME, libjulia_path, image_file, depsjlexe = jlinfo[:4]
            self._debug("pyprogramname =", depsjlexe)
            self._debug("sys.executable =", sys.executable)
            self._debug("JULIA_HOME = %s,  libjulia_path = %s" % (JULIA_HOME, libjulia_path))
            if not os.path.exists(libjulia_path):
                raise JuliaError("Julia library (\"libjulia\") not found! {}".format(libjulia_path))

            # fixes a specific issue with python 2.7.13
            # ctypes.windll.LoadLibrary refuses unicode argument
            # http://bugs.python.org/issue29294
            if sys.version_info >= (2,7,13) and sys.version_info < (2,7,14):
                libjulia_path = libjulia_path.encode("ascii")

            self.api = ctypes.PyDLL(libjulia_path, ctypes.RTLD_GLOBAL)
            if not jl_init_path:
                if jl_runtime_path:
                    jl_init_path = os.path.dirname(os.path.realpath(jl_runtime_path)).encode("utf-8")
                else:
                    jl_init_path = JULIA_HOME.encode("utf-8") # initialize with JULIA_HOME

            use_separate_cache = not is_compatible_exe(jlinfo, _debug=self._debug)
            self._debug("use_separate_cache =", use_separate_cache)
            if use_separate_cache:
                PYCALL_JULIA_HOME = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),"fake-julia").replace("\\","\\\\")
                os.environ["JULIA_HOME"] = PYCALL_JULIA_HOME  # TODO: this line can be removed when dropping Julia v0.6
                os.environ["JULIA_BINDIR"] = PYCALL_JULIA_HOME
                jl_init_path = PYCALL_JULIA_HOME.encode("utf-8")

            if not hasattr(self.api, "jl_init_with_image"):
                if hasattr(self.api, "jl_init_with_image__threading"):
                    self.api.jl_init_with_image = self.api.jl_init_with_image__threading
                else:
                    raise ImportError("No libjulia entrypoint found! (tried jl_init_with_image and jl_init_with_image__threading)")
            self.api.jl_init_with_image.argtypes = [char_p, char_p]
            self._debug("calling jl_init_with_image(%s, %s)" % (jl_init_path, image_file))
            self.api.jl_init_with_image(jl_init_path, image_file.encode("utf-8"))
            self._debug("seems to work...")

        else:
            # we're assuming here we're fully inside a running Julia process,
            # so we're fishing for symbols in our own process table
            self.api = ctypes.PyDLL(None)

        # Store the running interpreter reference so we can start using it via self.call
        self.api.jl_.argtypes = [void_p]
        self.api.jl_.restype = None

        # Set the return types of some of the bridge functions in ctypes terminology
        self.api.jl_eval_string.argtypes = [char_p]
        self.api.jl_eval_string.restype = void_p

        self.api.jl_exception_occurred.restype = void_p
        self.api.jl_typeof_str.argtypes = [void_p]
        self.api.jl_typeof_str.restype = char_p
        self.api.jl_call2.argtypes = [void_p, void_p, void_p]
        self.api.jl_call2.restype = void_p
        self.api.jl_get_field.argtypes = [void_p, char_p]
        self.api.jl_get_field.restype = void_p
        self.api.jl_typename_str.restype = char_p
        self.api.jl_unbox_voidpointer.argtypes = [void_p]
        self.api.jl_unbox_voidpointer.restype = py_object

        for c_type in UNBOXABLE_TYPES:
            jl_unbox = getattr(self.api, "jl_unbox_{}".format(c_type))
            jl_unbox.argtypes = [void_p]
            jl_unbox.restype = getattr(ctypes, "c_{}".format({
                "float32": "float",
                "float64": "double",
            }.get(c_type, c_type)))

        self.api.jl_typeof.argtypes = [void_p]
        self.api.jl_typeof.restype = void_p

        self.api.jl_exception_clear.restype = None
        self.api.jl_stderr_obj.argtypes = []
        self.api.jl_stderr_obj.restype = void_p
        self.api.jl_stderr_stream.argtypes = []
        self.api.jl_stderr_stream.restype = void_p
        self.api.jl_printf.restype = ctypes.c_int
        self.api.jl_exception_clear()

        if init_julia:
            if use_separate_cache:
                # First check that this is supported
                version_range = self._unbox_as(self._call("""
                Int64(if VERSION < v"0.6-"
                    2
                elseif VERSION >= v"0.7-"
                    1
                else
                    0
                end)
                """), "int64")
                if version_range == 2:
                    raise RuntimeError(
                        "PyJulia does not support Julia < 0.6 anymore")
                elif version_range == 1:
                    raise_separate_cache_error(runtime, jlinfo)
                # Intercept precompilation
                os.environ["PYCALL_PYTHON_EXE"] = sys.executable
                os.environ["PYCALL_JULIA_HOME"] = PYCALL_JULIA_HOME
                os.environ["PYJULIA_IMAGE_FILE"] = image_file
                os.environ["PYCALL_LIBJULIA_PATH"] = os.path.dirname(libjulia_path)
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

            jl_atexit_hook = self.api.jl_atexit_hook
            jl_atexit_hook.argtypes = [ctypes.c_int]
            atexit.register(jl_atexit_hook, 0)

        # Currently, PyJulia assumes that `Main.PyCall` exsits.  Thus, we need
        # to import `PyCall` again here in case `init_julia=False` is passed:
        self._call(u"using PyCall")

        # Whether we initialized Julia or not, we MUST create at least one
        # instance of PyObject and the convert function. Since these will be
        # needed on every call, we hold them in the Julia object itself so
        # they can survive across reinitializations.
        self.api.PyObject = self._call("PyCall.PyObject")
        self.api.convert = self._call("convert")

        # Flag process-wide that Julia is initialized and store the actual
        # runtime interpreter, so we can reuse it across calls and module
        # reloads.
        _julia_runtime[0] = self.api

        self.sprint = self.eval('sprint')
        self.showerror = self.eval('showerror')

        if self.eval('VERSION >= v"0.7-"'):
            self.eval("@eval Main import Base.MainInclude: eval, include")
            # https://github.com/JuliaLang/julia/issues/28825

    def _debug(self, *msg):
        """
        Print some debugging stuff, if enabled
        """
        if self.is_debugging:
            print(*msg, file=sys.stderr)
            sys.stderr.flush()

    def _call(self, src):
        """
        Low-level call to execute a snippet of Julia source.

        This only raises an exception if Julia itself throws an error, but it
        does NO type conversion into usable Python objects nor any memory
        management. It should never be used for returning the result of Julia
        expressions, only to execute statements.
        """
        # self._debug("_call(%s)" % src)
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
        self._debug("exception occured? " + str(exoc))
        if not exoc:
            # self._debug("No Exception")
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
            res = self.api.jl_call2(self.api.convert, self.api.PyObject, exoc)
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
        res = self.api.jl_call2(self.api.convert, self.api.PyObject, ans)

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
