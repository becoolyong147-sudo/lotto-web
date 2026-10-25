# -*- coding: utf-8 -*-
"""
dragon_pick.py — 龙系(豪龙/9龙)「数字偏爱」选号
看过去 500 期头二三: 数字、打数、前2D、后2D 哪些常开 → 给每个号码打分 → 取最高 500 个。
回测(倒回去每期只用当时以前的资料, 1000期): 豪龙 中197 vs 随便143; 9龙 中178 vs 随便143; 两半都赢。其他家看不出效果, 所以只给龙系用。
"""
import numpy as np, math
CAP, WIN = 500, 500
NUM = np.arange(10000)
DIG = np.stack([NUM // 1000 % 10, NUM // 100 % 10, NUM // 10 % 10, NUM % 10], 1)
HAS = np.stack([(DIG == d).any(1) for d in range(10)], 1)
_DA = {(1, 1, 1, 1): 0, (2, 1, 1): 1, (2, 2): 2, (3, 1): 3, (4,): 4}
DA = np.array([_DA[tuple(sorted([list(r).count(c) for c in set(r)], reverse=True))] for r in DIG])
F2, B2 = DIG[:, 0] * 10 + DIG[:, 1], DIG[:, 2] * 10 + DIG[:, 3]
LABS = [(DA, 1.0), (F2, 0.5), (B2, 0.5)]
SH = [np.bincount(l) / 10000 for l, _ in LABS]
HSH = HAS.mean(0)


def score(draws, t):
    """用 draws[t-WIN:t] 给 10000 个号码打分; draws 是 [(日期, [头,二,三])]"""
    nums = np.array([int(n) for _, ns in draws[max(0, t - WIN):t] for n in ns]); N = len(nums)
    sc = (HAS * np.log((HAS[nums].sum(0) + 1) / (N * HSH + 1))).sum(1)
    for (lab, a), sh in zip(LABS, SH):
        cnt = np.bincount(lab[nums], minlength=len(sh))
        sc = sc + np.log((cnt + a) / (N * sh + a))[lab]
    return sc


def pick(draws, t=None, cap=CAP):
    t = len(draws) if t is None else t
    sc = score(draws, t)
    idx = np.argsort(-sc, kind="stable")[:cap]
    return ["%04d" % i for i in idx]


def backtest(draws, n=500, cap=CAP):
    hit = exp = 0; rows = []
    for t in range(len(draws) - n, len(draws)):
        s = set(pick(draws, t, cap)); got = [x for x in draws[t][1] if x in s]
        hit += bool(got); exp += 1 - (1 - cap / 10000) ** 3
        rows.append((draws[t][0], draws[t][1], got))
    return hit, exp, rows
