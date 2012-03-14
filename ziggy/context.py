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
import random

from . import utils
from . import network

class Context(object):
    __slots__ = ["name", "data", "id", "_writable", "start_time", "_sample_checks", "enabled"]
    def __init__(self, name, id=None, sample=None):
        self.name = name
        self.data = {}
        self.start_time = time.time()
        self._sample_checks = {}

        parent_ctx = _get_context(utils.parse_key(name)[:-1])

        if id is not None:
            self.id = id
        elif parent_ctx:
            self.id = parent_ctx.id

        if parent_ctx and not parent_ctx.enabled:
            self.enabled = False
        elif sample:
            sample_name, rate = sample
            if sample_name == name:
                self.enabled = bool(random.random() <= rate)
            else:
                self.enabled = _get_context(sample_name).sampled_for(name, rate)
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

    def to_dict(self):
        return {'id': self.id,
                'type': self.name,
                'start_time': self.start_time,
                'end_time': time.time(),
                'body': self.data
               }

    def __enter__(self):
        _add_context(self)
        self._writable = True
        return self

    def __exit__(self, type, value, traceback):
        self._writable = False
        _remove_context(self)
        if self.enabled:
            network.send(self)


_contexts = []
_contexts_by_name = {}

def _add_context(context):
    assert context.name not in _contexts_by_name
    _contexts_by_name[context.name] = context
    _contexts.append(context)

def _get_context(name):
    return _contexts_by_name.get(str(name))

def _remove_context(context):
    del _contexts_by_name[context.name]
    _contexts.remove(context)

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
