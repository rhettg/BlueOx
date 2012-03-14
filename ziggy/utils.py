# -*- coding: utf-8 -*-

"""
ziggy.util
~~~~~~~~

This module provides utility functions that are used within Ziggy

:copyright: (c) 2012 by Rhett Garber.
:license: ISC, see LICENSE for more details.

"""

class ParsedKey(list):
    def __init__(self, value):
        if '.' in value:
            for part in value.split('.'):
                try:
                    self.append(int(part))
                except ValueError:
                    self.append(part)
        else:
            self.append(value)

    def __str__(self):
        return '.'.join((str(v) for v in self))

def parse_key(key):
    return ParsedKey(key)

def get_deep(target, key, default=None):
    value = target
    for elem in parse_key(key):
        try:
            value = value[elem]
        except (KeyError, IndexError):
            return default

    return value

def set_deep(target, key, value):
    iter_value = target
    p_key = parse_key(key)
    for elem in p_key[:-1]:
        if isinstance(elem, int):
            raise ValueError(elem)

        iter_value = iter_value.setdefault(elem, {})

    iter_value[p_key[-1]] = value
