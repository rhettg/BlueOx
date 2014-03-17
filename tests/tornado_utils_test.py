import time
import pprint
import random
import collections
import traceback
from testify import *

import tornado.ioloop
import tornado.gen
import tornado.web
import blueox.tornado_utils

# vendor module. Tornado testing in Testify
import tornado_test

class AsyncHandler(blueox.tornado_utils.BlueOxRequestHandlerMixin, tornado.web.RequestHandler):
    @blueox.tornado_utils.coroutine
    def get(self):
        loop = self.request.connection.stream.io_loop

        req_id = self.blueox_ctx.id
        blueox.set('async', True)

        result = yield blueox.tornado_utils.AsyncHTTPClient(loop).fetch(self.application.test_url)
        assert result.code == 200

        with blueox.Context('.extra'):
            blueox.set('continue_id', req_id)

        self.write("Hello, world")
        self.finish()


class AsyncErrorHandler(blueox.tornado_utils.BlueOxRequestHandlerMixin, tornado.web.RequestHandler):
    @blueox.tornado_utils.coroutine
    def get(self):
        loop = self.request.connection.stream.io_loop

        called = yield tornado.gen.Task(loop.add_timeout, time.time() + random.randint(1, 2))

        raise Exception('hi')

    def write_error(self, status_code, **kwargs):
        if 'exc_info' in kwargs:
            blueox.set('exception', ''.join(traceback.format_exception(*kwargs["exc_info"])))

        return super(AsyncErrorHandler, self).write_error(status_code, **kwargs)


class MainHandler(blueox.tornado_utils.BlueOxRequestHandlerMixin, tornado.web.RequestHandler):
    def get(self):
        blueox.set('async', False)
        self.write("Hello, world")


class SimpleTestCase(tornado_test.AsyncHTTPTestCase):
    @setup
    def setup_bluox(self):
        blueox.configure(None, None, recorder=self.logit)

    @setup
    def setup_log(self):
        self.log_ctx = collections.defaultdict(list)

    @setup
    def build_client(self):
        self.http_client = blueox.tornado_utils.AsyncHTTPClient(self.io_loop)

    def logit(self, ctx):
        self.log_ctx[ctx.id].append(ctx)

    def get_app(self):
        application = tornado.web.Application([
            (r"/", MainHandler),
            (r"/async", AsyncHandler),
            (r"/error", AsyncErrorHandler),
        ])

        application.test_url = self.get_url("/")
        return application

    def test_error(self):
        f = self.http_client.fetch(self.get_url("/error"), self.stop)
        resp = self.wait()

        #for ctx_id in self.log_ctx:
            #print ctx_id
            #for ctx in self.log_ctx[ctx_id]:
                #pprint.pprint(ctx.to_dict())

        assert_equal(len(self.log_ctx), 2)

        found_exception = False
        for ctx_list in self.log_ctx.values():
            for ctx in ctx_list:
                if ctx.to_dict()['body'].get('exception'):
                    found_exception = True

        assert found_exception

    def test_context(self):
        self.http_client.fetch(self.get_url("/async"), self.stop)
        resp = self.wait()

        #for ctx_id in self.log_ctx:
            #print
            #print ctx_id
            #for ctx in self.log_ctx[ctx_id]:
                #pprint.pprint(ctx.to_dict())

        # If everything worked properly, we should have two separate ids, one will have two contexts associated with it.
        # Hopefully it's the right one.
        found_sync = None
        found_async = None
        found_client = 0
        for ctx_list in self.log_ctx.values():
            for ctx in ctx_list:
                if ctx.name == "request" and ctx.to_dict()['body']['async']:
                    assert_equal(len(ctx_list), 3)
                    found_async = ctx
                if ctx.name == "request" and not ctx.to_dict()['body']['async']:
                    assert_equal(len(ctx_list), 1)
                    found_sync = ctx
                if ctx.name.endswith("httpclient"):
                    found_client += 1

        assert found_async
        assert found_sync
        assert_equal(found_client, 2)

        assert_equal(resp.code, 200)
