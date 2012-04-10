import time
from testify import *

import blueox

class SimpleTestCase(TestCase):
    def test(self):
        context = blueox.Context('test', 1)
        with context:
            with blueox.timeit('test_time'):
                time.sleep(0.25)

        assert 1.0 > context.data['test_time'] > 0.0
