#!/usr/bin/env python

import logging
import os
from pprint import pformat

import numpy as np
import scipy.stats as scs


class EwmaSignalDetector(object):
    def __init__(self, ema_span=1000, significance_level=0.01,
                 trigger_sharpe_ratio=1):
        self.__logger = logging.getLogger(__name__)
        self.ema_span = ema_span
        self.significance_level = significance_level
        self.trigger_sharpe_ratio = trigger_sharpe_ratio
        self.__logger.debug('vars(self):' + os.linesep + pformat(vars(self)))

    def detect(self, df_tick, position_side=None):
        pass
