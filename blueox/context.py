# -*- coding: utf-8 -*-
"""
blueox.context
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
import threading
import functools
import logging

from . import utils
from . import network

log = logging.getLogger(__name__)

# This will be redefined by our configuration to tell us where to record stuff
# to.
_recorder_function = None


class Context(object):
    __slots__ = ["name", "data", "id", "_writable", "start_time",
                 "_sample_checks", "enabled"]

    def __init__(self, type_name, id=None, sample=None):
        """Create a new blueox logging context

        Arguments:
        type_name -- The Name for the event. Special prefix characters can
            control the name with respect to where this context fits into the
            heirarchy of parent requests. Examples:

            '.foo' - Will generate a name like '<parent name>.foo'
            '.foo.bar' - If the parent ends in '.foo', the final name will be '<parent name>.bar'
            '^.foo' - Will use the top-most context, generating '<top parent name>.foo'
            'top.foo.bar' - The name will be based on the longest matched
                parent context. If there is a parent context named 'top' and a
                parent context named 'top.foo', the new context will be named
                'top.foo.bar'

        id -- (optional) user-generated identifier

        sample -- (optional, tuple) of (sample parent, sample ratio). Examples:

            ('..', 0.25) will enable logging for 25% of the parent contexts.
            ('.', 0.25) will enable logging for 25% of the current context.
        """
        if type_name.startswith('.'):
            parent_ctx = current_context()

            if type_name.startswith('..'):
                raise ValueError("Invalid type name")

            clean_type_name = type_name[1:]
        elif type_name.startswith('^'):
            parent_ctx = top_context()

            if not type_name.startswith('^.'):
                raise ValueError("Invalid relative type name syntax")

            clean_type_name = type_name[2:]
        else:
            parent_ctx = find_closest_context(type_name)
            if parent_ctx is None:
                clean_type_name = type_name
            else:
                if parent_ctx.name == type_name:
                    # Previously we crashed with this being an invalid name,
                    # but we probably don't want to crash even though it's a
                    # highly unusual situation.
                    log.warning("Duplicate type name: %r", type_name)
                    clean_type_name = type_name
                elif type_name.startswith(parent_ctx.name):
                    # If the parent is a prefix of our current type name, we'll
                    # keep it as the parent, otherwise we're a separate branch
                    # of the context tree.
                    clean_type_name = type_name[len(parent_ctx.name) + 1:]
                else:
                    clean_type_name = type_name
                    parent_ctx = None

        if parent_ctx is None:
            self.name = clean_type_name
        else:
            parent_parts = sorted(enumerate(parent_ctx.name.split('.')),
                                  reverse=True)
            for ppart_ndx, ppart in parent_parts:
                if ppart == type_name.split('.')[1]:
                    self.name = '.'.join(parent_ctx.name.split('.')[:ppart_ndx]
                                         + type_name.split('.')[1:])
                    break
            else:
                self.name = '.'.join((parent_ctx.name, clean_type_name))

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
            self.id = (struct.pack(">L", time.time()) + os.urandom(12)).encode(
                'hex')

        if parent_ctx and not parent_ctx.enabled:
            self.enabled = False
        elif sample:
            sample_name, rate = sample

            if sample_name == type_name or sample_name == '.':
                sample_parent_ctx = self
            elif sample_name == '..':
                sample_parent_ctx = parent_ctx or self
            elif sample_name == '^':
                sample_parent_ctx = top_context() or self
            else:
                sample_parent_ctx = _get_context(sample_name)

            if sample_parent_ctx == self:
                self.enabled = bool(random.random() <= rate)
            else:
                self.enabled = sample_parent_ctx.sampled_for(type_name, rate)
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
        return {
            'id': self.id,
            'type': self.name,
            'host': os.uname()[1],
            'pid': os.getpid(),
            'start': self.start_time,
            'end': time.time(),
            'body': self.data
        }

    def start(self):
        _add_context(self)
        self._writable = True

    def stop(self):
        self._writable = False
        _remove_context(self)

    def done(self):
        self.stop()  # Just be sure
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


threadLocal = threading.local()


def init_contexts():
    if not getattr(threadLocal, 'init', None):
        threadLocal._contexts = []
        threadLocal._contexts_by_name = {}
        threadLocal.init = True


def clear_contexts():
    """Remove any currently active contexts.

    Does not 'close' any contexts, but just clears out any we may still have a
    handle on. This is useful in testing or anywhere else where you want to be
    absolutely sure you have a clean environment.
    """
    init_contexts()

    threadLocal._contexts_by_name.clear()
    del threadLocal._contexts[:]


def _add_context(context):
    init_contexts()

    if context.name in threadLocal._contexts_by_name:
        return
    threadLocal._contexts_by_name[context.name] = context
    threadLocal._contexts.append(context)


def _get_context(name):
    return threadLocal._contexts_by_name.get(str(name))


def _remove_context(context):
    init_contexts()
    try:
        del threadLocal._contexts_by_name[context.name]
    except KeyError:
        pass

    try:
        threadLocal._contexts.remove(context)
    except ValueError:
        pass


def current_context():
    init_contexts()
    try:
        return threadLocal._contexts[-1]
    except IndexError:
        return None


def top_context():
    """Return the outermost context"""
    init_contexts()
    try:
        return threadLocal._contexts[0]
    except IndexError:
        return None


def _calculate_match_length(a_parts, b_parts):
    length = 0
    for a, b in zip(a_parts, b_parts):
        if a != b:
            break
        length += 1

    return length


def find_closest_context(type_name):
    init_contexts()

    type_name_parts = type_name.split('.')
    if not type_name_parts[0]:
        raise ValueError(type_name)

    matched_ctx = None
    matched_ctx_len = 0
    for ctx in threadLocal._contexts:
        ctx_parts = ctx.name.split('.')

        shared_part_count = _calculate_match_length(type_name_parts, ctx_parts)

        if matched_ctx_len < shared_part_count:
            matched_ctx = ctx
            matched_ctx_len = shared_part_count

    return matched_ctx


def find_context(type_name):
    init_contexts()

    if type_name == '.':
        return current_context()
    elif type_name == '^':
        return top_context()
    elif type_name == '..':
        try:
            return threadLocal._contexts[-2]
        except IndexError:
            return None
    else:
        return _get_context(type_name)


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


def context_wrap(type_name, sample=None):
    """Decorator for wrapping a function call with a context"""

    def wrapper(func):

        @functools.wraps(func)
        def inner(*args, **kwargs):
            with Context(type_name, sample=sample):
                return func(*args, **kwargs)

        return inner

    return wrapper
