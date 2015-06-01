# -*- coding: utf-8 -*-

"""
blueox
~~~~~~~~

:copyright: (c) 2012 by Rhett Garber
:license: ISC, see LICENSE for more details.

"""

__title__ = 'blueox'
__version__ = '0.11.0'
__author__ = 'Rhett Garber'
__author_email__ = 'rhettg@gmail.com'
__license__ = 'ISC'
__copyright__ = 'Copyright 2015 Rhett Garber'
__description__ = 'A library for python-based application logging and data collection'
__url__ = 'https://github.com/rhettg/BlueOx'

import logging
import os

from . import utils
from . import network
from . import ports
from .context import (
    Context,
    set,
    append,
    add,
    context_wrap,
    current_context,
    find_context,
    clear_contexts)
from . import context as _context_mod
from .errors import Error
from .logger import LogHandler
from .timer import timeit

log = logging.getLogger(__name__)


def configure(host, port, recorder=None):
    """Initialize blueox

    This instructs the blueox system where to send it's logging data. If blueox is not configured, log data will
    be silently dropped.

    Currently we support logging through the network (and the configured host and port) to a blueoxd instances, or
    to the specified recorder function
    """
    if recorder:
        _context_mod._recorder_function = recorder
    elif host and port:
        network.init(host, port)
        _context_mod._recorder_function = network.send
    else:
        log.info("Empty blueox configuration")
        _context_mod._recorder_function = None


def default_configure(host=None):
    """Configure BlueOx based on defaults

    Accepts a connection string override in the form `localhost:3514`. Respects
    environment variable BLUEOX_HOST
    """
    host = ports.default_collect_host(host)
    hostname, port = host.split(':')

    try:
        int_port = int(port)
    except ValueError:
        raise Error("Invalid value for port")

    configure(hostname, int_port)


def shutdown():
    network.close()
