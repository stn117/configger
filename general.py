# -*- coding: utf-8 -*-
import re
import codecs
import os
import argparse
import sys
import logging
import json

"""

"""

parser = argparse.ArgumentParser(
    description='Config processor',
    formatter_class=argparse.RawTextHelpFormatter
)

cmd_help = """
upkey [old_key] [new_key] - update key
upval [key] [new_value]   - update value
add [key] [value]         - add new key value string to end of file
list                      - just parse file
"""

parser.add_argument('cfg_path', help='config file path')
parser.add_argument("-l", help="logging level",
                    default='info', dest='log_level')
parser.add_argument("cmd", choices=['upkey', 'upval', 'add', 'list'], help=cmd_help)
parser.add_argument("args", metavar='arg', nargs='*', help="keys and values")

args = parser.parse_args()

FORMAT = '%(asctime)s [%(levelname)s] - %(message)s'
logging.basicConfig(format=FORMAT, level=getattr(logging, args.log_level.upper()))


class ValidExc(Exception):
    pass


class BrokenConfig(Exception):
    pass


class Replacer:
    def __init__(self, replace_field, new_value):
        self.new_value = new_value
        self.replace_method = replace_field

    def __call__(self, matchobj):
        if self.replace_method == 'key':
            return self.replaceKey(matchobj)
        if self.replace_method == 'value':
            return self.replaceValue(matchobj)

        return self.doNothing(matchobj)

    def doNothing(self, matchobj):
        return matchobj.string

    def replaceKey(self, matchobj):
        old_container = matchobj.group('key_space')
        value = matchobj.group('value_space') or u''
        comment = matchobj.group('comment') or u''

        _old = matchobj.group('key')
        _new = self.new_value

        if len(_new) < len(_old):
            _new = _new.ljust(len(_old)) + old_container[len(_old):]
        elif len(_new) > len(_old) and len(_new) < len(old_container):
                _new = _new + old_container[len(_new):]

        return u'{}{}{}'.format(_new, value, comment)

    def replaceValue(self, matchobj):
        new_value = self.new_value
        value_container = matchobj.group('value_space')
        old_value = matchobj.group('value')
        comment = matchobj.group('comment') or u''

        if not value_container:
            new_value = ' ' + new_value

        elif len(new_value) < len(old_value):
            inserting_str = new_value.ljust(len(old_value))
            new_value = value_container[:1] + inserting_str + \
                value_container[len(inserting_str) + 1:]
        elif len(new_value) > len(old_value):
            if len(new_value) < len(value_container):
                new_value = value_container[:1] + \
                    new_value + \
                    value_container[len(new_value) + 1:]
            if len(new_value) >= len(value_container):
                new_value = value_container[:1] + new_value
        return u'{}{}{}'.format(matchobj.group('key_space'), new_value, comment)


class Config(object):
    def __init__(self, path):
        self.path = path
        self.fullmatch = r'^\s*(?P<key_space>(?P<key>[a-zA-Z][\w-]*)\s*)' \
                          '(?P<value_space>\s(?P<value>[^#].*?)\s*)?' \
                          '(?P<comment>\s#.*|$)'

    def parse(self, skip_broken=True):
        with codecs.open(self.path, "r", "utf-8") as fd:
            lines = [re.sub("\s+", " ", l).strip() for l in fd.readlines()]

        data = {}
        for i, l in enumerate(lines):
            if not l or l.startswith('#'):
                continue
            m = re.match(self.fullmatch, l)

            if not m:
                msg = 'Line {} is invalid: {}'.format(i, l)
                if not skip_broken:
                    raise BrokenConfig(msg)
                logging.warning(msg)
                continue

            data[m.group('key')] = m.group('value') or u''

        print data

    def addValue(self, key, value=None, comment=None):
        comment = u' # {}'.format(comment) if comment else u''
        value = u' {}'.format(value) if value else u''
        # append to file
        with codecs.open(self.path, "a", "utf-8") as fd:
            fd.write(u'{key}{value}{comment}\n'.format(
                key=key, value=value, comment=comment))

    def removeKey(self, key):
        if not self._isKeyOk(key):
            raise ValidExc('The key isn\'t ok')

        def rm(line):
            if line.lstrip().startswith(key):
                return None
            return line

        self._modify(rm)

    def _buildRegex(self, key):
        return r'^\s*(?P<key_space>(?P<key>{key})\s*)' \
                '(?P<value_space>\s(?P<value>[^#].*?)\s*)?' \
                '(?P<comment>\s#.*|$)'.format(key=key)

    def updateValue(self, key, new_value):
        if not self._isKeyOk(key):
            raise ValidExc('The key isn\'t ok')

        self._checkValue(new_value)

        regex = self._buildRegex(key)

        def f(line):
            return re.sub(regex, Replacer('value', new_value), line, re.UNICODE)

        self._modify(f)

    def updateKey(self, old_key, new_key):
        if not self._isKeyOk(old_key):
            raise ValidExc('The old key isn\'t ok')
        if not self._isKeyOk(new_key):
            raise ValidExc('The new key isn\'t ok')

        regex = self._buildRegex(old_key)

        def f(line):
            return re.sub(regex, Replacer('key', new_key), line, re.UNICODE)

        self._modify(f)

    def _modify(self, mod_func):
        new_lines = []

        with codecs.open(self.path, "r", "utf-8") as fd:
            for line in fd.readlines():
                line = line.rstrip()
                new_line = mod_func(line)
                if new_line is not None:
                    new_lines.append(new_line)

        with codecs.open(self.path, "w+", "utf-8") as fd:
            for l in new_lines:
                fd.write(l + u'\n')

    def _checkValue(self, v):
        res = re.match(r'\s#', v)
        if res:
            logging.warning('The value contains comment')

    def _isCommentOk(self, c):
        if c.startswith('#'):
            return True
        return False

    def _isKeyOk(self, k):
        res = re.match(r'^[a-zA-Z][\w_-]+$', k)
        if res:
            return True
        return False


if __name__ == '__main__':

    if not os.path.isfile(args.cfg_path):
        logging.error('bad file path')
        sys.exit(1)

    worker = Config(args.cfg_path)

    if args.cmd == 'list':
        json.dumps(worker.parse())
        exit(0)

    key = args.args[0].decode('utf-8')
    value = args.args[1].decode('utf-8') if len(args.args) > 1 else u''

    if args.cmd == 'upkey':
        worker.updateKey(key, value)

    if args.cmd == 'upval':
        worker.updateValue(key, value)

    if args.cmd == 'add':
        worker.addValue(key, value)

    print('done')

