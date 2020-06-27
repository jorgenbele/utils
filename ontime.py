#!/bin/env python3
# Author: Jørgen Bele Reinfjell
# Date: at some point in 2018
# Description:
#  Runs a command at a given time in
#  the future. Useful once in a while.
"""
Usage: ontime [options] <timestamp> <command>

Options:
   --timezone <timezone>
"""

from docopt import docopt
import arrow
import sys
import time
import subprocess
import shlex

def run_command(command):
    cmd_split = shlex.split(command)

    print('Running command', cmd_split, file=sys.stderr)
    subprocess.call(cmd_split)


def main():
    args = docopt(__doc__)
    print(args)

    timezone = args.get('<timezone>',  'Europe/Oslo')
    timestamp = arrow.get(args['<timestamp>'], 'DD.MM.YY H:m').replace(tzinfo=timezone)
    command = args['<command>']

    print('Timezone:', timezone)
    print('Timestamp:', timestamp)
    now = arrow.now(timezone)
    print('Now', now)
    
    if now > timestamp:
        print('Time set in the past, QUITTING!')
        sys.exit(1)
    
    print('Sleeping for', timestamp - now)
    time.sleep((timestamp - now).seconds)

    run_command(command)

if __name__ == '__main__':
    main()
