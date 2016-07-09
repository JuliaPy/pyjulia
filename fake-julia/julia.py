# Minimal repl.c to support precompilation with python symbols already loaded
import ctypes
import sys
import os
from ctypes import *
if sys.platform.startswith('darwin'):
    sh_ext = ".dylib"
elif sys.platform.startswith('win32'):
    sh_ext = ".dll"
else:
    sh_ext = ".so"
libjulia_path = os.environ["PYCALL_LIBJULIA_PATH"] + "/lib" + os.environ["PYCALL_JULIA_FLAVOR"] + sh_ext
libjulia = ctypes.CDLL(libjulia_path, ctypes.RTLD_GLOBAL)
os.environ["JULIA_HOME"] = os.environ["PYCALL_JULIA_HOME"]

# Set up the calls from libjulia we'll use
libjulia.jl_parse_opts.argtypes = [POINTER(c_int), POINTER(POINTER(c_char_p))]
libjulia.jl_parse_opts.restype = None
libjulia.jl_init.argtypes = [c_void_p]
libjulia.jl_init.restype = None
libjulia.jl_get_global.argtypes = [c_void_p,c_void_p]
libjulia.jl_get_global.restype = c_void_p
libjulia.jl_symbol.argtypes = [c_char_p]
libjulia.jl_symbol.restype = c_void_p
libjulia.jl_apply_generic.argtypes = [POINTER(c_void_p), c_int]
libjulia.jl_apply_generic.restype = c_void_p
libjulia.jl_set_ARGS.argtypes = [c_int, POINTER(c_char_p)]
libjulia.jl_set_ARGS.restype = None
libjulia.jl_atexit_hook.argtypes = [c_int]
libjulia.jl_atexit_hook.restype = None
libjulia.jl_eval_string.argtypes = [c_char_p]
libjulia.jl_eval_string.restype = None

# Ok, go
argc = c_int(len(sys.argv)-1)
argv = (c_char_p * (len(sys.argv)))()
if sys.version_info[0] < 3:
    argv_strings = sys.argv
else:
    argv_strings = [str.encode('utf-8') for str in sys.argv]
argv[1:-1] = argv_strings[2:]
argv[0] = argv_strings[0]
argv[-1] = None
argv2 = (POINTER(c_char_p) * 1)()
argv2[0] = ctypes.cast(ctypes.addressof(argv),POINTER(c_char_p))
libjulia.jl_parse_opts(byref(argc),argv2)
libjulia.jl_init(0)
libjulia.jl_set_ARGS(argc,argv2[0])
jl_base_module = c_void_p.in_dll(libjulia, "jl_base_module")
_start = libjulia.jl_get_global(jl_base_module, libjulia.jl_symbol(b"_start"))
args = (c_void_p * 1)()
args[0] = _start
libjulia.jl_apply_generic(args, 1)
libjulia.jl_atexit_hook(0)

# As an optimization, share precompiled packages with the main cache directory
libjulia.jl_eval_string(b"""
    outputji = Base.JLOptions().outputji
    if outputji != C_NULL && !isdefined(Main, :PyCall)
        outputfile = unsafe_string(outputji)
        target = Base.LOAD_CACHE_PATH[2]
        targetpath = joinpath(target, basename(outputfile))
        if is_windows()
            try
                cp(outputfile, targetpath; remove_destination = true)
            catch e
                ccall(:jl_, Void, (Any,), e)
            end
        else
            mv(outputfile, targetpath; remove_destination = true)
            symlink(targetpath, outputfile)
        end
    end
""")
