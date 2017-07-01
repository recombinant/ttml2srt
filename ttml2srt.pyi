#
# -*- coding: utf-8 -*-
from datetime import timedelta
from typing import Dict
from xml.etree.ElementTree import Element


def parse_time_expression(expression: str,
                          default_offset: timedelta = ...) \
        -> timedelta:
    ...


def parse_times(elem: Element, default_begin: timedelta = ...):
    ...


def render_subtitles(styles: Dict[str, Dict[str, str]],
                     elem: Element,
                     timestamp: timedelta) \
        -> str:
    ...


def format_timestamp(timestamp: timedelta) -> str: ...


def main():
    ...
