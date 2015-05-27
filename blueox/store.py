# -*- coding: utf-8 -*-

"""
blueox.store
~~~~~~~~

This module provides utility functions for managing log files as created by
oxd.

:copyright: (c) 2015 by Rhett Garber
:license: ISC, see LICENSE for more details.

"""
import logging
import datetime
import os
import re
import collections
import io
import bz2

try:
    import boto
except ImportError:
    boto = None
else:
    from boto.s3.connection import OrdinaryCallingFormat

from . import errors

log = logging.getLogger(__name__)


DATE_FORMATS = ["%Y%m%d", "%Y%m%d %H:%M"]


class InvalidDateError(errors.Error):
    pass


def parse_date_range_argument(value):
    dt = None
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            pass

    raise InvalidDateError()


class LogFile(object):
    """Represents a remote log file"""

    def __init__(self, type_name, host=None, dt=None, date=None, bzip=False):
        self.type_name = type_name
        self.host = host
        self.bzip = bzip
        if (dt, date) == (None, None):
            raise ValueError("Needs a date")

        self.dt = dt
        self.date = date or dt.date()

    @property
    def sort_dt(self):
        # Log files may not represent an actual datetime, but sometimes we need
        # to sort them like they are, preferrably incorporating the fact that
        # users may switch from daily rotation (the default) to hourly.
        if self.dt:
            return self.dt
        else:
            return datetime.datetime(
                self.date.year,
                self.date.month,
                self.date.day)

    def get_local_file_path(self, log_path):
        return os.path.join(log_path, self.file_path)

    def s3_key(self, bucket):
        return boto.s3.key.Key(bucket, name=self.file_path)

    def local_stream(self, log_path):
        def stream():
            if self.bzip:
                decompressor = bz2.BZ2Decompressor()
            else:
                decompressor = None

            with io.open(self.get_local_file_path(log_path), "rb") as f:
                for data in f:
                    if decompressor:
                        r = decompressor.decompress(data)
                    else:
                        r = data

                    if r is not None:
                        yield r


    def s3_stream(self, bucket):
        """Create a iterable stream of data from the log file.

        Automatically handles bzip decoding
        """
        def stream():
            key = self.s3_key(bucket)

            if self.bzip:
                decompressor = bz2.BZ2Decompressor()
            else:
                decompressor = None

            for data in self.s3_key(bucket):
                if decompressor:
                    r = decompressor.decompress(data)
                else:
                    r = data

                if r is not None:
                    yield r

        return stream()

    def build_remote(self, host):
        return LogFile(
            self.type_name,
            host=host,
            dt=self.dt,
            date=self.date,
            bzip=self.bzip)

    @property
    def file_name(self):
        if self.dt:
            date_name_str = self.dt.strftime('%Y%m%d%H')
        else:
            date_name_str = self.date.strftime('%Y%m%d')

        bzip_str = ""
        if self.bzip:
            bzip_str = ".bz2"

        host_str = ""
        if self.host:
            host_str = "-{}".format(self.host)

        return "{type}-{date_name}{host_str}.log{bzip}".format(
            type=self.type_name,
            host_str=host_str,
            date_name=date_name_str,
            bzip=bzip_str)

    @property
    def file_path(self):
        date_str = self.date.strftime('%Y%m%d')
        return "{date}/{filename}".format(
            date=date_str,
            filename=self.file_name)

    @classmethod
    def from_filename(cls, filename):
        basename = os.path.basename(filename)
        match = re.match(
            r"^(?P<stream>.+)" # stream name like "nginx-error"
            r"\-(?P<date>\d{8,10})" # date like 20140229 or 2014022910
            r"\-?(?P<host>.+)?" # optional server name
            r"\.log" # .log
            r"(?P<zip>\.bz2|\.gz)?$",
            basename)

        if match is None:
            raise ValueError(basename)

        match_info = match.groupdict()

        log_dt = log_date = None
        if len(match_info['date']) == len('yyyymmddHH'):
            log_dt = datetime.datetime.strptime(match_info["date"], '%Y%m%d%H')
        else:
            log_date = datetime.datetime.strptime(match_info["date"], '%Y%m%d').date()

        return LogFile(
            match_info["stream"],
            host=match_info.get('host'),
            dt=log_dt,
            date=log_date,
            bzip=bool(match_info['zip']))

    @classmethod
    def from_s3_key(cls, key):
        return cls.from_filename(key.name)


def list_log_files(log_path):
    """Find and parse all the log files in the specified log path"""
    log_files = []
    for dirpath, dirnames, filenames in os.walk(log_path):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)

            try:
                log_file = LogFile.from_filename(filename)
            except ValueError:
                log.warning("Not a blueox log file: %s", full_path)
                continue
            log_files.append(log_file)

    return log_files


def filter_log_files_for_zipping(log_files):
    """Identify unzipped log files that are approporate for zipping.

    Each unique log type found should have the most recent log file unzipped
    as it's probably still in use.
    """
    files_by_type = collections.defaultdict(list)
    for f in log_files:
        if f.bzip:
            continue

        files_by_type[f.type_name].append(f)

    out_files = []

    for type_files in files_by_type.values():
        type_files.sort(key=lambda f: f.sort_dt)

        # We should always leave one unzipped file for each type (the likely
        # active one)
        out_files += type_files[:-1]

    return out_files


def zip_log_file(log_file, log_path):
    orig_path = log_file.get_local_file_path(log_path)

    log_file.bzip = True

    zip_path = log_file.get_local_file_path(log_path)

    # It's hard to believe, but this appears in testing to be just as fast as
    # spawning a bzip2 process.
    zip_file = bz2.BZ2File(
        zip_path, 'w', io.DEFAULT_BUFFER_SIZE)

    with io.open(orig_path, "rb") as fp:
        for data in fp:
            zip_file.write(data)
    zip_file.close()
    os.unlink(orig_path)


def s3_prefix_for_date_and_type(date, type_name):
    date_str = date.strftime('%Y%m%d')
    return "{}/{}-".format(date_str, type_name)


def inclusive_date_range(start_dt, end_dt):
    start_date = start_dt.date()
    end_date = end_dt.date()

    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += datetime.timedelta(days=1)


def find_log_files_in_s3(bucket, type_name, start_dt, end_dt):
    prefixes = []
    for dt in inclusive_date_range(start_dt, end_dt):
        prefixes.append(s3_prefix_for_date_and_type(dt, type_name))

    log_files = []
    for pf in prefixes:
        for key in bucket.list(pf):
            try:
                log_files.append(LogFile.from_s3_key(key))
            except ValueError as e:
                log.warning("S3 key %r not a log file: %r", key, e)
                continue

    out_log_files = []
    for lf in log_files:
        assert lf.type_name == type_name

        if lf.dt is None:
            # For log files that cover an entire day, we'll include it even if
            # the query was for a specific time range.
            out_log_files.append(lf)

        elif lf.dt >= start_dt and lf.dt <= end_dt:
            out_log_files.append(lf)

    return out_log_files


def find_log_files_in_path(log_path, type_name, start_dt, end_dt):
    log_files = list_log_files(log_path)
    out_log_files = []

    for lf in log_files:
        if lf.dt is None:
            if lf.date < start_dt.date() or lf.date > end_dt.date():
                continue
        else:
            if lf.dt < start_dt or lf.dt > end_dt:
                continue

        out_log_files.append(lf)

    return out_log_files


def open_bucket(bucket_name):
    region_name = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')

    # We need to specify calling_format to get around bugs in having a '.' in
    # the bucket name
    conn = boto.s3.connect_to_region(region_name, calling_format=OrdinaryCallingFormat())

    bucket = conn.get_bucket(bucket_name)
    if not bucket:
        parser.error("Missing bucket {}".format(bucket_name))

    return bucket
