import random
import struct
import decimal

from testify import *
import zmq
import msgpack

from blueox import utils
from blueox import network
from blueox import context

class NoNetworkSendTestCase(TestCase):
    def test(self):
        """Verify that if network isn't setup, send just does nothing"""
        network.send(context.Context('test', 1))

class NetworkSendTestCase(TestCase):
    @setup
    def build_context(self):
        self.context = context.Context('test', 1)

    @setup
    def init_network(self):
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

        event_meta, raw_data = self.server.recv_multipart()
        network.check_meta_version(event_meta)
        _, event_time, event_host, event_type = struct.unpack(network.META_STRUCT_FMT, event_meta)
        assert_equal(event_type, 'test')

        data = msgpack.unpackb(raw_data)
        assert_equal(data['id'], 1)
        assert_equal(data['type'], 'test')
        assert_equal(utils.get_deep(data['body'], "bar.baz"), 10.0)


class SerializeContextTestCase(TestCase):
    @setup
    def build_context(self):
        self.context = context.Context('test', 1)

    def test_decimal(self):
        with self.context:
            self.context.set('value', decimal.Decimal("6.66"))
        meta_data, context_data = network._serialize_context(self.context)
        data = msgpack.unpackb(context_data)
        assert_equal(data['body']['value'], "6.66")

    def test_decimal(self):
        with self.context:
            self.context.set('value', Exception('hello'))

        meta_data, context_data = network._serialize_context(self.context)
        data = msgpack.unpackb(context_data)
        assert_equal(data['body'], None)



