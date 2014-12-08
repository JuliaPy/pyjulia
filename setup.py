#!/usr/bin/env python
"""Julia/Python bridge with IPython support.
"""

from setuptools import setup

setup(name='julia',
      version='0.1.1',
      description=__doc__,
      author='The Julia and IPython development teams.',
      author_email='julia@julialang.org',
      license='MIT',
      keywords='julia python',
      classifiers=[
        # Bug for now, I cannot upload if more than 1 classifier
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        #'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        #'Intended Audience :: Developers',

        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        #'Programming Language :: Python :: 2',
        #'Programming Language :: Python :: 2.7',
        #'Programming Language :: Python :: 3',
        #'Programming Language :: Python :: 3.4',
      ],
      url='http://julialang.org',
      packages=['julia'],
     )
