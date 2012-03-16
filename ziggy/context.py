# -*- coding: utf-8 -*-

"""
ziggy.context
~~~~~~~~

This module provides the concept of 'Context' for collecting data that will
generate a log event.

:copyright: (c) 2012 by Rhett Garber
:license: ISC, see LICENSE for more details.

"""
import time
import os
import random
import struct

from . import utils
from . import network

# This will be redefined by our configuration to tell us where to record stuff
# to.
_recorder_function = None

class Context(object):
    __slots__ = ["name", "data", "id", "_writable", "start_time", "_sample_checks", "enabled"]
    def __init__(self, type_name, id=None, sample=None):
        parent_ctx = current_context()

        if parent_ctx:
            self.name = ".".join((parent_ctx.name, type_name))
        else:
            self.name = type_name

        self.data = {}
        self.start_time = time.time()
        self._sample_checks = {}

        if id is not None:
            self.id = id
        elif parent_ctx:
            self.id = parent_ctx.id
        else:
            # Generate an id if one wasn't provided and we don't have any parents
            # We're going to encode the time as the front 4 bytes so we have some order to the ids
            # that could prove useful later on by making sorting a little easier.
            self.id = (struct.pack(">L", time.time()) + os.urandom(12)).encode('hex')

        if parent_ctx and not parent_ctx.enabled:
            self.enabled = False
        elif sample:
            sample_name, rate = sample
            if sample_name == type_name or sample_name == '.':
                self.enabled = bool(random.random() <= rate)
            elif parent_ctx and sample_name == '..':
                self.enabled = parent_ctx.sampled_for(type_name, rate)
            else:
                self.enabled = _get_context(sample_name).sampled_for(type_name, rate)
        else:
            self.enabled = True

        self._writable = False

    @property
    def writable(self):
        """Indicates the contest is open and can be written to"""
        return self._writable

    def sampled_for(self, name, rate):
        if name not in self._sample_checks:
            self._sample_checks[name] = bool(random.random() <= rate)
        return self._sample_checks[name]

    def set(self, key, *args, **kwargs):
        if not self.writable:
            raise ValueError()

        if args and kwargs:
            raise ValueError()

        if len(args) > 1:
            utils.set_deep(self.data, key, args)
        elif args:
            utils.set_deep(self.data, key, args[0])
        elif kwargs:
            existing_value = utils.get_deep(self.data, key, {})
            existing_value.update(kwargs)
            utils.set_deep(self.data, key, existing_value)

    def append(self, key, value):
        if not self.writable:
            raise ValueError()

        existing_value = utils.get_deep(self.data, key, [])
        existing_value.append(value)
        if len(existing_value) == 1:
            utils.set_deep(self.data, key, existing_value)

    def add(self, key, value):
        if not self.writable:
            raise ValueError()

        existing_value = utils.get_deep(self.data, key, 0)
        utils.set_deep(self.data, key, existing_value + value)

    def to_dict(self):
        return {'id': self.id,
                'type': self.name,
                'start_time': self.start_time,
                'end_time': time.time(),
                'body': self.data
               }

    def start(self):
        _add_context(self)
        self._writable = True

    def stop(self):
        self._writable = False
        _remove_context(self)

    def done(self):
        self.stop() # Just be sure
        if self.enabled and _recorder_function:
            _recorder_function(self)

        # Make sure we don't get any duplicate data
        # I would clear out all the data here, but that makes testing a little
        # more challenging.
        self.enabled = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()
        self.done()

_contexts = []
_contexts_by_name = {}

def _add_context(context):
    if context.name in _contexts_by_name:
        return
    _contexts_by_name[context.name] = context
    _contexts.append(context)

def _get_context(name):
    return _contexts_by_name.get(str(name))

def _remove_context(context):
    try:
        del _contexts_by_name[context.name]
    except KeyError:
        pass

    try:
        _contexts.remove(context)
    except ValueError:
        pass

def current_context():
    try:
        return _contexts[-1]
    except IndexError:
        return None

def set(*args, **kwargs):
    context = current_context()
    if context:
        context.set(*args, **kwargs)

def append(*args, **kwargs):
    context = current_context()
    if context:
        context.append(*args, **kwargs)

def add(*args, **kwargs):
    context = current_context()
    if context:
        context.add(*args, **kwargs)
