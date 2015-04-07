import pprint
from testify import *

import blueox
from blueox import client


class SimpleGrouperTest(TestCase):
    @setup
    def build_stream(self):
        events = [{'id': 1, 'type': 'foo.bar', 'body': 'Hello World'},
                  {'id': 1, 'type': 'foo', 'body': 'All Done'}]

        self.stream = (event for event in events)

    @setup
    def build_grouper(self):
        self.grouper = client.Grouper(self.stream)

    def test(self):
        output = list(self.grouper)
        assert_equal(len(output), 1)
        assert_equal(len(output[0]), 2)

        assert_equal(self.grouper.size, 0)

class MaxGrouperTest(TestCase):
    @setup
    def build_stream(self):
        events = [
                  {'id': 1, 'type': 'foo.bar', 'body': 'Hello World'},
                  {'id': 2, 'type': 'foo.bar', 'body': 'Hello World 2'},
                  {'id': 1, 'type': 'foo', 'body': 'All Done'}]

        self.stream = (event for event in events)

    @setup
    def build_grouper(self):
        self.grouper = client.Grouper(self.stream, max_size=1)

    def test(self):
        output = list(self.grouper)
        assert_equal(len(output), 1)
        assert_equal(len(output[0]), 1)


