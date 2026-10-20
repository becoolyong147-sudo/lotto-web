# -*- coding: utf-8 -*-
"""
trend_report.py — 每日「形态走势」报告(最近1个月), 算法跟 lottery.html 的 📊形态走势 一样
数据: slim_data.json(历史) + auto_results.json(新成绩); 头二三合在一起看(每家一个月约 39 个号码)
偏多/偏少 = 跟「公平的话应该开几次」比, 差得明显(z≥2)才列出来。
用法: python trend_report.py [天数=30]
"""
import json, math, os, sys
from datetime import date, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
MARKETS = ["万能", "跑马", "多多", "新加坡", "豪龙", "9龙", "沙巴", "砂拉越"]


def dr(n):
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n


def cnt(n, f):
    return sum(1 for c in n if f(int(c)))


odd = lambda d: d % 2 == 1
big = lambda d: d >= 5


def da(n):
    k = sorted([n.count(c) for c in set(n)], reverse=True)
    return {(1, 1, 1, 1): "24打(四个都不同)", (2, 1, 1): "12打(一对)", (2, 2): "6打(两对)", (3, 1): "4打(三个同)", (4,): "1打(四个同)"}[tuple(k)]


def seg(v, cuts, labs):
    for c, l in zip(cuts, labs):
        if v <= c:
            return l
    return labs[-1]


DIMS = {
    "单双": lambda n: (lambda c: "4单" if c == 4 else "4双" if c == 0 else f"{c}单{4-c}双")(cnt(n, odd)),
    "大小": lambda n: (lambda c: "4大" if c == 4 else "4小" if c == 0 else f"{c}大{4-c}小")(cnt(n, big)),
    "打数": da,
    "数根": lambda n: "根9" if sum(map(int, n)) == 0 else f"根{dr(sum(map(int, n)))}",
    "点数": lambda n: seg(sum(map(int, n)), [8, 12, 16, 20, 24, 28, 36], ["0-8点", "9-12点", "13-16点", "17-20点", "21-24点", "25-28点", "29-36点"]),
    "前3D点数": lambda n: "前3D " + seg(sum(map(int, n[:3])), [6, 10, 14, 18, 22, 27], ["0-6", "7-10", "11-14", "15-18", "19-22", "23-27"]),
    "后3D点数": lambda n: "后3D " + seg(sum(map(int, n[1:])), [6, 10, 14, 18, 22, 27], ["0-6", "7-10", "11-14", "15-18", "19-22", "23-27"]),
}
SHARE = {}
for k, f in DIMS.items():
    c = {}
    for i in range(10000):
        l = f("%04d" % i); c[l] = c.get(l, 0) + 1
    SHARE[k] = {l: v / 10000 for l, v in c.items()}
GID = {}
GSIZE = {}
for i in range(10000):
    g = "".join(sorted("%04d" % i)); GID[i] = g; GSIZE[g] = GSIZE.get(g, 0) + 1
HALFN = {"h1": "偏上半年", "h2": "偏下半年", "bal": "上下均衡", "new": "分身组没开过"}


def load():
    sd = json.load(open(os.path.join(BASE, "slim_data.json"), encoding="utf-8"))["DB"]
    by = {}
    for mk, txt in sd.items():
        for line in (txt.splitlines() if isinstance(txt, str) else []):
            p = line.split(",")
            if len(p) >= 5:
                by[(mk, p[0][:10])] = [x.zfill(4) for x in p[2:5]]
    try:
        for x in json.load(open(os.path.join(BASE, "auto_results.json"), encoding="utf-8"))["draws"]:
            if len(x.get("nums") or []) >= 3:
                by[(x["market"], x["date"][:10])] = [str(v).zfill(4) for v in x["nums"][:3]]
    except Exception:
        pass
    out = {}
    for (mk, d), nums in by.items():
        if all(len(n) == 4 and n.isdigit() for n in nums):
            out.setdefault(mk, []).append((d, nums))
    for mk in out:
        out[mk].sort()
    return out


def z(o, e, n):
    return (o - e) / math.sqrt(max(e * (1 - e / max(n, 1)), 1e-4))


def market_report(mk, draws, days):
    if not draws:
        return None
    last = draws[-1][0]
    cut = (date.fromisoformat(last) - timedelta(days=days)).isoformat()
    h1, h2 = {}, {}
    cat_cnt = {"h1": 0, "h2": 0, "bal": 0, "new": 10000}

    def cat(n):
        g = GID[n]; a, b = h1.get(g, 0), h2.get(g, 0)
        if a + b == 0: return "new"
        if a > b * 1.2: return "h1"
        if b > a * 1.2: return "h2"
        return "bal"

    obs = {k: {} for k in DIMS}; obs["半年型"] = {}
    exp_half = {c: 0.0 for c in HALFN}
    N, ndraw = 0, 0
    for d, nums in draws:
        half = 1 if int(d[5:7]) <= 6 else 2
        if d >= cut:
            ndraw += 1
            for n in nums:
                N += 1
                for k, f in DIMS.items():
                    l = f(n); obs[k][l] = obs[k].get(l, 0) + 1
                c = cat(int(n)); obs["半年型"][c] = obs["半年型"].get(c, 0) + 1
                for cc in HALFN:
                    exp_half[cc] += cat_cnt[cc] / 10000
        for n in nums:
            v = int(n); g = GID[v]; b4 = cat(v)
            (h1 if half == 1 else h2)[g] = (h1 if half == 1 else h2).get(g, 0) + 1
            af = cat(v)
            if af != b4:
                cat_cnt[b4] -= GSIZE[g]; cat_cnt[af] += GSIZE[g]
    hot, cold = [], []
    for k in DIMS:
        for l, sh in SHARE[k].items():
            o, e = obs[k].get(l, 0), N * sh
            zz = z(o, e, N)
            if zz >= 2: hot.append((zz, f"{l}({k}) 开了 {o} 次,公平的话约 {e:.0f} 次"))
            elif zz <= -2 and e >= 3: cold.append((zz, f"{l}({k}) 只开 {o} 次,公平的话约 {e:.0f} 次"))
    for c, nm in HALFN.items():
        o, e = obs["半年型"].get(c, 0), exp_half[c]
        if e < 0.5: continue
        zz = z(o, e, N)
        if zz >= 2: hot.append((zz, f"{nm}(半年型) 开了 {o} 次,公平的话约 {e:.0f} 次"))
        elif zz <= -2 and e >= 3: cold.append((zz, f"{nm}(半年型) 只开 {o} 次,公平的话约 {e:.0f} 次"))
    hot.sort(reverse=True); cold.sort()
    # 最多的几种(就算没到「明显」也让人看到大概)
    top = []
    for k in ("单双", "大小", "打数"):
        if obs[k]:
            l, o = max(obs[k].items(), key=lambda t: t[1]); top.append(f"{k}最多是「{l}」{o} 次")
    ld, ln = draws[-1]
    lines = [f"**{mk}**({cut[5:]} ~ {last[5:]},{ndraw} 期,头二三共 {N} 个号码)"]
    lines.append("  最新一期 " + last[5:] + ":" + " / ".join(ln) + "  →  " + ",".join(DIMS["单双"](n) + "·" + DIMS["大小"](n) for n in ln))
    if hot: lines += ["  🔴 偏多:" + h for _, h in hot[:4]]
    if cold: lines += ["  🔵 偏少:" + c for _, c in cold[:4]]
    if not hot and not cold: lines.append("  ⚪ 这个月各种形态都在正常范围,没有明显偏多或偏少")
    lines.append("  · " + ";".join(top))
    return "\n".join(lines), len(hot) + len(cold)


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    data = load()
    out, flagged = [], 0
    for mk in MARKETS:
        r = market_report(mk, data.get(mk, []), days)
        if r:
            out.append(r[0]); flagged += r[1]
    head = f"📊 形态走势日报 · {date.today().isoformat()} · 最近 {days} 天 · 头二三\n" \
           f"(🔴偏多 / 🔵偏少 = 跟「公平的话应该开几次」差得明显才列出;一共 {flagged} 项)\n"
    txt = head + "\n" + "\n\n".join(out)
    os.makedirs(os.path.join(BASE, "docs", "trend"), exist_ok=True)
    open(os.path.join(BASE, "docs", "trend", f"trend_{date.today().isoformat()}.md"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
