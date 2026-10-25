# -*- coding: utf-8 -*-
"""
make_report.py — 手机看的每日报告 report.html(放到 lotto-web, 网址 …/lotto-web/report.html)
内容: ⑤ 稳定条件(只有豪龙/9龙找到) · ④ 热形态主杆 · ①②③ 三种 2D + ⭐最满意(详细页 picks.html) · 形态走势
另外把 docs/notes.md(Claude 写的「今天的重点」, 若有)放在最上面。
"""
import json, os, sys, io, contextlib, glob, shutil, html as H
from datetime import date
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import dragon_pick as DP, trend_report as TR, picks_report as PR, cond_report as CR

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


SUM = {}


def stable_section(data):
    out = {}
    for mk in PR.MARKETS:
        if mk in STABLE: continue
        dr_ = data[mk]
        name, f, l1, l2 = search_best(dr_)
        S = [n for n in ("%04d" % q for q in range(10000)) if f(n)]
        ok = l2 >= 1.1
        SUM[mk] = dict(n=len(S), ok=ok, hit=sum(1 for x in dr_[-15:] if any(f(n) for n in x["nums"])))
        out[mk] = (f"<div class='c'><b>{mk}:{name}</b> {'✅ 稳定' if ok else '⚠️ 不稳定'}<details><summary class='m'>挑号条件(技术说明)</summary><div class='m'>2016-23 开出是公平的 {l1:.2f} 倍,"
                   f"2024 起验证:{l2:.2f} 倍。</div></details>"
                   f"{PR.numblock(S, PR.recent_set(dr_))}{rows15(dr_, f)}</div>")
    for mk, (name, f, proof) in STABLE.items():
        dr_ = data[mk]
        S = [n for n in ("%04d" % q for q in range(10000)) if f(n)]
        SUM[mk] = dict(n=len(S), ok=True, hit=sum(1 for x in dr_[-15:] if any(f(n) for n in x["nums"])))
        rec = [r for r in (PR.recs_at(dr_, len(dr_) - 1, k) for k, _ in PR.METHODS) if r is not None]
        S.sort(key=lambda n: (-sum(PR.score(n, r) for r in rec), n))
        out[mk] = (f"<div class='c fav'><b>{mk}:{name}</b> ✅ 稳定<details><summary class='m'>挑号条件(技术说明)</summary><div class='m'>{proof}(两段时间都成立,才算稳定)</div></details>"
                   f"{PR.numblock(S, PR.recent_set(dr_))}{rows15(dr_, f)}</div>")
    return out


TRD = None


def trend_html(mk):
    """本月开奖走势: 白话总结 + 最近几期 + 各形态/数字的柱状对比(含上个月)"""
    global TRD
    from datetime import timedelta
    if TRD is None: TRD = TR.load()
    dr_ = TRD.get(mk, [])
    if not dr_: return "<div class='m'>没有数据</div>"
    last = date.fromisoformat(dr_[-1][0])
    c1 = (last - timedelta(days=30)).isoformat(); c0 = (last - timedelta(days=60)).isoformat()
    cur = [n for d, ns in dr_ if d > c1 for n in ns]
    prv = [n for d, ns in dr_ if c0 < d <= c1 for n in ns]
    nd = sum(1 for d, _ in dr_ if d > c1)
    N = len(cur)
    def tally(lst, f):
        c = {}
        for n in lst:
            for l in (f(n) if isinstance(f(n), list) else [f(n)]): c[l] = c.get(l, 0) + 1
        return c
    def block(title, f, share, order=None, hint=""):
        a, b = tally(cur, f), tally(prv, f)
        labs = order or sorted(share, key=lambda l: -share[l])
        mx = max([a.get(l, 0) for l in labs] + [share[l] * N for l in labs] + [1])
        rows = ""
        for l in labs:
            o, e = a.get(l, 0), share[l] * N
            zz = TR.z(o, e, N)
            tag = "🔴偏多" if zz >= 2 else ("🔵偏少" if zz <= -2 and e >= 3 else "")
            rows += (f"<div class='br'><span class='bl'>{H.escape(l)}</span><span class='bb'><i style='width:{o/mx*100:.0f}%'></i>"
                     f"<u style='left:{e/mx*100:.0f}%'></u></span><span class='bv'>{o}<span class='m'> /{e:.0f}</span> {tag}</span>"
                     f"<span class='bp m'>上月{b.get(l, 0)}</span></div>")
        return f"<div class='c'><b>{title}</b> <span class='m'>{hint}</span>{rows}</div>"
    ds = {d: sum(n.count(str(d)) for n in cur) for d in range(10)}
    exp_d = N * 4 / 10
    hot = sorted(ds, key=lambda d: -ds[d])[:3]; cold = sorted(ds, key=lambda d: ds[d])[:3]
    top = lambda k: max(tally(cur, TR.DIMS[k]).items(), key=lambda x: x[1])
    out = f"<div class='m'>{c1[5:]} ~ {dr_[-1][0][5:]} · {nd} 期 · 头二三共 {N} 个号码(每格:这个月开几次 /公平约几次)</div>"
    out += ("<div class='c'><b>一句话</b><div style='line-height:1.8'>"
            f"🔥 数字最常开:{'、'.join(f'{d}({ds[d]}次)' for d in hot)}<br>"
            f"🧊 数字最少开:{'、'.join(f'{d}({ds[d]}次)' for d in cold)}<br>"
            f"单双最常见 <b>{top('单双')[0]}</b>({top('单双')[1]}次),大小最常见 <b>{top('大小')[0]}</b>({top('大小')[1]}次),"
            f"点数最常落在 <b>{top('点数')[0]}</b>({top('点数')[1]}次)</div></div>")
    rows = ""
    for d, ns in dr_[-8:][::-1]:
        rows += "<div class='n'>" + d[5:] + " " + " / ".join(ns) + "</div>"
    out += f"<div class='c'><b>最近 8 期开奖</b><div style='margin-top:4px'>{rows}</div></div>"
    out += block("🔢 数字 0~9 各出现几次", lambda n: sorted(set(n)) if False else list(n), {str(d): .4 for d in range(10)}, [str(d) for d in range(10)], "(每个号码4个数字,公平约各一样多)")
    for k, nm in (("点数", "➕ 四个数字加起来(点数)"), ("单双", "⚖️ 单双"), ("大小", "↕️ 大小(5以上算大)"), ("打数", "🔁 打数(有没有重复数字)"), ("数根", "🌳 数根"), ("前3D点数", "前3位加起来"), ("后3D点数", "后3位加起来")):
        order = list(TR.SHARE[k].keys())
        if k in ("点数", "前3D点数", "后3D点数", "数根", "大小", "单双"): order = sorted(order)
        out += block(nm, TR.DIMS[k], TR.SHARE[k], order)
    out += "<div class='m'>🔴=比公平应有的明显多,🔵=明显少(差得够大才标)。柱子是这个月开的次数,竖线是公平的话应该有的次数。</div>"
    return out


COMBO_JS = r"""<div class='c'><b>🔗 数字组合观察</b> <span class='m'>勾你想看的数字,看每个奖含这些数字的次数</span>
<div id='cb_D' style='margin:8px 0'></div>
<div>方式:<select id='cb_M'><option value='all'>号码里同时有这些数字</option><option value='any'>号码里有其中任何一个</option></select>
 范围:<select id='cb_W'><option>30</option><option selected>100</option><option>300</option></select> 期</div>
<div id='cb_O' style='margin-top:8px;line-height:1.8'></div></div>
<script>(function(){
const DR=__DATA__;const D=document.getElementById('cb_D'),O=document.getElementById('cb_O'),M=document.getElementById('cb_M'),W=document.getElementById('cb_W');
const sel=new Set([1]);
for(let d=0;d<10;d++){const l=document.createElement('label');l.style.cssText='display:inline-block;margin:2px 8px 2px 0;font-size:18px';
 const c=document.createElement('input');c.type='checkbox';c.checked=d==1;c.onchange=()=>{c.checked?sel.add(d):sel.delete(d);go()};l.append(c,' '+d);D.append(l)}
function ok(n,mode){const S=[...sel];if(!S.length)return false;return mode=='all'?S.every(d=>n.includes(d)):S.some(d=>n.includes(d))}
function go(){const mode=M.value,w=+W.value,rows=DR.slice(-w);if(!sel.size){O.textContent='请先勾一个数字';return}
 let p=0;for(let i=0;i<10000;i++)if(ok(String(i).padStart(4,'0'),mode))p++;p/=10000;
 const names=['头奖','二奖','三奖'];let h=[0,0,0],any=0,all=0;
 rows.forEach(r=>{let k=0;r[1].forEach((n,i)=>{if(ok(n,mode)){h[i]++;k++}});if(k)any++;if(k==3)all++});
 const N=rows.length,pa=1-Math.pow(1-p,3);
 let miss=0;for(let i=DR.length-1;i>=0;i--){if(DR[i][1].some(n=>ok(n,mode)))break;miss++}
 const pc=x=>(x*100).toFixed(0)+'%';
 let t=`<div class='m'>随便一个号码含这些数字的机会约 <b>${pc(p)}</b>;一期三个奖至少有一个约 <b>${pc(pa)}</b></div>`;
 names.forEach((nm,i)=>t+=`${nm}:<b>${h[i]}</b>/${N} 期有(${pc(h[i]/N)}) <span class='m'>公平约 ${pc(p)}</span><br>`);
 t+=`<b>一期三个奖至少一个有:${any}/${N} 期(${pc(any/N)})</b> <span class='m'>公平约 ${pc(pa)}</span><br>三个奖都有:${all} 期 <span class='m'>公平约 ${pc(p*p*p)}</span><br>`;
 t+=`目前这个条件已经连续 <b>${miss}</b> 期没出现<br><div class='m' style='margin-top:6px'>最近 20 期(头/二/三,绿=有):</div>`;
 DR.slice(-20).reverse().forEach(r=>{t+=`<div class='n'>${r[0].slice(5)} `+r[1].map(n=>ok(n,mode)?`<span class=g>${n}</span>`:n).join(' / ')+'</div>'});
 O.innerHTML=t}
M.onchange=W.onchange=go;go()})()</script>"""


def combo_html(mk):
    global TRD
    if TRD is None: TRD = TR.load()
    dr_ = TRD.get(mk, [])[-300:]
    return COMBO_JS.replace("__DATA__", json.dumps(dr_, ensure_ascii=False))


def dragon_card(mk):
    """豪龙/9龙: 数字偏爱主推 500 个(回测有效); 其他家不给"""
    global TRD
    if mk not in ("豪龙", "9龙"): return ""
    if TRD is None: TRD = TR.load()
    dr_ = TRD[mk]
    lst = DP.pick(dr_)
    h, e, rows = DP.backtest(dr_, 500)
    h2 = sum(1 for r in rows[-250:] if r[2]); e2 = 250 * (1 - (1 - DP.CAP / 10000) ** 3)
    ds = [d for d in range(10)]
    cnt = {d: sum(n.count(str(d)) for _, ns in dr_[-DP.WIN:] for n in ns) for d in ds}
    hot = sorted(ds, key=lambda d: -cnt[d])[:4]; cold = sorted(ds, key=lambda d: cnt[d])[:3]
    rec = "".join(f"<div class='n'>{d[5:]} {' / '.join(('<span class=g>'+n+'</span>') if n in g else n for n in ns)} {'✅' if g else '❌'}</div>" for d, ns, g in rows[-15:][::-1])
    return (f"<h2>🐉 {mk}数字偏爱主推(回测有效)</h2><div class='c fav'><div style='line-height:1.8'>"
            f"这家有稳定的数字偏好:过去 {DP.WIN} 期里最常出现 <b>{'、'.join(map(str, hot))}</b>,最少出现 <b>{'、'.join(map(str, cold))}</b>。<br>"
            f"我按数字、打数、前后 2D 给号码打分,取最高的 <b>{len(lst)}</b> 个。<br>"
            f"倒回去测最近 500 期(每期只用当时以前的资料):中 <b>{h}</b> 期,随便买同样个数约 <b>{e:.0f}</b> 期;最近 250 期:中 {h2} 期,随便买约 {e2:.0f} 期。</div>"
            f"{PR.numblock(lst)}<div class='m' style='margin-top:6px'>最近 15 期(当时照这样挑的号码,中的标绿):</div>{rec}</div>")


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
    BT = {}
    for mk in PR.MARKETS:
        dr_ = data.get(mk, [])
        (lst, main_, f3, das, why, s24), bt = CR.run(dr_)
        BT[mk] = bt
        cond[mk] = (f"<div class='c'><b>{mk}</b> · 最新 {dr_[-1]['date']}<div class='m'>{H.escape(why)};前3D偏多:{'、'.join(sorted(f3)) or '不限'};打数:{'+'.join(sorted(das))};冷门不要</div>"
                    f"{PR.numblock(lst, PR.recent_set(dr_))}"
                    f"<div class='m'>回测 {bt['n']} 期(每期约 {bt['avg']:.0f} 个):中头二三 <b>{bt['hit']}</b> 期,随便买同样个数约 <b>{bt['exp']:.1f}</b> 期</div>"
                    + "<div class='m' style='margin-top:6px'>最近 15 期(当时照这样挑的号码,中的标绿):</div>"
                    + "".join(f"<div class='n'>{r['date'][5:]} {' / '.join(('<span class=g>'+n+'</span>') if n in r['got'] else n for n in r['nums'])} {'✅' if r['got'] else '❌'}</div>" for r in bt['rows'][-15:][::-1])
                    + "</div>")
    notes = ""
    np_ = os.path.join(BASE, "docs", "notes.md")
    if os.path.exists(np_):
        ls_ = [l.strip() for l in open(np_, encoding="utf-8").read().splitlines() if l.strip()]
        notes = "<details><summary><b>📝 " + H.escape(ls_[0]) + "(点开看详细)</b></summary><ul style='padding-left:20px;line-height:1.7'>" + "".join("<li>" + H.escape(l.lstrip("- ")) + "</li>" for l in ls_[1:]) + "</ul></details>"
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

.br{display:flex;align-items:center;gap:6px;font-size:13px;margin:3px 0}.bl{width:96px;flex:none}.bb{flex:1;position:relative;height:12px;background:#f1f5f9;border-radius:6px}
.bb i{position:absolute;left:0;top:0;bottom:0;background:#60a5fa;border-radius:6px}.bb u{position:absolute;top:-2px;bottom:-2px;width:2px;background:#ef4444}
.bv{width:96px;flex:none;text-align:right}.bp{width:48px;flex:none}
details{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;margin:10px 0}summary{cursor:pointer;font-size:16px}nav a{margin-right:10px}pre{white-space:pre-wrap;font-size:13px}.btn{display:block;background:#fff;border:1px solid #cbd5e1;border-radius:10px;padding:14px;margin:8px 0;font-size:17px;text-decoration:none;color:#0f172a}</style>"""
    HEAD = "<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
    links = ""
    for k, mk in enumerate(PR.MARKETS):
        fav = "".join(f"<div class='n'>{H.escape(l)}</div>" for l in fav_d.get(mk, []) if "⭐" in l)
        trl = chr(10).join(tr_d.get(mk, []))
        sm = SUM[mk]; bt = BT[mk]
        better = bt['hit'] - bt['exp']
        bt_txt = "比随便买好" if better >= 3 else ("比随便买差" if better <= -3 else "跟随便买差不多")
        trust = "✅ 这个条件两段时间都撑得住,可信度较高" if sm['ok'] else "⚠️ 这个条件近期没撑住,当参考就好"
        verdict = f"<div class='c fav'><div style='font-size:18px'><b>{mk}</b> · 最新一期 {data[mk][-1]['date']}</div>"                   f"<div style='font-size:16px;line-height:1.8;margin-top:6px'>🎯 今天主推 <b>{sm['n']}</b> 个号码(往下看,点「复制」就能用)<br>"                   f"📅 最近15期里中过 <b>{sm['hit']}</b> 期<br>{trust}<br>"                   f"🔥 另一种挑法(热形态)过去{bt['n']}期:中 {bt['hit']} 期,随便买约 {bt['exp']:.0f} 期 → <b>{bt_txt}</b></div></div>"
        pg = f"""{HEAD}<title>{mk} {today}</title>{CSS}{PR.NUM_CSS_JS}
<nav><a href='report.html'>← 回总目录</a></nav>
{verdict}
{dragon_card(mk)}<h2>🎯 今天主推的号码</h2><div class='m'>已经去掉最近 {PR.RECENT_N} 期开过的号码。排前面的优先。</div>{stab[mk]}
<details><summary><b>🔥 另一种挑法(热形态)</b> · 点开看</summary>{cond[mk]}</details>
<details><summary><b>⭐ 最满意的 12 个</b> · 点开看</summary><div class='c'>{fav}<div style='margin-top:6px'><a href='picks.html'>👉 看完整号码和回测</a></div></div></details>
<details><summary><b>🔗 数字组合观察(比如「有1」)</b> · 点开看</summary>{combo_html(mk)}</details>
<details><summary><b>📊 这个月开奖的走势</b> · 点开看</summary>{trend_html(mk)}</details>
<div class='m'>更新时间 {today}</div>"""
        open(os.path.join(BASE, f"report_{k}.html"), "w", encoding="utf-8").write(pg)
        icon = "✅" if sm['ok'] else "⚠️"
        links += f"<a class='btn' href='report_{k}.html'><b>{mk}</b> <span class='m'>最新 {data[mk][-1]['date']}</span><br><span style='font-size:14px'>{icon} 主推 {sm['n']} 个 · 近15期中 {sm['hit']} 期 · 热形态{bt_txt}</span></a>"
    page = f"""{HEAD}<title>每日报告 {today}</title>{CSS}
<h1>📋 每日报告 · {today}</h1><div class='m'>点进公司就能看到今天买哪些号码。✅=条件比较可信,⚠️=只当参考。</div><nav><a href='./' target='_top'>← 回系统</a></nav>
{links}{notes}<div class='m'>更新时间 {today}</div>"""
    open(os.path.join(BASE, "report.html"), "w", encoding="utf-8").write(page)
    shutil.copy2(os.path.join(BASE, "docs", "picks", f"picks_{today}.html"), os.path.join(BASE, "picks.html"))
    print("report.html + picks.html 已生成")


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
