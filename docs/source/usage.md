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

In IPython (and therefore in Jupyter), you can directly execute Julia code using `%julia` magic:

```python
In [1]: %load_ext julia.magic
Initializing Julia interpreter. This may take some time...

In [2]: %julia [1 2; 3 4] .+ 1 
Out[2]: 
array([[2, 3],
       [4, 5]], dtype=int64)
```

You can "interpolate" Python objects into Julia code via `$var` for the value of single variables or `py"expression"` for the result of any arbitrary Python code:
```julia
In [3]: arr = [1,2,3]

In [4]: %julia $arr .+ 1
Out[4]: 
array([2, 3, 4], dtype=int64)

In [5]: %julia sum(py"[x**2 for x in arr]")
Out[5]: 14
```

Python interpolation is not performed inside of strings (instead this is treated as regular Julia string interpolation), and can also be overridden elsewhere by using `$$...` to insert a literal `$...`:

```julia
In [6]: %julia foo=3; "$foo"
Out[6]: '3'

In [7]: %julia bar=3; :($$bar)
Out[7]: 3
```

Variables are automatically converted between equivalent Python/Julia types (should they exist). You can turn this off by appending `o` to the Python string:

```python
In [8]: %julia typeof(py"1"), typeof(py"1"o)
Out[8]: (<PyCall.jlwrap Int64>, <PyCall.jlwrap PyObject>)
```

Interpolated variables obey Python scope, as expected:

```python
In [9]: x = "global"
   ...: def f():
   ...:     x = "local"
   ...:     ret = %julia py"x"
   ...:     return ret
   ...: f()
Out[9]: 'local'
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
