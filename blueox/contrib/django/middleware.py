import sys
import traceback
import logging

import blueox

from django.conf import settings

class Middleware(object):
    def __init__(self):
        if hasattr(settings, 'BLUEOX_HOST'):
            if settings.BLUEOX_HOST:
                blueox.default_configure(settings.BLUEOX_HOST)
            else:
                blueox.configure(None, None)
        else:
            blueox.default_configure()

    def process_request(self, request):
        request.blueox = blueox.Context(".".join((getattr(settings, 'BLUEOX_NAME', ''), 'request')))
        request.blueox.start()

        blueox.set('method', request.method)
        blueox.set('path', request.path)

        headers = {}
        for k,v in request.META.iteritems():
            if k.startswith('HTTP_') or k in ('CONTENT_LENGTH', 'CONTENT_TYPE'):
                headers[k] = v
        blueox.set('headers', headers)

        blueox.set('uri', request.build_absolute_uri())
        blueox.set('client_ip', request.META['REMOTE_ADDR'])

        return None

    def process_response(self, request, response):
        # process_request() is not guaranteed to be called
        if not hasattr(request, 'blueox'):
            return response

        # We collect some additional data in the response, just to ensure
        # middleware ordering doesn't matter.
        if hasattr(request, 'user'):
            blueox.set('user', request.user.id)

        for key in ('version', 'revision'):
            if hasattr(request, key):
                blueox.set(key, getattr(request, key))

        # Other middleware may have blocked our response.
        if response is not None:

            blueox.set('response_status_code', response.status_code)

            if not response.streaming:
                blueox.set('response_size', len(response.content))

            headers = {}
            for k, v in response.items():
                headers[k] = v

            blueox.set('response_headers', headers)

        request.blueox.done()

        return response

    def process_exception(self, request, exception):
        blueox.set('exception', ''.join(traceback.format_exception(*sys.exc_info())))
        return None
