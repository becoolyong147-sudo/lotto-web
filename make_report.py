# -*- coding: utf-8 -*-
"""
make_report.py — 手机看的每日报告 report.html(放到 lotto-web, 网址 …/lotto-web/report.html)
内容: ⑤ 稳定条件(只有豪龙/9龙找到) · ④ 热形态主杆 · ①②③ 三种 2D + ⭐最满意(详细页 picks.html) · 形态走势
另外把 docs/notes.md(Claude 写的「今天的重点」, 若有)放在最上面。
"""
import os, sys, io, contextlib, glob, shutil, html as H
from datetime import date
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import trend_report as TR, picks_report as PR, cond_report as CR

# ⑤ 稳定条件: 2016-23 找到, 2024 起验证仍成立(stable_cond.py)
STABLE = {
    "豪龙": ("有4 + 前3D 15-18点 + 4D 17-20点",
             lambda n: "4" in n and 15 <= sum(map(int, n[:3])) <= 18 and 17 <= sum(map(int, n)) <= 20,
             "2016-23 开出是公平的 1.27 倍, 2024 起 1.24 倍"),
    "9龙": ("有4 + 24打 + 后3D 11-14点",
            lambda n: "4" in n and len(set(n)) == 4 and 11 <= sum(map(int, n[1:])) <= 14,
            "2016-23 开出是公平的 1.40 倍, 2024 起 1.31 倍"),
}


def search_best(dr_):
    """其他家: 2016-23 里找开得最多的 3 条件组合(号码 300-800 个), 再看 2024 起还在不在"""
    import numpy as np, itertools
    N = ["%04d" % q for q in range(10000)]
    sm = np.array([sum(map(int, n)) for n in N]); f3 = np.array([sum(map(int, n[:3])) for n in N]); b3 = np.array([sum(map(int, n[1:])) for n in N])
    atoms = {}
    for lo, hi in [(0, 8), (9, 12), (13, 16), (17, 20), (21, 24), (25, 28), (29, 36)]:
        atoms[f"4D {lo}-{hi}点"] = (sm >= lo) & (sm <= hi)
    for lo, hi in [(0, 6), (7, 10), (11, 14), (15, 18), (19, 22), (23, 27)]:
        atoms[f"前3D {lo}-{hi}点"] = (f3 >= lo) & (f3 <= hi); atoms[f"后3D {lo}-{hi}点"] = (b3 >= lo) & (b3 <= hi)
    atoms["24打"] = np.array([len(set(n)) == 4 for n in N]); atoms["12打"] = np.array([len(set(n)) == 3 for n in N])
    for d in "0123456789":
        atoms[f"有{d}"] = np.array([d in n for n in N])
    ctr, cte = np.zeros(10000), np.zeros(10000)
    for x in dr_:
        if x["date"] < "2016-01-01": continue
        for n in x["nums"]:
            (cte if x["date"] >= "2024-01-01" else ctr)[int(n)] += 1
    ttr, tte = ctr.sum(), cte.sum()
    best = None
    for combo in itertools.combinations(atoms, 3):
        m = atoms[combo[0]] & atoms[combo[1]] & atoms[combo[2]]
        k = int(m.sum())
        if not 300 <= k <= 800: continue
        l1 = ctr[m].sum() / (ttr * k / 10000)
        if best is None or l1 > best[0]:
            best = (l1, combo, m, k)
    l1, combo, m, k = best
    l2 = cte[m].sum() / (tte * k / 10000)
    return " + ".join(combo), (lambda n, m=m: bool(m[int(n)])), l1, l2


def rows15(dr_, f):
    rows = ""
    for x in dr_[-15:][::-1]:
        g = [n for n in x["nums"] if f(n)]
        rows += f"<div class='n'>{x['date'][5:]} {' / '.join(('<span class=g>'+n+'</span>') if n in g else n for n in x['nums'])} {'✅' if g else '❌'}</div>"
    hit = sum(1 for x in dr_[-15:] if any(f(n) for n in x["nums"]))
    return f"<div class='m' style='margin-top:6px'>最近 15 期(中的标绿):中 <b>{hit}</b> 期</div>{rows}"


def stable_section(data):
    out = {}
    for mk in PR.MARKETS:
        if mk in STABLE: continue
        dr_ = data[mk]
        name, f, l1, l2 = search_best(dr_)
        S = [n for n in ("%04d" % q for q in range(10000)) if f(n)]
        ok = l2 >= 1.1
        out[mk] = (f"<div class='c'><b>{mk}:{name}</b> {'✅ 稳定' if ok else '⚠️ 不稳定'}<div class='m'>2016-23 开出是公平的 {l1:.2f} 倍(这段里最好的组合),"
                   f"拿 2024 起来验证:{l2:.2f} 倍。{'两段都多开。' if ok else '验证段没有保持住,只能当参考。'}</div>"
                   f"{PR.numblock(S, PR.recent_set(dr_))}{rows15(dr_, f)}</div>")
    for mk, (name, f, proof) in STABLE.items():
        dr_ = data[mk]
        S = [n for n in ("%04d" % q for q in range(10000)) if f(n)]
        rec = [r for r in (PR.recs_at(dr_, len(dr_) - 1, k) for k, _ in PR.METHODS) if r is not None]
        S.sort(key=lambda n: (-sum(PR.score(n, r) for r in rec), n))
        out[mk] = (f"<div class='c fav'><b>{mk}:{name}</b> ✅ 稳定<div class='m'>{proof}(两段时间都成立,才算稳定)。号码按 2D 对上段数排,前面的优先。</div>"
                   f"{PR.numblock(S, PR.recent_set(dr_))}{rows15(dr_, f)}</div>")
    return out


def main():
    today = date.today().isoformat()
    data = PR.load()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        PR.main()                                   # 生成 docs/picks/picks_日期.html
    picks_brief = buf.getvalue()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        TR.main()
    trend_txt = buf.getvalue()
    cond = {}
    for mk in PR.MARKETS:
        dr_ = data.get(mk, [])
        (lst, main_, f3, das, why, s24), bt = CR.run(dr_)
        cond[mk] = (f"<div class='c'><b>{mk}</b> · 最新 {dr_[-1]['date']}<div class='m'>{H.escape(why)};前3D偏多:{'、'.join(sorted(f3)) or '不限'};打数:{'+'.join(sorted(das))};冷门不要</div>"
                    f"{PR.numblock(lst, PR.recent_set(dr_))}"
                    + "<div class='m' style='margin-top:6px'>最近 15 期(当时照这样挑的号码,中的标绿):</div>"
                    + "".join(f"<div class='n'>{r['date'][5:]} {' / '.join(('<span class=g>'+n+'</span>') if n in r['got'] else n for n in r['nums'])} {'✅' if r['got'] else '❌'}</div>" for r in bt['rows'][-15:][::-1])
                    + "</div>")
    notes = ""
    np_ = os.path.join(BASE, "docs", "notes.md")
    if os.path.exists(np_):
        notes = "<div class='c' style='border:2px solid #2563eb'><b>📝 今天的重点</b><div style='white-space:pre-wrap'>" + H.escape(open(np_, encoding="utf-8").read()) + "</div></div>"
    import re
    def split_by(txt, pat):
        d, cur = {}, None
        for l in txt.splitlines():
            m = re.search(pat, l)
            if m: cur = m.group(1); d[cur] = []
            if cur: d[cur].append(l)
        return d
    fav_d = split_by(picks_brief, r"【(.+?)】")
    tr_d = split_by(trend_txt, r"^\*\*(.+?)\*\*")
    stab = stable_section(data)
    CSS = """<style>body{font-family:system-ui,'Microsoft YaHei';max-width:900px;margin:auto;padding:12px;background:#f8fafc;color:#0f172a}
.c{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;margin:10px 0}.n{font-family:monospace;font-size:14px;line-height:1.7;word-break:break-all}
h2{color:#b45309;margin:20px 0 4px}.g{color:#15803d;font-weight:700}.m{color:#64748b;font-size:13px}.fav{background:#fef3c7;border:2px solid #f59e0b}
nav a{margin-right:10px}pre{white-space:pre-wrap;font-size:13px}.btn{display:block;background:#fff;border:1px solid #cbd5e1;border-radius:10px;padding:14px;margin:8px 0;font-size:17px;text-decoration:none;color:#0f172a}</style>"""
    HEAD = "<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
    links = ""
    for k, mk in enumerate(PR.MARKETS):
        fav = "".join(f"<div class='n'>{H.escape(l.split(' | 回测')[0])}</div>" for l in fav_d.get(mk, []) if "⭐" in l)
        trl = chr(10).join(tr_d.get(mk, []))
        pg = f"""{HEAD}<title>{mk} {today}</title>{CSS}{PR.NUM_CSS_JS}
<h1>📋 {mk} · {today}</h1><div class='m'>号码都已去掉最近 {PR.RECENT_N} 期(头二三)开过的。最新一期 {data[mk][-1]['date']}</div>
<nav><a href='report.html'>← 回总目录</a><a href='#s5'>⑤稳定</a><a href='#s4'>④主杆</a><a href='#s123'>①②③</a><a href='#tr'>形态走势</a></nav>
<h2 id='s5'>⑤ 稳定条件</h2>{stab[mk]}
<h2 id='s4'>④ 热形态主杆</h2>{cond[mk]}
<h2 id='s123'>①②③ ⭐最满意</h2><div class='c'>{fav}<div style='margin-top:6px'><a href='picks.html'>👉 看完整号码和回测(picks.html)</a></div></div>
<h2 id='tr'>📊 形态走势(最近 1 个月)</h2><div class='c'><pre>{H.escape(trl)}</pre></div>
<div class='m'>更新时间 {today}</div>"""
        open(os.path.join(BASE, f"report_{k}.html"), "w", encoding="utf-8").write(pg)
        links += f"<a class='btn' href='report_{k}.html'>{mk}  <span class='m'>最新 {data[mk][-1]['date']}</span></a>"
    page = f"""{HEAD}<title>每日报告 {today}</title>{CSS}
<h1>📋 每日报告 · {today}</h1><div class='m'>点进公司,看那一家自己的号码和数据。</div><nav><a href='./' target='_top'>← 回系统</a></nav>
{notes}{links}<div class='m'>更新时间 {today}</div>"""
    open(os.path.join(BASE, "report.html"), "w", encoding="utf-8").write(page)
    shutil.copy2(os.path.join(BASE, "docs", "picks", f"picks_{today}.html"), os.path.join(BASE, "picks.html"))
    print("report.html + picks.html 已生成")


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
