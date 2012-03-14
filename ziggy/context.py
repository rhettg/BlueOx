# -*- coding: utf-8 -*-

"""
ziggy.context
~~~~~~~~

This module provides utility functions that are used within Bootstrap
that are also useful for external consumption.

:copyright: (c) 2012 by Rhett Garber
:license: ISC, see LICENSE for more details.

"""

from . import utils
from . import network

class Context(object):
    __slots__ = ["name", "data", "id", "_writable"]
    def __init__(self, name, *args):
        self.name = name
        self.data = {}

        # Figure out an id for our context. It could be provided to us, 
        # or it could need to be inhertied from our parent
        self.id = None
        if len(args) > 1:
            self.id = args
        elif len(args) == 1:
            self.id = args[0]
        else:
            parent_ctx = _get_context(utils.parse_key(name)[:-1])
            if parent_ctx:
                self.id = parent_ctx.id

        if self.id:
            self.data['_id'] = self.id

        self._writable = False

    @property
    def writable(self):
        """Indicates the contest is open and can be written to"""
        return self._writable

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

    def __enter__(self):
        _add_context(self)
        self._writable = True
        return self

    def __exit__(self, type, value, traceback):
        self._writable = False
        _remove_context(self)
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

def set(*args, **kwargs):
    try:
        context = _contexts[-1]
    except IndexError:
        pass
    else:
        context.set(*args, **kwargs)

def append(*args, **kwargs):
    try:
        context = _contexts[-1]
    except IndexError:
        pass
    else:
        context.append(*args, **kwargs)
