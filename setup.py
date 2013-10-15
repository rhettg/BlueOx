#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import glob
from distutils.core import setup

PACKAGES = [
    'blueox',
    'blueox.contrib',
    'blueox.contrib.django',
    'blueox.contrib.celery']

def get_init_val(val, packages=PACKAGES):
    pkg_init = "%s/__init__.py" % PACKAGES[0]
    value = '__%s__' % val
    fn = open(pkg_init)
    for line in fn.readlines():
        if line.startswith(value):
            return line.split('=')[1].strip().strip("'")


setup(
    name='%s' % get_init_val('title'),
    version=get_init_val('version'),
    description=get_init_val('description'),
    long_description=open('README').read(),
    classifiers=["Topic :: System :: Logging", "Topic :: System :: Monitoring"],
    author=get_init_val('author'),
    author_email=get_init_val('author_email'),
    url=get_init_val('url'),
    license=get_init_val('license'),
    package_data={'': ['LICENSE', 'NOTICE', 'README', 'README.md']},
    scripts=glob.glob("bin/*"),
    install_requires=['pyzmq','msgpack_python'],
    requires=['pyzmq','msgpack_python'],
    packages=PACKAGES
)
