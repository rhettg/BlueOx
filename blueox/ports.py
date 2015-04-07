# -*- coding: utf-8 -*-

"""
blueox.ports
~~~~~~~~

This module provides utilities for generating connect strings.

BlueOx, thanks to it's 0mq roots has a somewhat complex relationship with
ports, which we'd like to abstract from the user as much as possible.

:copyright: (c) 2015 by Rhett Garber
:license: ISC, see LICENSE for more details.

"""
import os


ENV_VAR_CONTROL_HOST = 'BLUEOX_CLIENT_HOST'
ENV_VAR_COLLECT_HOST = 'BLUEOX_HOST'

DEFAULT_HOST = '127.0.0.1'
DEFAULT_CONTROL_PORT = 3513
DEFAULT_COLLECT_PORT = 3514


def _default_host(host, default_host, default_port):
    """Build a default host string
    """
    if not host:
        host = default_host
    if ':' not in host:
        host = "{}:{}".format(host, default_port)

    return host


def default_control_host(host=None):
    default_host = os.environ.get(ENV_VAR_CONTROL_HOST, DEFAULT_HOST)
    return _default_host(host, default_host, DEFAULT_CONTROL_PORT)


def default_collect_host(host=None):
    default_host = os.environ.get(ENV_VAR_COLLECT_HOST, DEFAULT_HOST)
    return _default_host(host, default_host, DEFAULT_COLLECT_PORT)
