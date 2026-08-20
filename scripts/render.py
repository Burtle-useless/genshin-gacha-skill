"""把統計數字畫成報表：完整版 HTML（星象占卜風）與對話內嵌 widget 片段。

兩份的設計約束完全不同，所以分成兩套渲染，不要試圖共用樣式：
- report：獨立檔案，可載 Google Fonts、可用深色底，走遊戲風。
- widget：跑在對話 iframe 裡，CSP 只放行少數 CDN（所以圖示必須 base64 內嵌），
  且規範要求外層背景透明、顏色一律走 CSS 變數以同時支援亮／暗色模式。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n

POOL_ORDER =["character", "weapon", "chronicled", "standard", "novice"]

# 報表用色（深色底自成一套，不跟 widget 共用）
GOLD, CRIMSON, DIM, INK = "#C8A45C", "#9E4B4B", "#6E6A8A", "#EDE7DA"
VIOLET = "#7C6BA8"  # 四星，跟金／紅拉開好辨識
# widget 用色：亮暗兩色模式都要看得清楚，所以用中間調
W_WIN, W_WAI, W_NOW = "#639922", "#E24B4A", "#BA7517"

HARD_PITY = {"character": 90, "weapon": 80, "standard": 90, "chronicled": 90, "novice": 50}
FOUR_PITY = 10  # 四星保底，長條分母

VIEWS = ("five", "split", "merge")  # 只看五星／四星分開／合併時間軸


def load_icons(data_dir):
    f = data_dir / "icon_map.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def rows_for(pool_key, pool, limit=None, include_four=False):
    """回傳 (名稱, 抽數, 顏色鍵, 標註, 星級)，最新的排前面。

    四星併進來時仍照時間排序，讓「合併時間軸」檢視不必另外組一份 DOM。
    """
    fives = pool.get("fives", [])
    if limit:
        fives = fives[-limit:]
    rows = []
    if pool.get("current_pity"):
        rows.append((None, pool["current_pity"], "now", "ongoing", 5))

    items = [dict(f, rank=5) for f in fives]
    if include_four:
        items += [dict(f, rank=4) for f in pool.get("fours", [])]
    items.sort(key=lambda f: f["time"], reverse=True)

    for f in items:
        # tag 一律回 key，翻成什麼字是渲染時才決定的
        if f["rank"] == 4:
            rows.append((f["name"], f["pity"], "four", None, 4))
        elif pool_key in ("character", "weapon"):
            key = "wai" if f.get("wai") else "win"
            tag = "lost" if f.get("wai") else f.get("kind")
            rows.append((f["name"], f["pity"], key, tag, 5))
        else:
            rows.append((f["name"], f["pity"], "plain", None, 5))
    return rows


# ---------------------------------------------------------------- report ----
REPORT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500&family=Noto+Serif+TC:wght@400;500&family=Noto+Sans+TC:wght@400;500&display=swap');
*{box-sizing:border-box}
body{margin:0;padding:0;background:#0C0C18;color:#EDE7DA;
 font-family:'Noto Sans TC',sans-serif;line-height:1.7;
 background-image:radial-gradient(circle at 18% 12%,rgba(200,164,92,.10),transparent 42%),
  radial-gradient(circle at 82% 4%,rgba(110,106,138,.16),transparent 38%);
 background-attachment:fixed}
.wrap{max-width:1020px;margin:0 auto;padding:56px 32px 96px}
.hero{display:flex;align-items:flex-end;justify-content:space-between;gap:32px;flex-wrap:wrap}
h1{font-family:'Cinzel','Noto Serif TC',serif;font-weight:500;font-size:15px;letter-spacing:.32em;
 text-transform:uppercase;color:#C8A45C;margin:0 0 10px}
.verdict{font-family:'Noto Serif TC',serif;font-size:62px;line-height:1;font-weight:500;margin:0}
.reason{color:#9B97B5;font-size:14px;margin-top:10px;max-width:64ch}
.uid{text-align:right;font-size:13px;color:#6E6A8A}
.uid b{display:block;font-size:26px;color:#EDE7DA;font-weight:500;letter-spacing:.04em}
.rule{height:1px;background:linear-gradient(90deg,#C8A45C,rgba(200,164,92,0) 72%);margin:40px 0 32px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.plate{position:relative;background:rgba(255,255,255,.035);border:1px solid rgba(200,164,92,.20);
 padding:16px 18px}
.plate::before,.plate::after{content:'';position:absolute;width:7px;height:7px;border:1px solid #C8A45C}
.plate::before{top:-1px;left:-1px;border-right:0;border-bottom:0}
.plate::after{bottom:-1px;right:-1px;border-left:0;border-top:0}
.plate .k{font-size:12px;letter-spacing:.14em;color:#9B97B5}
.plate .v{font-family:'Cinzel',serif;font-size:30px;font-weight:500;margin-top:4px;
 font-variant-numeric:tabular-nums}
.plate .s{font-size:12px;color:#6E6A8A}
h2{font-family:'Noto Serif TC',serif;font-weight:500;font-size:21px;margin:0}
.sec{margin-top:48px}
.sechead{display:flex;align-items:baseline;gap:16px;border-bottom:1px solid rgba(200,164,92,.22);
 padding-bottom:10px;margin-bottom:8px;flex-wrap:wrap}
.sechead .meta{font-size:13px;color:#9B97B5;font-variant-numeric:tabular-nums}
.sechead .meta em{color:#C8A45C;font-style:normal}
.row{display:flex;align-items:center;gap:12px;padding:5px 0;
 animation:rise .5s cubic-bezier(.2,.7,.3,1) backwards}
@keyframes rise{from{opacity:0;transform:translateY(6px)}}
.av{width:34px;height:34px;flex:none;border-radius:50%;background:rgba(255,255,255,.05);
 border:1px solid rgba(200,164,92,.28);object-fit:cover}
.av.ph{display:flex;align-items:center;justify-content:center;color:#6E6A8A;font-size:15px}
.nm{width:118px;flex:none;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.track{flex:1;height:20px;background:rgba(255,255,255,.05)}
.fill{display:block;height:100%;transform-origin:left;
 animation:grow .8s cubic-bezier(.2,.7,.3,1) backwards}
@keyframes grow{from{transform:scaleX(0)}}
.pt{width:64px;flex:none;text-align:right;font-size:13px;color:#9B97B5;
 font-variant-numeric:tabular-nums}
.tg{width:44px;flex:none;font-size:12px;color:#6E6A8A}
.tg.w{color:#C46B6B}
.views{display:flex;gap:8px;margin-top:36px;flex-wrap:wrap}
.views button{background:transparent;border:1px solid rgba(200,164,92,.28);color:#9B97B5;
 padding:7px 15px;font:inherit;font-size:13px;cursor:pointer}
.views button:hover{color:#EDE7DA}
.views button.on{color:#0C0C18;background:#C8A45C;border-color:#C8A45C}
.list{display:flex;flex-direction:column}
body[data-v=five] .r4,body[data-v=five] .fourblock,body[data-v=five] .inv.f4{display:none}
body[data-v=split] .r4{order:2}
body[data-v=split] .sep{display:flex}
.sep{display:none;order:1;align-items:center;gap:12px;margin:16px 0 8px;
 color:#9A8BC4;font-size:12px}
.sep::after{content:'';flex:1;height:1px;background:rgba(124,107,168,.35)}
.rank{display:flex;flex-wrap:wrap;gap:10px;margin-top:6px}
.rank .c{display:flex;align-items:center;gap:9px;background:rgba(255,255,255,.035);
 border:1px solid rgba(124,107,168,.25);padding:7px 13px 7px 8px}
.rank .c img{width:30px;height:30px;border-radius:50%}
.rank .c b{font-family:'Cinzel',serif;font-weight:500;font-size:17px;color:#C8B6E6}
.legend{display:flex;gap:20px;font-size:12px;color:#9B97B5;margin:14px 0 6px}
.legend i{display:inline-block;width:22px;height:8px;margin-right:7px;vertical-align:1px}
.cols{display:grid;grid-template-columns:minmax(0,1fr) 314px;gap:36px;align-items:start}
aside{position:sticky;top:24px;max-height:calc(100vh - 48px);overflow-y:auto;
 padding-right:16px;scrollbar-gutter:stable;
 scrollbar-width:thin;scrollbar-color:rgba(200,164,92,.34) transparent}
aside::-webkit-scrollbar{width:6px}
aside::-webkit-scrollbar-track{background:transparent}
aside::-webkit-scrollbar-thumb{background:rgba(200,164,92,.34);border-radius:3px}
aside::-webkit-scrollbar-thumb:hover{background:rgba(200,164,92,.55)}
.inv{margin-bottom:26px}
.inv h3{font-family:'Noto Serif TC',serif;font-size:14px;font-weight:500;margin:0 0 8px;
 padding-bottom:7px;border-bottom:1px solid rgba(200,164,92,.22);
 display:flex;justify-content:space-between;align-items:baseline}
.inv h3 span{font-size:12px;color:#6E6A8A;font-family:'Cinzel',serif}
.inv.f4 h3{border-bottom-color:rgba(124,107,168,.32)}
.iv{display:flex;align-items:center;gap:8px;padding:3px 0;font-size:13px}
.iv img{width:24px;height:24px;border-radius:50%;flex:none;
 border:1px solid rgba(200,164,92,.24)}
.inv.f4 .iv img{border-color:rgba(124,107,168,.3)}
.iv .n{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.iv .q{font-family:'Cinzel',serif;font-size:14px;color:#C8A45C;font-variant-numeric:tabular-nums}
.inv.f4 .iv .q{color:#A492D0}
@media(max-width:920px){.cols{grid-template-columns:1fr}
 aside{position:static;max-height:none;overflow:visible}}
.foot{margin-top:64px;padding-top:18px;border-top:1px solid rgba(255,255,255,.08);
 font-size:12px;color:#6E6A8A}
"""


def _report_rows(pool_key, pool, icons, t):
    colors = {"win": GOLD, "wai": CRIMSON, "now": "#7A6A3E", "plain": DIM, "four": VIOLET}
    hard5 = HARD_PITY.get(pool_key, 90)
    out = []
    for i, (name, pity, key, tag, rank) in enumerate(rows_for(pool_key, pool, include_four=True)):
        # 四星的保底是 10 抽，跟五星共用分母會讓長條全部縮成一小截
        hard = FOUR_PITY if rank == 4 else hard5
        delay = min(i * 6, 500)
        pct = max(3, min(100, round(pity / hard * 100)))
        if name is None:
            av = '<span class="av ph">?</span>'
            label = t("row.current")
        else:
            meta = icons.get(name)
            av = (f'<img class="av" src="{meta["file"]}" alt="{t.name(name, icons)}" '
                  f'loading="lazy">' if meta else '<span class="av ph">·</span>')
            label = t.name(name, icons)
        tag_text = t(f"tag.{tag}") if tag in ("soft", "hard", "lost") else (
            t("row.ongoing") if tag == "ongoing" else "")
        out.append(
            f'<div class="row r{rank}" style="animation-delay:{delay}ms">{av}'
            f'<span class="nm">{label}</span>'
            f'<span class="track"><span class="fill" style="width:{pct}%;'
            f'background:{colors[key]};animation-delay:{delay}ms"></span></span>'
            f'<span class="pt">{t("pulls", n=pity)}</span>'
            f'<span class="tg{" w" if key == "wai" else ""}">{tag_text}</span></div>'
        )
    return "".join(out)


INV_BLOCKS = (
    ("five_char", ""),
    ("five_weapon", ""),
    ("four_char", " f4"),
    ("four_weapon", " f4"),
)


def _inventory(s, icons, t):
    """側欄清冊：四／五星 × 角色／武器，各自列出抽到幾個。"""
    out = []
    for key, extra in INV_BLOCKS:
        items = s.get("inventory", {}).get(key) or []
        if not items:
            continue
        rows = "".join(
            '<div class="iv">'
            + (f'<img src="{icons[i["name"]]["file"]}" alt="" loading="lazy">'
               if i["name"] in icons else '<span class="av ph">·</span>')
            + f'<span class="n">{t.name(i["name"], icons)}</span>'
            + f'<span class="q">{i["count"]}</span></div>'
            for i in items
        )
        total = sum(i["count"] for i in items)
        out.append(
            f'<div class="inv{extra}"><h3>{t(f"inv.{key}")}'
            f'<span>{t("inv.meta", kinds=len(items), total=total)}</span></h3>{rows}</div>'
        )
    return f'<aside>{"".join(out)}</aside>'


def build_report(s, data_dir, default_view="five", t=None):
    t = t or i18n.T(i18n.DEFAULT_LANG)
    icons = load_icons(data_dir)
    char = s["pools"].get("character", {})
    four = s.get("four_star", {})
    base_up = s.get("baseline_per_up", 90.3)

    plates = [
        (t("m.total"), f"{s['total_pulls']:,}",
         t("m.total.sub", five=s["rank_counts"]["5"], four=s["rank_counts"]["4"])),
        (t("m.per_five"), f"{char.get('avg_pity') or '—'}",
         t("m.per_five.sub", base=s["baseline_pity"])),
        (t("m.win"), f"{char.get('small_win_rate') or '—'}%",
         t("m.win.sub", win=char.get("small_win", 0), total=char.get("small_total", 0))),
        (t("m.per_up"), f"{char.get('avg_per_up') or '—'}",
         t("m.per_up.sub", base=base_up, cost=f"{char.get('cost_per_up') or 0:,}")),
        (t("m.pity"), f"{char.get('current_pity', 0)}",
         t("m.pity.sub", left=max(0, 90 - char.get("current_pity", 0)))),
        (t("m.dry"), f"{s['longest_dry_days']:.0f}", t("m.dry.sub")),
    ]
    plate_html = "".join(
        f'<div class="plate"><div class="k">{k}</div><div class="v">{v}</div>'
        f'<div class="s">{sub}</div></div>' for k, v, sub in plates
    )

    legend = (
        f'<div class="legend"><span><i style="background:{GOLD}"></i>{t("lg.win")}</span>'
        f'<span><i style="background:{CRIMSON}"></i>{t("lg.lost")}</span>'
        f'<span><i style="background:#7A6A3E"></i>{t("lg.now")}</span></div>'
    )

    views = "".join(
        f'<button data-v="{v}"{" class=\'on\'" if v == default_view else ""}>{t(f"v.{v}")}</button>'
        for v in VIEWS
    )

    sections = []
    for key in POOL_ORDER:
        pool = s["pools"].get(key)
        if not pool or not pool["pulls"]:
            continue
        bits = [t("sec.meta", pulls=f"{pool['pulls']:,}", five=pool["five_count"])]
        if pool.get("avg_pity"):
            bits.append(t("sec.avg", n=f'<em>{pool["avg_pity"]}</em>'))
        if pool.get("small_win_rate") is not None:
            bits.append(t("sec.winrate", n=f'<em>{pool["small_win_rate"]}</em>'))
        bits.append(t("sec.pity", n=f'<em>{pool["current_pity"]}</em>'))
        if pool.get("four_count"):
            bits.append(t("sec.four", n=pool["four_count"], avg=f'<em>{pool["avg_pity4"]}</em>'))
        sections.append(
            f'<section class="sec"><div class="sechead"><h2>{t(f"pool.{key}")}</h2>'
            f'<span class="meta">{t("sep").join(bits)}</span></div>'
            + (legend if key in ("character", "weapon") else "")
            + f'<div class="list"><div class="sep">{t("sep.four")}</div>'
            + _report_rows(key, pool, icons, t) + "</div></section>"
        )

    if four.get("total"):
        cards = "".join(
            '<span class="c">'
            + (f'<img src="{icons[it["name"]]["file"]}" alt="" loading="lazy">'
               if it["name"] in icons else '<span class="av ph">·</span>')
            + f'<span>{t.name(it["name"], icons)}<br><b>{it["count"]}</b></span></span>'
            for it in four["top"]
        )
        sections.append(
            f'<section class="sec fourblock"><div class="sechead"><h2>{t("four.title")}</h2>'
            f'<span class="meta">'
            + t("four.meta", total=four["total"], unique=four["unique"],
                avg=f'<em>{four["avg_pity"]}</em>')
            + f'</span></div><div class="rank">{cards}</div></section>'
        )

    label, reason = t.luck(s["luck_key"], avg=s.get("luck_avg"),
                           base=base_up, diff=s.get("luck_diff"))
    html_lang = "zh-Hant" if t.lang == "zh" else "en"
    return (
        f'<!DOCTYPE html><html lang="{html_lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{t("title")} ・ UID {s["uid"]}</title><style>{REPORT_CSS}</style></head>'
        f'<body data-v="{default_view}"><div class="wrap">'
        f'<div class="hero"><div><h1>{t("kicker")}</h1>'
        f'<p class="verdict">{label}</p><p class="reason">{reason}</p></div>'
        f'<div class="uid">{t("uid")}<b>{s["uid"]}</b>'
        f'{s["first_time"][:10]} — {s["last_time"][:10]}</div></div>'
        f'<div class="rule"></div><div class="grid">{plate_html}</div>'
        f'<div class="views">{views}</div>'
        f'<div class="cols"><div>{"".join(sections)}</div>{_inventory(s, icons, t)}</div>'
        + f'<p class="foot">'
        + t("foot", four=FOUR_PITY, total=f'{s["total_pulls"]:,}')
        + "</p></div>"
        "<script>const b=document.body,vs=document.querySelectorAll('.views button');"
        "vs.forEach(x=>x.onclick=()=>{b.dataset.v=x.dataset.v;"
        "vs.forEach(y=>y.classList.toggle('on',y===x))});</script>"
        "</body></html>"
    )


# ---------------------------------------------------------------- widget ----
def _widget_rows(pool_key, pool, limit, cls, t, icons):
    colors = {"win": W_WIN, "wai": W_WAI, "now": W_NOW, "plain": "#888780"}
    hard = HARD_PITY.get(pool_key, 90)
    out = []
    for name, pity, key, tag, _rank in rows_for(pool_key, pool, limit=limit):
        pct = max(4, min(100, round(pity / hard * 100)))
        if name is None:
            av, label = '<span class="av"></span>', t("row.current")
        else:
            # 同一個角色會出現很多次，圖示只在 <style> 裡定義一次再用 class 引用，
            # 直接內嵌 base64 會讓 widget 肥好幾倍
            av = f'<span class="av {cls[name]}"></span>' if name in cls else '<span class="av"></span>'
            label = t.name(name, icons)
        tag_text = t(f"tag.{tag}") if tag in ("soft", "hard", "lost") else (
            t("row.ongoing") if tag == "ongoing" else "")
        out.append(
            f'<div class="rw">{av}<span class="nm">{label}</span>'
            f'<span class="tk"><span class="fl" style="width:{pct}%;'
            f'background:{colors[key]}"></span></span>'
            f'<span class="pt">{t("pulls", n=pity)}</span>'
            f'<span class="tg">{tag_text}</span></div>'
        )
    return "".join(out)


def build_widget(s, data_dir, per_pool=6, four_top=5, t=None):
    t = t or i18n.T(i18n.DEFAULT_LANG)
    icons = load_icons(data_dir)
    char = s["pools"].get("character", {})
    weap = s["pools"].get("weapon", {})

    # 先掃過所有要畫的列，收集真正用得到的圖示，一個只留一份
    cls, sheet = {}, []
    for key in POOL_ORDER:
        pool = s["pools"].get(key)
        if not pool:
            continue
        for name, _, _, _, _ in rows_for(key, pool, limit=per_pool):
            if name and name in icons and name not in cls:
                cls[name] = f"g{len(cls)}"
                sheet.append(f'.{cls[name]}{{background-image:url({icons[name]["b64"]})}}')
    for it in s.get("four_star", {}).get("top", [])[:four_top]:
        if it["name"] in icons and it["name"] not in cls:
            cls[it["name"]] = f"g{len(cls)}"
            sheet.append(f'.{cls[it["name"]]}{{background-image:url({icons[it["name"]]["b64"]})}}')
    # 每列的樣式都一樣，重複寫成 inline 會讓片段肥一倍，所以抽成 class
    style = (
        "<style>"
        ".av{width:24px;height:24px;flex:none;border-radius:50%;"
        "background-color:var(--color-background-secondary);background-size:cover}"
        ".rw{display:flex;align-items:center;gap:9px;margin-bottom:5px}"
        ".nm{width:84px;flex:none;font-size:13px;color:var(--color-text-primary);"
        "overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
        ".tk{flex:1;height:16px;background:var(--color-background-secondary);"
        "border-radius:4px;overflow:hidden}"
        ".fl{display:block;height:100%;border-radius:4px}"
        ".pt{width:48px;flex:none;text-align:right;font-size:12px;color:var(--color-text-secondary)}"
        ".tg{width:42px;flex:none;font-size:11px;color:var(--color-text-tertiary);"
        "white-space:nowrap}"
        ".mc{background:var(--color-background-secondary);"
        "border-radius:var(--border-radius-md);padding:12px 14px}"
        ".mk{font-size:13px;color:var(--color-text-secondary)}"
        ".mv{font-size:24px;font-weight:500;color:var(--color-text-primary);margin-top:2px}"
        ".ms{font-size:11px;color:var(--color-text-tertiary);margin-top:2px}"
        ".ph{font-size:16px;font-weight:500;color:var(--color-text-primary)}"
        ".pm{font-size:12px;color:var(--color-text-secondary);margin:2px 0 9px}"
        ".lg{display:flex;gap:14px;font-size:12px;color:var(--color-text-secondary);"
        "margin-bottom:9px}"
        ".sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px}"
        ".rk{display:flex;flex-wrap:wrap;gap:8px}"
        ".rc{display:flex;align-items:center;gap:7px;background:var(--color-background-secondary);"
        "border-radius:var(--border-radius-md);padding:6px 11px 6px 7px;font-size:13px;"
        "color:var(--color-text-primary)}"
        + "".join(sheet) + "</style>"
    )

    base_up = s.get("baseline_per_up", 90.3)
    label, _reason = t.luck(s["luck_key"], avg=s.get("luck_avg"),
                            base=base_up, diff=s.get("luck_diff"))
    cards = [
        (t("m.verdict"), label, t("m.verdict.sub", base=base_up)),
        (t("m.total"), f"{s['total_pulls']:,}", t("m.five_count", n=s["rank_counts"]["5"])),
        (t("m.per_five"), t("pulls", n=char.get("avg_pity") or "—"),
         t("m.per_five.sub", base=s["baseline_pity"])),
        (t("m.win"), f"{char.get('small_win_rate') or '—'}%",
         t("m.win.sub", win=char.get("small_win", 0), total=char.get("small_total", 0))),
        (t("m.per_up"), t("pulls", n=char.get("avg_per_up") or "—"),
         t("m.per_up.sub_short", base=base_up)),
        (t("m.pity"), t("pulls", n=char.get("current_pity", 0)),
         t("m.pity.sub", left=max(0, 90 - char.get("current_pity", 0)))),
    ]
    card_html = "".join(
        f'<div class="mc"><div class="mk">{k}</div><div class="mv">{v}</div>'
        f'<div class="ms">{sub}</div></div>' for k, v, sub in cards
    )

    legend = (
        '<div class="lg">'
        f'<span><span class="sw" style="background:{W_WIN}"></span>{t("lg.win")}</span>'
        f'<span><span class="sw" style="background:{W_WAI}"></span>{t("lg.lost")}</span>'
        f'<span><span class="sw" style="background:{W_NOW}"></span>{t("lg.now")}</span></div>'
    )

    sections = []
    for key in POOL_ORDER:
        pool = s["pools"].get(key)
        if not pool or not pool["five_count"]:
            continue
        meta = t("sec.meta", pulls=f'{pool["pulls"]:,}', five=pool["five_count"])
        if pool.get("avg_pity"):
            meta += t("sep") + t("sec.avg", n=pool["avg_pity"])
        shown = min(per_pool, pool["five_count"])
        more = (f'<div class="ms">{t("more", n=shown)}</div>'
                if pool["five_count"] > per_pool else "")
        sections.append(
            '<div style="margin-top:1.5rem">'
            f'<div class="ph">{t(f"pool.{key}")}</div><div class="pm">{meta}</div>'
            + (legend if key in ("character", "weapon") else "")
            + _widget_rows(key, pool, per_pool, cls, t, icons) + more + "</div>"
        )

    four = s.get("four_star") or {}
    if four.get("total"):
        chips = "".join(
            f'<span class="rc"><span class="av {cls.get(it["name"], "")}"></span>'
            f'{t.name(it["name"], icons)} <b style="font-weight:500">{it["count"]}</b></span>'
            for it in four["top"][:four_top]
        )
        sections.append(
            f'<div style="margin-top:1.5rem"><div class="ph">{t("four.title")}</div>'
            f'<div class="pm">'
            + t("four.meta_short", total=four["total"], unique=four["unique"],
                avg=four["avg_pity"])
            + f'</div><div class="rk">{chips}</div></div>'
        )

    buttons = (
        '<div style="display:flex;gap:8px;margin-top:1.5rem">'
        f"<button onclick=\"sendPrompt('{t('btn.next.prompt')}')\">{t('btn.next')}</button>"
        f"<button onclick=\"sendPrompt('{t('btn.refetch.prompt')}')\">{t('btn.refetch')}</button>"
        "</div>"
    )

    return (
        f'<h2 class="sr-only">'
        + t("sr", uid=s["uid"], total=s["total_pulls"], avg=char.get("avg_pity"),
            win=char.get("small_win_rate"))
        + "</h2>"
        + style +
        '<div style="padding:1rem 0">'
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));'
        f'gap:12px">{card_html}</div>'
        + "".join(sections) + buttons + "</div>"
    )
