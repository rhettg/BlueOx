from testify import *

import ziggy
from ziggy import context

class SimpleTestCase(TestCase):
    def test(self):
        with context.Context('test'):
            assert True

class SimpleSetTestCase(TestCase):
    @setup
    def build_context(self):
        self.context = context.Context('test')

    def test(self):
        with self.context:
            self.context.set('foo', True)

        assert_equal(self.context.data['foo'], True)

class NestedIDTestCase(TestCase):
    def test(self):
        with context.Context('test', 5):
            with context.Context('test.foo') as c:
                assert_equal(c.id, 5)


class ModuleLevelTestCase(TestCase):
    def test(self):
        with ziggy.Context('test', 5):
            ziggy.set('foo', True)

class EmptyModuleLevelTestCase(TestCase):
    def test(self):
        ziggy.set('foo', True)
