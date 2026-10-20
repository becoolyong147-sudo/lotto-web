# -*- coding: utf-8 -*-
"""
cond_report.py — ④ 热形态主杆选号(用户的条件), 每一步都只用当期之前的资料
  主杆   : 最近 30 天 头/二/三 各自开最多的「4D点数段」, 有 ≥2 个奖位相同的 → 那段就是主杆;
           没有相同 → 用三个奖位合起来开最多的那段
  前3D   : 最近 30 天偏多(z≥2)的前3D点数段;没有偏多就不限
  打数   : 24打 + 12打;如果这家最近一年 24打 ≥54%(9龙常年如此) → 只要 24打
  冷热   : 只要 🔥热门 / 🔵中性 号码(跟「我的功课」同一个算法), ❄️冷门不要
  2D     : 号码至少有一段落在三种 2D(主打/混合数根/数根分前后)的推荐里
回测: 最近 300 期逐期照做, 下期头二三有没有中 vs 随便买同样个数
"""
import sys, os
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trend_report as TR
import picks_report as PR

FP, F3, DA = TR.DIMS["点数"], TR.DIMS["前3D点数"], TR.DIMS["打数"]
NUMS = ["%04d" % q for q in range(10000)]
CAP = 500                               # 一期最多 500 个(2D 对上段数多的优先)
LAB = [(FP(n), F3(n), DA(n)[:3]) for n in NUMS]


class Hot:
    """hotOf: 距上次开出的期数 / 平均间隔 ≤0.5 热, ≥1.5 冷"""
    def __init__(self):
        self.cn = [0] * 10000; self.fi = [-1] * 10000; self.li = [-1] * 10000; self.cur = 0

    def add(self, nums):
        for n in nums:
            q = int(n)
            if self.fi[q] < 0: self.fi[q] = self.cur
            self.li[q] = self.cur; self.cn[q] += 1
        self.cur += 1

    def tier(self, q):
        if self.cn[q] >= 2:
            avg = (self.li[q] - self.fi[q]) / (self.cn[q] - 1)
            r = (self.cur - self.li[q]) / avg if avg > 0 else 0
            return "hot" if r <= 0.5 else ("cold" if r >= 1.5 else "mid")
        return "mid"


def conditions(draws, i):
    d = draws[i]["date"]
    cut = (date.fromisoformat(d) - timedelta(days=30)).isoformat()
    win = [x for x in draws[max(0, i - 60):i + 1] if x["date"] >= cut]
    per = []
    for p in range(3):
        c = {}
        for x in win:
            l = FP(x["nums"][p]); c[l] = c.get(l, 0) + 1
        per.append(max(sorted(c.items()), key=lambda t: t[1])[0])
    same = [l for l in set(per) if per.count(l) >= 2]
    if same:
        main, why = same[0], f"头二三最多的点数段:{'/'.join(per)} → 相同的 {same[0]} 做主杆"
    else:
        c = {}
        for x in win:
            for n in x["nums"]:
                l = FP(n); c[l] = c.get(l, 0) + 1
        main = max(sorted(c.items()), key=lambda t: t[1])[0]
        why = f"头二三最多的点数段:{'/'.join(per)} 都不一样 → 用合起来最多的 {main}"
    nums = [n for x in win for n in x["nums"]]
    N = len(nums)
    c3 = {}
    for n in nums:
        l = F3(n); c3[l] = c3.get(l, 0) + 1
    f3 = {l for l, sh in TR.SHARE["前3D点数"].items() if TR.z(c3.get(l, 0), N * sh, N) >= 2}
    yr = (date.fromisoformat(d) - timedelta(days=365)).isoformat()
    ny = [n for x in draws[max(0, i - 400):i + 1] if x["date"] >= yr for n in x["nums"]]
    s24 = sum(1 for n in ny if DA(n).startswith("24")) / max(len(ny), 1)
    das = {"24打"} if s24 >= 0.54 else {"24打", "12打"}
    return main, f3, das, why, s24


def pick(draws, i, hot):
    main, f3, das, why, s24 = conditions(draws, i)
    recs = [r for r in (PR.recs_at(draws, i, k) for k, _ in PR.METHODS) if r is not None]
    def go(f3):
        out = []
        for q in range(10000):
            fp, f3l, da = LAB[q]
            if fp != main or da not in das or (f3 and f3l not in f3):
                continue
            n = NUMS[q]
            m = sum(PR.score(n, r) for r in recs)
            if m == 0 or hot.tier(q) == "cold":
                continue
            out.append((m, n))
        return out
    out = go(f3)
    if not out and f3:                      # 条件互相冲突(例如 17-20点 + 前3D 23-27)→ 放掉前3D
        f3 = set(); out = go(f3)
    out.sort(key=lambda t: (-t[0], t[1]))
    return [n for _, n in out[:CAP]], main, f3, das, why, s24


def run(draws, bt=300):
    hot = Hot()
    start = max(1, len(draws) - bt - 1)
    for x in draws[:start]:
        hot.add(x["nums"])
    rows, hit, exp, sz = [], 0, 0.0, 0
    for i in range(start, len(draws)):
        hot.add(draws[i]["nums"])
        if i == len(draws) - 1:
            break
        lst = pick(draws, i, hot)[0]
        s = set(lst); nxt = draws[i + 1]["nums"]
        got = [n for n in nxt if n in s]
        rows.append({"date": draws[i + 1]["date"], "nums": nxt, "got": got, "size": len(lst)})
        hit += bool(got); exp += 1 - (1 - len(lst) / 10000) ** 3; sz += len(lst)
    now = pick(draws, len(draws) - 1, hot)
    return now, {"n": len(rows), "hit": hit, "exp": exp, "avg": sz / max(len(rows), 1), "rows": rows}


def main():
    data = PR.load()
    for mk in sys.argv[1:] or PR.MARKETS:
        dr_ = data.get(mk, [])
        (lst, main_, f3, das, why, s24), bt = run(dr_)
        print(f"\n【{mk}】最新 {dr_[-1]['date']}  {why}")
        print(f"  前3D偏多:{'、'.join(sorted(f3)) or '没有(不限)'}  打数:{'+'.join(sorted(das))}(最近一年24打占 {s24*100:.0f}%)  冷门不要")
        print(f"  ④ 号码 {len(lst)} 个: {' '.join(lst[:40])}{' …' if len(lst) > 40 else ''}")
        print(f"  回测 {bt['n']} 期,平均每期 {bt['avg']:.0f} 个,中头二三 {bt['hit']} 期;随便买同样个数约 {bt['exp']:.1f} 期")


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
