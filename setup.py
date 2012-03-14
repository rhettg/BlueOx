#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ziggy
from distutils.core import setup

# publish package
#if sys.argv[-1] == 'publish':
#    os.system('python setup.py sdist upload')
#    sys.exit()
#
## run tests
#if sys.argv[-1] == 'test':
#    os.system('python test_requests.py')
#    sys.exit()


setup(
    name='ziggy',
    version=ziggy.__version__,
    description='Ziggy Application Logging',
    long_description=open('README.rst').read(),
    author='Rhett Garber',
    url='http://github.com/rhettg/Ziggy',
    package_data={'': ['LICENSE', 'NOTICE']},
    license=bootstrap.__license__,
    #packages=find_packages()
    packages=['ziggy']
)
