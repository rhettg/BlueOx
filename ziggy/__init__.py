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
from .context import Context, set, append, add
from . import context as _context_mod
from .errors import Error
from .timer import timeit


def configure(host, port, recorder=None):
    global _record_function
    if recorder is None:
        network.init(host, port)
        context._recorder_function = network.send
    else:
        context._recorder_function = recorder

