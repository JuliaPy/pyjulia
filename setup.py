#!/usr/bin/env python

from setuptools import setup
import os


def pyload(name):
    ns = {}
    with open(name) as f:
        exec(compile(f.read(), name, "exec"), ns)
    return ns

# In case it's Python 2:
try:
    execfile
except NameError:
    pass
else:
    def pyload(path):
        ns = {}
        execfile(path, ns)
        return ns


repo_root = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(repo_root, "README.md")) as f:
    long_description = f.read()
# https://packaging.python.org/guides/making-a-pypi-friendly-readme/

ns = pyload(os.path.join(repo_root, "julia", "release.py"))
version = ns["__version__"]

setup(name='julia',
      version=version,
      description="Julia/Python bridge with IPython support.",
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='The Julia and IPython development teams.',
      author_email='julia@julialang.org',
      license='MIT',
      keywords='julia python',
      classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        #'Intended Audience :: Developers',

        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
      ],
      url='http://julialang.org',
      packages=['julia'],
      package_data={'julia': ['fake-julia/*']},
      entry_points={
          "console_scripts": [
              "python-jl = julia.python_jl:main",
          ],
      },
      # We bundle Julia scripts etc. inside `julia` directory.  Thus,
      # this directory must exist in the file system (not in a zip
      # file):
      zip_safe=False,
      )
