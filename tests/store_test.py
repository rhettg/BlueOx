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


class LogFileFilePathTes(TestCase):
    def test_simple_date(self):
        date = datetime.date(2015, 5, 21)
        lf = store.LogFile("foo", date=date)
        assert_equal(lf.file_path, "20150521/foo-20150521.log")

    def test_simple_dt(self):
        dt = datetime.datetime(2015, 5, 21, 20)
        lf = store.LogFile("foo", dt=dt)
        assert_equal(lf.file_path, "20150521/foo-2015052120.log")

    def test_dt_host(self):
        dt = datetime.datetime(2015, 5, 21, 20)
        lf = store.LogFile("foo", dt=dt, host='localhost')
        assert_equal(lf.file_path, "20150521/foo-2015052120-localhost.log")

    def test_dt_zipped(self):
        dt = datetime.datetime(2015, 5, 21, 20)
        lf = store.LogFile("foo", dt=dt, bzip=True)
        assert_equal(lf.file_path, "20150521/foo-2015052120.log.bz2")


class LogFileFromFilenameTest(TestCase):
    def test_simple_date(self):
        file_name = "/var/log/20150521/foo-20150521.log"
        lf = store.LogFile.from_filename(file_name)
        assert_equal(lf.type_name, "foo")
        assert_equal(lf.date, datetime.date(2015, 5, 21))
        assert_equal(lf.host, None)
        assert_equal(lf.bzip, False)

    def test_simple_dt(self):
        file_name = "/var/log/20150521/foo-2015052120.log"
        lf = store.LogFile.from_filename(file_name)
        assert_equal(lf.dt, datetime.datetime(2015, 5, 21, 20))

    def test_host(self):
        file_name = "/var/log/20150521/foo-2015052120-localhost.log"
        lf = store.LogFile.from_filename(file_name)
        assert_equal(lf.host, "localhost")

    def test_bzip(self):
        file_name = "/var/log/20150521/foo-2015052120-localhost.log.bz2"
        lf = store.LogFile.from_filename(file_name)
        assert lf.bzip
