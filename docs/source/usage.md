Usage
-----

PyJulia provides a high-level interface which assumes a "normal" setup
(e.g., `julia` program is in your `PATH`) and a low-level interface
which can be used in a customized setup.

### High-level interface

To call a Julia function in a Julia module, import the Julia module
(say `Base`) with:

```pycon
>>> from julia import Base
```

and then call Julia functions in `Base` from python, e.g.,

```pycon
>>> Base.sind(90)
```

Other variants of Python import syntax also work:

```pycon
>>> import julia.Base
>>> from julia.Base import Enums    # import a submodule
>>> from julia.Base import sin      # import a function from a module
```

The global namespace of Julia's interpreter can be accessed via a
special module `julia.Main`:

```pycon
>>> from julia import Main
```

You can set names in this module to send Python values to Julia:

```pycon
>>> Main.xs = [1, 2, 3]
```

which allows it to be accessed directly from Julia code, e.g., it can
be evaluated at Julia side using Julia syntax:

```pycon
>>> Main.eval("sin.(xs)")
```

### Low-level interface

If you need a custom setup for PyJulia, it must be done *before*
importing any Julia modules.  For example, to use the Julia
executable named `custom_julia`, run:

```pycon
>>> from julia import Julia
>>> jl = julia.Julia(runtime="custom_julia")
```

You can then use, e.g.,

```pycon
>>> from julia import Base
```

### IPython magic

In IPython (and therefore in Jupyter), you can directly execute Julia code using `%%julia` magic:

```python
In [1]: %load_ext julia.magic
Initializing Julia interpreter. This may take some time...

In [2]: %julia [1 2; 3 4] .+ 1 
Out[2]: 
array([[2, 3],
       [4, 5]], dtype=int64)
```

You can "interpolate" Python results into Julia code via `$var` for single variable names, `$(expression)` for *most* Python code (although notably excluding comprehensions and any Python syntax which is not also valid Julia syntax), or `py"expression"` for *any* arbitrary Python code:

```julia
In [3]: arr = [1,2,3]

In [4]: %julia $arr .+ 1
Out[4]: 
array([2, 3, 4], dtype=int64)

In [5]: %julia $(len(arr))
Out[5]: 3

In [6]: %julia py"[x**2 for x in arr]"
Out[6]: array([1, 4, 9], dtype=int64)
```

Interpolation is never performed inside of strings. If you wish to override interpolation elsewhere, use `$$...` to insert a literal `$...`:

```julia
In [7]: %julia foo=3; "$foo"
Out[7]: '3'

In [8]: %julia bar=3; :($$bar)
Out[8]: 3
```

Variables are automatically converted between equivalent Python/Julia types (should they exist). You can turn this off by appending `o` to the Python string:

```python
In [9]: %julia typeof(py"1"), typeof(py"1"o)
Out[9]: (<PyCall.jlwrap Int64>, <PyCall.jlwrap PyObject>)
```

Note that interpolated variables always refer to the global Python scope:

```python
In [10]: x = "global"
    ...: def f():
    ...:     x = "local"
    ...:     ret = %julia py"x"
    ...:     return ret
    ...: f()
Out[10]: 'global'
```

#### IPython configuration

PyJulia-IPython integration can be configured via IPython's
configuration system.  For the non-default behaviors, add the
following lines in, e.g.,
``~/.ipython/profile_default/ipython_config.py`` (see
[Introduction to IPython configuration](https://ipython.readthedocs.io/en/stable/config/intro.html)).

To disable code completion in ``%julia`` and ``%%julia`` magics, use

```python
c.JuliaMagics.completion = False  # default: True
```

To disable code highlighting in ``%%julia`` magic for terminal
(non-Jupyter) IPython, use

```python
c.JuliaMagics.highlight = False  # default: True
```

To enable [Revise.jl](https://github.com/timholy/Revise.jl)
automatically, use

```python
c.JuliaMagics.revise = True  # default: False
```

### Virtual environments

PyJulia can be used in Python virtual environments created by
`virtualenv`, `venv`, and any tools wrapping them such as `pipenv`,
provided that Python executable used in such environments are linked
to identical libpython used by PyCall.  If this is not the case,
initializing PyJulia (e.g., `import julia.Main`) prints an informative
error message with detected paths to libpython.  See
[PyCall documentation](https://github.com/JuliaPy/PyCall.jl) for how
to configure Python executable.

Note that Python environment created by `conda` is not supported.
