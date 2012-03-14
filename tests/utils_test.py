from testify import *

from ziggy import utils

class SimpleKeyParseTestCase(TestCase):
    @setup
    def parse(self):
        self.value = utils.parse_key('foo')

    def test(self):
        """verify that a single element key works"""
        assert len(self.value), 1
        assert_equal(self.value[0], 'foo')
        assert_equal(str(self.value), 'foo')


class LayerKeyParseTestCase(TestCase):
    @setup
    def parse(self):
        self.value = utils.parse_key('foo.bar')

    def test(self):
        """verify that a simple two element key works"""
        assert len(self.value), 2
        assert_equal(self.value[0], 'foo')
        assert_equal(self.value[1], 'bar')
        assert_equal(str(self.value), 'foo.bar')


class IndexKeyParseTestCase(TestCase):
    @setup
    def parse(self):
        self.value = utils.parse_key('foo.bar.2')

    def test(self):
        """verify that a key with index values works"""
        assert len(self.value), 3
        assert_equal(self.value[0], 'foo')
        assert_equal(self.value[1], 'bar')
        assert_equal(self.value[2], 2)
        assert_equal(str(self.value), 'foo.bar.2')


class SimpleGetDeepTestCase(TestCase):
    @setup
    def build_value(self):
        self.value = {'foo': True}

    def test_found(self):
        """verify we can find a shallow value"""
        assert_equal(utils.get_deep(self.value, 'foo'), True)

    def test_default(self):
        """verify we can handle simple miss for a shallow value"""
        assert_equal(utils.get_deep(self.value, 'bar', 5), 5)


class DeeperGetDeepTestCase(TestCase):
    @setup
    def build_value(self):
        self.value = {'foo': {'bar': True}}

    def test_found(self):
        """verify we can find a deep value"""
        assert_equal(utils.get_deep(self.value, 'foo.bar'), True)

    def test_default(self):
        """verify we can handle a missing deep value"""
        assert_equal(utils.get_deep(self.value, 'foo.zoo', 5), 5)


class ListedGetDeepTestCase(TestCase):
    @setup
    def build_value(self):
        self.value = {'foo': [{'bar': True}]}

    def test_found(self):
        """verify we can find an indexed value"""
        assert_equal(utils.get_deep(self.value, 'foo.0.bar'), True)

    def test_default(self):
        """verify a missing indexed value works"""
        assert_equal(utils.get_deep(self.value, 'foo.1.bar', 5), 5)


class SimpleSetDeepTestCase(TestCase):
    @setup
    def build_value(self):
        self.value = {}
        utils.set_deep(self.value, 'foo', True)

    def test(self):
        """verify we can set a shallow value"""
        assert_equal(utils.get_deep(self.value, 'foo'), True)


class DeeperSetDeepTestCase(TestCase):
    @setup
    def build_value(self):
        self.value = {}
        utils.set_deep(self.value, 'foo.bar', True)

    def test(self):
        """verify we can set a shallow value"""
        assert_equal(utils.get_deep(self.value, 'foo.bar'), True)


class ExistingSetDeepTestCase(TestCase):
    @setup
    def build_value(self):
        self.value = {'foo': {'bar': True}}
        utils.set_deep(self.value, 'foo.baz', True)

    def test(self):
        """verify we can set a shallow value"""
        assert_equal(utils.get_deep(self.value, 'foo.baz'), True)
