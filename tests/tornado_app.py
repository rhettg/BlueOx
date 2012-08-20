import pprint
import time
import blueox
import random
import blueox.tornado_utils

blueox.tornado_utils.install()

import tornado.web
import tornado.gen
import tornado.ioloop
import tornado.autoreload


class MainHandler(blueox.tornado_utils.SampleRequestHandler):
    def get(self):
        self.write("Hello, world")

class AsyncHandler(blueox.tornado_utils.SampleRequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        loop = tornado.ioloop.IOLoop.instance()

        req_id = self.blueox.id

        called = yield tornado.gen.Task(loop.add_timeout, time.time() + random.randint(1, 5))

        with blueox.Context('request.extra'):
            blueox.set('continue_id', req_id)

        self.write("Hello, world")
        self.finish()


class AsyncCrashHandler(blueox.tornado_utils.SampleRequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        loop = tornado.ioloop.IOLoop.instance()

        req_id = self.blueox.id

        called = yield tornado.gen.Task(loop.add_timeout, time.time() + random.randint(1, 5))

        raise Exception("This Handler is Broken!")


class ManualAsyncHandler(blueox.tornado_utils.SampleRequestHandler):
    @tornado.web.asynchronous
    def get(self):
        pprint.pprint(blueox.context._contexts)
        loop = tornado.ioloop.IOLoop.instance()

        loop.add_timeout(time.time() + random.randint(1, 5), self._complete_get)
        return

    def _complete_get(self):
        self.blueox.start()

        with blueox.Context('request.extra'):
            blueox.set('continue_id', self.blueox.id)

        self.write("Hello, world")
        self.finish()

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/async", AsyncHandler),
    (r"/async_crash", AsyncCrashHandler),
    (r"/async2", ManualAsyncHandler),
])

def logit(ctx):
    pprint.pprint(ctx.to_dict())

if __name__ == "__main__":
    # Iniatialize the blue ox system. Providing a recorder function rather than a host and port
    # will allow us to receive the data right away rather than forwarding to an oxd instance.
    blueox.configure(None, None, recorder=logit)

    # Instruct tornado's autoreload to shutodwn blueox during reload.
    # Note: Since we're not actually using the network in this example, this
    # probably isn't strictly necessary.
    tornado.autoreload.add_reload_hook(blueox.shutdown)

    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()


