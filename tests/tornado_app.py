import pprint
import time
import ziggy
import random
import ziggy.tornado_utils

ziggy.tornado_utils.install()

import tornado.web
import tornado.gen
import tornado.ioloop


class MainHandler(ziggy.tornado_utils.SampleRequestHandler):
    def get(self):
        self.write("Hello, world")

class AsyncHandler(ziggy.tornado_utils.SampleRequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        loop = tornado.ioloop.IOLoop.instance()

        req_id = self.ziggy.id

        called = yield tornado.gen.Task(loop.add_timeout, time.time() + random.randint(1, 5))

        with ziggy.Context('request.extra'):
            ziggy.set('continue_id', req_id)

        self.write("Hello, world")
        self.finish()

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/async", AsyncHandler),
])

def logit(ctx):
    pprint.pprint(ctx.to_dict())

if __name__ == "__main__":
    ziggy.configure(None, None, recorder=logit)
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()


