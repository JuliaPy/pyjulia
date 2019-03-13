PyJulia
=======

[![Latest documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://pyjulia.readthedocs.io/en/latest/)
[![Build Status](https://travis-ci.org/JuliaPy/pyjulia.svg?branch=master)](https://travis-ci.org/JuliaPy/pyjulia)
[![Build status](https://ci.appveyor.com/api/projects/status/github/JuliaPy/pyjulia?svg=true)](https://ci.appveyor.com/project/Keno/pyjulia)

Experimenting with developing a better interface to [Julia language](https://julialang.org/) that works with [Python](https://www.python.org/) 2 & 3 and Julia v0.6+.

Quick usage
-----------

```console
$ julia                                  # install PyCall.jl
...
julia> using Pkg  # for julia ≥ 0.7
julia> Pkg.add("PyCall")
...
julia> exit()

$ python3 -m pip install --user julia    # install PyJulia
...

$ python3                                # short demo
>>> from julia import Base
>>> Base.sind(90)
1.0
```

See more in the [documentation](https://pyjulia.readthedocs.io).
