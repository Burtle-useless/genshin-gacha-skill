"""拉完所有卡池的祈願紀錄，增量合併進本機 JSON。

官方 API 只回得到近半年的紀錄，過期就永久消失，所以本機這份檔只增不減。
"""
import json
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n

# Windows 主控台預設 CP950，不改的話中文輸出會變亂碼
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

T = i18n.T(i18n.resolve_lang())  # main() 解析 --lang 後可能重設

DATA_DIR = Path.home() / "AppData" / "Local" / "genshin-gacha"
PAGE_SIZE = 20
# 官方會限流，間隔別調小
REQUEST_GAP = 0.6

# getConfigList 失效時的後備名單。正常情況不會用到——動態列出才跟得上新卡池。
FALLBACK_TYPES = ["100", "200", "301", "302", "500"]

# getConfigList 只回「目前開著的」卡池，實測會漏掉 400（角色活動祈願-2）與
# 500（集錄祈願）。這兩個一定要補進候選，沒資料時只是多兩次空請求，很便宜。
# 已實測探過 600~5000 沒有其他隱藏 id，不用再擴。
KNOWN_EXTRA_TYPES = ["400", "500"]


def load_url() -> str:
    url_file = DATA_DIR / "url.txt"
    if not url_file.exists():
        sys.exit(T("cli.no_url", file=url_file))
    return url_file.read_text(encoding="ascii").strip()


def build_session(url: str):
    """從快取抓到的網址拆出 host 與驗證參數，其餘查詢參數丟掉。"""
    parsed = urlparse(url)
    q = parse_qs(parsed.query)

    def one(key, default=None):
        return q.get(key, [default])[0]

    authkey = one("authkey")
    if not authkey:
        sys.exit(T("cli.no_authkey"))

    base = f"{parsed.scheme}://{parsed.netloc}/gacha_info/api"
    params = {
        "authkey": authkey,
        "authkey_ver": one("authkey_ver", "1"),
        "sign_type": one("sign_type", "2"),
        # 一律用 zh-tw 存，不跟著玩家的遊戲語言跑。API 會照 lang 回傳角色名與
        # item_type，若隨客戶端變動（英文客戶端會回 Character／Weapon），
        # 圖鑑對照與「角色/武器」分類就會全部失準。顯示語言另由 i18n 決定。
        "lang": "zh-tw",
        "game_biz": one("game_biz", "hk4e_global"),
    }
    region = one("region")
    if region:
        params["region"] = region
    return base, params


def api_get(base, endpoint, params):
    r = requests.get(f"{base}/{endpoint}", params=params, timeout=20)
    r.raise_for_status()
    body = r.json()
    if body.get("retcode") != 0:
        code = body.get("retcode")
        msg = body.get("message", "")
        if code in (-101, -100):
            sys.exit(T("cli.expired", code=code))
        sys.exit(T("cli.api_error", code=code, msg=msg))
    return body.get("data") or {}


def list_gacha_types(base, params):
    """動態列出當前所有卡池類型，新卡池（如千星奇域）才不會被漏掉。"""
    try:
        data = api_get(base, "getConfigList", dict(params))
        types = [t["key"] for t in data.get("gacha_type_list", [])]
        names = {t["key"]: t.get("name", t["key"]) for t in data.get("gacha_type_list", [])}
        if types:
            return types, names
    except SystemExit:
        raise
    except Exception as exc:
        print(T("cli.config_fallback", err=exc))
    return list(FALLBACK_TYPES), {t: t for t in FALLBACK_TYPES}


def fetch_type(base, params, gacha_type, label):
    """翻完單一卡池的所有頁。end_id 游標往回翻，回空陣列就結束。"""
    out = []
    end_id = "0"
    page = 1
    while True:
        p = dict(params)
        p.update({
            "gacha_type": gacha_type,
            "page": str(page),
            "size": str(PAGE_SIZE),
            "end_id": end_id,
        })
        data = api_get(base, "getGachaLog", p)
        batch = data.get("list") or []
        if not batch:
            break
        out.extend(batch)
        end_id = batch[-1]["id"]
        page += 1
        time.sleep(REQUEST_GAP)
    print(T("cli.fetched", t=gacha_type, label=label, n=len(out)))
    return out


def main():
    global T
    lang = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--lang=")), None)
    T = i18n.T(i18n.resolve_lang(lang))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    base, params = build_session(load_url())

    types, names = list_gacha_types(base, params)
    for extra in KNOWN_EXTRA_TYPES:
        if extra not in types:
            types.append(extra)
    print(T("cli.types", types=", ".join(f"{x}={names.get(x, x)}" for x in types)))

    fetched = []
    for gacha_type in types:
        fetched.extend(fetch_type(base, params, gacha_type, names.get(gacha_type, gacha_type)))

    if not fetched:
        sys.exit(T("cli.nothing"))

    uid = fetched[0]["uid"]
    store_file = DATA_DIR / f"records_{uid}.json"

    # 只增不減：舊檔先讀進來，新資料以 id 為鍵覆蓋合併
    store = {"uid": uid, "pool_names": {}, "records": {}}
    if store_file.exists():
        store = json.loads(store_file.read_text(encoding="utf-8"))
        store.setdefault("records", {})
        store.setdefault("pool_names", {})

    before = len(store["records"])
    for rec in fetched:
        store["records"][rec["id"]] = rec
    store["pool_names"].update(names)
    added = len(store["records"]) - before

    store_file.write_text(
        json.dumps(store, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    print(f"\nUID {uid}")
    print(T("cli.merged", got=len(fetched), added=added))
    print(T("cli.stored", n=len(store["records"]), file=store_file))


if __name__ == "__main__":
    main()
