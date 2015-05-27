from testify import *
import io
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


class LogFileFilePathTest(TestCase):
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

    def test_fqdnhost(self):
        file_name = "/var/log/20150521/foo-2015052120-ip-192-168-1-1.compute.internal.log"
        lf = store.LogFile.from_filename(file_name)
        assert_equal(lf.host, "ip-192-168-1-1.compute.internal")

    def test_bzip(self):
        file_name = "/var/log/20150521/foo-2015052120-localhost.log.bz2"
        lf = store.LogFile.from_filename(file_name)
        assert lf.bzip


class S3LogFileFromS3KeyTest(TestCase):
    def test(self):
        key = turtle.Turtle()
        key.name = "20150521/foo-20150521-localhost.log.bz2"
        lf = store.S3LogFile.from_s3_key(key)

        assert_equal(lf.type_name, "foo")
        assert_equal(lf.date, datetime.date(2015, 5, 21))
        assert_equal(lf.host, "localhost")
        assert_equal(lf.bzip, True)


class LocalLogFileBuildRemoteTest(TestCase):
    def test(self):
        lf = store.LocalLogFile('foo', dt=datetime.datetime(2015, 5, 21, 20), bzip=True)

        r_lf = lf.build_remote('log-host')

        assert_equal(r_lf.host, 'log-host')
        assert_equal(r_lf.type_name, 'foo')
        assert_equal(r_lf.date, datetime.date(2015, 5, 21))
        assert r_lf.bzip


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
        log_file = store.LocalLogFile("foo", date=datetime.date(2015, 5, 21))

        full_file_path = os.path.join(self.log_path, log_file.file_path)
        os.makedirs(os.path.dirname(full_file_path))
        with open(full_file_path, "w") as f:
            f.write("hi")

        store.zip_log_file(log_file, self.log_path)
        assert log_file.bzip
        assert os.path.exists(os.path.join(self.log_path, log_file.file_path))


class S3PrefixTest(TestCase):
    def test(self):
        dt = datetime.datetime(2015, 5, 21)
        prefix = store.s3_prefix_for_date_and_type(dt, "foo")
        assert_equal(prefix, "20150521/foo-")


class InclusiveDateRangeTest(TestCase):
    def test_dates(self):
        start_dt = datetime.datetime(2015, 5, 19)
        end_dt = datetime.datetime(2015, 5, 21)
        dates = list(store.inclusive_date_range(start_dt, end_dt))

        assert_equal(len(dates), 3)
        assert_equal(dates[0], start_dt.date())
        assert_equal(dates[-1], end_dt.date())

    def test_boundry(self):
        start_dt = datetime.datetime(2015, 5, 19, 20)
        end_dt = datetime.datetime(2015, 5, 21, 3)
        dates = list(store.inclusive_date_range(start_dt, end_dt))

        assert_equal(len(dates), 3)
        assert_equal(dates[0], start_dt.date())
        assert_equal(dates[-1], end_dt.date())


class FindLogFilesInS3Test(TestCase):
    def test_empty(self):
        start_dt = datetime.datetime(2015, 5, 19)
        end_dt = datetime.datetime(2015, 5, 21)

        bucket = turtle.Turtle()

        def do_list(prefix):
            return []

        bucket.list = do_list

        log_files = store.find_log_files_in_s3(bucket, "foo", start_dt, end_dt)
        assert_equal(len(log_files), 0)

    def test_date(self):
        start_dt = datetime.datetime(2015, 5, 19)
        end_dt = datetime.datetime(2015, 5, 21)

        bucket = turtle.Turtle()

        def do_list(prefix):
            if prefix.startswith("20150519"):
                key = turtle.Turtle()
                key.name = "20150519/foo-20150519-localhost.log.bz2"
                return [key]
            else:
                return []

        bucket.list = do_list

        log_files = store.find_log_files_in_s3(bucket, "foo", start_dt, end_dt)
        assert_equal(len(log_files), 1)
        assert_equal(log_files[0].type_name, "foo")

    def test_range(self):
        start_dt = datetime.datetime(2015, 5, 19, 1)
        end_dt = datetime.datetime(2015, 5, 19, 3)

        bucket = turtle.Turtle()

        def do_list(prefix):
            assert prefix.startswith("20150519")

            return [
                turtle.Turtle(name="20150519/foo-2015051900-localhost.log.bz2"),
                turtle.Turtle(name="20150519/foo-2015051901-localhost.log.bz2"),
                turtle.Turtle(name="20150519/foo-2015051902-localhost.log.bz2"),
                turtle.Turtle(name="20150519/foo-2015051903-localhost.log.bz2"),
                turtle.Turtle(name="20150519/foo-2015051904-localhost.log.bz2"),
            ]

        bucket.list = do_list

        log_files = store.find_log_files_in_s3(bucket, "foo", start_dt, end_dt)
        assert_equal(len(log_files), 3)
        assert_equal(log_files[0].dt, start_dt)
        assert_equal(log_files[-1].dt, end_dt)

    def test_range_with_date_key(self):
        start_dt = datetime.datetime(2015, 5, 19, 1)
        end_dt = datetime.datetime(2015, 5, 19, 3)

        bucket = turtle.Turtle()

        def do_list(prefix):
            assert prefix.startswith("20150519")

            return [
                turtle.Turtle(name="20150519/foo-20150519-localhost.log.bz2"),
            ]

        bucket.list = do_list

        log_files = store.find_log_files_in_s3(bucket, "foo", start_dt, end_dt)
        assert_equal(len(log_files), 1)


class FindLogFilesInLocalTest(TestCase):
    @setup
    def build_log_directory(self):
        self.log_path = tempfile.mkdtemp(suffix="oxtest")

    @teardown
    def remove_log_directory(self):
        shutil.rmtree(self.log_path)

    def test_empty(self):
        start_dt = datetime.datetime(2015, 5, 19)
        end_dt = datetime.datetime(2015, 5, 21)

        log_files = store.find_log_files_in_path(self.log_path, "foo", start_dt, end_dt)
        assert_equal(len(log_files), 0)

    def test_range(self):
        dts = [
            datetime.datetime(2015, 5, 19, 0),
            datetime.datetime(2015, 5, 19, 1),
            datetime.datetime(2015, 5, 19, 2),
            datetime.datetime(2015, 5, 19, 3),
            datetime.datetime(2015, 5, 19, 4)]

        os.makedirs(os.path.join(self.log_path, dts[0].strftime("%Y%m%d")))

        for dt in dts:
            date_str = dt.strftime('%Y%m%d')
            dt_str = dt.strftime('%Y%m%d%H')
            full_path = os.path.join(self.log_path, date_str, "foo-{}.log".format(dt_str))
            with io.open(full_path, "w") as f:
                f.write(u"hi")

        start_dt = datetime.datetime(2015, 5, 19, 1)
        end_dt = datetime.datetime(2015, 5, 19, 3)
        log_files = store.find_log_files_in_path(self.log_path, "foo", start_dt, end_dt)

        assert_equal(len(log_files), 3)
        assert_equal(log_files[0].dt, start_dt)
        assert_equal(log_files[-1].dt, end_dt)


