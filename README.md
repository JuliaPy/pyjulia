PyJulia
=======

[![Build Status](https://travis-ci.org/JuliaLang/pyjulia.svg?branch=master)](https://travis-ci.org/JuliaLang/pyjulia)
[![Build status](https://ci.appveyor.com/api/projects/status/vu38lh59skrtal03?svg=true)](https://ci.appveyor.com/project/EQt/pyjulia)

Experimenting with developing a better interface to julia that works with Python 2 & 3.

to run the tests, execute from the toplevel directory

```shell
python -m unittest discover
```

**Note** You need to explicitly add julia to your `PATH`, an alias will not work.

`pyjulia` is tested against Python versions 2.7, 3.3 and 3.4.  Older versions of Python are not supported.

Installation
------------
You will need to install PyCall in your existing Julia installation

```julia
Pkg.add("PyCall")
```

Your python installation must be able to call Julia.  If your installer
does not add the Julia binary directory to your `PATH`, you will have to
add it.

`pyjulia` is known to work with `PyCall.jl` ≥ `v0.7.2`.

If you run into problems using `pyjulia`, first check the version of `PyCall.jl` you have installed by running `Pkg.installed("PyCall")`.

Usage
-----
To call Julia functions from python, first import the library

```python
import julia
```

then create a Julia object that makes a bridge to the Julia interpreter

```python
j = julia.Julia()
```

You can then call Julia functions from python, e.g.

```python
j.sind(90)
```

How it works
------------
PyJulia loads the `libjulia` library and executes the statements therein.
To convert the variables, the `PyCall` package is used.



Limitations
------------

Not all valid Julia identifiers are valid Python identifiers.  Unicode identifiers are invalid in Python 2.7 and so `pyjulia` cannot call or access Julia methods/variables with names that are not ASCII only.  Additionally, it is a common idiom in Julia to append a `!` character to methods which mutate their arguments.  These method names are invalid Python identifers.  `pyjulia` renames these methods by subsituting `!` with `_b`.  For example, the Julia method `sum!` can be called in `pyjulia` using `sum_b(...)`.


TODOs
-----

* [ ] Think about a mechanism to transfer Python variables to Julia, e.g.
```python
a = [1, 2, 3]
j.push(a)
j.eval("length(a)")
```
  The opposite direction, i.e. transferring Variables from Julia to Python, is easy:
```julia
j.eval("j = [1 2 3]")
a = j.eval("j")
len(a)
```

* [ ] How should we distinguish between different methods in Julia when calling from Python?

* [ ] The code uses the [`ctypes.PYDLL`][pydll] instead of the simple `ctypes.CDLL`.  Maybe we should change this in the future.  Also possible that some issues are because of that.  The biggest difference is the Python _global interpreter lock_ (GIL).


[pydll]: https://docs.python.org/3/library/ctypes.html#ctypes.PyDLL
