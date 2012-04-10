# -*- coding: utf-8 -*-

"""
blueox.network
~~~~~~~~

This module provides our interface into ZeroMQ

:copyright: (c) 2012 by Rhett Garber.
:license: ISC, see LICENSE for more details.

"""
import logging

import zmq
import bson

log = logging.getLogger(__name__)

_zmq_context = None
_zmq_socket = None

def init(host, port):
    global _zmq_context
    global _zmq_socket

    _zmq_context = zmq.Context()

    _zmq_socket = _zmq_context.socket(zmq.PUSH)
    _zmq_socket.connect("tcp://%s:%d" % (host, port))
    _zmq_socket.hwm = 100

def send(context):
    if _zmq_socket is not None:
        try:
            _zmq_socket.send(bson.dumps(context.to_dict()), zmq.NOBLOCK)
        except zmq.ZMQError, e:
            log.exception("Failed sending blueox event, buffer full?")
    else:
        log.info("Skipping sending event %s", context.name)

def close():
    global _zmq_context
    global _zmq_socket

    _zmq_socket.close()
    _zmq_socket = None
    _zmq_context = None
