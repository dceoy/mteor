#!/usr/bin/env python
"""
Automated Trader using MetaTrader 5

Usage:
  mteor -h|--help
  mteor --version
  mteor mt5 [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>]

Options:
  -h, --help            Print help and exit
  --version             Print version and exit
  --debug, --info       Execute a command with debug|info messages
  --mt5-exe=<path>      Specify a path to a MetaTrader 5 (MT5) exe file
  --mt5-login=<str>     Specify a MT5 trading account number
  --mt5-password=<str>  Specify a MT5 trading account password
  --mt5-server=<str>    Specify a MT5 trade server name
"""

import logging
import os

import MetaTrader5 as Mt5
from docopt import docopt

from . import __version__


def main():
    args = docopt(__doc__, version=f'mteor {__version__}')
    _set_log_config(debug=args['--debug'], info=args['--info'])
    logger = logging.getLogger(__name__)
    logger.debug(f'args:{os.linesep}{args}')
    if args['mt5']:
        print('MetaTrader5 package author: ', Mt5.__author__)
        print('MetaTrader5 package version: ', Mt5.__version__)
        initialize_kwargs = {
            **({'path': args['--mt5-exe']} if args['--mt5-exe'] else dict()),
            **(
                {'login': int(args['--mt5-login'])}
                if args['--mt5-login'] else dict()
            ),
            **(
                {'password': args['--mt5-password']}
                if args['--mt5-password'] else dict()
            ),
            **(
                {'server': args['--mt5-server']}
                if args['--mt5-server'] else dict()
            )
        }
        if not Mt5.initialize(**initialize_kwargs):
            raise RuntimeError(
                'MetaTrader5.initialize() failed, error code =',
                Mt5.last_error()
            )
        print(Mt5.terminal_info())
        print(Mt5.version())
        Mt5.shutdown()


def _set_log_config(debug=None, info=None):
    if debug:
        lv = logging.DEBUG
    elif info:
        lv = logging.INFO
    else:
        lv = logging.WARNING
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S', level=lv
    )
