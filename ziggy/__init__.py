# -*- coding: utf-8 -*-

"""
Ziggy
~~~~~~~~

:copyright: (c) 2012 by Rhett Garber
:license: ISC, see LICENSE for more details.

"""

__title__ = 'ziggy'
__version__ = '0.0.1'
__build__ = 0
__author__ = 'Rhett Garber'
__license__ = 'ISC'
__copyright__ = 'Copyright 2012 Rhett Garber'


from . import utils
from . import network
from .context import Context, set, append
from .errors import Error
from .timer import timeit

def configure(host, port):
    network.init(host, port)
