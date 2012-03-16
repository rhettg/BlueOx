# -*- coding: utf-8 -*-

"""
ziggy.tornado
~~~~~~~~

This module provides hooks for using ziggy with the Tornado async web server.
Making ziggy useful inside tornado is a challenge since you'll likely want a
ziggy context per request, but multiple requests can be going on at once inside
tornado.

:copyright: (c) 2012 by Rhett Garber
:license: ISC, see LICENSE for more details.

"""
import functools
import logging
import traceback
import types

log = logging.getLogger(__name__)

import tornado.web
import tornado.gen
import tornado.simple_httpclient

import ziggy

def install():
    """Install ziggy hooks by poking into the tornado innards

    THIS MUST BE DONE BEFORE IMPORTING APPLICATION REQUEST HANDLERS
    We have to replace some decorators before they are used to create your class

    This is pretty hacky and may make you feel uncomfortable. It's only here so
    that ziggy can be used with the minimal amount of extra boilerplate.  Your
    always free to be more explicit depending on your needs.

    Up to you if you want to hide your uglyiness in here or have it spread
    throughout your application.
    
    """
    tornado.gen.engine = gen_engine
    tornado.gen.Runner = ZiggyRunner


# Our hook into the request cycle is going to be provided by wrapping the
# _execute() method.  This creates our ziggy context, starts it, and then stops
# it at the end. We'll leave it up to the finish() method to close us out.
def wrap_execute(type_name):
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self.ziggy = ziggy.Context(type_name)
            try:
                self.ziggy.start()
                return func(self, *args, **kwargs)
            finally:
                # We're done executing in this context for the time being. Either we've already
                # finished handling our ziggy context, or we'll allow a later finish() call to 
                # mark it done.
                self.ziggy.stop()

        return wrapper

    return decorate

def wrap_finish(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        finally:
            self.ziggy.done()

    return wrapper

class SampleRequestHandler(tornado.web.RequestHandler):
    """Sample base request handler necessary for providing smart ziggy contexts through a web request.

    We need to wrap two methods: _execute() and finish()

    To specify a name for your top level event, pass it the wrap_execute() decorator.

    The idea is that when _execute is called, we'll generate a ziggy Context
    with the name specified. This should cover any methods like get() or
    post(). When _execute returns, we'll be in either one of two states. Either
    finish() has been called and we are all done, or finish() will be called
    later due to some async complexity. 

    Optionally, we also provide redefined methods that add critical data about
    the request to the active ziggy context.
    """
    def prepare(self):
        ziggy.set('headers', self.request.headers)
        ziggy.set('method', self.request.method)
        ziggy.set('uri', self.request.uri)

    def write_error(self, status_code, **kwargs):
        if 'exc_info' in kwargs:
            ziggy.set('exception', ''.join(traceback.format_exception(*kwargs["exc_info"])))
    
        return super(SampleRequestHandler, self).write_error(status_code, **kwargs)

    def write(self, chunk):
        ziggy.add('response_size', len(chunk))
        return super(SampleRequestHandler, self).write(chunk)

    def finish(self):
        res = super(SampleRequestHandler, self).finish()
        ziggy.set('response_status_code', self._status_code)
        return res

    _execute = wrap_execute('request')(tornado.web.RequestHandler._execute)
    finish = wrap_finish(finish)


# We need a custom version of this decorator so that we can pass in our ziggy
# context to the Runner
def gen_engine(func):
    """Hacked up copy of tornado.gen.engine decorator
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        if isinstance(gen, types.GeneratorType):
            ziggy_ctx = getattr(args[0], 'ziggy', None)
            ZiggyRunner(gen, ziggy_ctx).run()
            return
        assert gen is None, gen
        # no yield, so we're done
    return wrapper


# Custom version of gen.Runner that starts and stops the ziggy context
class ZiggyRunner(tornado.gen.Runner):
    def __init__(self, gen, ziggy_context):
        self.ziggy_ctx = ziggy_context
        super(ZiggyRunner, self).__init__(gen)

    def run(self):
        try:
            if self.ziggy_ctx:
                self.ziggy_ctx.start()

            return super(ZiggyRunner, self).run()
        finally:
            if self.ziggy_ctx:
                self.ziggy_ctx.stop()

class AsyncHTTPClient(tornado.simple_httpclient.SimpleAsyncHTTPClient):
    def __init__(self, *args, **kwargs):
        self.ziggy_name = 'httpclient'
        return super(AsyncHTTPClient, self).__init__(*args, **kwargs)

    def fetch(self, request, callback, **kwargs):
        ctx = ziggy.Context(self.ziggy_name)
        ctx.start()
        if isinstance(request, basestring):
            ctx.set('request.uri', request)
        else:
            ctx.set('request.uri', request.url)
            ctx.set('request.size', len(request.body) if request.body else 0)

        ctx.stop()

        def wrap_callback(response):
            ctx.start()
            ctx.set('response.code', response.code)
            ctx.set('response.size', len(response.body))
            ctx.done()
            callback(response)

        return super(AsyncHTTPClient, self).fetch(request, wrap_callback, **kwargs)

