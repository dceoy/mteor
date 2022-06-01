#!/usr/bin/env python

import logging
import os
from pprint import pformat

import numpy as np
import scipy.stats as scs


class SignalDetector(object):
    def __init__(self, lrr_ema_span=1000, sr_ema_span=1000,
                 significance_level=0.01):
        self.__logger = logging.getLogger(__name__)
        self.lrr_ema_span = lrr_ema_span
        self.sr_ema_span = sr_ema_span
        self.significance_level = significance_level
        self.__logger.debug('vars(self):' + os.linesep + pformat(vars(self)))

    def detect(self, df_tick, position_side=None):
        df_sig = self._calculate_log_return_rate(
            df_sr=self._calculate_sharpe_ratio(
                df_tick=df_tick, span=self.sr_ema_span
            ),
            span=self.lrr_ema_span
        )
        sig = (
            df_sig.iloc[-1].to_dict() if df_sig.shape[0] > 0
            else {c: np.nan for c in df_sig.columns}
        )
        self.__logger.debug(f'sig: {sig}')
        lrr_ema_ci = self._calculate_ci(
            alpha=(1 - self.significance_level), df=(self.lrr_ema_span - 1),
            loc=sig['lrr_ema'], scale=sig['lrr_emse']
        )
        self.__logger.debug(f'lrr_ema_ci: {lrr_ema_ci}')
        sr_ema_ci = self._calculate_ci(
            alpha=(1 - self.significance_level),
            df=(self.sr_ema_span - 1), loc=sig['sr_ema'],
            scale=sig['sr_emse']
        )
        self.__logger.debug(f'sr_ema_ci: {sr_ema_ci}')
        if ((sr_ema_ci[0] > 0 and lrr_ema_ci[1] > 0)
                or (lrr_ema_ci[0] > 0 and sr_ema_ci[1] > 0)):
            act = 'long'
        elif ((sr_ema_ci[1] < 0 and lrr_ema_ci[0] < 0)
              or (lrr_ema_ci[1] < 0 and sr_ema_ci[0] < 0)):
            act = 'short'
        elif ((position_side == 'short'
               and ((sig['lrr_ema'] > 0 and sig['sr_ema'] > 0)
                    or lrr_ema_ci[0] > 0 or sr_ema_ci[0] > 0))
              or (position_side == 'long'
                  and ((sig['lrr_ema'] < 0 and sig['sr_ema'] < 0)
                       or lrr_ema_ci[1] < 0 or sr_ema_ci[1] < 0))):
            act = 'closing'
        else:
            act = None
        self.__logger.debug(f'act: {act}')
        return {
            'act': act, **sig, 'lrr_ema_ci_lower': lrr_ema_ci[0],
            'lrr_ema_ci_upper': lrr_ema_ci[1], 'sr_ema_ci_lower': sr_ema_ci[0],
            'sr_ema_ci_upper': sr_ema_ci[1],
            'log_str': '{0:^36}|{1:^32}|'.format(
                'LRR:{0:>10}{1:>18}'.format(
                    '{:.1g}'.format(sig['lrr_ema']),
                    np.array2string(
                        lrr_ema_ci,
                        formatter={'float_kind': lambda f: f'{f:.1g}'}
                    )
                ),
                'SR:{0:>9}{1:>16}'.format(
                    '{:.1g}'.format(sig['sr_ema']),
                    np.array2string(
                        sr_ema_ci,
                        formatter={'float_kind': lambda f: f'{f:.1g}'}
                    )
                )
            )
        }

    @staticmethod
    def _calculate_sharpe_ratio(df_tick, span):
        return df_tick.assign(
            log_return=lambda d: np.log(d[['ask', 'bid']].mean(axis=1)).diff(),
            delta_sec=lambda d: d.index.to_series().diff().dt.total_seconds()
        ).assign(
            log_return_rate=lambda d: (
                d['log_return'] / d['delta_sec']
                * d['tick_volume'] / d['tick_volume'].mean()
            )
        ).assign(
            pl_ratio=lambda d: (np.exp(d['log_return_rate']) - 1)
        ).assign(
            sharpe_ratio=lambda d: (
                d['pl_ratio'] * d['bid'] / d['ask']
                / d['pl_ratio'].rolling(window=span).std(ddof=1)
            )
        ).assign(
            sr_ema=lambda d:
            d['sharpe_ratio'].ewm(span=span, adjust=False).mean(),
            sr_emse=lambda d: np.sqrt(
                d['sharpe_ratio'].ewm(span=span, adjust=False).var(ddof=1)
                / span
            )
        )

    @staticmethod
    def _calculate_log_return_rate(df_sr, span):
        return df_sr.assign(
            lrr_ema=lambda d:
            d['log_return_rate'].ewm(span=span, adjust=False).mean(),
            lrr_emse=lambda d: np.sqrt(
                d['log_return_rate'].ewm(span=span, adjust=False).var(ddof=1)
                / span
            )
        )

    @staticmethod
    def _calculate_ci(*args, **kwargs):
        return np.array(scs.t.interval(*args, **kwargs))
