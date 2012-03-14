# -*- coding: utf-8 -*-

"""
ziggy.context
~~~~~~~~

This module provides utility functions that are used within Bootstrap
that are also useful for external consumption.

:copyright: (c) 2012 by Firstname Lastname.
:license: ISC, see LICENSE for more details.

"""

from . import utils

class Context(object):
    def __init__(self, name, *args):
        self.name = name
        self.data = {}
        if len(args) > 1:
            self.id = args
        elif len(args) == 1:
            self.id = args[0]
        else:
            parent_ctx = get_context(utils.key_parse(name)[:-1])
            if parent_ctx:
                self.id = parent_ctx.id

        if self.id:
            self.data['_id'] = self.id


    def set(key, *args, **kwargs):
        existing_value = utils.get_deep(self.data, key, None)

        if len(args) > 1:
            utils.set_deep(self.data, key, args)
        elif args:
            utils.set_deep(self.data, key, args[0])
        
        if kwargs:
            existing_value.update(kwargs)
            utils.set_deep(self.data, key, existing)

    def append(key, value):
        existing_value = utils.get_deep(self.data, key, [])
        existing_value.append(value)
        if len(existing_value) == 1:
            utils.set_deep(self.data, key, existing_value)

    def __enter__(self):
        _add_context(self)

    def __exit__(self, type, value, traceback):
        _remove_context(self)


_contexts_by_name = {}

def _add_context(context):
    _contexts_by_name[context.name] = context

def _remove_context(context):
    del _contexts_by_name[context.name]
