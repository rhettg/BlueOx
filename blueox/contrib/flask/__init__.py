import blueox
import traceback
import sys
from flask import request, got_request_exception


class BlueOxMiddleware(object):
    """BlueOx Application Middleware for request/response objects

    BlueOx middleware has 3 callbacks registered with flask:
        before_request:
            Initialize a blueox context and populate with metadata about the
            request such as header information, request url, and client ip.
        after_request:
            Add more metadata about the response back to the client then chean
            up and flush the corresponding context created during
            before_request.
        handle_exception:
            When an exception is fired, flask will dispatch to this function to
            log it to blueox.
    """

    def __init__(self, app):
        self.app = app

        if 'BLUEOX_HOST' in app.config:
            self.blueox_host = app.config['BLUEOX_HOST']
            if self.blueox_host:
                blueox.default_configure(self.blueox_host)
        else:
            blueox.default_configure()

        self.app.before_request(self.before_request)
        self.app.after_request(self.after_request)

        got_request_exception.connect(self.handle_exception, self.app)

    def before_request(self, *args, **kwargs):
        request.blueox = blueox.Context(
            ".".join((self.app.config.get('BLUEOX_NAME', ''), 'request')))

        blueox.set('method', request.method)
        blueox.set('path', request.path)

        headers = {}
        for k, v in request.environ.iteritems():
            if (
                k.startswith('HTTP_') or k in
                ('CONTENT_LENGTH', 'CONTENT_TYPE')):
                headers[k] = v

        blueox.set('headers', headers)
        blueox.set('url', request.url)
        blueox.set('client_ip', request.environ.get('REMOTE_ADDR'))

    def after_request(self, response):
        if not hasattr(request, 'blueox'):
            return

        if hasattr(request, 'user'):
            blueox.set('user', request.user.id)

        for key in ('version', 'revision'):
            if hasattr(request, key):
                blueox.set(key, getattr(request, key))

        if response is not None:
            blueox.set('response_status_code', response.status_code)

            if not response.is_streamed:
                blueox.set('response_size', response.content_length)

        request.blueox.done()

        return response

    def handle_exception(self, *args, **kwargs):
        blueox.set(
            'exception', ''.join(traceback.format_exception(*sys.exc_info())))
