"""抓取四／五星角色與武器頭像，快取到本機，並產出給 widget 用的 base64 縮圖。

祈願 API 回傳的 item_id 是空字串，只能用繁中名稱對應——所以對不上的名字一律
印出來，不要靜默跳過，否則報表會默默少一堆圖。

順便建立繁中 → 英文的名稱對照：兩份圖鑑都有 icon 檔名，拿它當鍵就能接起來。
"""
import base64
import io
import json
import sys
from pathlib import Path

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = Path.home() / "AppData" / "Local" / "genshin-gacha"
ICON_DIR = DATA_DIR / "icons"
# ambr.top 的 DNS 已失效，gi.yatta.moe 是同一個服務的可用網域
BASE = "https://gi.yatta.moe"
THUMB_PX = 24  # widget 走 base64 內嵌，尺寸直接決定 token 成本


def load_catalog():
    """繁中名 -> {icon, en}。角色與武器合併成一張表。"""
    table, english = {}, {}
    for kind in ("avatar", "weapon"):
        for locale, sink in (("cht", table), ("en", english)):
            r = requests.get(f"{BASE}/api/v2/{locale}/{kind}", timeout=30)
            r.raise_for_status()
            for item in r.json()["data"]["items"].values():
                if sink is table:
                    table[item["name"]] = {"icon": item["icon"], "en": None}
                else:
                    english[item["icon"]] = item["name"]
    for meta in table.values():
        meta["en"] = english.get(meta["icon"])
    return table


def wanted_names(records_file):
    """四星也要抓——報表的四星區、合併時間軸與側欄清冊都會用到。"""
    store = json.loads(records_file.read_text(encoding="utf-8"))
    return {r["name"] for r in store["records"].values() if r["rank_type"] in ("4", "5")}


def main():
    lang = i18n.resolve_lang(
        next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--lang=")), None))
    t = i18n.T(lang)

    files = sorted(DATA_DIR.glob("records_*.json"))
    if not files:
        sys.exit(t("cli.icons_no_records"))

    ICON_DIR.mkdir(parents=True, exist_ok=True)
    table = load_catalog()
    names = wanted_names(files[0])
    print(t("cli.icons_need", total=len(table), n=len(names)))

    out, missing, failed = {}, [], []
    for name in sorted(names):
        meta = table.get(name)
        if not meta:
            missing.append(name)
            continue
        icon = meta["icon"]

        png = ICON_DIR / f"{icon}.png"
        if not png.exists():
            resp = requests.get(f"{BASE}/assets/UI/{icon}.png", timeout=30)
            if resp.status_code != 200:
                failed.append(f"{name}({icon}) HTTP {resp.status_code}")
                continue
            png.write_bytes(resp.content)

        img = Image.open(png).convert("RGBA")
        img.thumbnail((THUMB_PX, THUMB_PX), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=45, method=6)
        out[name] = {
            "icon": icon,
            "en": meta["en"],
            "file": f"icons/{icon}.png",
            "b64": "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode(),
        }

    (DATA_DIR / "icon_map.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    total_kb = sum(len(v["b64"]) for v in out.values()) / 1024
    print(t("cli.icons_done", n=len(out), kb=f"{total_kb:.0f}",
            file=DATA_DIR / "icon_map.json"))
    no_en = [n for n, v in out.items() if not v["en"]]
    if no_en:
        print(f"WARN: {len(no_en)} 個名稱沒有英文對照：{'、'.join(no_en)}")
    if missing:
        print(t("cli.icons_missing", n=len(missing), names="、".join(missing)))
    if failed:
        print(t("cli.icons_failed", n=len(failed), items="; ".join(failed)))


if __name__ == "__main__":
    main()
