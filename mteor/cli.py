#!/usr/bin/env python
"""
Automated Trader using MetaTrader 5

Usage:
  mteor mt5 [--mt5-exe=<path>] [--mt5-login=<str>] [--mt5-password=<str>]
    [--mt5-server=<str>]
  mteor -h|--help
  mteor --version

Options:
  --mt5-exe=<path>      Specify a path to a MetaTrader 5 (MT5) exe file
  --mt5-login=<str>     Specify a MT5 trading account number
  --mt5-password=<str>  Specify a MT5 trading account password
  --mt5-server=<str>    Specify a MT5 trade server name
  -h, --help            Print help and exit
  --version             Print version and exit
"""

import logging
import os

import MetaTrader5 as Mt5
from docopt import docopt
from oandacli.util.logger import set_log_config

from . import __version__


def main():
    args = docopt(__doc__, version=f'mteor {__version__}')
    set_log_config(debug=args['--debug'], info=args['--info'])
    logger = logging.getLogger(__name__)
    logger.debug(f'args:{os.linesep}{args}')
    if args['mt5']:
        print('MetaTrader5 package author: ', Mt5.__author__)
        print('MetaTrader5 package version: ', Mt5.__version__)
        initialize_kwargs = {
            k: v for k, v in [
                ('path', args['--mt5-exe']), ('login', args['--mt5-login']),
                ('password', args['--mt5-password']),
                ('server', args['--mt5-server'])
            ] if v is not None
        }
        if not Mt5.initialize(**initialize_kwargs):
            raise RuntimeError(
                'MetaTrader5.initialize() failed, error code =',
                Mt5.last_error()
            )
        print(Mt5.terminal_info())
        print(Mt5.version())
        Mt5.shutdown()
