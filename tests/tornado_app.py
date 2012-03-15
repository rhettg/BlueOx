import pprint
import ziggy
import ziggy.tornado_utils

ziggy.tornado_utils.install()

import tornado.web
import tornado.gen
import tornado.ioloop


class MainHandler(ziggy.tornado_utils.SampleRequestHandler):
    def get(self):
        print "hi"
        self.write("Hello, world")

application = tornado.web.Application([
    (r"/", MainHandler),
])

def logit(ctx):
    pprint.pprint(ctx.to_dict())

if __name__ == "__main__":
    ziggy.configure(None, None, recorder=logit)
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()


