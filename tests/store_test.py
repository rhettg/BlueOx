from testify import *
import datetime
import shutil
import tempfile
import os

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


class ListLogFilesTest(TestCase):
    @setup
    def build_log_directory(self):
        self.log_path = tempfile.mkdtemp(suffix="oxtest")

    @teardown
    def remove_log_directory(self):
        shutil.rmtree(self.log_path)

    def test_empty(self):
        files = store.list_log_files(self.log_path)
        assert_equal(len(files), 0)

    def test_garbage(self):
        file_name = os.path.join(self.log_path, "foo.dat")
        with open(file_name, "w") as f:
            f.write("hi")

        files = store.list_log_files(self.log_path)
        assert_equal(len(files), 0)

    def test_simple(self):
        file_name = os.path.join(self.log_path, "foo-20150521.log")
        with open(file_name, "w") as f:
            f.write("hi")

        files = store.list_log_files(self.log_path)
        assert_equal(len(files), 1)
        assert_equal(files[0].type_name, "foo")


class FilterUnzippedTest(TestCase):
    def test_no_zipped(self):
        files = [store.LogFile('foo', date=datetime.date.today(), bzip=True)]
        out_files = store.filter_log_files_for_zipping(files)
        assert_equal(len(out_files), 0)

    def test_leave_active(self):
        files = [store.LogFile('foo', date=datetime.date.today())]
        out_files = store.filter_log_files_for_zipping(files)
        assert_equal(len(out_files), 0)

    def test_zippable(self):
        files = [
            store.LogFile('foo', date=datetime.date.today()),
            store.LogFile('bar', date=datetime.date.today()),
            store.LogFile('bar', date=datetime.date.today() - datetime.timedelta(days=1))
        ]
        out_files = store.filter_log_files_for_zipping(files)
        assert_equal(len(out_files), 1)
        assert_equal(out_files[0], files[-1])

    def test_zippable_hourly(self):
        files = [
            store.LogFile('bar', dt=datetime.datetime(2015, 5, 21, 19)),
            store.LogFile('bar', dt=datetime.datetime(2015, 5, 21, 20))
        ]
        out_files = store.filter_log_files_for_zipping(files)
        assert_equal(len(out_files), 1)
        assert_equal(out_files[0], files[0])

    def test_hourly_and_daily(self):
        files = [
            store.LogFile('bar', date=datetime.date(2015, 5, 20)),
            store.LogFile('bar', dt=datetime.datetime(2015, 5, 21, 19)),
            store.LogFile('bar', dt=datetime.datetime(2015, 5, 21, 20))
        ]
        out_files = store.filter_log_files_for_zipping(files)
        assert_equal(len(out_files), 2)


class ZipLogFileTest(TestCase):
    @setup
    def build_log_directory(self):
        self.log_path = tempfile.mkdtemp(suffix="oxtest")

    @teardown
    def remove_log_directory(self):
        shutil.rmtree(self.log_path)

    def test(self):
        log_file = store.LogFile("foo", date=datetime.date(2015, 5, 21))

        full_file_path = os.path.join(self.log_path, log_file.file_path)
        os.makedirs(os.path.dirname(full_file_path))
        with open(full_file_path, "w") as f:
            f.write("hi")

        store.zip_log_file(log_file, self.log_path)
        assert log_file.bzip
        assert os.path.exists(os.path.join(self.log_path, log_file.file_path))
