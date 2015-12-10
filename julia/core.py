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
import ctypes
import ctypes.util
import os
import sys
import keyword
import subprocess

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


def base_functions(julia):
    bases = {}
    names = julia.eval("names(Base)")
    for name in names:
        if (ismacro(name) or
            isoperator(name) or
            isprotected(name) or
            notascii(name)):
            continue
        try:
            # skip modules for now
            if isamodule(julia, name):
                continue
            if name.startswith("_"):
                continue
            if not isafunction(julia, name):
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

_julia_runtime = [False]

class Julia(object):
    """
    Implements a bridge to the Julia interpreter or library.
    This uses the Julia PyCall module to perform type conversions and allow
    full access to the entire Julia interpreter.
    """

    @staticmethod
    def find_sysimg(julia_home):
        paths = [os.path.join(julia_home, *candidate)
                 for candidate in [('sys.so',),
                                     ('lib','julia','sys.so'),
                                     ('julia','sys.ji'),
                                     ('sys.ji')]]

        for path in paths:
            if os.path.exists(path):
                return path
        raise JuliaError("Failed to find system image (checked %s)" % (paths,))

    def __init__(self, init_julia=True, jl_init_path=None):
        """Create a Python object that represents a live Julia interpreter.

        Parameters
        ==========

        init_julia : bool
            If True, try to initialize the Julia interpreter. If this code is
            being called from inside an already running Julia, the flag should
            be passed as False so the interpreter isn't re-initialized.

        jl_init_path : str (optional)
            Path to your Julia directory

        Note that it is safe to call this class constructor twice in the same
        process with `init_julia` set to True, as a global reference is kept
        to avoid re-initializing it. The purpose of the flag is only to manage
        situations when Julia was initialized from outside this code.
        """

        # Ugly hack to register the julia interpreter globally so we can reload
        # this extension without trying to re-open the shared lib, which kills
        # the python interpreter. Nasty but useful while debugging
        if _julia_runtime[0]:
            self.api = _julia_runtime[0]
            return

        if init_julia:
            try:
                if jl_init_path:
                    runtime = os.path.join(jl_init_path, 'bin', 'julia')
                else:
                    runtime = 'julia'
                juliainfo = subprocess.check_output(
                    [runtime, "-e",
                     """
                     println(JULIA_HOME)
                     println(Libdl.dlpath(Libdl.dlopen(\"libjulia\")))
                     """])
                JULIA_HOME, libjulia_path = juliainfo.decode("utf-8").rstrip().split("\n")
            except:
                raise JuliaError('error starting up the Julia process')

            if not os.path.exists(libjulia_path):
                raise JuliaError("Julia library (\"libjulia\") not found! {}".format(libjulia_path))
            self.api = ctypes.PyDLL(libjulia_path, ctypes.RTLD_GLOBAL)
            self.api.julia_init.argtypes = [ctypes.c_int]
            self.api.julia_init(1)

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
        self.api.jl_bytestring_ptr.restype = char_p

        self.api.jl_exception_clear.restype = None
        self.api.jl_stderr_obj.argtypes = []
        self.api.jl_stderr_obj.restype = void_p
        self.api.jl_stderr_stream.argtypes = []
        self.api.jl_stderr_stream.restype = void_p
        self.api.jl_show.restype = None
        self.api.jl_show.argtypes = [void_p, void_p]
        self.api.jl_printf.restype = ctypes.c_int
        self.api.jl_exception_clear()

        if init_julia:
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

        for name, func in iteritems(base_functions(self)):
             setattr(self, name, func)

        sys.meta_path.append(JuliaImporter(self))

    def _call(self, src):
        """
        Low-level call to execute a snippet of Julia source.

        This only raises an exception if Julia itself throws an error, but it
        does NO type conversion into usable Python objects nor any memory
        management. It should never be used for returning the result of Julia
        expressions, only to execute statements.
        """

        ans = self.api.jl_eval_string(src.encode('utf-8'))
        self.check_exception(src)

        return ans

    def check_exception(self, src=None):
        exoc = self.api.jl_exception_occurred()
        if not exoc:
            self.api.jl_exception_clear()
            return

        stderr = self.api.jl_stderr_obj()
        self.api.jl_show(stderr, exoc)
        self.api.jl_printf(self.api.jl_stderr_stream(), "\n");

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
        self.eval('help("{}")'.format(name))

    def eval(self, src):
        """ Execute code in Julia, then pull some results back to Python. """
        if src is None:
            return None
        #print "eval('%s')" % src
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
