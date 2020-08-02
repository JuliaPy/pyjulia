Development
===========

Release
-------

Step 1: Release
^^^^^^^^^^^^^^^

Bump the version number and push the change to ``release/main`` branch
in https://github.com/JuliaPy/pyjulia.  This triggers a CI that:

1. releases the package on ``test.pypi.org``,
2. installs the released package,
3. runs the test with the installed package and then
4. re-releases the package on ``pypi.org``.


Step 2: Tag
^^^^^^^^^^^

Create a Git tag with the form ``vX.Y.Z``, merge ``release/main`` to
``master`` branch, and then push the tag and ``master`` branch.


Special branches
----------------

``release/main``
    Push to this branch triggers the deploy to ``test.pypi.org``, test
    the uploaded package, and then re-upload it to ``pypi.org``.

``release/test``
    Push to this branch triggers the deploy to ``test.pypi.org`` and
    test the uploaded package.

``release/test-uploaded``
    Push to this branch triggers the test that would be run for the
    final stage for ``release/test``.  Handy for just testing this
    stage.
