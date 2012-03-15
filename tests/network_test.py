import random

from testify import *
import zmq
import bson

from ziggy import utils
from ziggy import network
from ziggy import context

class NoNetworkSendTestCase(TestCase):
    def test(self):
        """Verify that if network isn't setup, send just does nothing"""
        network.send(context.Context('test', 1))

class NetworkSendTestCase(TestCase):
    @setup
    def build_context(self):
        self.context = context.Context('test', 1)

    @setup
    def configure_network(self):
        self.port = random.randint(30000, 40000)
        network.init("127.0.0.1", self.port)

    @setup
    def configure_network(self):
        context._recorder_function = network.send

    @teardown
    def unconfigure_network(self):
        context._recorder_function = None

    @setup
    def build_server_socket(self):
        self.server = network._zmq_context.socket(zmq.PULL)
        self.server.bind("tcp://127.0.0.1:%d" % self.port)

    @teardown
    def destroy_server(self):
        self.server.close(linger=0)

    @teardown
    def destory_network(self):
        network.close()

    def test(self):
        with self.context:
            self.context.set('foo', True)
            self.context.set('bar.baz', 10.0)

        raw_data = self.server.recv()
        data = bson.loads(raw_data)
        assert_equal(data['id'], 1)
        assert_equal(data['type'], 'test')
        assert_equal(utils.get_deep(data['body'], "bar.baz"), 10.0)


