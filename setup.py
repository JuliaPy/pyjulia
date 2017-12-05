#!/usr/bin/env python
"""Julia/Python bridge with IPython support.
"""

from setuptools import setup
import sys

doc = __doc__
try:
    import pypandoc
    with open('README.md') as f:
        desc = f.read()
    print('will convert description from markdown to rst.')
    doc = pypandoc.convert(desc, 'rst', format='markdown')
except Exception:
    print('Unable to convert markdown to rst. Please install `pypandoc` and `pandoc` to use markdown long description.')

setup(name='julia',
      version='0.1.5',
      description=doc,
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
      ],
      url='http://julialang.org',
      packages=['julia'],
      package_data={'julia': ['fake-julia/*']}
     )
