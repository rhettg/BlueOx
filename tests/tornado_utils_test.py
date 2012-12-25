import time
import pprint
import random
import collections
from testify import *

import tornado.ioloop
import tornado.gen
import tornado.web
import blueox.tornado_utils

import tornado_test

blueox.tornado_utils.install()

class AsyncHandler(blueox.tornado_utils.SampleRequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        loop = self.request.connection.stream.io_loop

        req_id = self.blueox.id

        called = yield tornado.gen.Task(loop.add_timeout, time.time() + random.randint(1, 2))

        with blueox.Context('.extra'):
            blueox.set('continue_id', req_id)

        self.write("Hello, world")
        self.finish()


class MainHandler(blueox.tornado_utils.SampleRequestHandler):
    def get(self):
        self.write("Hello, world")


class SimpleTestCase(tornado_test.AsyncHTTPTestCase):
    @setup
    def setup_bluox(self):
        blueox.configure(None, None, recorder=self.logit)

    @setup
    def setup_log(self):
        self.log_ctx = collections.defaultdict(list)

    def logit(self, ctx):
        self.log_ctx[ctx.id].append(ctx)

    def get_app(self):
        application = tornado.web.Application([
            (r"/", MainHandler),
            (r"/async", AsyncHandler),
        ])
        return application

    def test(self):
        self.http_client.fetch(self.get_url("/async"), self.stop)
        self.http_client.fetch(self.get_url("/"), lambda x : x)
        resp = self.wait()

        #for ctx_id in self.log_ctx:
            #print ctx_id
            #for ctx in self.log_ctx[ctx_id]:
                #pprint.pprint(ctx.to_dict())

        # If everything worked properly, we should have two separate ids, one will have two contexts associated with it.
        # Hopefully it's the right one.
        found = None
        for ctx_list in self.log_ctx.values():
            for ctx in ctx_list:
                if ctx.name == "request" and ctx.to_dict()['body']['uri'] == '/async':
                    found = ctx
                    break

        assert found

        assert_equal(len(self.log_ctx[found.id]), 2)

        assert_equal(resp.code, 200)
