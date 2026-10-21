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


def stable_section(data):
    out = []
    for mk, (name, f, proof) in STABLE.items():
        dr_ = data[mk]
        S = [n for n in ("%04d" % q for q in range(10000)) if f(n)]
        rec = [r for r in (PR.recs_at(dr_, len(dr_) - 1, k) for k, _ in PR.METHODS) if r is not None]
        S.sort(key=lambda n: (-sum(PR.score(n, r) for r in rec), n))
        rows = ""
        for x in dr_[-15:][::-1]:
            g = [n for n in x["nums"] if f(n)]
            rows += f"<div class='n'>{x['date'][5:]} {' / '.join(('<span class=g>'+n+'</span>') if n in g else n for n in x['nums'])} {'✅' if g else '❌'}</div>"
        out.append(f"<div class='c fav'><b>{mk}:{name}</b> · {len(S)} 个号码<div class='m'>{proof}(两段时间都成立,才算稳定)。号码按 2D 对上段数排,前面的优先。</div>"
                   f"{PR.numblock(S)}<div class='m' style='margin-top:6px'>最近 15 期(中的标绿):</div>{rows}</div>")
    return "".join(out)


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
    cond = []
    for mk in PR.MARKETS:
        dr_ = data.get(mk, [])
        (lst, main_, f3, das, why, s24), bt = CR.run(dr_)
        cond.append(f"<div class='c'><b>{mk}</b> · 最新 {dr_[-1]['date']}<div class='m'>{H.escape(why)};前3D偏多:{'、'.join(sorted(f3)) or '不限'};打数:{'+'.join(sorted(das))};冷门不要</div>"
                    f"<div><b>{len(lst)} 个号码</b></div>{PR.numblock(lst)}"
                    f"<div class='m'>回测 {bt['n']} 期(每期约 {bt['avg']:.0f} 个):中头二三 <b>{bt['hit']}</b> 期,随便买同样个数约 <b>{bt['exp']:.1f}</b> 期</div></div>")
    notes = ""
    np_ = os.path.join(BASE, "docs", "notes.md")
    if os.path.exists(np_):
        notes = "<div class='c' style='border:2px solid #2563eb'><b>📝 今天的重点</b><div style='white-space:pre-wrap'>" + H.escape(open(np_, encoding="utf-8").read()) + "</div></div>"
    fav = "".join(f"<div class='n'>{H.escape(l)}</div>" for l in picks_brief.splitlines() if "【" in l or "⭐" in l)
    page = f"""<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>每日报告 {today}</title><style>body{{font-family:system-ui,'Microsoft YaHei';max-width:900px;margin:auto;padding:12px;background:#f8fafc;color:#0f172a}}
.c{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;margin:10px 0}}.n{{font-family:monospace;font-size:14px;line-height:1.7;word-break:break-all}}
h2{{color:#b45309;margin:20px 0 4px}}.g{{color:#15803d;font-weight:700}}.m{{color:#64748b;font-size:13px}}.fav{{background:#fef3c7;border:2px solid #f59e0b}}
nav a{{margin-right:10px}}pre{{white-space:pre-wrap;font-size:13px}}</style>{PR.NUM_CSS_JS}
<h1>📋 每日报告 · {today}</h1><nav><a href='./' target='_top'>← 回系统</a><a href='#s5'>⑤稳定</a><a href='#s4'>④主杆</a><a href='#s123'>①②③</a><a href='#tr'>形态走势</a></nav>
{notes}
<h2 id='s5'>⑤ 稳定条件(只有豪龙、9龙找到)</h2><div class='m'>2016-2023 年找出来,再拿 2024 年以后的资料验证,两段都多开才算。其他 6 家没有找到稳定的条件。</div>{stable_section(data)}
<h2 id='s4'>④ 热形态主杆(你的条件)</h2>{''.join(cond)}
<h2 id='s123'>①②③ 三种 2D + ⭐最满意</h2><div class='c'>{fav}<div style='margin-top:6px'><a href='picks.html'>👉 看每家完整号码和回测</a></div></div>
<h2 id='tr'>📊 形态走势(最近 1 个月)</h2><div class='c'><pre>{H.escape(trend_txt)}</pre></div>
<div class='m'>更新时间 {today}</div>"""
    open(os.path.join(BASE, "report.html"), "w", encoding="utf-8").write(page)
    shutil.copy2(os.path.join(BASE, "docs", "picks", f"picks_{today}.html"), os.path.join(BASE, "picks.html"))
    print("report.html + picks.html 已生成")


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
