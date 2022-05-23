#!/usr/bin/env python

import logging
import os
from pprint import pformat

import MetaTrader5 as Mt5
import pandas as pd


class BettingSystem(object):
    def __init__(self, strategy='Martingale'):
        self.__logger = logging.getLogger(__name__)
        strategies = [
            'Martingale', 'Paroli', "d'Alembert", 'Pyramid', "Oscar's grind",
            'Constant'
        ]
        matched_strategy = [
            s for s in strategies if (
                strategy.lower().replace("'", '').replace(' ', '')
                == s.lower().replace("'", '').replace(' ', '')
            )
        ]
        if matched_strategy:
            self.strategy = matched_strategy[0]
        else:
            raise ValueError(f'invalid strategy: {strategy}')
        self.__logger.debug('vars(self):' + os.linesep + pformat(vars(self)))

    def calculate_volume_by_pl(self, unit_volume, history_deals,
                               init_volume=None):
        deals = [
            d for d in history_deals
            if d.type in {Mt5.DEAL_TYPE_BUY, Mt5.DEAL_TYPE_SELL}
        ]
        assert all([d.volume > 0 for d in deals])
        last_volume = (deals[-1].volume if deals else 0)
        self.__logger.debug(f'last_volume: {last_volume}')
        if not deals:
            return last_volume or init_volume or unit_volume
        else:
            pl = pd.Series([d.profit for d in deals], dtype=float)
            if pl.iloc[-1] < 0:
                won_last = False
            elif pl.iloc[-1] > 0 and pl[-2:].sum() > 0:
                won_last = True
            else:
                won_last = None
            self.__logger.debug(f'won_last: {won_last}')
            return self._calculate_volume(
                unit_volume=unit_volume, init_volume=init_volume,
                last_volume=last_volume, won_last=won_last,
                all_time_high=(pl.cumsum().idxmax() == pl.index[-1])
            )

    def _calculate_volume(self, unit_volume, init_volume=None,
                          last_volume=None, won_last=None,
                          all_time_high=False):
        if won_last is None:
            return last_volume or init_volume or unit_volume
        elif self.strategy == 'Martingale':
            return (unit_volume if won_last else last_volume * 2)
        elif self.strategy == 'Paroli':
            return (last_volume * 2 if won_last else unit_volume)
        elif self.strategy == "d'Alembert":
            return (unit_volume if won_last else last_volume + unit_volume)
        elif self.strategy == 'Pyramid':
            if not won_last:
                return (last_volume + unit_volume)
            elif last_volume < unit_volume:
                return last_volume
            else:
                return (last_volume - unit_volume)
        elif self.strategy == "Oscar's grind":
            self.__logger.debug(f'all_time_high: {all_time_high}')
            if all_time_high:
                return init_volume or unit_volume
            elif won_last:
                return (last_volume + unit_volume)
            else:
                return last_volume
        elif self.strategy == 'Constant':
            return unit_volume
        else:
            raise ValueError(f'invalid strategy: {self.strategy}')
