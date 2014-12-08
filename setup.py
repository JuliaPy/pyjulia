#!/usr/bin/env python
"""Julia/Python bridge with IPython support.
"""
import os

from setuptools import setup

setup(name='julia',
      version='0.1.1',
      description=__doc__,
      author='The Julia and IPython development teams.',
      author_email='julia@julialang.org',
      url='http://julialang.org',
      packages=['julia'],
     )
