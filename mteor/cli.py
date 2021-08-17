#!/usr/bin/env python
"""
Automated Trader using MetaTrader 5

Usage:
    mteor -h|--help
    mteor --version

Options:
    -h, --help              Print help and exit
    --version               Print version and exit
"""

import logging
import os

from docopt import docopt
from oandacli.util.logger import set_log_config

from . import __version__


def main():
    args = docopt(__doc__, version=f'mteor {__version__}')
    set_log_config(debug=args['--debug'], info=args['--info'])
    logger = logging.getLogger(__name__)
    logger.debug(f'args:{os.linesep}{args}')
