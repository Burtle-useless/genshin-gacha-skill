"""圖鑑查不到的新角色，必須退成灰色圓標且名字照抓到的顯示。

這是保險機制的確定性防線：新角色上線到圖鑑收錄之間一定有空窗，那段期間
report 與 widget 都不准壞掉、也不准把名字吃掉。
"""
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import render

DATA_DIR = Path.home() / "AppData" / "Local" / "genshin-gacha"
UNKNOWN = "測試用未收錄角色"


def load_stats():
    f = next(DATA_DIR.glob("stats_*.json"), None)
    if not f:
        sys.exit("SKIP: 本機沒有 stats_*.json，請先跑 analyze.py")
    return json.loads(f.read_text(encoding="utf-8"))


def main():
    stats = load_stats()
    char = stats["pools"]["character"]
    # 把最新一筆五星改成圖鑑一定查不到的名字
    char["fives"][-1]["name"] = UNKNOWN

    icons = render.load_icons(DATA_DIR)
    assert UNKNOWN not in icons, "測試名稱竟然存在於圖鑑，換一個"

    widget = render.build_widget(stats, DATA_DIR)
    report = render.build_report(stats, DATA_DIR)

    fails = []
    # 1. 名字必須照顯示
    if UNKNOWN not in widget:
        fails.append("widget 沒顯示未收錄角色的名字")
    if UNKNOWN not in report:
        fails.append("report 沒顯示未收錄角色的名字")

    # 2. 必須退成沒有圖片 class 的灰標，不能引用到別人的圖
    row = widget.split(UNKNOWN)[0].rsplit('<div class="rw', 1)[-1]
    if 'class="av"' not in row:
        fails.append(f"widget 未退成灰標，該列為：{row[:120]}")

    rrow = report.split(UNKNOWN)[0].rsplit('<div class="row', 1)[-1]
    if 'class="av ph"' not in rrow:
        fails.append(f"report 未退成灰標，該列為：{rrow[:120]}")

    # 3. 不准為了缺圖就整列消失（用 class 前綴比對，樣式類名改了也不會誤報）
    if 'class="rw' not in widget:
        fails.append("widget 沒有任何資料列")
    if 'class="row' not in report:
        fails.append("report 沒有任何資料列")

    if fails:
        print("FAIL")
        for f in fails:
            print(" -", f)
        sys.exit(1)
    print(f"PASS：未收錄角色「{UNKNOWN}」在 report 與 widget 都退成灰標且名字正常顯示")


if __name__ == "__main__":
    main()
