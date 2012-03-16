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
            with context.Context('.foo') as c:
                assert_equal(c.name, 'test.foo')
                assert_equal(c.id, 5)


class ModuleLevelTestCase(TestCase):
    def test(self):
        with ziggy.Context('test', 5):
            ziggy.set('foo', True)

class EmptyModuleLevelTestCase(TestCase):
    def test(self):
        ziggy.set('foo', True)

class SampleTestCase(TestCase):
    def test(self):
        enabled = []
        for _ in range(100):
            context = ziggy.Context('test', 5, sample=('test', 0.25))
            enabled.append(1 if context.enabled else 0)
        
        assert 40 > sum(enabled) > 15

        
class ParentSampleTestCase(TestCase):
    def test(self):
        enabled = []
        for _ in range(100):
            parent_context = ziggy.Context('test', 5)
            with parent_context:
                sub_enabled = []
                for _ in range(10):
                    context = ziggy.Context('.sub', sample=('..', 0.25))
                    sub_enabled.append(1 if context.enabled else 0)
                    enabled.append(1 if context.enabled else 0)
                assert all(sub_enabled) or not any(sub_enabled)

        assert 400 > sum(enabled) > 150
