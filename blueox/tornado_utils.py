# -*- coding: utf-8 -*-

"""
blueox.tornado
~~~~~~~~

This module provides hooks for using blueox with the Tornado async web server.
Making blueox useful inside tornado is a challenge since you'll likely want a
blueox context per request, but multiple requests can be going on at once inside
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
import tornado.stack_context

import blueox

def install():
    """Install blueox hooks by poking into the tornado innards

    THIS MUST BE DONE BEFORE IMPORTING APPLICATION REQUEST HANDLERS
    We have to replace some decorators before they are used to create your class

    This is pretty hacky and may make you feel uncomfortable. It's only here so
    that blueox can be used with the minimal amount of extra boilerplate.  Your
    always free to be more explicit depending on your needs.

    Up to you if you want to hide your uglyiness in here or have it spread
    throughout your application.
    
    """
    tornado.gen.engine = gen_engine
    tornado.gen.Runner = BlueOxRunner


# Our hook into the request cycle is going to be provided by wrapping the
# _execute() method.  This creates our blueox context, starts it, and then stops
# it at the end. We'll leave it up to the finish() method to close us out.
def wrap_execute(type_name):
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self.blueox = blueox.Context(type_name)
            self.blueox.start()
            try:
                return func(self, *args, **kwargs)
            finally:
                # We're done executing in this context for the time being. Either we've already
                # finished handling our blueox context, or we'll allow a later finish() call to 
                # mark it done.
                self.blueox.stop()

        return wrapper

    return decorate

def wrap_exception(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.blueox.start()
        try:
            return func(self, *args, **kwargs)
        finally:
            self.blueox.stop()

    return wrapper

def wrap_finish(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        finally:
            self.blueox.done()

    return wrapper

class SampleRequestHandler(tornado.web.RequestHandler):
    """Sample base request handler necessary for providing smart blueox contexts through a web request.

    We need to wrap two methods: _execute() and finish()

    To specify a name for your top level event, pass it the wrap_execute() decorator.

    The idea is that when _execute is called, we'll generate a blueox Context
    with the name specified. This should cover any methods like get() or
    post(). When _execute returns, we'll be in either one of two states. Either
    finish() has been called and we are all done, or finish() will be called
    later due to some async complexity. 

    Optionally, we also provide redefined methods that add critical data about
    the request to the active blueox context.
    """
    def prepare(self):
        blueox.set('headers', self.request.headers)
        blueox.set('method', self.request.method)
        blueox.set('uri', self.request.uri)

    def write_error(self, status_code, **kwargs):
        if 'exc_info' in kwargs:
            blueox.set('exception', ''.join(traceback.format_exception(*kwargs["exc_info"])))
    
        return super(SampleRequestHandler, self).write_error(status_code, **kwargs)

    def write(self, chunk):
        blueox.add('response_size', len(chunk))
        return super(SampleRequestHandler, self).write(chunk)

    def finish(self, *args, **kwargs):
        res = super(SampleRequestHandler, self).finish(*args, **kwargs)
        blueox.set('response_status_code', self._status_code)
        return res

    _execute = wrap_execute('request')(tornado.web.RequestHandler._execute)
    finish = wrap_finish(finish)
    _stack_context_handle_exception = wrap_exception(tornado.web.RequestHandler._stack_context_handle_exception)


# We need a custom version of this decorator so that we can pass in our blueox
# context to the Runner
def gen_engine(func):
    """Hacked up copy of tornado.gen.engine decorator
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        runner = None

        def handle_exception(typ, value, tb):
            # if the function throws an exception before its first "yield"
            # (or is not a generator at all), the Runner won't exist yet.
            # However, in that case we haven't reached anything asynchronous
            # yet, so we can just let the exception propagate.
            if runner is not None:
                return runner.handle_exception(typ, value, tb)
            return False

        with tornado.stack_context.ExceptionStackContext(handle_exception) as deactivate:
            gen = func(*args, **kwargs)
            if isinstance(gen, types.GeneratorType):
                blueox_ctx = getattr(args[0], 'blueox', None)
                runner = BlueOxRunner(gen, deactivate, blueox_ctx)
                runner.run()
                return
            assert gen is None, gen
            deactivate()
            # no yield, so we're done
    return wrapper


# Custom version of gen.Runner that starts and stops the blueox context
class BlueOxRunner(tornado.gen.Runner):
    def __init__(self, gen, deactivate_stack_context, blueox_context):
        self.blueox_ctx = blueox_context
        super(BlueOxRunner, self).__init__(gen, deactivate_stack_context)

    def run(self):
        try:
            if self.blueox_ctx:
                self.blueox_ctx.start()

            return super(BlueOxRunner, self).run()
        finally:
            if self.blueox_ctx:
                self.blueox_ctx.stop()

class AsyncHTTPClient(tornado.simple_httpclient.SimpleAsyncHTTPClient):
    def __init__(self, *args, **kwargs):
        self.blueox_name = '.httpclient'
        return super(AsyncHTTPClient, self).__init__(*args, **kwargs)

    def fetch(self, request, callback, **kwargs):
        ctx = blueox.Context(self.blueox_name)
        ctx.start()
        if isinstance(request, basestring):
            ctx.set('request.uri', request)
            ctx.set('request.method', kwargs.get('method', 'GET'))
        else:
            ctx.set('request.uri', request.url)
            ctx.set('request.method', request.method)
            ctx.set('request.size', len(request.body) if request.body else 0)

        ctx.stop()

        def wrap_callback(response):
            ctx.start()
            ctx.set('response.code', response.code)
            ctx.set('response.size', len(response.body) if response.body else 0)
            ctx.done()
            callback(response)

        return super(AsyncHTTPClient, self).fetch(request, wrap_callback, **kwargs)

