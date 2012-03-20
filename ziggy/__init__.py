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

import logging

from . import utils
from . import network
from .context import Context, set, append, add
from . import context as _context_mod
from .errors import Error
from .timer import timeit

log = logging.getLogger(__name__)


def configure(host, port, recorder=None):
    """Initialize ziggy

    This instructs the ziggy system where to send it's logging data. If ziggy is not configured, log data will
    be silently dropped.

    Currently we support logging through the network (and the configured host and port) to a ziggyd instances, or
    to the specified recorder function
    """
    global _record_function
    if recorder:
        context._recorder_function = recorder
    elif host and port:
        network.init(host, port)
        context._recorder_function = network.send
    else:
        log.info("Empty ziggy configuration")
        context._recorder_function = None

