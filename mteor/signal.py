#!/usr/bin/env python

import logging
import os
from pprint import pformat

import numpy as np
import scipy.stats as scs


class SignalDetector(object):
    def __init__(self, signal_ema_span=1024, significance_level=0.01):
        self.__logger = logging.getLogger(__name__)
        self.signal_ema_span = signal_ema_span
        self.significance_level = significance_level
        self.__logger.debug('vars(self):' + os.linesep + pformat(vars(self)))

    def detect(self, df_tick, position_side=None):
        df_sig = self._calculate_sharpe_ratio(
            df_lrr=self._calculate_log_return_rate(
                df_tick=df_tick, span=self.signal_ema_span
            ),
            span=self.signal_ema_span
        )
        sig = (
            df_sig.iloc[-1].to_dict() if df_sig.shape[0] > 0
            else {c: np.nan for c in df_sig.columns}
        )
        emlrr_ci = self._calculate_ci(
            alpha=(1 - self.significance_level), df=(self.signal_ema_span - 1),
            loc=sig['lrr_ema'], scale=sig['lrr_emse']
        )
        emsr_ci = self._calculate_ci(
            alpha=(1 - self.significance_level), df=(self.signal_ema_span - 1),
            loc=sig['sr_ema'], scale=sig['sr_emse']
        )
        if emlrr_ci[0] > 0 and emsr_ci[0] > 0:
            act = 'long'
        elif emlrr_ci[1] < 0 and emsr_ci[1] < 0:
            act = 'short'
        elif ((position_side == 'short'
               and ((emlrr_ci[0] > 0 and sig['sr_ema'] > 0)
                    or (emsr_ci[0] > 0 and sig['lrr_ema'] > 0)))
              or (position_side == 'long'
                  and ((emlrr_ci[1] < 0 and sig['sr_ema'] < 0)
                       or (emsr_ci[1] < 0 and sig['lrr_ema'] < 0)))):
            act = 'closing'
        else:
            act = None
        return {
            'act': act, **sig,
            'emlrr_ci_lower': emlrr_ci[0],
            'emlrr_ci_upper': emlrr_ci[1],
            'emsr_ci_lower': emsr_ci[0], 'emsr_ci_upper': emsr_ci[1],
            'log_str': '{0:^38}|{1:^34}|'.format(
                'EMLRR:{0:>10}{1:>18}'.format(
                    '{:.1g}'.format(emlrr_ci.mean()),
                    np.array2string(
                        emlrr_ci,
                        formatter={'float_kind': lambda f: f'{f:.1g}'}
                    )
                ),
                'EMSR:{0:>9}{1:>16}'.format(
                    '{:.1g}'.format(emsr_ci.mean()),
                    np.array2string(
                        emsr_ci, formatter={'float_kind': lambda f: f'{f:.1g}'}
                    )
                )
            )
        }

    @staticmethod
    def _calculate_log_return_rate(df_tick, span):
        return df_tick.reset_index().assign(
            mid=lambda d: d[['ask', 'bid']].mean(axis=1),
            delta_sec=lambda d: d['time_msc'].diff().dt.total_seconds()
        ).set_index('time_msc').assign(
            lrr=lambda d: (np.log(d['mid']).diff() / d['delta_sec'])
        ).assign(
            lrr_ema=lambda d: d['lrr'].ewm(span=span, adjust=False).mean(),
            lrr_emse=lambda d:
            np.sqrt(d['lrr'].ewm(span=span, adjust=False).var(ddof=1) / span)
        )

    @staticmethod
    def _calculate_sharpe_ratio(df_lrr, span):
        return df_lrr.assign(
            return_rate=lambda d: (np.exp(d['log_return']) - 1),
            spread_ratio=lambda d: (1 - ((d['ask'] - d['bid']) / d['mid']))
        ).assign(
            sr=lambda d: (
                d['return_rate'] * d['spread_ratio']
                / d['return_rate'].rolling(window=span).std(ddof=1)
            )
        ).assign(
            sr_ema=lambda d: d['sr'].ewm(span=span, adjust=False).mean(),
            sr_emse=lambda d:
            np.sqrt(d['sr'].ewm(span=span, adjust=False).var(ddof=1) / span)
        )

    @staticmethod
    def _calculate_ci(*args, **kwargs):
        return np.array(scs.t.interval(*args, **kwargs))
