This directory contains a python script that pretends to be the julia executable
and is used as such to allow julia precompilation to happen in the same environment.

When a Julia module `Foo` is imported in Julia, it gets "precompiled" to
a Foo.ji cache file that speeds up subsequent loads.  See:
[Module initialization and precompilation](https://docs.julialang.org/en/stable/manual/modules/#Module-initialization-and-precompilation-1)
in Julia manual.  PyCall uses this precompilation mechanism to reduce
JIT compilation required during its initialization.  This results in
embedding the path to `libpython` used by PyCall to its precompilation
cache.  Furthermore, `libpython` ABI such as C struct layout varies
across Python versions.  Currently, this is determined while
precompiling PyJulia and cannot be changed at run-time.  Consequently,
PyJulia can use the precompilation cache of PyCall created by standard
Julia module loader only if the PyCall cache is compiled with the
`libpython` used by the current Python process.  This, of course,
requires the Python executable to be dynamically linked to
`libpython` in the first place.  Furthermore, it also applies to any
Julia packages using PyCall.

If `python` is statically linked to `libpython`, PyJulia has to use
PyCall in a mode that loads CPython API symbols from the `python`
process itself.  Generating a precompilation cache compatible with
this mode requires to do it within a _`python`_ process.  A key thing
to notice here is that the precompilation in Julia works by *launching
a new process* that loads the module in a special "output-ji" mode (by
running `julia --output-ji`) that creates the cache file.  Thus, we
need to configure Julia in such a way that it uses our custom
executable script that behaves like `julia` program for the
precompilation.

That is what `fake-julia` does.   By changing the `JULIA_HOME` (v0.6) we trick Julia
into launching `fake-julia/julia` instead of the "real" `julia` process during precompilation.  `fake-julia/julia`
is actually a Python script, but it links `libjulia` and uses `libjulia` to process the command-line arguments,
so it mimics the behavior of the `julia` process.  Since `fake-julia/julia` is running from within the `python`
process, PyCall configures itself correctly.

(From the above discussion, it should be clear that the fake-julia trick is only really necessary for
compiling PyCall and other Julia modules that use PyCall.   For other Julia modules, the compiled code
should be identical to the normal Julia cache, so as an optimization `fake-julia/julia` shares the same cache
file with the real `julia` in that case.)

Unfortunately, this "hack" does not work for Julia 0.7 and above due
to the change in the module loading system.  For ongoing discussion,
see: https://github.com/JuliaLang/julia/issues/28518

For the discussion during the initial implementation, see also:
https://github.com/JuliaPy/PyCall.jl/pull/293 and
https://github.com/JuliaPy/pyjulia/pull/54
