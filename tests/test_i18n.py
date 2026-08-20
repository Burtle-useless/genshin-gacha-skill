"""語言表完整性。

缺一個 key 不會馬上炸，只有在剛好渲染到那個畫面時才露出來（而且是靜默顯示成
key 本身），所以這裡用靜態掃描擋住：程式碼裡用到的每個 key，兩種語言都要有。
"""
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import analyze
import i18n
import render

# 動態組出來的 key（f"pool.{key}" 這種），靜態掃不到，這裡逐一列舉展開
DYNAMIC = (
    [f"pool.{k}" for k in set(analyze.POOL_OF.values())]
    + [f"v.{v}" for v in render.VIEWS]
    + [f"tag.{k}" for k in ("soft", "hard", "lost")]
    + [f"inv.{k}" for k, _ in render.INV_BLOCKS]
)


def used_keys():
    keys = set(DYNAMIC)
    pattern = re.compile(r"""\bt\(\s*["']([a-z][a-z0-9_.]*)["']""")
    for f in (SKILL / "scripts").glob("*.py"):
        if f.name == "i18n.py":
            continue
        keys |= set(pattern.findall(f.read_text(encoding="utf-8")))
    # T(...) 建構子會被誤抓，剔除明顯不是 key 的
    return {k for k in keys if "." in k or k in ("pulls", "sep", "title", "kicker", "uid")}


def main():
    fails = []

    zh, en = set(i18n.S["zh"]), set(i18n.S["en"])
    if zh - en:
        fails.append(f"en 缺少 {len(zh - en)} 個 key：{sorted(zh - en)}")
    if en - zh:
        fails.append(f"zh 缺少 {len(en - zh)} 個 key：{sorted(en - zh)}")

    for lang in i18n.LANGS:
        missing = sorted(k for k in used_keys() if k not in i18n.S[lang])
        if missing:
            fails.append(f"{lang} 沒有程式用到的 key：{missing}")

    # 歐非等級：analyze 可能吐出的每個 key，兩種語言都要有對應說法
    ratings = {"blessed", "lucky", "balanced", "unlucky", "cursed", "unknown"}
    produced = {analyze.luck_key(v) for v in (None, 0, 50, 75, 85, 95, 105, 130)}
    if not produced <= ratings:
        fails.append(f"luck_key 吐出未預期的值：{produced - ratings}")
    for lang in i18n.LANGS:
        missing = sorted(ratings - set(i18n.LUCK[lang]))
        if missing:
            fails.append(f"{lang} 的 LUCK 缺少：{missing}")

    # 每個等級的理由模板都要能吃下全部參數，不能有漏帶的欄位
    for lang in i18n.LANGS:
        for key in ratings:
            try:
                i18n.T(lang).luck(key, avg=74.7, base=90.3, diff=16)
            except KeyError as exc:
                fails.append(f"{lang}/{key} 的理由模板有未提供的欄位 {exc}")

    if fails:
        print("FAIL")
        for f in fails:
            print(" -", f)
        sys.exit(1)
    print(f"PASS：zh/en 各 {len(zh)} 個 key 對齊，{len(used_keys())} 個使用中的 key 全部有翻譯")


if __name__ == "__main__":
    main()
