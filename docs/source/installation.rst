==============
 Installation
==============

.. admonition:: tl;dr

   1. :ref:`Install Julia <install-julia>`.

   2. :ref:`Install PyJulia <install-pyjulia>` by

      .. code-block:: console

         $ python3 -m pip install --user julia

      Remove ``--user`` if you are using a virtual environment.

   3. :ref:`Install Julia dependencies of PyJulia <install-julia-packages>`
      by

      .. code-block:: console

         $ python3
         >>> import julia
         >>> julia.install()

See below for more detailed explanations.

**Note:** If you are using Python installed with Ubuntu or ``conda``,
PyJulia may not work with the default setting. For workarounds, see
:doc:`Troubleshooting <troubleshooting>`. Same caution applies to any
Debian-based and possibly other GNU/Linux distributions.


.. _install-julia:

Step 1: Install Julia
=====================

Get the Julia installer from https://julialang.org/downloads/.  See
also the `Platform Specific Instructions
<https://julialang.org/downloads/platform.html>`_.

Your python installation must be able to call command line program
``julia``. If your installer does not add the Julia binary directory to
your ``PATH``, you will have to add it. *An alias will not work.*

Alternatively, you can pass the file path of the Julia executable to
PyJulia functions.  See `julia.install` and `Julia`.


.. _install-pyjulia:

Step 2: Install PyJulia
=======================

**Note:** If you are not familiar with ``pip`` and have some troubles
with the following installation steps, we recommend going through the
`Tutorial in Python Packaging User Guide
<https://packaging.python.org/tutorials/installing-packages/>`_ or
`pip's User Guide <https://pip.pypa.io/en/stable/user_guide/>`_.

To get released versions you can use:

.. code-block:: console

   $ python3 -m pip install --user julia
   $ python2 -m pip install --user julia  # If you need Python 2

where ``--user`` should be omitted if you are using virtual environment
(``virtualenv``, ``venv``, ``conda``, etc.).

If you are interested in using the development version, you can install
PyJulia directly from GitHub:

.. code-block:: console

   $ python3 -m pip install --user 'https://github.com/JuliaPy/pyjulia/archive/master.zip#egg=julia'

You may clone it directly to (say) your home directory.

.. code-block:: console

   $ git clone https://github.com/JuliaPy/pyjulia

then inside the ``pyjulia`` directory you need to run the python setup
file

.. code-block:: console

   $ cd pyjulia
   $ python3 -m pip install --user .
   $ python3 -m pip install --user -e .  # If you want "development install"

The ``-e`` flag makes a development install, meaning that any change to
PyJulia source tree will take effect at next python interpreter restart
without having to reissue an install command.

See :doc:`Testing <testing>` for how to run tests.


.. _install-julia-packages:

Step 3: Install Julia packages required by PyJulia
==================================================

Launch a Python REPL and run the following code

>>> import julia
>>> julia.install()

This installs Julia packages required by PyJulia.  See also
`julia.install`.

Alternatively, you can use Julia's builtin package manager.

.. code-block:: jlcon

   julia> using Pkg
   julia> Pkg.add("PyCall")

Note that PyCall must be built with Python executable that is used to
import PyJulia.  See https://github.com/JuliaPy/PyCall.jl for more
information about configuring PyCall.
