Limitations
-----------

Mismatch in valid set of identifiers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Not all valid Julia identifiers are valid Python identifiers. Unicode
identifiers are invalid in Python 2.7 and so PyJulia cannot call or
access Julia methods/variables with names that are not ASCII only.
Although Python 3 allows Unicode identifiers, they are more aggressively
normalized than Julia. For example, ``ϵ`` (GREEK LUNATE EPSILON SYMBOL)
and ``ε`` (GREEK SMALL LETTER EPSILON) are identical in Python 3 but
different in Julia. Additionally, it is a common idiom in Julia to
append a ``!`` character to methods which mutate their arguments. These
method names are invalid Python identifers. PyJulia renames these
methods by subsituting ``!`` with ``_b``. For example, the Julia method
``sum!`` can be called in PyJulia using ``sum_b(...)``.

Pre-compilation mechanism in Julia 1.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There was a major overhaul in the module loading system between Julia
0.6 and 1.0. As a result, the “hack” supporting the PyJulia to load
PyCall stopped working. For the implementation detail of the hack, see:
https://github.com/JuliaPy/pyjulia/tree/v0.3.0/src/julia/fake-julia

For the update on this problem, see:
https://github.com/JuliaLang/julia/issues/28518

Ctrl-C does not work / terminates the whole Python process
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Currently, initializing PyJulia (e.g., by ``from julia import Main``)
disables ``KeyboardInterrupt`` handling in the Python process. If you
are using normal ``python`` interpreter, it means that canceling the
input by Ctrl-C does not work and repeatedly providing Ctrl-C terminates
the whole Python process with the error message
``WARNING: Force throwing a SIGINT``. Using IPython 7.0 or above is
recommended to avoid such accidental shutdown.

It also means that there is no safe way to cancel long-running
computations or I/O at the moment. Sending SIGINT with Ctrl-C will
terminate the whole Python process.

For the update on this problem, see:
https://github.com/JuliaPy/pyjulia/issues/211

No threading support
~~~~~~~~~~~~~~~~~~~~

PyJulia cannot be used in different threads since libjulia is not
thread safe. However, you can `use multiple threads within Julia
<https://docs.julialang.org/en/v1.0/manual/parallel-computing/#Multi-Threading-(Experimental)-1>`_.
For example, start IPython by ``JULIA_NUM_THREADS=4 ipython`` and then
run:

.. code:: julia

   In [1]: %load_ext julia.magic
   Initializing Julia runtime. This may take some time...

   In [2]: %%julia
      ...: a = zeros(10)
      ...: Threads.@threads for i = 1:10
      ...:     a[i] = Threads.threadid()
      ...: end
      ...: a
   Out[3]: array([1., 1., 1., 2., 2., 2., 3., 3., 4., 4.])

PyJulia does not release GIL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PyJulia does not release the Global Interpreter Lock (GIL) while calling
Julia functions since PyCall expects the GIL to be acquired always. It
means that Python code and Julia code cannot run in parallel.
