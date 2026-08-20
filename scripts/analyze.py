"""分析本機累積的祈願紀錄，產出統計 JSON、完整報表 HTML、內嵌 widget 片段。

只負責算數字；畫面全部交給 render.py。
"""
import collections
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n
import render

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = Path.home() / "AppData" / "Local" / "genshin-gacha"
SKILL_DIR = Path(__file__).resolve().parent.parent
PULL_COST = 160  # 一抽 160 原石

# 301 和 400 是同一個「角色活動祈願」拆成的兩條並行池，保底共通，一定要合併算
POOL_OF = {
    "100": "novice",
    "200": "standard",
    "301": "character",
    "400": "character",
    "302": "weapon",
    "500": "chronicled",
}
# 角色池平均「每個五星」的期望抽數（含軟保底）
BASELINE_PITY = 62.3
# 平均「每個限定五星」的期望抽數——歐非要看這個，不是上面那個。
# 兩者差在 50/50：歪掉的那次也要算進成本裡。
#   經典 50/50：62.3 × (0.5×1 + 0.5×2) = 93.45 抽
#   5.0 起的捕獲明光把 UP 綜合機率拉到 55%：62.3 × (0.55×1 + 0.45×2) = 90.3 抽
BASELINE_PER_UP = 90.3
BASELINE_PER_UP_LEGACY = 93.45


def load_records(uid=None, t=None):
    t = t or i18n.T(i18n.DEFAULT_LANG)
    files = sorted(DATA_DIR.glob("records_*.json"))
    if not files:
        sys.exit(t("cli.no_records", dir=DATA_DIR))
    if uid:
        files = [f for f in files if uid in f.name]
        if not files:
            sys.exit(t("cli.no_uid", uid=uid))
    store = json.loads(files[0].read_text(encoding="utf-8"))
    recs = list(store["records"].values())
    recs.sort(key=lambda r: int(r["id"]))
    return store["uid"], recs


def split_pools(recs):
    pools = {}
    for r in recs:
        pools.setdefault(POOL_OF.get(r["gacha_type"], "other"), []).append(r)
    return pools


def rank_entries(pool_recs, rank):
    """回傳該星級每次出貨的間隔抽數，以及目前已墊幾抽。

    四星與五星算法相同：間隔是「距上一次同星級出貨隔了幾抽」，
    中間夾到的其他星級照樣算一抽。
    """
    out, since = [], 0
    for r in pool_recs:
        since += 1
        if r["rank_type"] == rank:
            out.append({
                "name": r["name"],
                "item_type": r["item_type"],
                "time": r["time"],
                "pity": since,
            })
            since = 0
    return out, since


def build_standard_set(pools):
    """常駐五星名單：種子清單 ∪ 使用者自己在常駐池抽到的五星。

    限定角色永遠不會出現在常駐池，所以這個聯集不會誤判，而且會自我修正。
    """
    seed = json.loads((SKILL_DIR / "data" / "standard_pool.json").read_text(encoding="utf-8"))
    names = set(seed["characters"]) | set(seed["weapons"])
    for r in pools.get("standard", []):
        if r["rank_type"] == "5":
            names.add(r["name"])
    return names


def mark_wai(fives, standard_set):
    """標記每次五星是小保底還是大保底、有沒有歪。"""
    guaranteed = False
    for f in fives:
        if guaranteed:
            f["kind"] = "hard"   # 大保底
            f["wai"] = False
            guaranteed = False
        else:
            f["kind"] = "soft"   # 小保底
            f["wai"] = f["name"] in standard_set
            guaranteed = f["wai"]
    return fives


def max_streak(flags, want):
    best = cur = 0
    for v in flags:
        cur = cur + 1 if v == want else 0
        best = max(best, cur)
    return best


def luck_key(avg_per_up):
    """歐非以「每個限定五星花多少抽」為準，不是「每個五星花多少抽」。

    後者不含歪掉的成本，歪再多都反映不出來，拿來評歐非會失真。
    只回 key，叫什麼名字是語言層的事（見 i18n.LUCK）。

    中間三段刻意不對稱：守恆帶 ±8%，兩側各 12%。抽卡樣本小、波動大，
    帶子太窄評價會一直跳。
    """
    if not avg_per_up:
        return "unknown"
    ratio = avg_per_up / BASELINE_PER_UP
    if ratio < 0.80:
        return "blessed"
    if ratio < 0.92:
        return "lucky"
    if ratio < 1.08:
        return "balanced"
    if ratio < 1.20:
        return "unlucky"
    return "cursed"


def longest_dry_spell(recs):
    fmt = "%Y-%m-%d %H:%M:%S"
    best, when = 0.0, None
    for a, b in zip(recs, recs[1:]):
        gap = (datetime.strptime(b["time"], fmt) - datetime.strptime(a["time"], fmt)).total_seconds()
        if gap > best:
            best, when = gap, a["time"]
    # 最後一抽到現在也算一段空窗
    if recs:
        tail = (datetime.now() - datetime.strptime(recs[-1]["time"], fmt)).total_seconds()
        if tail > best:
            best, when = tail, recs[-1]["time"]
    return best / 86400, when


def analyze(uid, recs):
    pools = split_pools(recs)
    standard_set = build_standard_set(pools)

    stats = {
        "uid": uid,
        "total_pulls": len(recs),
        "first_time": recs[0]["time"],
        "last_time": recs[-1]["time"],
        "rank_counts": {k: sum(1 for r in recs if r["rank_type"] == k) for k in ("5", "4", "3")},
        "pools": {},
    }

    dry_days, dry_from = longest_dry_spell(recs)
    stats["longest_dry_days"] = round(dry_days, 1)
    stats["longest_dry_from"] = dry_from

    for pool, pool_recs in pools.items():
        if pool == "other":
            continue
        fives, current = rank_entries(pool_recs, "5")
        fours, current4 = rank_entries(pool_recs, "4")
        entry = {
            "pulls": len(pool_recs),
            "current_pity": current,
            "five_count": len(fives),
            "avg_pity": round(statistics.mean(f["pity"] for f in fives), 1) if fives else None,
            "fives": fives,
            "four_count": len(fours),
            "current_pity4": current4,
            "avg_pity4": round(statistics.mean(f["pity"] for f in fours), 1) if fours else None,
            "fours": fours,
        }

        if pool in ("character", "weapon"):
            mark_wai(fives, standard_set)
            small = [f for f in fives if f["kind"] == "soft"]
            up = [f for f in fives if not f["wai"]]
            entry["small_total"] = len(small)
            entry["small_win"] = sum(1 for f in small if not f["wai"])
            entry["small_win_rate"] = round(entry["small_win"] / len(small) * 100, 1) if small else None
            entry["up_count"] = len(up)
            consumed = len(pool_recs) - current
            entry["avg_per_up"] = round(consumed / len(up), 1) if up else None
            entry["cost_per_up"] = round(consumed / len(up) * PULL_COST) if up else None
            flags = [f["wai"] for f in small]
            entry["max_win_streak"] = max_streak(flags, False)
            entry["max_wai_streak"] = max_streak(flags, True)

        stats["pools"][pool] = entry

    # 四星彙總。四星的 UP 判定需要逐期卡池名單，本機沒有那份資料，
    # 所以只給「出了幾個、隔多久出一個、誰出最多」，不假裝算得出四星歪不歪。
    fours_all = [f for p in stats["pools"].values() for f in p["fours"]]
    counter = collections.Counter(f["name"] for f in fours_all)
    kinds = {f["name"]: f["item_type"] for f in fours_all}
    stats["four_star"] = {
        "total": len(fours_all),
        "unique": len(counter),
        "avg_pity": round(statistics.mean(f["pity"] for f in fours_all), 1) if fours_all else None,
        "top": [{"name": n, "count": c, "item_type": kinds[n]} for n, c in counter.most_common(8)],
    }

    # 側欄清冊：四／五星 × 角色／武器 四個區塊，各自列出每個名字抽到幾個。
    # 跨卡池合計——「這隻抽到幾個」問的是總數，不是在哪個池抽到的。
    inventory = {}
    for rank_key, field in (("five", "fives"), ("four", "fours")):
        items = [f for p in stats["pools"].values() for f in p[field]]
        for kind_key, kind in (("char", "角色"), ("weapon", "武器")):
            c = collections.Counter(f["name"] for f in items if f["item_type"] == kind)
            inventory[f"{rank_key}_{kind_key}"] = [
                {"name": n, "count": k} for n, k in c.most_common()
            ]
    stats["inventory"] = inventory

    char = stats["pools"].get("character", {})
    avg_up = char.get("avg_per_up")
    stats["luck_key"] = luck_key(avg_up)
    stats["luck_avg"] = avg_up
    stats["luck_diff"] = round(abs(avg_up - BASELINE_PER_UP)) if avg_up else None
    stats["baseline_pity"] = BASELINE_PITY
    stats["baseline_per_up"] = BASELINE_PER_UP
    stats["baseline_per_up_legacy"] = BASELINE_PER_UP_LEGACY
    return stats


def main():
    # 用法：analyze.py [UID] [--view=five|split|merge]
    # --view 只決定報表開啟時的預設檢視，三種檢視在網頁裡隨時可按鈕切換
    # --lang 覆寫 data/config.json 的設定
    view, lang, rest = "five", None, []
    for a in sys.argv[1:]:
        if a.startswith("--view="):
            view = a.split("=", 1)[1]
        elif a.startswith("--lang="):
            lang = a.split("=", 1)[1]
        else:
            rest.append(a)

    if lang is not None and lang not in i18n.LANGS:
        sys.exit(i18n.T(i18n.DEFAULT_LANG)("cli.bad_lang", opts="／".join(i18n.LANGS)))
    t = i18n.T(i18n.resolve_lang(lang))
    if view not in render.VIEWS:
        sys.exit(t("cli.bad_view", opts="／".join(render.VIEWS)))

    uid, recs = load_records(rest[0] if rest else None, t)
    stats = analyze(uid, recs)

    (DATA_DIR / f"stats_{uid}.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    (DATA_DIR / f"report_{uid}.html").write_text(
        render.build_report(stats, DATA_DIR, view, t), encoding="utf-8")
    (DATA_DIR / f"widget_{uid}.html").write_text(
        render.build_widget(stats, DATA_DIR, t=t), encoding="utf-8")

    label, reason = t.luck(stats["luck_key"], avg=stats["luck_avg"],
                           base=stats["baseline_per_up"], diff=stats["luck_diff"])
    print(t("cli.summary", uid=uid, total=f"{stats['total_pulls']:,}",
            label=label, reason=reason))
    for key in render.POOL_ORDER:
        p = stats["pools"].get(key)
        if not p or not p["pulls"]:
            continue
        line = t("cli.pool", label=t(f"pool.{key}"), pulls=f"{p['pulls']:,}",
                 five=p["five_count"], avg=p["avg_pity"], pity=p["current_pity"])
        if p.get("small_win_rate") is not None:
            line += t("cli.winrate", n=p["small_win_rate"])
        print(line)

    widget = DATA_DIR / f"widget_{uid}.html"
    report = DATA_DIR / f"report_{uid}.html"
    # 直接給可點的網址，不要讓人自己去拼路徑
    print(t("cli.report", url=f"file:///{report.as_posix()}"))
    print(t("cli.others", stats=f"stats_{uid}.json", widget=widget.name,
            kb=f"{widget.stat().st_size / 1024:.0f}"))


if __name__ == "__main__":
    main()
