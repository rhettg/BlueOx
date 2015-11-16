from testify import *

import blueox
from blueox import context

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


class NestedOverlapIDTestCase(TestCase):
    def test_relative(self):
        with context.Context('test.bar', 5):
            with context.Context('.bar.foo') as c:
                assert_equal(c.name, 'test.bar.foo')
                assert_equal(c.id, 5)

    def test_from_top(self):
        with context.Context('test.bar', 5):
            with context.Context('^.bar.foo') as c:
                assert_equal(c.name, 'test.bar.foo')
                assert_equal(c.id, 5)

    def test_explicit(self):
        with context.Context('test.bar', 5):
            with context.Context('test.bar.foo') as c:
                assert_equal(c.name, 'test.bar.foo')
                assert_equal(c.id, 5)



class NoNestedOverlapTestCase(TestCase):
    def test(self):
        with context.Context('test.bar'):
            with context.Context('test.foo') as c:
                assert_equal(c.name, 'test.foo')


class TopNestedIDTestCase(TestCase):
    def test(self):
        with context.Context('test', 5):
            with context.Context('.bar'):
                with context.Context('^.foo') as c:
                    assert_equal(c.name, 'test.foo')
                    assert_equal(c.id, 5)


class FindClosestContextTestCase(TestCase):
    def test_simple(self):
        with context.Context('test.bar', 5) as ctx:
            test_ctx = context.find_closest_context('test.bar')
            assert_equal(ctx, test_ctx)

    def test_skip_up(self):
        with context.Context('test', 5) as ctx:
            with context.Context('.bar'):
                test_ctx = context.find_closest_context('test')
                assert_equal(ctx, test_ctx)

    def test_not_found(self):
        test_ctx = context.find_closest_context('test')
        assert_equal(test_ctx, None)


class FindContextTestCase(TestCase):
    def test_by_name(self):
        with context.Context('test.foo') as ctx:
            test_ctx = context.find_context('test.foo')
            assert_equal(test_ctx, ctx)

    def test_current(self):
        with context.Context('test'):
            with context.Context('test.foo') as ctx:
                test_ctx = context.find_context('.')
                assert_equal(test_ctx, ctx)

    def test_parent(self):
        with context.Context('test') as ctx:
            with context.Context('test.foo'):
                test_ctx = context.find_context('..')
                assert_equal(test_ctx, ctx)

    def test_top(self):
        with context.Context('test') as ctx:
            with context.Context('test.foo'):
                test_ctx = context.find_context('^')
                assert_equal(test_ctx, ctx)


class ModuleLevelTestCase(TestCase):
    def test(self):
        with blueox.Context('test', 5):
            blueox.set('foo', True)


class EmptyModuleLevelTestCase(TestCase):
    def test(self):
        blueox.set('foo', True)


class SampleTestCase(TestCase):
    def test(self):
        enabled = []
        for _ in range(100):
            context = blueox.Context('test', 5, sample=('test', 0.25))
            enabled.append(1 if context.enabled else 0)
        
        assert 40 > sum(enabled) > 15

        
class ParentSampleTestCase(TestCase):
    def test(self):
        enabled = []
        for _ in range(100):
            parent_context = blueox.Context('test', 5)
            with parent_context:
                sub_enabled = []
                for _ in range(10):
                    context = blueox.Context('.sub', sample=('..', 0.25))
                    sub_enabled.append(1 if context.enabled else 0)
                    enabled.append(1 if context.enabled else 0)
                assert all(sub_enabled) or not any(sub_enabled)

        assert 400 > sum(enabled) > 150


class ContextWrapTestCase(TestCase):
    @setup
    def build_function(self):
        @blueox.context_wrap('foo')
        def my_function(value):
            blueox.set('value', value)
            self.context = context.current_context()
            return True

        self.function = my_function

    def test(self):
        assert_equal(self.function('test'), True)

        assert self.context
        assert not self.context.writable
        assert_equal(self.context.to_dict()['body']['value'], 'test')


class ClearContextsTestCase(TestCase):
    def test(self):
        c = blueox.Context('test')
        c.start()

        blueox.clear_contexts()

        assert_equal(blueox.current_context(), None)


class BrokenCurrentContextTestCase(TestCase):
    @setup
    def broken_context(self):
        c = blueox.Context('test')
        assert not c.writable
        blueox.context._add_context(c)

    @teardown
    def clear(self):
        blueox.clear_contexts()

    def test(self):
        # Non-writable context shouldn't show up.
        current_c = blueox.current_context()
        assert not current_c
