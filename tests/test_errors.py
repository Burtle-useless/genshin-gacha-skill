"""錯誤路徑：資料不存在或參數給錯時，要吐乾淨的 ERROR 訊息，不能噴 traceback。

使用者第一次跑一定是空的，這條路徑比正常路徑更常被走到。
"""
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import analyze
import fetch
import i18n

fails = []


def expect_exit(label, fn):
    """必須是 SystemExit 且訊息以 ERROR 開頭，不能是其他例外。"""
    try:
        fn()
    except SystemExit as exc:
        msg = str(exc.code)
        if not msg.startswith("ERROR"):
            fails.append(f"{label}: 訊息沒有 ERROR 前綴 -> {msg[:80]}")
    except Exception as exc:
        fails.append(f"{label}: 噴出 {type(exc).__name__} 而不是乾淨的 SystemExit -> {exc}")
    else:
        fails.append(f"{label}: 資料不存在卻沒有報錯")


def cli(args):
    return subprocess.run([sys.executable, str(SCRIPTS / "analyze.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp)
        for mod in (analyze, fetch):
            mod.DATA_DIR = empty

        for lang in i18n.LANGS:
            t = i18n.T(lang)
            expect_exit(f"analyze/{lang} 無紀錄檔", lambda: analyze.load_records(None, t))
            expect_exit(f"analyze/{lang} 找不到 UID", lambda: analyze.load_records("999", t))
        fetch.T = i18n.T("zh")
        expect_exit("fetch 無 url.txt", fetch.load_url)
        expect_exit("fetch 網址沒有 authkey",
                    lambda: fetch.build_session("https://example.com/x?lang=zh-tw"))

    for args, label in (
        (["--lang=fr"], "--lang 給錯"),
        (["--view=bogus"], "--view 給錯"),
    ):
        r = cli(args)
        if r.returncode == 0:
            fails.append(f"{label}: 竟然成功了")
        elif "ERROR" not in (r.stdout + r.stderr):
            fails.append(f"{label}: 沒有 ERROR 訊息 -> {(r.stdout + r.stderr)[:80]}")
        elif "Traceback" in r.stderr:
            fails.append(f"{label}: 噴了 traceback")

    if fails:
        print("FAIL")
        for f in fails:
            print(" -", f)
        sys.exit(1)
    print("PASS：空資料與錯誤參數都吐乾淨的 ERROR，沒有 traceback")


if __name__ == "__main__":
    main()
