#!/usr/bin/python
"""Announce the started and last-edited dates of files in this Git repo.

Bug: uses your local time zone rather than the commit timezone.
"""
import subprocess
import sys
import time


def when(filename):
    kid = subprocess.Popen('git log --pretty=raw --'.split() + [filename],
                           stdout=subprocess.PIPE)
    authorlines = [line for line in kid.stdout if line.startswith('author ')]
    dates = [int(words[-2]) for words in [line.split() for line in authorlines]]
    if not dates:
        return None, None
    return min(dates), max(dates)

def format_when(filename, start, end):
    if start is None or end is None:
        return '%s needs manual-investigation-of-dates\n' % filename
    return ('%s written %s\n'
            + '%s updated %s\n') % (filename, date(start),
                                    filename, date(end))

def date(time_t):
    struct_tm = time.localtime(time_t)
    return '%04d-%02d-%02d' % (struct_tm.tm_year,
                               struct_tm.tm_mon,
                               struct_tm.tm_mday)

def main(args):
    for filename in args:
        sys.stdout.write(format_when(filename, *when(filename)))

if __name__ == '__main__':
    main(sys.argv[1:])
