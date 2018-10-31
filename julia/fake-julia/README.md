This directory contains a python script that pretends to be the julia executable
and is used as such to allow julia precompilation to happen in the same environment.

When a Julia module Foo marked with `__precompile__(true)` is imported in Julia, it gets "precompiled" to
a Foo.ji cache file that speeds up subsequent loads.  See:
    https://docs.julialang.org/en/stable/manual/modules/#Module-initialization-and-precompilation-1
A key thing to understand is that this precompilation works by *launching a new Julia process*
that loads the module in a special "output-ji" mode (by running `julia --output-ji`) that creates
the cache file.

A second key thing to understand is that pyjulia is using PyCall configured in a different way than
when PyCall is called from with a `julia` process.  Within a `julia` process, PyCall works by loading
`libpython` to call the CPython API.   Within a `python` process (for `pyjulia`), at least if
`python` is statically linked to `libpython`, PyCall works instead by loading CPython API symbols from
the `python` process itself.   This difference affects how PyCall functions are compiled, which means
that *pyjulia cannot use the same PyCall.ji cache file* as julia.   This extends to any Julia module
*using* PyCall: every such module needs to have a precompiled cache file that is different from the ordinary
Julia module cache.

The combination of these two facts mean that when PyCall, or any Julia module that uses PyCall,
is loaded from pyjulia with a statically linked `python`, we have to precompile a separate version of it.
Since "normal" precompilation launches a new `julia` process, this process would create the wrong
(`libpython`) version of the PyCall cache file.    So, we have to force precompilation to launch
a `python` process, not a `julia` process, so that PyCall is compiled correctly for running inside `python`.

That is what `fake-julia` does.   By changing the `JULIA_HOME` (v0.6) or `JULIA_BINDIR` (v0.7+) environment variable, we trick Julia
into launching `fake-julia/julia` instead of the "real" `julia` process during precompilation.  `fake-julia/julia`
is actually a Python script, but it links `libjulia` and uses `libjulia` to process the command-line arguments,
so it mimics the behavior of the `julia` process.  Since `fake-julia/julia` is running from within the `python`
process, PyCall configures itself correctly.

(From the above discussion, it should be clear that the fake-julia trick is only really necessary for
compiling PyCall and other Julia modules that use PyCall.   For other Julia modules, the compiled code
should be identical to the normal Julia cache, so as an optimization `fake-julia/julia` shares the same cache
file with the real `julia` in that case.)

See also the discussion in https://github.com/JuliaPy/PyCall.jl/pull/293 and https://github.com/JuliaPy/pyjulia/pull/54
