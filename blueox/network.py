# -*- coding: utf-8 -*-

"""
blueox.network
~~~~~~~~

This module provides our interface into ZeroMQ

:copyright: (c) 2012 by Rhett Garber.
:license: ISC, see LICENSE for more details.

"""
import logging
import struct

import zmq
import msgpack

log = logging.getLogger(__name__)

META_STRUCT_FMT = ">Bf64p64p"

# We're going to include a version byte in our meta struct for future
# upgrading.  This is very quickly getting into the kind of bit packing I
# wanted to avoid for a logging infrastructure, but the performance gain is
# hard to ignore.
META_STRUCT_VERSION = 0x2
def check_meta_version(meta):
    value, = struct.unpack(">B", meta[0])
    if value != META_STRUCT_VERSION:
        raise ValueError(value)

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

            # Our sending format is made up of two messages. The first has a
            # quick to unpack set of meta data that our collector is going to
            # use for routing and stats. This is much faster than having the
            # collector decode the whole event. We're just going to use python
            # struct module to make a quick and dirty data structure
            context_dict = context.to_dict()
            assert len(context_dict['host']) < 64
            assert len(context_dict['type']) < 64
            meta_data = struct.pack(META_STRUCT_FMT, META_STRUCT_VERSION, context_dict['end'], context_dict['host'], context_dict['type'])

            _zmq_socket.send(meta_data, zmq.NOBLOCK|zmq.SNDMORE)
            _zmq_socket.send(msgpack.packb(context_dict), zmq.NOBLOCK)
        except zmq.ZMQError, e:
            log.exception("Failed sending blueox event, buffer full?")
    else:
        log.info("Skipping sending event %s", context.name)

def close():
    global _zmq_context
    global _zmq_socket

    if _zmq_socket:
        _zmq_socket.close()
        _zmq_socket = None
    _zmq_context = None
