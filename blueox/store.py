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

    def get_local_file_path(self, log_path):
        return os.path.join(log_path, self.file_path)

    def s3_key(self, bucket):
        return boto.s3.key.Key(bucket, name=self.file_path)

    def build_remote(self, host):
        return LogFile(
            self.type_name,
            host=host,
            dt=self.dt,
            date=self.date,
            bzip=self.bzip)

    @property
    def file_path(self):
        date_str = self.date.strftime('%Y%m%d')

        if self.dt:
            date_name_str = self.dt.strftime('%Y%m%d%H')
        else:
            date_name_str = date_str

        bzip_str = ""
        if self.bzip:
            bzip_str = ".bz2"

        host_str = ""
        if self.host:
            host_str = "-{}".format(self.host)

        return "{date}/{type}-{date_name}{host_str}.log{bzip}".format(
            date=date_str,
            type=self.type_name,
            host_str=host_str,
            date_name=date_name_str,
            bzip=bzip_str)

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
        type_files.sort(key=lambda f: f.dt or datetime.datetime(f.date.year, f.date.month, f.date.day))

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
