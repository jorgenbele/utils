#!/usr/bin/env python3
"""
Usage: ovsys [options] <command> [-a] [<args>...]

Options:
  --pretty
  --terse
  -v, --verbose                      Enable verbose output
  --config <configpath>              Override the default config path (~/.ovsys.json)
  --username <username>              Use username provided instead of from config
  --password <password>              Use password provided instead of from config
  --email-username <email-username>  Use email username provided instead of from config
  --email-password <email-password>  Use email password provided instead of from config
  --email-recipient <email-recipient>
  --email-sender <email-sender>
  --email-host <email-host>
  --email-port <email-port>
  --email-subject-format <email-subject-format>

Commands:
   ls|list [-a] <courses>            Displays a list of all courses
   daemon <courses>                  Sends an email when one of the courses changes
"""

# Author: Jørgen Bele Reinfjell
# Description: Command-line utility to ease use of the ovsys2
# Date: 26.01.2019 [dd.mm.yyyy]

from bs4 import BeautifulSoup as BS
from docopt import docopt
import json, re, requests, sys, os
from collections import defaultdict
from datetime import datetime

OVSYS_BASE_URL = 'https://ovsys.math.ntnu.no'

class ovsys:
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,nb;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'DNT': '1',
        'Referer': OVSYS_BASE_URL,
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
    }

    cached_frontpage_html = None

    session = None
    csrfmiddlewaretoken = None

    def __init__(self):
        pass

    def initialize_session(self):
        self.session = requests.session()
        r = self.session.get(OVSYS_BASE_URL, headers=self.headers)
        str_find = 'csrfmiddlewaretoken: \''
        mwtoken_start = r.text.find(str_find) + len(str_find)
        mwtoken_end = r.text.find('\'', mwtoken_start)
        self.csrfmiddlewaretoken = r.text[mwtoken_start:mwtoken_end]
        return True

    def login(self, username, password, next_url='/'):
        if not self.session:
            # User has not called initialize_session
            return None

        data = {
            'csrfmiddlewaretoken': self.csrfmiddlewaretoken,
            'username': username,
            'password': password,
            'next': next_url
        }
        r = self.session.post(OVSYS_BASE_URL + '/login/', data=data, headers=self.headers)

        self.cached_frontpage_html = r.text
        return r

    def __get(self, url_suffix=''):
        r = self.session.get(OVSYS_BASE_URL + url_suffix, headers=self.headers)
        return r

    def __update_cached_frontpage(self):
        self.cached_frontpage_html = self.__get().text

    def get_classes_urls(self):
        if not self.cached_frontpage_html:
            self.__update_cached_frontpage()
        bs = BS(self.cached_frontpage_html, features='lxml')
        classes_links = [link.get('href') for link in bs.findAll('a') if re.search('^/student/', link.get('href'))]
        return classes_links

    __status_states_list = ['delivered', 'corrected', 'graded']
    status_states = {
        'delivered': {'levert': True, 'ikke levert': False},
        'corrected': {'rettet': True, 'ikke rettet': False},
        'graded':    {'godkjent': 'pass', 'underkjent': 'fail', 'ikke vurdert': '----'},
    }

    def __status_str_to_table(self, status):
        start_index = status.find('status: ') + len('status: ')
        split_ = [x.strip().lower() for x in status[start_index:].split(',')]
        states = {}
        for i, v in enumerate(self.__status_states_list):
            if split_[i] in self.status_states[v].keys():
                states[self.__status_states_list[i]] = self.status_states[v][split_[i]]
            else:
                print('MALFORMED INPUT!', i, split_[i]) # TODO
                return None
        return states

    def get_class_exercises(self, class_url):
        r = self.__get(class_url)
        bs = BS(r.text, features='lxml')
        exercises_elems = [link for link in bs.findAll('a') if re.search('/exercise/', link.get('href'))]
        ret = []
        for elem in exercises_elems:
            elem_data = {'id': None, 'name': None, 'status': None}
            elem_data['id'] = elem.get('href').split('/')[-1]
            elem_data['name'] = (elem.findAll('div', class_='col-xs-12 col-sm-6 col-md-8')[0].find('strong').text)
            #elem_data['status'] = (elem.findAll('div', class_='col-xs-12 col-sm-6 col-md-4')[0].text.strip())
            elem_data['status'] = self.__status_str_to_table((elem.findAll('div', class_='col-xs-12 col-sm-6 col-md-4')[0].text.strip()))
            ret.append(elem_data)
        return ret

    @staticmethod
    def class_url_to_code(class_name):
        return class_name.split('/')[2]

#
def gen_msg(config, changed):
    s = ''
    for e in changed:
        s += str(e)
    return s

# MAIL
import smtplib
def send_mail(config, msg):
    email = config['email']
    print('email:', email)
    server = smtplib.SMTP(email['host'], email['port'])
    server.ehlo()
    server.starttls()

    #Next, log in to the server
    server.login(email['username'], email['password'])

    #Send the mail
    server.sendmail(email['sender'], email['recipient'], msg)
    print(datetime.now(), 'SENT EMAIL')

# CLI UTILITY
DEFAULT_CONFIG_PATH = os.path.expanduser('~/.ovsys.json')
config = {
    'ovsys': {
        'username': None,
        'password': None,
    },
    'email': {
        'username': None,
        'password': None,
        'recipient': None,
        'sender': None,
        'host': None,
        'port': None,
        'subject_format': 'OVSYS2: {class_code} changed',
    }
}

def load_config(path=DEFAULT_CONFIG_PATH):
    global config
    with open(path) as f:
        #data = defaultdict(None, json.load(f))
        data = json.load(f)
        config = data
        #print('loaded', config)
    return True

def get_matches(ovsys, args):
    class_urls = ovsys.get_classes_urls()
    matches = []

    if len(args['<args>']) == 0:
        matches = class_urls
    else:
        for arg in args['<args>']:
            c_matches = [url for url in class_urls if re.search(arg, url)]
            matches += c_matches
    return matches


def main(argv):
    global config
    args = docopt(__doc__, argv)
    ArgFlags.from_args(args)
    if ArgFlags.verbose:
        print(args)

    if args['--config']:
        assert load_config(os.path.expanduser(args['--config']))
    else:
        load_config()

    # These flags override the config file
    # ovsys
    for key in config['ovsys'].keys():
        if args['--' + key]:
            config['ovsys'][key] = args['--' + key]

    # email
    for key in config['email'].keys():
        if args['--email-' + key.replace('_', '-')]:
            config['email'][key] = args['--email-' + key]

    assert config['ovsys']['username'] and config['ovsys']['password']

    o = ovsys()
    assert o.initialize_session()
    assert o.login(config['ovsys']['username'], config['ovsys']['password'])

    headers = []
    rows = []
    show_all = False
    if args['-a']:
        show_all = True

    if args['<command>'] in ('list', 'ls'):
        matches = get_matches(o, args)
        for url in matches:
            class_code = ovsys.class_url_to_code(url)
            pprint(class_code + (':' if show_all else ''), bold=True)

            if show_all:
                headers =  ['Exercise', 'Del', 'Cor', 'Res']
                col_opts = ['left', 'center', 'center', 'center']
                enabled_rows = set()
                rows = []
                for i, elem in enumerate(o.get_class_exercises(url)):
                    s = elem['status']
                    yes_no = lambda b: ('yes' if b else 'no') if type(b) == bool else b
                    #yes_no = lambda b: b
                    maybe_quote = lambda s: '"{}"'.format(s) if not ArgFlags.pretty else s
                    #maybe_quote = lambda s: s
                    rows.append([maybe_quote(elem['name']), yes_no(s['delivered']), yes_no(s['corrected']), yes_no(s['graded'])])
                    if s['graded'] == 'pass':
                        enabled_rows.add(i)
                print_rows(rows, spacing=3, header=headers, enabled_rows=enabled_rows, column_options=col_opts)
                print()

    elif args['<command>'] == 'daemon':
        matches = get_matches(o, args)
        prev_state = [] # list of results of class_exercises()
        print('Watching:', matches)
        while True:
            for url in matches:
                class_code = ovsys.class_url_to_code(url)
                pprint(class_code + (':' if show_all else ''), bold=True)
                exercises = o.get_class_exercises(url)
                if state != prev_state:
                    # TODO
                    print('CHANGED')
                    print('STATE', state)
                    msg = gen_msg(config, ['test1', 'test2'])
                    send_mail(config, msg)
                print('DID NOT CHANGE')
            sleep(10)

    else:
        print('No such command: `{}`'.format(args['<command>']))
        sys.exit(1)


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

#def pprint(fargs, *args, word_wrap=True, warning=False, bold=False, success=False, enabled=False, fatal=False, header=False, **kwargs):

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
        #elif header:
        #    color_str = escape('[33m') # orange
        #elif arch:
        elif header:
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
            pprint(aligned[0], arch=True, header=True, **kwargs)
            aligned.pop(0)
        for i, row in enumerate(aligned):
            pprint(row, enabled=(i in enabled_rows), **kwargs)
    else:
        for row in rows:
            print('{}'.format(' '.join(stringify(row))))

    return True
### END OF COPY


if __name__ == "__main__":
    main(sys.argv[1:])
