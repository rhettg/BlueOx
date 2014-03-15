"""Version of tornado testing base classes that are designed to work with 
Testify.

"""
import Cookie
import tornado.httputil
from tornado.httpclient import AsyncHTTPClient
from tornado.httpserver import HTTPServer
from tornado.stack_context import StackContext, NullContext
import contextlib
import logging
import sys
import time
import json
import urlparse
import pprint

try:
    import mechanize
except ImportError:
    mechanize = None

import testify

from tornado.ioloop import IOLoop

_next_port = 10000
def get_unused_port():
    """Returns a (hopefully) unused port number."""
    global _next_port
    port = _next_port
    _next_port = _next_port + 1
    return port

class TornadoTestError(Exception): pass

class TestHTTPResponse(object):
    def __init__(self, response):
        self._resp = response
    
    def __getattr__(self, name):
        return getattr(self._resp, name)
    
    @property
    def json_body(self):
        return json.loads(self.body)

    def form(self, name=None):
        forms = mechanize.ParseString(self._resp.body, self._resp.request.url)

        for f in forms:
            if f.name == name:
                return f
        else:
            if name is None:
                return forms[-1]
            else:
                raise ValueError(name)
    
    def __str__(self):
        return str(self._resp)

class AsyncTestCase(testify.TestCase):
    """TestCase subclass for testing IOLoop-based asynchronous code.

    The unittest framework is synchronous, so the test must be complete
    by the time the test method returns.  This method provides the stop()
    and wait() methods for this purpose.  The test method itself must call
    self.wait(), and asynchronous callbacks should call self.stop() to signal
    completion.

    By default, a new IOLoop is constructed for each test and is available
    as self.io_loop.  This IOLoop should be used in the construction of
    HTTP clients/servers, etc.  If the code being tested requires a
    global IOLoop, subclasses should override get_new_ioloop to return it.

    The IOLoop's start and stop methods should not be called directly.
    Instead, use self.stop self.wait.  Arguments passed to self.stop are
    returned from self.wait.  It is possible to have multiple
    wait/stop cycles in the same test.

    Example::

        # This test uses an asynchronous style similar to most async
        # application code.
        class MyTestCase(AsyncTestCase):
            def test_http_fetch(self):
                client = AsyncHTTPClient(self.io_loop)
                client.fetch("http://www.tornadoweb.org/", self.handle_fetch)
                self.wait()

            def handle_fetch(self, response)
                # Test contents of response (failures and exceptions here
                # will cause self.wait() to throw an exception and end the
                # test).
                self.stop()

        # This test uses the argument passing between self.stop and self.wait
        # for a simpler, more synchronous style
        class MyTestCase2(AsyncTestCase):
            def test_http_fetch(self):
                client = AsyncHTTPClient(self.io_loop)
                client.fetch("http://www.tornadoweb.org/", self.stop)
                response = self.wait()
                # Test contents of response
    """
    __test__ = False

    failureException = TornadoTestError

    def __init__(self, *args, **kwargs):
        super(AsyncTestCase, self).__init__(*args, **kwargs)
        self.__stopped = False
        self.__running = False
        self.__failure = None
        self.__stop_args = None

    @testify.setup
    def build_io_loop(self):
        self.io_loop = self.get_new_ioloop()

    @testify.teardown
    def close_io_loop(self):
        if (not IOLoop.initialized() or
            self.io_loop is not IOLoop.instance()):
            # Try to clean up any file descriptors left open in the ioloop.
            # This avoids leaks, especially when tests are run repeatedly
            # in the same process with autoreload (because curl does not
            # set FD_CLOEXEC on its file descriptors)
            #self.io_loop.close(all_fds=True)
            
            # Closing all fds leads to errors. I think the client is somehow expecting it's
            # fd to still be open??
            self.io_loop.close()
            

    def get_new_ioloop(self):
        """Creates a new IOLoop for this test.  May be overridden in
        subclasses for tests that require a specific IOLoop (usually
        the singleton).
        """
        return IOLoop()

    @contextlib.contextmanager
    def _stack_context(self):
        try:
            yield
        except Exception:
            self.__failure = sys.exc_info()
            self.stop()

    def run(self):
        with StackContext(self._stack_context):
            super(AsyncTestCase, self).run()

    def stop(self, _arg=None, **kwargs):
        """Stops the ioloop, causing one pending (or future) call to wait()
        to return.

        Keyword arguments or a single positional argument passed to stop() are
        saved and will be returned by wait().
        """
        assert _arg is None or not kwargs
        self.__stop_args = kwargs or _arg
        if self.__running:
            self.io_loop.stop()
            self.__running = False
        self.__stopped = True

    def wait(self, condition=None, timeout=5):
        """Runs the IOLoop until stop is called or timeout has passed.

        In the event of a timeout, an exception will be thrown.

        If condition is not None, the IOLoop will be restarted after stop()
        until condition() returns true.
        """
        if not self.__stopped:
            if timeout:
                def timeout_func():
                    try:
                        raise self.failureException(
                          'Async operation timed out after %d seconds' %
                          timeout)
                    except Exception:
                        self.__failure = sys.exc_info()
                    self.stop()
                self.io_loop.add_timeout(time.time() + timeout, timeout_func)
            while True:
                self.__running = True
                with NullContext():
                    # Wipe out the StackContext that was established in
                    # self.run() so that all callbacks executed inside the
                    # IOLoop will re-run it.
                    self.io_loop.start()
                if (self.__failure is not None or
                    condition is None or condition()):
                    break
        assert self.__stopped
        self.__stopped = False
        if self.__failure is not None:
            # 2to3 isn't smart enough to convert three-argument raise
            # statements correctly in some cases.
            if isinstance(self.__failure[1], self.__failure[0]):
                raise self.__failure[1], None, self.__failure[2]
            else:
                raise self.__failure[0], self.__failure[1], self.__failure[2]
        result = self.__stop_args
        self.__stop_args = None
        return result


class AsyncHTTPTestCase(AsyncTestCase):
    """A test case that starts up an HTTP server.

    Subclasses must override get_app(), which returns the
    tornado.web.Application (or other HTTPServer callback) to be tested.
    Tests will typically use the provided self.http_client to fetch
    URLs from this server.

    Example::

        class MyHTTPTest(AsyncHTTPTestCase):
            def get_app(self):
                return Application([('/', MyHandler)...])

            def test_homepage(self):
                # The following two lines are equivalent to
                #   response = self.fetch('/')
                # but are shown in full here to demonstrate explicit use
                # of self.stop and self.wait.
                self.http_client.fetch(self.get_url('/'), self.stop)
                response = self.wait()
                # test contents of response
    """
    __test__ = False

    @testify.setup
    def build_client(self):
        self.http_client = AsyncHTTPClient(io_loop=self.io_loop)

    @testify.setup
    def build_server(self):
        self.__port = None

        # We have a much simplified implementation of cookies for our test hook.
        # We're going to ignore pretty much everything like host, path, secure, expires etc.
        # It's basically a dumb key-value store, represented by.... a dictionary
        self.cookie_jar = {}

        self._app = self.get_app()
        self.http_server = HTTPServer(self._app, io_loop=self.io_loop,
                                      **self.get_httpserver_options())
        self.http_server.listen(self.get_http_port(), address="127.0.0.1")

    @testify.teardown
    def stop_client_server(self):
        self.http_client.close()
        self.http_server.stop()

    def get_app(self):
        """Should be overridden by subclasses to return a
        tornado.web.Application or other HTTPServer callback.
        """
        raise NotImplementedError()

    def fetch(self, request, **kwargs):
        """Convenience method to synchronously fetch a url.

        The given path will be appended to the local server's host and port.
        Any additional kwargs will be passed directly to
        AsyncHTTPClient.fetch (and so could be used to pass method="POST",
        body="...", etc).
        """
        timeout = None
        if 'timeout' in kwargs:
            timeout = kwargs.pop('timeout')
        
        if hasattr(request, 'url'):
            parsed = urlparse.urlparse(request.url)
            request.url = self.update_urlparsed(parsed)
        else:
            parsed = urlparse.urlparse(request)
            request = self.update_urlparsed(parsed)

        if 'headers' in kwargs and not isinstance(kwargs['headers'], tornado.httputil.HTTPHeaders):
            # Upgrade our headers to a fancy object so we can add multiple values.
            kwargs['headers'] = tornado.httputil.HTTPHeaders(kwargs['headers'])
        else:
            kwargs.setdefault('headers', tornado.httputil.HTTPHeaders())

        if 'body' in kwargs and not isinstance(kwargs['body'], basestring):
            kwargs['body'] = json.dumps(kwargs['body'])
            kwargs['headers']['Content-Type'] = 'application/json'

        if 'cookies' in kwargs:
            for cookie in kwargs['cookies']:
                for val in cookie.values():
                    kwargs['headers'].add('Cookie', val.OutputString(None))

        if self.cookie_jar:
            cookie = Cookie.SimpleCookie(self.cookie_jar)
            for val in cookie.values():
                kwargs['headers'].add('Cookie', val.OutputString(None))
        
        self.http_client.fetch(request, self.stop, **kwargs)
        res = self.wait(timeout=timeout)

        for cookie_val in res.headers.get_list('set-cookie'):
            cookie = Cookie.SimpleCookie()
            cookie.load(cookie_val)
            for val in cookie.values():
                if not val.value:
                    del self.cookie_jar[val.key]
                else:
                    self.cookie_jar[val.key] = val.value

        return TestHTTPResponse(res)

    def set_cookie(self, name, value):
        self.cookie_jar[name] = value

    def clear_cookie(self, name):
        del self.cookie_jar[name]

    def get_httpserver_options(self):
        """May be overridden by subclasses to return additional
        keyword arguments for HTTPServer.
        """
        return {}

    def get_http_port(self):
        """Returns the port used by the HTTPServer.

        A new port is chosen for each test.
        """
        if self.__port is None:
            self.__port = get_unused_port()
        return self.__port

    def get_url(self, path):
        """Returns an absolute url for the given path on the test server."""
        return 'http://localhost:%s%s' % (self.get_http_port(), path)
    
    def update_urlparsed(self, parsed):
        return urlparse.urlunparse(['http', 'localhost:%s' % self.get_http_port()] + list(parsed[2:]))
        

