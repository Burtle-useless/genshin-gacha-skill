"""語言層。

設計前提：**統計層不碰語言**。`stats.json` 只存 key 與數字（例如 luck_key="lucky"、
pool key="character"），文字一律在渲染時才查表。這樣換語言不用重跑分析，
資料檔也不會被某一種語言綁死。

語言決定順序：--lang 參數 > 環境變數 GENSHIN_GACHA_LANG > data/config.json > zh
"""
import json
import os
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LANG = "zh"
LANGS = ("zh", "en")

S = {
    "zh": {
        "sep": " ・ ",
        "title": "祈願紀錄",
        "kicker": "Wish Records",
        "uid": "UID",
        # 卡池
        "pool.character": "角色活動祈願",
        "pool.weapon": "武器活動祈願",
        "pool.standard": "常駐祈願",
        "pool.chronicled": "集錄祈願",
        "pool.novice": "新手祈願",
        # 指標卡
        "m.total": "總抽數",
        "m.total.sub": "五星 {five} ・ 四星 {four}",
        "m.per_five": "每個五星",
        "m.per_five.sub": "理論值 {base} 抽",
        "m.win": "小保底不歪",
        "m.win.sub": "{win} / {total} 次 ・ 理論 55%",
        "m.per_up": "每個限定五星",
        "m.per_up.sub": "理論值 {base} 抽 ・ 約 {cost} 原石",
        "m.per_up.sub_short": "理論值 {base} 抽",
        "m.pity": "目前已墊",
        "m.pity.sub": "距硬保底 {left} 抽",
        "m.dry": "最久沒抽",
        "m.dry.sub": "天",
        "m.verdict": "歐非度",
        "m.verdict.sub": "限定金基準 {base} 抽",
        "m.five_count": "五星 {n} 個",
        "m.each_five": "每次出五星",
        # 檢視
        "v.five": "只看五星",
        "v.split": "四星分開",
        "v.merge": "合併時間軸",
        "sep.four": "以下為四星",
        # 列
        "row.current": "目前已墊",
        "row.ongoing": "進行中",
        "tag.soft": "小保底",
        "tag.hard": "大保底",
        "tag.lost": "歪",
        "pulls": "{n} 抽",
        # 圖例
        "lg.win": "抽到 UP",
        "lg.lost": "歪了",
        "lg.now": "目前保底進度",
        # 區段
        "sec.meta": "{pulls} 抽 ・ {five} 個五星",
        "sec.avg": "平均 {n} 抽",
        "sec.winrate": "不歪 {n}%",
        "sec.pity": "已墊 {n}",
        "sec.four": "四星 {n} 個／平均 {avg} 抽",
        "four.title": "四星常客",
        "four.meta": "{total} 個四星 ・ {unique} 種 ・ 平均 {avg} 抽出一個",
        "four.meta_short": "{total} 個四星 ・ {unique} 種 ・ 平均 {avg} 抽出一個",
        "more": "只顯示最近 {n} 次，完整清單在報表檔",
        # 側欄
        "inv.five_char": "五星角色",
        "inv.five_weapon": "五星武器",
        "inv.four_char": "四星角色",
        "inv.four_weapon": "四星武器",
        "inv.meta": "{kinds} 種 ・ {total} 個",
        # 按鈕
        "btn.next": "下一隻該不該抽 ↗",
        "btn.refetch": "重新抓取 ↗",
        "btn.next.prompt": "依我目前的保底進度，下一隻 UP 角色值得抽嗎",
        "btn.refetch.prompt": "把我的祈願紀錄再抓一次並更新分析",
        # 頁尾
        "foot": ("原石數＝抽數 × 160，未計入每日委託、紀行等收入。"
                 "四星長條的分母是 {four} 抽保底，五星是各池硬保底。"
                 "本機累計 {total} 抽；官方 API 只回得到近半年，更早的紀錄需靠長期累積。"),
        "sr": "UID {uid} 的原神祈願統計：共 {total} 抽，角色池平均 {avg} 抽出五星，小保底不歪率 {win}%。",
        # 指令列
        "cli.summary": "UID {uid} ・ {total} 抽 ・ {label}（{reason}）",
        "cli.pool": "  {label}：{pulls} 抽 / {five} 個五星 / 平均 {avg} / 已墊 {pity}",
        "cli.winrate": " / 不歪率 {n}%",
        "cli.report": "報表：{url}",
        "cli.others": "其他輸出：{stats}、{widget}（{kb} KB）",
        "cli.no_records": "ERROR: {dir} 下沒有紀錄檔，請先跑 fetch.py",
        "cli.no_uid": "ERROR: 找不到 UID {uid} 的紀錄檔",
        "cli.bad_lang": "ERROR: --lang 只能是 {opts}",
        "cli.bad_view": "ERROR: --view 只能是 {opts}",
        "cli.no_url": "ERROR: 找不到 {file}，請先跑 get_url.ps1",
        "cli.no_authkey": "ERROR: 網址裡沒有 authkey，重跑 get_url.ps1",
        "cli.expired": "ERROR: authkey 已過期或無效（retcode {code}），請重跑 get_url.ps1",
        "cli.api_error": "ERROR: API 回 retcode {code}: {msg}",
        "cli.types": "卡池類型：{types}",
        "cli.fetched": "  [{t}] {label}: {n} 筆",
        "cli.nothing": "ERROR: 一筆紀錄都沒抓到，authkey 可能已過期",
        "cli.merged": "本次抓到 {got} 筆，新增 {added} 筆",
        "cli.stored": "本機累計 {n} 筆 -> {file}",
        "cli.config_fallback": "WARN: getConfigList 失敗（{err}），改用後備名單",
        "cli.icons_need": "圖鑑 {total} 筆，需要 {n} 個四／五星圖示",
        "cli.icons_done": "完成 {n} 個圖示，base64 合計 {kb} KB -> {file}",
        "cli.icons_missing": "圖鑑查無此名（{n}）：{names}",
        "cli.icons_failed": "下載失敗（{n}）：{items}",
        "cli.icons_no_records": "ERROR: 沒有紀錄檔，請先跑 fetch.py",
    },
    "en": {
        "sep": " · ",
        "title": "Wish records",
        "kicker": "Wish Records",
        "uid": "UID",
        "pool.character": "Character event wish",
        "pool.weapon": "Weapon event wish",
        "pool.standard": "Standard wish",
        "pool.chronicled": "Chronicled wish",
        "pool.novice": "Beginners' wish",
        "m.total": "Total pulls",
        "m.total.sub": "{five} five-star · {four} four-star",
        "m.per_five": "Per five-star",
        "m.per_five.sub": "Expected {base} pulls",
        "m.win": "50/50 won",
        "m.win.sub": "{win} of {total} · expected 55%",
        "m.per_up": "Per featured five-star",
        "m.per_up.sub": "Expected {base} pulls · about {cost} primogems",
        "m.per_up.sub_short": "Expected {base} pulls",
        "m.pity": "Current pity",
        "m.pity.sub": "{left} pulls to hard pity",
        "m.dry": "Longest gap",
        "m.dry.sub": "days",
        "m.verdict": "Luck rating",
        "m.verdict.sub": "Baseline {base} pulls per featured",
        "m.five_count": "{n} five-star",
        "m.each_five": "per five-star",
        "v.five": "Five-star only",
        "v.split": "Four-star separate",
        "v.merge": "Merged timeline",
        "sep.four": "Four-star below",
        "row.current": "Current pity",
        "row.ongoing": "ongoing",
        "tag.soft": "50/50",
        "tag.hard": "guaranteed",
        "tag.lost": "lost",
        "pulls": "{n} pulls",
        "lg.win": "Won featured",
        "lg.lost": "Lost 50/50",
        "lg.now": "Current pity",
        "sec.meta": "{pulls} pulls · {five} five-star",
        "sec.avg": "avg {n} pulls",
        "sec.winrate": "{n}% won",
        "sec.pity": "pity {n}",
        "sec.four": "{n} four-star / avg {avg} pulls",
        "four.title": "Frequent four-stars",
        "four.meta": "{total} four-star · {unique} unique · one every {avg} pulls",
        "four.meta_short": "{total} four-star · {unique} unique · one every {avg} pulls",
        "more": "Showing the latest {n}; full list is in the report file",
        "inv.five_char": "Five-star characters",
        "inv.five_weapon": "Five-star weapons",
        "inv.four_char": "Four-star characters",
        "inv.four_weapon": "Four-star weapons",
        "inv.meta": "{kinds} unique · {total} total",
        "btn.next": "Should I pull next? ↗",
        "btn.refetch": "Refetch records ↗",
        "btn.next.prompt": "Given my current pity, is the next featured character worth pulling for?",
        "btn.refetch.prompt": "Fetch my wish history again and refresh the analysis",
        "foot": ("Primogems = pulls x 160, excluding dailies, Battle Pass and other income. "
                 "Four-star bars are scaled to the {four}-pull pity, five-star bars to each "
                 "banner's hard pity. {total} pulls stored locally; the official API only "
                 "returns about six months, so earlier records depend on long-term accumulation."),
        "sr": ("Genshin wish stats for UID {uid}: {total} pulls, {avg} pulls per five-star on the "
               "character banner, {win}% of 50/50s won."),
        "cli.summary": "UID {uid} · {total} pulls · {label} ({reason})",
        "cli.pool": "  {label}: {pulls} pulls / {five} five-star / avg {avg} / pity {pity}",
        "cli.winrate": " / {n}% won",
        "cli.report": "Report: {url}",
        "cli.others": "Also written: {stats}, {widget} ({kb} KB)",
        "cli.no_records": "ERROR: no record file in {dir}, run fetch.py first",
        "cli.no_uid": "ERROR: no record file for UID {uid}",
        "cli.bad_lang": "ERROR: --lang must be one of {opts}",
        "cli.bad_view": "ERROR: --view must be one of {opts}",
        "cli.no_url": "ERROR: {file} not found, run get_url.ps1 first",
        "cli.no_authkey": "ERROR: no authkey in the URL, rerun get_url.ps1",
        "cli.expired": "ERROR: authkey expired or invalid (retcode {code}), rerun get_url.ps1",
        "cli.api_error": "ERROR: API returned retcode {code}: {msg}",
        "cli.types": "Banner types: {types}",
        "cli.fetched": "  [{t}] {label}: {n} records",
        "cli.nothing": "ERROR: no records fetched at all, the authkey may have expired",
        "cli.merged": "Fetched {got} records, {added} new",
        "cli.stored": "{n} records stored locally -> {file}",
        "cli.config_fallback": "WARN: getConfigList failed ({err}), falling back to the known list",
        "cli.icons_need": "Catalog has {total} entries; {n} four/five-star icons needed",
        "cli.icons_done": "{n} icons ready, {kb} KB of base64 -> {file}",
        "cli.icons_missing": "Not found in catalog ({n}): {names}",
        "cli.icons_failed": "Download failed ({n}): {items}",
        "cli.icons_no_records": "ERROR: no record file, run fetch.py first",
    },
}

# 歐非等級：(標籤, 理由模板)。門檻在 analyze.py，這裡只管叫法。
LUCK = {
    "zh": {
        "blessed": ("極歐", "平均 {avg} 抽拿下一隻限定五星，理論值 {base} 抽，快了 {diff} 抽"),
        "lucky": ("歐", "平均 {avg} 抽拿下一隻限定五星，理論值 {base} 抽，快了 {diff} 抽"),
        "balanced": ("歐非守恆", "平均 {avg} 抽拿下一隻限定五星，理論值 {base} 抽，幾乎貼著理論值"),
        "unlucky": ("偏非", "平均 {avg} 抽拿下一隻限定五星，理論值 {base} 抽，慢了 {diff} 抽"),
        "cursed": ("非", "平均 {avg} 抽拿下一隻限定五星，理論值 {base} 抽，慢了 {diff} 抽"),
        "unknown": ("資料不足", "還沒抽到限定五星，算不出來"),
    },
    "en": {
        "blessed": ("Blessed", "{avg} pulls per featured five-star against a {base} baseline, {diff} ahead"),
        "lucky": ("Lucky", "{avg} pulls per featured five-star against a {base} baseline, {diff} ahead"),
        "balanced": ("Balanced", "{avg} pulls per featured five-star against a {base} baseline, right on target"),
        "unlucky": ("Unlucky", "{avg} pulls per featured five-star against a {base} baseline, {diff} behind"),
        "cursed": ("Cursed", "{avg} pulls per featured five-star against a {base} baseline, {diff} behind"),
        "unknown": ("Not enough data", "No featured five-star pulled yet"),
    },
}


def resolve_lang(cli_value=None):
    for candidate in (cli_value, os.environ.get("GENSHIN_GACHA_LANG"), _config_lang()):
        if candidate in LANGS:
            return candidate
    return DEFAULT_LANG


def _config_lang():
    f = SKILL_DIR / "data" / "config.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("lang")
    except Exception:
        return None


class T:
    """查表器。缺 key 時直接回 key 本身，寧可畫面難看也不要整份炸掉。"""

    def __init__(self, lang):
        self.lang = lang if lang in LANGS else DEFAULT_LANG

    def __call__(self, key, **kw):
        text = S[self.lang].get(key) or S[DEFAULT_LANG].get(key) or key
        return text.format(**kw) if kw else text

    def luck(self, key, **kw):
        label, reason = LUCK[self.lang].get(key) or LUCK[DEFAULT_LANG]["unknown"]
        return label, reason.format(**kw)

    def name(self, raw, icons):
        """角色／武器名稱。英文版查圖鑑的英文名，查不到就沿用原名。"""
        if self.lang == "zh":
            return raw
        return (icons.get(raw) or {}).get("en") or raw
