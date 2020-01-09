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
  runtime (see `Fixture`_ and `Marker`_).

* The tests requiring Julia can be skipped with :option:`--no-julia`.

* It enables debug-level logging.  This is highly recommended
  especially in CI setting as miss-configuration of PyJulia may result
  in segmentation fault in which Python cannot provide useful
  traceback.

To activate PyJulia's pytest plugin [#]_ add ``-p julia.pytestplugin``
to the command line option.  There are several ways to do this by
default in your project.  One option is to include this using
``addopts`` setup of ``pytest.ini`` or ``tox.ini`` file.  See `How to
change command line options defaults
<https://docs.pytest.org/en/latest/customize.html#adding-default-options>`_:

.. code-block:: ini

   [pytest]
   addopts =
       -p julia.pytestplugin

.. [#] This plugin is not activated by default (as in normal
   ``pytest-*`` plugin packages) to avoid accidentally breaking user's
   ``pytest`` setup when PyJulia is included as a non-test dependency.


Options
=======

Following options can be passed to :program:`pytest`

.. option:: --no-julia

   Skip tests that require julia.

.. option:: --julia

   Undo ``--no-julia``; i.e., run tests that require julia.

.. option:: --julia-runtime

   Julia executable to be used.  Defaults to environment variable
   `PYJULIA_TEST_RUNTIME`.

.. option:: --julia-<julia_option>

   Some ``<julia_option>`` that can be passed to ``julia`` executable
   (e.g., ``--compiled-modules=no``) can be passed to ``pytest``
   plugin by ``--julia-<julia_option>`` (e.g.,
   ``--julia-compiled-modules=no``).  See ``pytest -p
   julia.pytestplugin --help`` for the actual list of options.


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


Marker
======

PyJulia's pytest plugin also includes a `pytest marker
<https://docs.pytest.org/en/latest/example/markers.html>`_ ``julia``
which can be used to mark that the test requires PyJulia setup.  It is
similar to ``julia`` fixture but it does not instantiate the actual
:class:`.Julia` object.

Example usage::

   import pytest

   @pytest.mark.julia
   def test_import():
       from julia import MyModule
