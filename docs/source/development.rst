Development
===========

Release
-------

Step 1: Test the release candidate using ``test.pypi.org``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Bump the version number and push the change to ``release/test`` branch
in https://github.com/JuliaPy/pyjulia.  This triggers a CI that:

1. runs the tests,
2. releases the package on ``test.pypi.org``,
3. installs the released package, and
4. then runs the test with the installed package.


Step 2: Release
^^^^^^^^^^^^^^^

If the CI pass, run:

.. code-block:: console

   $ make release


Step 3: Tag
^^^^^^^^^^^

Create a Git tag with the form ``vX.Y.Z``, merge ``release/test`` to
``master`` branch, and then push the tag and ``master`` branch.


Special branches
----------------

``release/test``
    Push to this branch triggers the deploy to ``test.pypi.org`` if all
    the tests are passed.  Uploaded package is tested in the next
    stage.

``upload/test``
    Push to this branch triggers the test that would be run for the
    final stage for ``release/test``.  Handy for just testing this
    stage.
