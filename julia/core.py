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
from __future__ import print_function
import ctypes
import ctypes.util
import os
import sys
import keyword
import subprocess
import time

from ctypes import c_void_p as void_p
from ctypes import c_char_p as char_p
from ctypes import py_object

# this is python 3.3 specific
from types import ModuleType, FunctionType

#-----------------------------------------------------------------------------
# Classes and funtions
#-----------------------------------------------------------------------------
python_version = sys.version_info

if python_version.major == 3:
    def iteritems(d): return iter(d.items())
else:
    iteritems = dict.iteritems


class JuliaError(Exception):
    pass


class JuliaModule(ModuleType):
    pass



# add custom import behavior for the julia "module"
class JuliaImporter(object):
    def __init__(self, julia):
        self.julia = julia

    # find_module was deprecated in v3.4
    def find_module(self, fullname, path=None):
        if path is None:
            pass
        if fullname.startswith("julia."):
            return JuliaModuleLoader(self.julia)


class JuliaModuleLoader(object):

    def __init__(self, julia):
        self.julia = julia

    # load module was deprecated in v3.4
    def load_module(self, fullname):
        juliapath = fullname.lstrip("julia.")
        if isamodule(self.julia, juliapath):
            mod = sys.modules.setdefault(fullname, JuliaModule(fullname))
            mod.__loader__ = self
            names = self.julia.eval("names({}, true, false)".format(juliapath))
            for name in names:
                if (ismacro(name) or
                    isoperator(name) or
                    isprotected(name) or
                    notascii(name)):
                    continue
                attrname = name
                if name.endswith("!"):
                    attrname = name.replace("!", "_b")
                if keyword.iskeyword(name):
                    attrname = "jl".join(name)
                try:
                    module_path = ".".join((juliapath, name))
                    module_obj = self.julia.eval(module_path)
                    is_module = self.julia.eval("isa({}, Module)"
                                                .format(module_path))
                    if is_module:
                        split_path = module_path.split(".")
                        is_base = split_path[-1] == "Base"
                        recur_module = split_path[-1] == split_path[-2]
                        if is_module and not is_base and not recur_module:
                            newpath = ".".join((fullname, name))
                            module_obj = self.load_module(newpath)
                    setattr(mod, attrname, module_obj)
                except Exception:
                    if isafunction(self.julia, name, mod_name=juliapath):
                        func = "{}.{}".format(juliapath, name)
                        setattr(mod, name, self.julia.eval(func))
            return mod
        elif isafunction(self.julia, juliapath):
            return getattr(self.julia, juliapath)
        else:
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


def isamodule(julia, julia_name):
    try:
        ret = julia.eval("isa({}, Module)".format(julia_name))
        return ret
    except:
        # try explicitly importing it..
        try:
            julia.eval("import {}".format(julia_name))
            ret = julia.eval("isa({}, Module)".format(julia_name))
            return ret
        except:
            pass
    return False


def isafunction(julia, julia_name, mod_name=""):
    code = "isa({}, Function)".format(julia_name)
    if mod_name:
        code = "isa({}.{}, Function)".format(mod_name, julia_name)
    try:
        return julia.eval(code)
    except:
        return False


def module_functions(julia, module):
    """Compute the function names in the julia module"""
    bases = {}
    names = julia.eval("names(%s)" % module)
    for name in names:
        if (ismacro(name) or
            isoperator(name) or
            isprotected(name) or
            notascii(name)):
            continue
        try:
            # skip undefined names
            if not julia.eval("isdefined(:%s)" % name):
                continue
            # skip modules for now
            if isamodule(julia, name):
                continue
            if name.startswith("_"):
                continue
            attr_name = name
            if name.endswith("!"):
                attr_name = name.replace("!", "_b")
            if keyword.iskeyword(name):
                attr_name = "jl".join(name)
            julia_func = julia.eval(name)
            bases[attr_name] = julia_func
        except:
            pass
    return bases

def determine_if_statically_linked():
    """Determines if this python executable is statically linked"""
    # Windows and OS X are generally always dynamically linked
    if not sys.platform.startswith('linux'):
        return False
    lddoutput = subprocess.check_output(["ldd",sys.executable])
    return not (b"libpython" in lddoutput)


_julia_runtime = [False]

class Julia(object):
    """
    Implements a bridge to the Julia interpreter or library.
    This uses the Julia PyCall module to perform type conversions and allow
    full access to the entire Julia interpreter.
    """

    def __init__(self, init_julia=True, jl_runtime_path=None, jl_init_path=None,
                 debug=False):
        """Create a Python object that represents a live Julia interpreter.

        Parameters
        ==========

        init_julia : bool
            If True, try to initialize the Julia interpreter. If this code is
            being called from inside an already running Julia, the flag should
            be passed as False so the interpreter isn't re-initialized.

        jl_runtime_path : str (optional)
            Path to your Julia binary, e.g. "/usr/local/bin/julia"

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

        if init_julia:
            if jl_runtime_path:
                runtime = jl_runtime_path
            else:
                runtime = 'julia'
            juliainfo = subprocess.check_output(
                [runtime, "-e",
                 """
                 println(JULIA_HOME)
                 println(Libdl.dlpath(string("lib", splitext(Base.julia_exename())[1])))
                 println(unsafe_string(Base.JLOptions().image_file))
                 PyCall_depsfile = Pkg.dir("PyCall","deps","deps.jl")
                 if isfile(PyCall_depsfile)
                    eval(Module(:__anon__),
                        Expr(:toplevel,
                         :(using Compat),
                         :(Main.Base.include($PyCall_depsfile)),
                         :(println(pyprogramname))))
                 else
                    println("nowhere")
                 end
                 """])
            JULIA_HOME, libjulia_path, image_file, depsjlexe = juliainfo.decode("utf-8").rstrip().split("\n")
            exe_differs = not depsjlexe == sys.executable
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

            use_separate_cache = exe_differs or determine_if_statically_linked()
            if use_separate_cache:
                PYCALL_JULIA_HOME = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),"fake-julia").replace("\\","\\\\")
                os.environ["JULIA_HOME"] = PYCALL_JULIA_HOME
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
            self.api = ctypes.PyDLL('')

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
        self.api.jl_get_field.restype = void_p
        self.api.jl_typename_str.restype = char_p
        self.api.jl_typeof_str.restype = char_p
        self.api.jl_unbox_voidpointer.restype = py_object

        self.api.jl_exception_clear.restype = None
        self.api.jl_stderr_obj.argtypes = []
        self.api.jl_stderr_obj.restype = void_p
        self.api.jl_stderr_stream.argtypes = []
        self.api.jl_stderr_stream.restype = void_p
        self.api.jl_printf.restype = ctypes.c_int
        self.api.jl_exception_clear()

        # We use show() for displaying uncaught exceptions.
        self.api.show = self._call("Base.show")

        if init_julia:
            if use_separate_cache:
                # First check that this is supported
                self._call("""
                    if VERSION < v"0.5-"
                        error(\"""Using pyjulia with a statically-compiled version
                                  of python or with a version of python that
                                  differs from that used by PyCall.jl is not
                                  supported on julia 0.4""\")
                    end
                """)
                # Intercept precompilation
                os.environ["PYCALL_PYTHON_EXE"] = sys.executable
                os.environ["PYCALL_JULIA_HOME"] = PYCALL_JULIA_HOME
                os.environ["PYJULIA_IMAGE_FILE"] = image_file
                os.environ["PYCALL_LIBJULIA_PATH"] = os.path.dirname(libjulia_path)
                # Add a private cache directory. PyCall needs a different
                # configuration and so do any packages that depend on it.
                self._call(u"unshift!(Base.LOAD_CACHE_PATH, abspath(Pkg.Dir._pkgroot()," +
                    "\"lib\", \"pyjulia%s-v$(VERSION.major).$(VERSION.minor)\"))" % sys.version_info[0])
                # If PyCall.ji does not exist, create an empty file to force
                # recompilation
                self._call(u"""
                    isdir(Base.LOAD_CACHE_PATH[1]) ||
                        mkpath(Base.LOAD_CACHE_PATH[1])
                    depsfile = joinpath(Base.LOAD_CACHE_PATH[1],"PyCall.ji")
                    isfile(depsfile) || touch(depsfile)
                """)

            self._call(u"using PyCall")
        # Whether we initialized Julia or not, we MUST create at least one
        # instance of PyObject and the convert function. Since these will be
        # needed on every call, we hold them in the Julia object itself so
        # they can survive across reinitializations.
        self.api.PyObject = self._call("PyCall.PyObject")
        self.api.convert = self._call("convert")

        # We use show() for displaying uncaught exceptions.
        self.api.show = self._call("Base.show")

        # Flag process-wide that Julia is initialized and store the actual
        # runtime interpreter, so we can reuse it across calls and module
        # reloads.
        _julia_runtime[0] = self.api

        self.add_module_functions("Base")

        sys.meta_path.append(JuliaImporter(self))

    def add_module_functions(self, module):
        for name, func in iteritems(module_functions(self, module)):
            setattr(self, name, func)

    def _debug(self, msg):
        """
        Print some debugging stuff, if enabled
        """
        if self.is_debugging:
            print(msg, file=sys.stderr)

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

    def check_exception(self, src=None):
        exoc = self.api.jl_exception_occurred()
        self._debug("exception occured? " + str(exoc))
        if not exoc:
            # self._debug("No Exception")
            self.api.jl_exception_clear()
            return
        self._debug("Retrieving exception infos...")
        stderr = self.api.jl_stderr_obj()
        self._debug("libjulia stderr = " + str(stderr))
        self.api.jl_call2(self.api.show, stderr, exoc)
        self._debug("show called ...")
        # self.api.jl_printf(self.api.jl_stderr_stream(), "\n");

        exception_type = self.api.jl_typeof_str(exoc).decode('utf-8')
        raise JuliaError(u'Exception \'{}\' occurred while calling julia code:\n{}'
                         .format(exception_type, src))

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
        res = self.api.jl_call2(void_p(self.api.convert), void_p(self.api.PyObject), void_p(ans))

        if res is None:
            self.check_exception("convert(PyCall.PyObject, %s)" % src)
        if res == 0:
            return None
        boxed_obj = self.api.jl_get_field(void_p(res), b'o')
        pyobj = self.api.jl_unbox_voidpointer(void_p(boxed_obj))
        # make sure we incref it before returning it,
        # as this is a borrowed reference
        ctypes.pythonapi.Py_IncRef(ctypes.py_object(pyobj))
        return pyobj

    def using(self, module):
        """Load module in Julia by calling the `using module` command"""
        self.eval("using %s" % module)
        self.add_module_functions(module)
