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
