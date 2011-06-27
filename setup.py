#!/usr/bin/env python
"""swissknife -- installer script"""

__author__  = "Tamas Nepusz"
__email__   = "ntamas@gmail.com"
__copyright__ = "Copyright (c) 2010-2011, Tamas Nepusz"
__license__ = "GPL"

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages

params = {}
params["name"] = "swissknife"
params["version"] = "1.0"
params["description"] = "A collection of handy utilities for data crunching"

params["packages"] = find_packages(exclude='tests')
params["scripts"] = ["bin/aggregate", "bin/groupby", "bin/remap", "bin/qplot"]

setup(**params)

