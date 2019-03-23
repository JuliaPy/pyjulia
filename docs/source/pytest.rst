===============
 pytest plugin
===============

.. program:: pytest

PyJulia automatically installs a `pytest plugin
<https://docs.pytest.org/en/latest/plugins.html>`_.  It takes care of
tricky aspects of PyJulia initialization:

* It loads ``libjulia`` as early as possible to avoid incompatibility
  of shared libraries such as ``libstdc++`` (assuming that the ones
  bundled with ``julia`` are newer than the ones otherwise loaded).

* It provides a way to succinctly mark certain tests require Julia
  runtime (see `Fixture`_).

* The tests requiring Julia can be skipped with :option:`--no-julia`.

Use |pytest -p no:pyjulia|_ to disable PyJulia plugin.

.. |pytest -p no:pyjulia| replace:: ``pytest -p no:pyjulia``
.. _pytest -p no:pyjulia:
   https://docs.pytest.org/en/latest/plugins.html#deactivating-unregistering-a-plugin-by-name


Options
=======

Following options can be passed to :program:`pytest`

.. option:: --no-julia

   Skip tests that require julia.

.. option:: --julia-runtime

   Julia executable to be used.  Defaults to environment variable
   `PYJULIA_TEST_RUNTIME`.

Fixture
=======

PyJulia's pytest plugin includes a `pytest fixture
<https://docs.pytest.org/en/latest/fixture.html>`_ ``julia`` which is
set to an instance of :class:`.Julia` that is appropriately
initialized.  Example usage::

   def test_eval(julia):
       assert julia.eval("1 + 1") == 2

This fixture also "marks" that this test requires a Julia runtime.
Thus, the tests using ``julia`` fixture are not run when
:option:`--no-julia` is passed.
