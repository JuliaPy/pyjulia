Troubleshooting
---------------

### Your Python interpreter is statically linked to libpython

If you use Python installed with Debian-based Linux distribution such
as Ubuntu or install Python by `conda`, you might have noticed that
PyJulia cannot be initialized properly with Julia ≥ 0.7.  This is
because those Python executables are statically linked to libpython.
(See [Limitations](limitations.md) for why that's a problem.)

If you are unsure if your `python` has this problem, you can quickly
check it by:

```console
$ ldd /usr/bin/python
        linux-vdso.so.1 (0x00007ffd73f7c000)
        libpthread.so.0 => /usr/lib/libpthread.so.0 (0x00007f10ef84e000)
        libc.so.6 => /usr/lib/libc.so.6 (0x00007f10ef68a000)
        libpython3.7m.so.1.0 => /usr/lib/libpython3.7m.so.1.0 (0x00007f10ef116000)
        /lib64/ld-linux-x86-64.so.2 => /usr/lib64/ld-linux-x86-64.so.2 (0x00007f10efaa4000)
        libdl.so.2 => /usr/lib/libdl.so.2 (0x00007f10ef111000)
        libutil.so.1 => /usr/lib/libutil.so.1 (0x00007f10ef10c000)
        libm.so.6 => /usr/lib/libm.so.6 (0x00007f10eef87000)
```

in Linux where `/usr/bin/python` should be replaced with the path to
your `python` command (use `which python` to find it out).  In macOS,
use `otool -L` instead of `ldd`.  If it does not print the path to
libpython like `/usr/lib/libpython3.7m.so.1.0` in above example, you
need to use one of the workaround below.

#### `python-jl`: an easy workaround

The easiest workaround is to use the `python-jl` command bundled in
PyJulia.  This can be used instead of normal `python` command for
basic use-cases such as:

```console
$ python-jl your_script.py
$ python-jl -c 'from julia.Base import banner; banner()'
$ python-jl -m IPython
```

See `python-jl --help` for more information.

##### How `python-jl` works

Note that `python-jl` works by launching Python interpreter inside
Julia.  Importantly, it means that PyJulia has to be installed in the
Python environment with which PyCall is configured.  That is to say,
following commands must work for `python-jl` to be usable:

```jlcon
julia> using PyCall

julia> pyimport("julia")
PyObject <module 'julia' from '/.../julia/__init__.py'>
```

In fact, you can simply use PyJulia inside the Julia REPL, if you are
comfortable with working in it:

```jlcon
julia> using PyCall

julia> py"""
       from julia import Julia
       Julia(init_julia=False)

       from your_module_using_pyjulia import function
       function()
       """
```

#### Turn off compilation cache

PyCall can work with statically linked libpython when compilation
cache is not used.  This can be done by passing keyword option
`compiled_modules=False` to `Julia` which is equivalent to command
line option `--compiled-modules=no`:

```pycon
>>> from julia.api import Julia
>>> jl = Julia(compiled_modules=False)
```

See also [low-level API](api.md)

#### Ultimate fix: build your own Python

Alternatively, you can use [pyenv](https://github.com/pyenv/pyenv) to
build Python with
[`--enable-shared` option](https://github.com/pyenv/pyenv/wiki#how-to-build-cpython-with---enable-shared).
Of course, manually building from Python source distribution with the
same configuration also works.

```console
$ PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.6.6
Downloading Python-3.6.6.tar.xz...
-> https://www.python.org/ftp/python/3.6.6/Python-3.6.6.tar.xz
Installing Python-3.6.6...
Installed Python-3.6.6 to /home/USER/.pyenv/versions/3.6.6

$ ldd ~/.pyenv/versions/3.6.6/bin/python3.6 | grep libpython
        libpython3.6m.so.1.0 => /home/USER/.pyenv/versions/3.6.6/lib/libpython3.6m.so.1.0 (0x00007fca44c8b000)
```

For more discussion, see:
<https://github.com/JuliaPy/pyjulia/issues/185>

### Segmentation fault in IPython

You may experience segmentation fault when using PyJulia in old
versions of IPython.  You can avoid this issue by updating IPython to
7.0 or above.  Alternatively, you can use IPython via Jupyter (e.g.,
`jupyter console`) to workaround the problem.

### Error due to `libstdc++` version

When you use PyJulia with another Python extension, you may see an
error like ``version `GLIBCXX_3.4.22' not found`` (Linux) or `The
procedure entry point ... could not be located in the dynamic link
library libstdc++6.dll` (Windows).  In this case, you might have
observed that initializing PyJulia first fixes the problem.  This is
because Julia (or likely its dependencies like LLVM) requires a recent
version of `libstdc++`.

Possible fixes:

* Initialize PyJulia (e.g., by `from julia import Main`) as early as
  possible.  Note that just importing PyJulia (`import julia`) does
  not work.
* Load `libstdc++.so.6` first by setting environment variable
  `LD_PRELOAD` (Linux) to
  `/PATH/TO/JULIA/DIR/lib/julia/libstdc++.so.6` where
  `/PATH/TO/JULIA/DIR/lib` is the directory which has `libjulia.so`.
  macOS and Windows likely to have similar mechanisms (untested).
* Similarly, set environment variable `LD_LIBRARY_PATH` (Linux) to
  `/PATH/TO/JULIA/DIR/lib/julia` directory.  Using `DYLD_LIBRARY_PATH`
  on macOS and `PATH` on Windows may work (untested).

See:
<https://github.com/JuliaPy/pyjulia/issues/180>,
<https://github.com/JuliaPy/pyjulia/issues/223>
