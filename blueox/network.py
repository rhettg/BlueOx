# -*- coding: utf-8 -*-

"""
blueox.network
~~~~~~~~

This module provides our interface into ZeroMQ

:copyright: (c) 2012 by Rhett Garber.
:license: ISC, see LICENSE for more details.

"""
import logging
import threading
import struct

import zmq
import msgpack

log = logging.getLogger(__name__)

# We want to limit how many messages we'll hold in memory so if our oxd is
# unavailable, we don't just run out of memory.  I based this value on rough
# value of rather large 3k sized messages, and how many we can fit in 10 megs.
MAX_QUEUED_MESSAGES = 3500

# If we have pending outgoing messages, this is how long we'll wait after
# being told to exit.
LINGER_SHUTDOWN_MSECS = 2000

META_STRUCT_FMT = "!Bd64p64p"

# We're going to include a version byte in our meta struct for future
# upgrading.  This is very quickly getting into the kind of bit packing I
# wanted to avoid for a logging infrastructure, but the performance gain is
# hard to ignore.
META_STRUCT_VERSION = 0x3
def check_meta_version(meta):
    value, = struct.unpack(">B", meta[0])
    if value != META_STRUCT_VERSION:
        raise ValueError(value)

threadLocal = threading.local()

# Context can be shared between threads
_zmq_context = None
_connect_str = None

def init(host, port):
    global _zmq_context
    global _connect_str

    _zmq_context = zmq.Context()
    _connect_str = "tcp://%s:%d" % (host, port)

def _thread_connect():
    if _zmq_context and not getattr(threadLocal, 'zmq_socket', None):
        threadLocal.zmq_socket = _zmq_context.socket(zmq.PUSH)
        threadLocal.zmq_socket.hwm = MAX_QUEUED_MESSAGES
        threadLocal.zmq_socket.linger = LINGER_SHUTDOWN_MSECS

        threadLocal.zmq_socket.connect(_connect_str)

def send(context):
    global _zmq_context
    _thread_connect()
    if threadLocal.zmq_socket is not None:
        try:
            log.info("Sending msg")
            # Our sending format is made up of two messages. The first has a
            # quick to unpack set of meta data that our collector is going to
            # use for routing and stats. This is much faster than having the
            # collector decode the whole event. We're just going to use python
            # struct module to make a quick and dirty data structure
            context_dict = context.to_dict()
            assert len(context_dict['host']) < 64
            assert len(context_dict['type']) < 64
            meta_data = struct.pack(META_STRUCT_FMT, META_STRUCT_VERSION, context_dict['end'], context_dict['host'], context_dict['type'])

            threadLocal.zmq_socket.send_multipart((meta_data, msgpack.packb(context_dict)), zmq.NOBLOCK)
        except zmq.ZMQError, e:
            log.exception("Failed sending blueox event, buffer full?")
    else:
        log.info("Skipping sending event %s", context.name)

def close():
    global _zmq_context

    if getattr(threadLocal, 'zmq_socket', None):
        threadLocal.zmq_socket.close()
        threadLocal.zmq_socket = None

    _zmq_context = None
