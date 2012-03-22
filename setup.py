#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import glob
from distutils.core import setup

# Some of this would be much nicer if I could put  constants in one place by
# importing the package
# import ziggy

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
    long_description=open('README').read(),
    classifiers=["Topic :: System :: Logging", "Topic :: System :: Monitoring"],
    author='Rhett Garber',
    author_email='rhettg@gmail.com',
    url='http://github.com/rhettg/Ziggy',
    package_data={'': ['LICENSE', 'NOTICE', 'README', 'README.md']},
    scripts=glob.glob("bin/*"),
    #license=ziggy.__license__,
    license="ISC",
    packages=['ziggy'],

)
