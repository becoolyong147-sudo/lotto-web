# -*- coding: utf-8 -*-
"""
picks_report.py — 下一期选号报告(三种 2D 来源), 算法跟 lottery.html 一样(全站统一的 ABS2D)
  ① 下一期主打  : ABS2D.B, 用最新一期「特别奖 10 个」算前/中/后 2D 目标
  ② 混合数根    : ABS2D.A mix, 数根用最近 2 期头二三(前后合并缺根), 1D 用最新一期头二三, 前2D/后2D 双缺
  ③ 数根分前后  : ABS2D.A split, 前/中/后 各自缺根 + 双缺
出号: 一个 4D 号码里有几段(前/中/后)落在推荐 2D 里 = 几分; 「我的号码」= 至少 2 段对上的。
最满意: 三种方法加起来得分最高的(各方法都对上的优先), 再按最近 1 个月形态走势(trend_report)不偏少的优先。
回测: 每一期只用那一期之前的资料, 看「我的号码」下期头二三有没有中, 跟「随便买同样个数」比。
用法: python picks_report.py            (输出 docs/picks/picks_日期.html + 终端简报)
"""
import json, os, sys, math, random
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import trend_report as TR

MARKETS = ["万能", "跑马", "多多", "新加坡", "豪龙", "9龙", "沙巴", "砂拉越"]
SEG = [(0, 2), (1, 3), (2, 4)]           # 前2D 中2D 后2D 在 4D 里的位置
SEGN = ["前", "中", "后"]
BT_DRAWS = 300                          # 回测最近几期


def dr(x):
    return 0 if x == 0 else (9 if x % 9 == 0 else x % 9)


# ---------- 统一算法(照抄 lottery.html ABS2D) ----------
def roots_absent(nums):
    pf, pm, pb = set(), set(), set()
    for s in nums:
        pf.add(dr(int(s[0]) + int(s[1]))); pm.add(dr(int(s[1]) + int(s[2]))); pb.add(dr(int(s[2]) + int(s[3])))
    r = range(1, 10)
    return {"F": {x for x in r if x not in pf}, "Mid": {x for x in r if x not in pm},
            "B": {x for x in r if x not in pb}, "M": {x for x in r if x not in pf and x not in pb}}


def digits_absent(nums):
    return [{d for d in range(10) if all(int(s[q]) != d for s in nums)} for q in range(4)]


def dbl(roots, a, b):
    return {"%d%d" % (u, v) for u in range(10) for v in range(10) if dr(u + v) in roots and u in a and v in b}


def method_A(prev2_top3, last_top3, mode):
    R, D = roots_absent(prev2_top3), digits_absent(last_top3)
    if mode == "mix":
        return [dbl(R["M"], D[0], D[1]), set(), dbl(R["M"], D[2], D[3])]
    return [dbl(R["F"], D[0], D[1]), dbl(R["Mid"], D[1], D[2]), dbl(R["B"], D[2], D[3])]


def method_B(sp):
    out = []
    for wa, wb in [(0, 1), (1, 2), (2, 3)]:
        roots = {dr(int(n[wa]) + int(n[wb])) for n in sp}
        a2 = [r for r in range(1, 10) if r not in roots]
        first = {}
        for n in sp:
            first[n[wa]] = first.get(n[wa], 0) + 1
        t1 = [str(d) for d in range(10) if str(d) not in first]
        if first:
            t1.append(max(first.items(), key=lambda t: t[1])[0])   # JS: 第一个出现次数最多的
        out.append({d1 + str(d2) for d1 in t1 for d2 in range(10) if dr(int(d1) + d2) in a2})
    return out


METHODS = [("zd", "① 下一期主打(特别奖)"), ("mix", "② 本期缺席 · 混合数根"), ("split", "③ 本期缺席 · 数根分前后")]


def load():
    sd = json.load(open(os.path.join(BASE, "slim_data.json"), encoding="utf-8"))["DB"]
    by = {}
    for mk, txt in sd.items():
        for line in (txt.splitlines() if isinstance(txt, str) else []):
            p = line.split(",")
            if len(p) >= 5:
                by[(mk, p[0][:10])] = {"nums": [x.zfill(4) for x in p[2:5]], "sp": []}
    for fn in ("small_prizes.json", "auto_results.json"):
        try:
            for x in json.load(open(os.path.join(BASE, fn), encoding="utf-8"))["draws"]:
                k = (x["market"], x["date"][:10])
                e = by.setdefault(k, {"nums": [], "sp": []})
                if fn == "auto_results.json" and len(x.get("nums") or []) >= 3:
                    e["nums"] = [str(v).zfill(4) for v in x["nums"][:3]]
                if x.get("sp"):
                    e["sp"] = [str(v).zfill(4) for v in x["sp"] if str(v).isdigit()]
        except Exception:
            pass
    out = {}
    for (mk, d), e in by.items():
        try: date.fromisoformat(d)
        except ValueError: continue          # 例如 xxxx-xx-00 这种坏日期
        if len(e["nums"]) == 3 and all(len(n) == 4 and n.isdigit() for n in e["nums"]):
            out.setdefault(mk, []).append({"date": d, "nums": e["nums"], "sp": [s for s in e["sp"] if len(s) == 4]})
    for mk in out:
        out[mk].sort(key=lambda x: x["date"])
    return out


def recs_at(draws, i, key):
    """用 draws[..i] (含 i) 算下一期的推荐 2D;不够资料返回 None"""
    if key == "zd":
        return method_B(draws[i]["sp"]) if len(draws[i]["sp"]) >= 3 else None
    if i < 1:
        return None
    return method_A(draws[i - 1]["nums"] + draws[i]["nums"], draws[i]["nums"], key)


def score(n, rec):
    return sum(1 for k, (a, b) in enumerate(SEG) if n[a:b] in rec[k])


def need(rec):
    """几段对上才算: 先要 2 段; 超过 600 个号码(你一期买约 500)且有中2D → 要 3 段都对上"""
    return 3 if rec[1] and count_ge(rec, 2) > 600 else 2


def my_numbers(rec):
    t = need(rec)
    return [n for n in ("%04d" % q for q in range(10000)) if score(n, rec) >= t]


def backtest(draws, key):
    rows, hit, exp, sz = [], 0, 0.0, 0
    start = max(1, len(draws) - BT_DRAWS - 1)
    for i in range(start, len(draws) - 1):
        rec = recs_at(draws, i, key)
        if rec is None:
            continue
        nxt = draws[i + 1]["nums"]
        # 不展开 10000 个号: 直接判下期头二三有没有在「至少2段对上」里
        t = need(rec)
        cnt2 = count_ge(rec, t)
        got = [n for n in nxt if score(n, rec) >= t]
        rows.append({"date": draws[i + 1]["date"], "size": cnt2, "got": got, "nums": nxt})
        sz += cnt2
        exp += 1 - (1 - cnt2 / 10000) ** 3
        if got:
            hit += 1
    return {"n": len(rows), "hit": hit, "exp": exp, "avg": sz / max(len(rows), 1), "rows": rows}


_C2 = {}


def count_ge(rec, t):
    key = (t,) + tuple(tuple(sorted(s)) for s in rec)
    if key in _C2:
        return _C2[key]
    f, m, b = rec
    c = 0
    # 数「至少 2 段对上」: 用 4 位逐个枚举太慢, 改按 (千百十个) 枚举 1 万次也只要 ~10ms
    for q in range(10000):
        n = "%04d" % q
        s = (n[0:2] in f) + (n[1:3] in m) + (n[2:4] in b)
        if s >= t:
            c += 1
    _C2[key] = c
    return c


def trend_ok_labels(draws):
    """最近 1 个月形态里「明显偏少」的标签 → 最满意号码尽量避开(只是排序用)"""
    try:
        r = TR.market_report.__wrapped__ if hasattr(TR.market_report, "__wrapped__") else None
    except Exception:
        r = None
    last = draws[-1]["date"]
    from datetime import timedelta
    cut = (date.fromisoformat(last) - timedelta(days=30)).isoformat()
    nums = [n for d in draws if d["date"] >= cut for n in d["nums"]]
    N = len(nums)
    hot, cold = set(), set()
    for k, f in TR.DIMS.items():
        obs = {}
        for n in nums:
            l = f(n); obs[l] = obs.get(l, 0) + 1
        for l, sh in TR.SHARE[k].items():
            z = TR.z(obs.get(l, 0), N * sh, N)
            if z >= 2: hot.add((k, l))
            elif z <= -2 and N * sh >= 3: cold.add((k, l))
    return hot, cold


def favourites(recs, draws, k=12):
    hot, cold = trend_ok_labels(draws)
    best = []
    for q in range(10000):
        n = "%04d" % q
        per = [score(n, r) for r in recs if r is not None]
        nm = sum(1 for s, r in zip(per, [r for r in recs if r is not None]) if s >= need(r))
        if nm == 0:
            continue
        labs = {(dk, f(n)) for dk, f in TR.DIMS.items()}
        t = len(labs & hot) - len(labs & cold)
        best.append((nm, sum(per), t, n))
    best.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3]))
    return best[:k], hot, cold


def fav_backtest(draws, k=12):
    """最满意 k 个号码的回测(只算最近 120 期, 比较慢)"""
    hit, exp, n, rows = 0, 0.0, 0, []
    start = max(1, len(draws) - 121)
    for i in range(start, len(draws) - 1):
        recs = [recs_at(draws, i, key) for key, _ in METHODS]
        if all(r is None for r in recs):
            continue
        fav, _, _ = favourites(recs, draws[:i + 1], k)
        fs = {x[3] for x in fav}
        nxt = draws[i + 1]["nums"]
        got = [x for x in nxt if x in fs]
        n += 1; exp += 1 - (1 - len(fs) / 10000) ** 3
        if got: hit += 1; rows.append((draws[i + 1]["date"], got))
    return {"n": n, "hit": hit, "exp": exp, "rows": rows}


def fmt2(s, k):
    return " ".join(sorted(("%sxx" if k == 0 else "x%sx" if k == 1 else "xx%s") % t for t in s))


def main():
    data = load()
    today = date.today().isoformat()
    html = [f"<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>选号报告 {today}</title><style>body{{font-family:system-ui,'Microsoft YaHei';max-width:900px;margin:auto;padding:12px;background:#f8fafc;color:#0f172a}}"
            ".c{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;margin:10px 0}.n{font-family:monospace;font-size:14px;line-height:1.7;word-break:break-all}"
            "h2{color:#b45309;margin:18px 0 4px}.g{color:#15803d;font-weight:700}.m{color:#64748b;font-size:13px}.fav{background:#fef3c7;border:2px solid #f59e0b}</style>"
            f"<h1>🎯 下一期选号报告 · {today}</h1><p class='m'>三种 2D 来源 → 出号(4D 里至少 2 段对上推荐 2D;太多就要 3 段)。每家附回测:最近几期如果照这样买,下一期头二三有没有中,跟随便买同样个数比。</p>"]
    brief = [f"🎯 选号报告 {today}"]
    for mk in MARKETS:
        draws = data.get(mk, [])
        if len(draws) < 5:
            continue
        last = draws[-1]
        html.append(f"<h2>{mk}</h2><div class='m'>根据最新一期 {last['date']}:{' / '.join(last['nums'])}</div>")
        recs = []
        bl = [f"\n【{mk}】最新 {last['date']}"]
        for key, name in METHODS:
            rec = recs_at(draws, len(draws) - 1, key)
            recs.append(rec)
            if rec is None:
                html.append(f"<div class='c'><b>{name}</b><div class='m'>最新一期没有特别奖资料,这份暂时出不了。</div></div>")
                bl.append(f"  {name}: 没资料")
                continue
            mine = my_numbers(rec)
            bt = backtest(draws, key)
            segs = "".join(f"<div><b>{SEGN[k]}2D</b>({len(rec[k])}个):<span class='n'>{fmt2(rec[k], k)}</span></div>" for k in range(3) if rec[k])
            rows = "".join(f"<div class='n'>{r['date'][5:]} 开 {' / '.join(('<span class=g>'+x+'</span>') if x in r['got'] else x for x in r['nums'])} {'✅' if r['got'] else '❌'}</div>"
                           for r in bt["rows"][-10:][::-1])
            html.append(f"<div class='c'><b>{name}</b>{segs}"
                        f"<div style='margin-top:6px'><b>我的号码 {len(mine)} 个</b>:</div><div class='n'>{' '.join(mine)}</div>"
                        f"<div style='margin-top:8px'><b>回测</b>:最近 {bt['n']} 期,平均每期 {bt['avg']:.0f} 个号码,"
                        f"中头二三 <b>{bt['hit']}</b> 期;随便买同样个数,平均会中 <b>{bt['exp']:.1f}</b> 期。</div>"
                        f"<div class='m'>最近 10 期(新的在上,中的标绿):</div>{rows}</div>")
            bl.append(f"  {name}: {len(mine)} 个号码 | 回测 {bt['n']} 期中 {bt['hit']} 期, 随便买约 {bt['exp']:.1f} 期")
        fav, hot, cold = favourites(recs, draws)
        fb = fav_backtest(draws)
        fl = " ".join(x[3] for x in fav)
        why = "".join(f"<div class='n'>{x[3]} — {x[0]} 种方法都对上,共 {x[1]} 段"
                      + (",形态是最近一个月偏多的" if x[2] > 0 else ",形态有最近一个月偏少的" if x[2] < 0 else "") + "</div>" for x in fav)
        html.append(f"<div class='c fav'><b>⭐ 我最满意的 {len(fav)} 个</b><div class='n' style='font-size:16px'>{fl}</div>{why}"
                    f"<div style='margin-top:6px'><b>回测</b>:最近 {fb['n']} 期每期照这样挑 {len(fav)} 个,中头二三 <b>{fb['hit']}</b> 期;随便买 {len(fav)} 个平均中 <b>{fb['exp']:.1f}</b> 期。"
                    + ("".join(f"<div class='n'>✅ {d} 中 <span class=g>{' '.join(g)}</span></div>" for d, g in fb["rows"][-5:][::-1])) + "</div></div>")
        bl.append(f"  ⭐最满意: {fl} | 回测 {fb['n']} 期中 {fb['hit']} 期, 随便买约 {fb['exp']:.1f} 期")
        brief += bl
    os.makedirs(os.path.join(BASE, "docs", "picks"), exist_ok=True)
    p = os.path.join(BASE, "docs", "picks", f"picks_{today}.html")
    open(p, "w", encoding="utf-8").write("".join(html))
    print("\n".join(brief))
    print("\n报告:", p)


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
