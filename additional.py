# -*- coding: utf-8 -*-
import os
import shutil
import time
import sys
import codecs


def safe_config_change(path, modifier, **argv):

    path_dump = argv.get('path_dump', '')
    interval = argv.get('interval', 1)
    tries = argv.get('tries', 5)
    mod_is_iterable = argv.get('mod_is_iterable', False)
    dump_path = path_dump + path + '.dump'
    new_path = path + '.new'

    try:
        shutil.copyfile(path, dump_path)
    except IOError:
        print 'dump creation failed'
        raise

    with codecs.open(new_path, 'w+', 'utf-8') as new_fd, \
            codecs.open(path, 'r', 'utf-8') as old_fd:
        if mod_is_iterable:
            for modified in modifier(old_fd.readline()):
                new_fd.write(modified)
        else:
            for line in old_fd.readline():
                new_fd.write(modifier(line))

    for x in range(tries):
        try:
            os.rename(new_path, path)
            return
        except OSError:
            time.sleep(interval)
            continue

    # if rename failed
    os.remove(new_path)
    raise Exception('exceeded the maximum number of tries')


def modifier_example_simple(line):
    """
    >>> отрефакторить код изменения/формирования содержимого в функци <<<
    1 - банальная функция обработки строк файла
    """
    return u'{}  {}'.format(line, time.time())


def modifier_example_with_potential_history(iterable):
    """
    >>> отрефакторить код изменения/формирования содержимого в функци <<<
    2 - итератор по содержимому старого файла,
         возможен вариант хранения истории и обработки связанных строк
    """
    for i in iterable:
        yield u'{} / {}'.format(i, time.time())

if __name__ == '__main__':
    safe_config_change(sys.argv[1], modifier_example_simple)