# -*- coding: utf-8 -*-

"""
blueox.timer
~~~~~~~~

This module has a timer context manager for easily tracking wall-clock time for some execution
:copyright: (c) 2012 by Rhett Garber
:license: ISC, see LICENSE for more details.

"""
import time

from . import context

class Timer(object):
    def __init__(self, context, key):
        self.context = context
        self.key = key
        self.start_time = time.time()

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.context.set(self.key, time.time() - self.start_time)

def timeit(key):
    return Timer(context.current_context(), key)
