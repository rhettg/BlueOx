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
