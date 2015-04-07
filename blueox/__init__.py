# -*- coding: utf-8 -*-

"""
blueox
~~~~~~~~

:copyright: (c) 2012 by Rhett Garber
:license: ISC, see LICENSE for more details.

"""

__title__ = 'blueox'
__version__ = '0.9.2'
__author__ = 'Rhett Garber'
__author_email__ = 'rhettg@gmail.com'
__license__ = 'ISC'
__copyright__ = 'Copyright 2012 Rhett Garber'
__description__ = 'A library for python-based application logging and data collection'
__url__ = 'https://github.com/rhettg/BlueOx'

import logging
import os

from . import utils
from . import network
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


ENV_VAR_HOST = 'BLUEOX_HOST'
ENV_VAR_PORT = 'BLUEOX_PORT'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 3514


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
    if host is None:
        host = os.environ.get(ENV_VAR_HOST, DEFAULT_HOST)

    if ':' not in host:
        configured_port = os.environ.get(ENV_VAR_PORT, DEFAULT_PORT)
        host = "{}:{}".format(configured_port)

    hostname, port = host.split(':')

    try:
        int_port = int(port)
    except ValueError:
        raise Error("Invalid value for port")

    configure(hostname, int_port)


def shutdown():
    network.close()
