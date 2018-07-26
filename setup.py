#!/usr/bin/env python

from distutils.core import setup

setup(name='nexusutils',
      version='1.0',
      description='Python NeXus Utilities',
      url='https://github.com/ess-dmsc/python-nexus-utilities',
      packages=['nexusutils'],
      dependency_links=['https://archive.panda3d.org/'],
      install_requires=['appdirs',
                        'h5py',
                        'numexpr',
                        'numpy',
                        'packaging',
                        'pyparsing',
                        'tables',
                        'matplotlib',
                        'tabulate',
                        'panda3d']
      )
