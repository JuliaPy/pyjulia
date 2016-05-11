#!/usr/bin/env python
"""
Minimal code to interacte with libjulia
"""

import subprocess
import ctypes
from ctypes import c_void_p as void_p
from ctypes import c_char_p as char_p
import sys

JULIA_EXE = "julia" if len(sys.argv) <= 1 else sys.argv[1]

def print_julia(jlcmd, julia_exe=JULIA_EXE):
    return subprocess.check_output([julia_exe, "-e", "print(" + jlcmd + ")"]).decode("utf8").strip()

libjulia = print_julia('Libdl.dlpath("libjulia")')
JULIA_INIT_DIR = print_julia("dirname(bytestring(Base.JLOptions().julia_bin))")
                                          
print("libjulia       = %s" % libjulia)
print("JULIA_INIT_DIR = %s" % JULIA_INIT_DIR)

api = ctypes.PyDLL(libjulia, ctypes.RTLD_GLOBAL)
api.jl_init.argtypes = [char_p]
api.jl_init(JULIA_INIT_DIR.encode("utf8"))

api.jl_eval_string.argtypes = [char_p]
api.jl_eval_string.restype = void_p
api.jl_exception_occurred.restype = void_p
api.jl_exception_clear.restype = None
api.jl_stderr_obj.argtypes = []
api.jl_stderr_obj.restype = void_p
api.jl_stderr_stream.argtypes = []
api.jl_stderr_stream.restype = void_p
api.jl_show.restype = None
api.jl_show.argtypes = [void_p, void_p]
api.jl_typeof_str.argtypes = [void_p]
api.jl_typeof_str.restype = char_p

api.jl_eval_string(b"import PyCall")
exoc = api.jl_exception_occurred()
if exoc:
    # msg = api.jl_typeof_str(exoc).decode("utf8")
    # print("Exception occured: " + msg)
    stderr = api.jl_stderr_obj()
    print("%x" % stderr)
    api.jl_show(stderr, exoc)


