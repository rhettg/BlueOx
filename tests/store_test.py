from testify import *
import datetime

import blueox
from blueox import store


class ParseDateArgumentTestCase(TestCase):
    def test_simple_date(self):
        dt = store.parse_date_range_argument("20150521")
        assert_equal(dt, datetime.datetime(2015, 5, 21, 0, 0, 0))

    def test_simple_time(self):
        dt = store.parse_date_range_argument("20150521 12:45")
        assert_equal(dt, datetime.datetime(2015, 5, 21, 12, 45, 0))

    def test_bad(self):
        with assert_raises(store.InvalidDateError):
            store.parse_date_range_argument("foo")
