#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import glob
#import ziggy
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
    #version=ziggy.__version__,
    version='0.1.0',
    description='Ziggy Python Application Logging',
    long_description=open('README.md').read(),
    author='Rhett Garber',
    url='http://github.com/rhettg/Ziggy',
    package_data={'': ['LICENSE', 'NOTICE']},
    scripts=glob.glob("bin/*"),
    #license=ziggy.__license__,
    license="ISC",
    #packages=find_packages()
    packages=['ziggy']
)
