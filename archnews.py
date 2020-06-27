#!/bin/env python3
# Author: Jørgen Bele Reinfjell
# Date: 10.10.2018 [dd.mm.yyyy]
# Description:
#   Shitty script for displaying archlinux news in
#   a nicely formatted way. Probably not useful for
#   anyone other than me.

"""
Usage: archnews [options]

Options:
  --pretty
  --terse
  -v, --verbose                  Enable verbose output
  -l <number>, --limit <number>  Limit to <number> recent posts

Displays a list of the recent arch linux news entries (limited using -l)
in a nicely formatted table.
"""
from bs4 import BeautifulSoup
import requests
from docopt import docopt
import sys

### FROM confs/common.py
def is_interactive():
    return sys.__stdout__.isatty()

class ArgFlags:
    pretty = False
    pretty_or_terse_flag_present = False
    verbose = False
    interactive = False

    @staticmethod
    def from_args(args):
        ArgFlags.interactive = is_interactive()
        for arg in [k for k, v in args.items() if v]: # only care about flags set to True
            if arg == '--pretty':
                ArgFlags.pretty = True
                ArgFlags.pretty_or_terse_flag_present = True
            elif arg == '--terse':
                ArgFlags.pretty = False
                ArgFlags.pretty_or_terse_flag_present = True
            elif arg == '--verbose':
                ArgFlags.verbose = True

        if not ArgFlags.pretty_or_terse_flag_present:
            # use --pretty implicitly when interactive
            ArgFlags.pretty = ArgFlags.interactive

# MODIFIED: added 'arch' flag
def pprint(fargs, *args, word_wrap=True, warning=False, bold=False, success=False, enabled=False, fatal=False, header=False, arch=False, **kwargs):
    def escape(s):
        return '\033{}'.format(s)

    """Pretty print"""
    if ArgFlags.pretty:
        bold_str = escape('[1m') if bold else ''
        color_str = ''
        reset_str = ''
        if warning or fatal:
            color_str = escape('[31m') # red
        elif success or enabled:
            color_str = escape('[32m') # green
        elif header:
            color_str = escape('[33m') # orange
        elif arch:
            color_str = escape('[35m') # magenta


        if bold or len(color_str) > 0:
            reset_str = escape('[0m') # none

        # TODO wordwrap
        nfargs = '{}{}{}'.format(bold_str, color_str, fargs)
        return print(nfargs, *args, reset_str, **kwargs)
    else:
        return print(fargs, *args, **kwargs)

def stringify(row):
    return [str(c) for c in row]

def align_columns(rows, column_options=None, spacing=1, header=None):
    """
    Aligns columns in a row of items.
    column_options is a list containing descibing how each column
    should be aligned
    Example: ['left', 'center', 'right'] will align the first column to the
    left, the second to the center, and the third to the right.
    """

    srows = []
    if header:
        srows.append(stringify(header))
    srows = srows + [stringify(row) for row in rows]

    column_details = {}
    for r in srows:
        for i, c in enumerate(r):
            if i not in column_details:
                column_details[i] = {'width': 0}
            column_details[i]['width'] = max(column_details[i]['width'], len(c))

    spacing_str = ' ' * spacing

    def align_row(row):
        nonlocal column_details, column_options
        out_columns = []
        for i, c in enumerate(row):
            align_chr = '<' # left-align by default
            if column_options:
                if column_options[i] == 'right':
                        align_chr = '>'
                elif column_options[i] == 'center':
                        align_chr = '^'
            out_columns.append('{0:{1}{2}}'.format(c, align_chr, column_details[i]['width']))
        return spacing_str.join(out_columns)

    out = []
    for r in srows:
        out.append(align_row(r))
    return out


def print_rows(rows, column_options=None, spacing=1, header=None, enabled_rows=set(), **kwargs):
    # TODO **kwargs
    # Only print header if pretty
    if len(rows) < 1:
        return False

    if ArgFlags.pretty:
        aligned = align_columns(rows=rows, column_options=column_options, spacing=spacing, header=header)
        #print(aligned)
        if header:
            #### MODIFIED : header=True => arch=True, for the maximum arch like experience
            pprint(aligned[0], arch=True, bold=True, **kwargs)
            aligned.pop(0)
        for i, row in enumerate(aligned):
            pprint(row, enabled=(i in enabled_rows), **kwargs)
    else:
        for row in rows:
            print('{}'.format(' '.join(stringify(row))))

    return True
### END OF COPY


ARCH_NEWS = 'https://www.archlinux.org/feeds/news'

def main(argv):
    args = docopt(__doc__, argv)
    #print(args)
    ArgFlags.from_args(args)
    if ArgFlags.verbose:
        print(args)

    r = requests.get(ARCH_NEWS)
    xml = r.text

    soup = BeautifulSoup(xml, 'xml')
    items = soup.findAll('item')

    pprint(":: News", bold=True)
    header = ['Published', 'Title', 'URL']
    rows = [[i.pubDate.text, i.title.text, i.link.text] for i in items[:int(args['--limit'] or -1)]]
    print_rows(rows, spacing=3, header=header)

if __name__ == '__main__':
    main(sys.argv[1:])
