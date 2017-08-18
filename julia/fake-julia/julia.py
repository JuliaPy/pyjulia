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
libjulia = ctypes.PyDLL(libjulia_path, ctypes.RTLD_GLOBAL)
os.environ["JULIA_HOME"] = os.environ["PYCALL_JULIA_HOME"]

if not hasattr(libjulia, "jl_init_with_image"):
    if hasattr(libjulia, "jl_init_with_image__threading"):
        libjulia.jl_init_with_image = libjulia.jl_init_with_image__threading
    else:
        raise ImportError("No libjulia entrypoint found! (tried jl_init and jl_init__threading)")

# Set up the calls from libjulia we'll use
libjulia.jl_parse_opts.argtypes = [POINTER(c_int), POINTER(POINTER(c_char_p))]
libjulia.jl_parse_opts.restype = None
libjulia.jl_init_with_image.argtypes = [c_char_p, c_char_p]
libjulia.jl_init_with_image.restype = None
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
libjulia.jl_init_with_image(os.environ["PYCALL_JULIA_HOME"].encode("utf-8"),
                            os.environ["PYJULIA_IMAGE_FILE"].encode("utf-8"))
libjulia.jl_set_ARGS(argc,argv2[0])
#libjulia.jl_eval_string(u"eval(Base,:(JULIA_HOME=\""+os.environ["PYCALL_JULIA_HOME"]+"\"))")
#libjulia.jl_eval_string(u"eval(Base,:(julia_cmd() = julia_cmd(joinpath(JULIA_HOME, julia_exename()))))")
libjulia.jl_eval_string(b"Base._start()")
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
