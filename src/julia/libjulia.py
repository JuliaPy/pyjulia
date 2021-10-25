from __future__ import absolute_import, print_function

import ctypes
import os
import sys
from contextlib import contextmanager
from ctypes import POINTER, c_char_p, c_int, c_void_p, pointer, py_object
from logging import getLogger  # see `.core.logger`

from .juliainfo import JuliaInfo
from .options import parse_jl_options
from .utils import is_apple, is_windows

logger = getLogger("julia")


UNBOXABLE_TYPES = (
    "bool",
    "int8",
    "uint8",
    "int16",
    "uint16",
    "int32",
    "uint32",
    "int64",
    "uint64",
    "float32",
    "float64",
)


def setup_libjulia(libjulia):
    # Store the running interpreter reference so we can start using it via self.call
    try:
        jl_ = libjulia.jl_
    except AttributeError:
        pass
    else:
        jl_.argtypes = [c_void_p]
        jl_.restype = None

    # Set the return types of some of the bridge functions in ctypes terminology
    libjulia.jl_eval_string.argtypes = [c_char_p]
    libjulia.jl_eval_string.restype = c_void_p

    libjulia.jl_exception_occurred.restype = c_void_p
    libjulia.jl_typeof_str.argtypes = [c_void_p]
    libjulia.jl_typeof_str.restype = c_char_p
    libjulia.jl_call2.argtypes = [c_void_p, c_void_p, c_void_p]
    libjulia.jl_call2.restype = c_void_p
    libjulia.jl_get_field.argtypes = [c_void_p, c_char_p]
    libjulia.jl_get_field.restype = c_void_p
    libjulia.jl_typename_str.restype = c_char_p
    libjulia.jl_unbox_voidpointer.argtypes = [c_void_p]
    libjulia.jl_unbox_voidpointer.restype = py_object

    for c_type in UNBOXABLE_TYPES:
        jl_unbox = getattr(libjulia, "jl_unbox_{}".format(c_type))
        jl_unbox.argtypes = [c_void_p]
        jl_unbox.restype = getattr(
            ctypes,
            "c_{}".format(
                {"float32": "float", "float64": "double"}.get(c_type, c_type)
            ),
        )

    # This does not exist in Julia 1.8 anymore:
    try:
        jl_typeof = libjulia.jl_typeof
    except AttributeError:
        pass
    else:
        jl_typeof.argtypes = [c_void_p]
        jl_typeof.restype = c_void_p

    libjulia.jl_exception_clear.restype = None
    libjulia.jl_stderr_obj.argtypes = []
    libjulia.jl_stderr_obj.restype = c_void_p
    libjulia.jl_stderr_stream.argtypes = []
    libjulia.jl_stderr_stream.restype = c_void_p
    libjulia.jl_printf.restype = ctypes.c_int

    libjulia.jl_parse_opts.argtypes = [POINTER(c_int), POINTER(POINTER(c_char_p))]
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
            raise RuntimeError(
                'Julia library ("libjulia") not found! {}'.format(libjulia_path)
            )

        # fixes a specific issue with python 2.7.13
        # ctypes.windll.LoadLibrary refuses unicode argument
        # http://bugs.python.org/issue29294
        if sys.version_info >= (2, 7, 13) and sys.version_info < (2, 7, 14):
            libjulia_path = libjulia_path.encode("ascii")

        with self._pathhack():
            self.libjulia = ctypes.PyDLL(libjulia_path, ctypes.RTLD_GLOBAL)

        setup_libjulia(self.libjulia)

    @contextmanager
    def _pathhack(self):
        if not is_windows and not is_apple:
            yield
            return
        # Using `os.chdir` as a workaround for an error in Windows
        # "The specified procedure could not be found."  It may be
        # possible to fix this on libjulia side and/or by tweaking
        # load paths directly only in Windows.  However, this solution
        # is reported to work by many users:
        # https://github.com/JuliaPy/pyjulia/issues/67
        # https://github.com/JuliaPy/pyjulia/pull/367
        # Using this workaround for Julia >= 1.6 in macOS for now:
        # https://github.com/JuliaLang/julia/issues/40246
        cwd = os.getcwd()
        try:
            os.chdir(os.path.dirname(self.libjulia_path))
            yield
        finally:
            os.chdir(cwd)

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

        self.was_initialized = self.jl_is_initialized()
        if self.was_initialized:
            set_libjulia(self)
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
            raise RuntimeError(
                "jl_init_path (bindir) {} is not a directory".format(jl_init_path)
            )
        if not os.path.exists(sysimage):
            raise RuntimeError("System image {} does not exist".format(sysimage))

        if options:
            assert not isinstance(options, str)
            # It seems that `argv_list[0]` is ignored and
            # `sys.executable` is used anyway:
            argv_list = [sys.executable]
            argv_list.extend(options)
            if sys.version_info[0] >= 3:
                argv_list = [s.encode("utf-8") for s in argv_list]

            argc = c_int(len(argv_list))
            argv = POINTER(c_char_p)((c_char_p * len(argv_list))(*argv_list))

            logger.debug("argv_list = %r", argv_list)
            logger.debug("argc = %r", argc)
            self.libjulia.jl_parse_opts(pointer(argc), pointer(argv))
            logger.debug("jl_parse_opts called")
            logger.debug("argc = %r", argc)
            for i in range(argc.value):
                logger.debug("argv[%d] = %r", i, argv[i])

        logger.debug("calling jl_init_with_image(%s, %s)", jl_init_path, sysimage)
        with self._pathhack():
            self.jl_init_with_image(
                jl_init_path.encode("utf-8"), sysimage.encode("utf-8")
            )
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


def get_inprocess_libjulia(**kwargs):
    if is_windows:
        # `InProcessLibJulia` does not work on Windows at the
        # moment.  See:
        # https://github.com/JuliaPy/pyjulia/issues/287
        api = LibJulia.load(**kwargs)
        set_libjulia(api)
        return api
    else:
        return InProcessLibJulia()
