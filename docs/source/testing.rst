Testing
-------

PyJulia can be tested by simply running |tox|_.

.. code-block:: console

   $ tox

The full syntax for invoking |tox|_ is

.. |tox| replace:: ``tox``
.. _tox: https://tox.readthedocs.io

.. code-block:: console

   $ [PYJULIA_TEST_REBUILD=yes] \
     [PYJULIA_TEST_RUNTIME=<julia>] \
     tox [options] [-- pytest options]

.. envvar:: PYJULIA_TEST_REBUILD

  *Be careful using this environment variable!*  When it is set to
  ``yes``, your ``PyCall.jl`` installation will be rebuilt using the
  Python interpreter used for testing.  The test suite tries to build
  back to the original configuration but the precompilation would be
  in the stale state after the test.  Note also that it does not work
  if you unconditionally set ``PYTHON`` environment variable in your
  Julia startup file.

.. envvar:: PYJULIA_TEST_RUNTIME

   ``julia`` executable to be used for testing.

``[-- pytest options]``
   Positional arguments after ``--`` are passed to |pytest|_.

.. |pytest| replace:: ``pytest``
.. _pytest: https://pytest.org


For example,

.. code-block:: console

   $ PYJULIA_TEST_REBUILD=yes \
     PYJULIA_TEST_RUNTIME=~/julia/julia \
     tox -e py37 -- -s

means to execute tests with

* PyJulia in shared-cache mode
* ``julia`` executable at ``~/julia/julia``
* Python 3.7
* |pytest|_'s capturing mode turned off
