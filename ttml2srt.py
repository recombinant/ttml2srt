#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
from datetime import timedelta
from typing import Dict, Set, List, Tuple, Optional
from xml.etree import ElementTree


def parse_time_expression(expression, default_offset=timedelta(0)):
    """
    Parse correct start and end times.
    """
    offset_time = re.match(r'^([0-9]+(\.[0-9]+)?)(h|m|s|ms|f|t)$', expression)
    if offset_time:
        time_value, fraction, metric = offset_time.groups()
        time_value = float(time_value)
        if metric == 'h':
            return default_offset + timedelta(hours=time_value)
        elif metric == 'm':
            return default_offset + timedelta(minutes=time_value)
        elif metric == 's':
            return default_offset + timedelta(seconds=time_value)
        elif metric == 'ms':
            return default_offset + timedelta(milliseconds=time_value)
        elif metric == 'f':
            raise NotImplementedError('Parsing time expressions by frame is not supported!')
        elif metric == 't':
            raise NotImplementedError('Parsing time expressions by ticks is not supported!')

    clock_time = re.match(r'^([0-9]{2,}):([0-9]{2,}):([0-9]{2,}(\.[0-9]+)?)$', expression)
    if clock_time:
        hours, minutes, seconds, fraction = clock_time.groups()
        return timedelta(hours=int(hours), minutes=int(minutes), seconds=float(seconds))

    clock_time_frames = re.match(r'^([0-9]{2,}):([0-9]{2,}):([0-9]{2,}):([0-9]{2,}(\.[0-9]+)?)$', expression)
    if clock_time_frames:
        raise NotImplementedError('Parsing time expressions by frame is not supported!')

    raise ValueError('unknown time expression: %s' % expression)


def parse_times(elem, default_begin=timedelta(0)):
    """
    Parse elements and decorate the elements with '{abs}begin' and '{abs}end'
    attributes for later retrieval with XPath expressions.
    """
    if 'begin' in elem.attrib:
        begin = parse_time_expression(elem.attrib['begin'], default_offset=default_begin)
    else:
        begin = default_begin
    elem.attrib['{abs}begin'] = begin

    end = None
    if 'end' in elem.attrib:
        end = parse_time_expression(elem.attrib['end'], default_offset=default_begin)

    dur = None
    if 'dur' in elem.attrib:
        dur = parse_time_expression(elem.attrib['dur'])

    if dur is not None:
        if end is None:
            end = begin + dur
        else:
            end = min(end, begin + dur)

    elem.attrib['{abs}end'] = end

    for child in elem:
        parse_times(child, default_begin=begin)


def render_subtitles(styles, elem, timestamp):
    """
    Render subtitles on each timestamp.
    """
    if timestamp < elem.attrib['{abs}begin']:
        return ''
    if elem.attrib['{abs}end'] is not None and timestamp >= elem.attrib['{abs}end']:
        return ''

    result = ''

    style: Dict[str, str] = {}
    if 'style' in elem.attrib:
        style.update(styles[elem.attrib['style']])

    if 'color' in style:
        result += '<font color="%s">' % style['color']

    if style.get('font_style') == 'italic':
        result += '<i>'

    if elem.text:
        result += elem.text.strip()
    if len(elem):
        for child in elem:
            result += render_subtitles(styles, child, timestamp)
            if child.tail:
                result += child.tail.strip()

    if 'color' in style:
        result += '</font>'

    if style.get('font_style') == 'italic':
        result += '</i>'

    if elem.tag in ('div', 'p', 'br'):
        result += '\n'

    return result


def format_timestamp(timestamp):
    return ('{:02d}:{:02d}:{:02.3f}'.format(int(timestamp.total_seconds() // 3600),
                                            int(timestamp.total_seconds() // 60 % 60),
                                            timestamp.total_seconds() % 60)).replace('.', ',')


def main():
    filename = sys.argv[1]

    tree = ElementTree.parse(filename)
    root = tree.getroot()

    # strip namespaces
    for elem in root.getiterator():
        elem.tag = elem.tag.split('}', 1)[-1]
        elem.attrib = {name.split('}', 1)[-1]: value for name, value in elem.attrib.items()}

    # get styles
    styles: Dict[str, Dict[str, str]] = {}

    for elem in root.findall('./head/styling/style'):
        style: Dict[str, str] = {}
        if 'color' in elem.attrib:
            color = elem.attrib['color']
            if color not in ('#FFFFFF', '#000000'):
                style['color'] = color
        if 'fontStyle' in elem.attrib:
            font_style = elem.attrib['fontStyle']
            if font_style in ('italic',):
                style['font_style'] = font_style
        styles[elem.attrib['id']] = style

    body = root.find('./body')

    parse_times(body)

    timestamps: Set[Optional[timedelta]] = set()
    for elem in body.findall('.//*[@{abs}begin]'):
        timestamps.add(elem.attrib['{abs}begin'])

    for elem in body.findall('.//*[@{abs}end]'):
        timestamps.add(elem.attrib['{abs}end'])

    timestamps.discard(None)

    rendered: List[Tuple[timedelta, str]] = []
    for timestamp in sorted(timestamps):
        rendered.append((timestamp, re.sub(r'\n\n\n+', '\n\n', render_subtitles(styles, body, timestamp)).strip()))

    if not rendered:
        exit(0)

    # group timestamps together if nothing changes
    rendered_grouped: List[Tuple[timedelta, str]] = []
    last_text = None
    for timestamp, content in rendered:
        if content != last_text:
            rendered_grouped.append((timestamp, content))
        last_text = content

    # output srt
    rendered_grouped.append((rendered_grouped[-1][0] + timedelta(hours=24), ''))

    srt_i = 1
    for i, (timestamp, content) in enumerate(rendered_grouped[:-1]):
        if content == '':
            continue
        print(srt_i)
        print(format_timestamp(timestamp) + ' --> ' + format_timestamp(rendered_grouped[i + 1][0]))
        print(content)
        srt_i += 1
        print('')


if __name__ == '__main__':
    main()
