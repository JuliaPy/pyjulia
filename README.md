pyjulia
=======

[![Build Status](https://travis-ci.org/JuliaInterop/pyjulia.svg?branch=master)](https://travis-ci.org/JuliaInterop/pyjulia)

Experimenting with developing a better interface to julia that works with Python 2 & 3.

to run the tests, execute from the toplevel directory

```shell
python -m unittest discover
```

**Note** You need to explicitly add julia to your PATH, an alias will not work.

`pyjulia` is tested against Python versions 2.7, 3.3 and 3.4.  Older versions of Python are not supported.

Installation
------------
You will need to install PyCall in your existing Julia installation

```
Pkg.add("PyCall")
```

Your python installation must be able to call Julia.  If your installer
does not add the Julia binary directory to your PATH, you will have to
add it.

`pyjulia` is known to work with `PyCall.jl` ≥ `v0.7.2`.  

If you run into problems using `pyjulia`, first check the version of `PyCall.jl` you have installed by running `Pkg.installed("PyCall")`.

Usage
-----
To call Julia functions from python, first import the library

```
import julia
```

then create a Julia object that makes a bridge to the Julia interpreter

```
j = julia.Julia()
```

You can then call Julia functions from python

```
j.sind(90)
```

Limitations
------------

Not all valid Julia identifiers are valid Python identifiers.  Unicode identifiers are invalid in Python 2.7 and so `pyjulia` cannot call or access Julia methods/variables with names that are not ASCII only.  Additionally, it is a common idiom in Julia to append a `!` character to methods which mutate their arguments.  These method names are invalid Python identifers.  `pyjulia` renames these methods by subsituting `!` with `_b`.  For example, the Julia method `sum!` can be called in `pyjulia` using `sum_b(...)`.
