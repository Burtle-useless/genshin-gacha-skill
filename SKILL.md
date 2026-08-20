---
name: genshin-gacha
description: 抓取並分析原神祈願（抽卡）紀錄。當使用者提到「抽卡紀錄」「祈願紀錄」「抽卡分析」「保底」「歪了沒」「四星命座」「原神 gacha」「wish history」，或要求取得祈願網址、統計出貨抽數、看歐非程度時使用。會自動從遊戲快取取出 authkey 網址、翻完所有卡池所有頁數、增量合併進本機 JSON、抓四五星頭像、算出統計並產出報表與對話內嵌面板。
---

# 原神祈願紀錄抓取與分析

四步，各自獨立可單跑。以下路徑相對於**本 skill 目錄**（`$s` 請換成實際位置，
Claude Code 通常在 `~/.claude/skills/genshin-gacha`、Codex CLI 在
`~/.codex/skills/genshin-gacha`）。資料一律放 `%LOCALAPPDATA%\genshin-gacha\`。

```powershell
& "$s\scripts\get_url.ps1"      # 1 取網址（會跳一次 UAC）
python "$s\scripts\fetch.py"    # 2 拉紀錄，增量合併
python "$s\scripts\icons.py"    # 3 抓四五星頭像（只在出現新角色時需要重跑）
python "$s\scripts\analyze.py"  # 4 算統計、出報表與 widget
```

參數：
- `--view=five|split|merge` 決定報表**開啟時**的預設檢視，三種檢視在網頁裡隨時可切換
- `--lang=zh|en` 覆寫語言；常設語言請改 `data/config.json`，或設環境變數
  `GENSHIN_GACHA_LANG`。優先序：`--lang` > 環境變數 > `config.json` > `zh`

## 環境需求

Windows（讀遊戲快取與 VSS 都是 Windows 專屬）、Python 3.9+、`requests`、`pillow`。
不需要任何 API key。

跟執行的 agent 無關——四個腳本都是獨立可跑的 CLI，Claude Code、Codex CLI
或手動執行都一樣。唯一有差別的是最後的呈現方式，見步驟 4。

## 前置

- 使用者必須**在遊戲內開過一次祈願紀錄頁面**，網址才會進快取。沒開過就抓不到。
- authkey 有效期約 24 小時，過期重跑步驟 1。
- 遊戲不用關。

## 步驟 1：取網址

從 `output_log.txt` 找遊戲路徑 → 挑最新的 `webCaches` 版本 → 讀 `Cache\Cache_Data\data_2`。

**這個檔被 `GenshinImpact.exe` 整場遊戲獨占鎖住**，直接讀必定失敗（sharing violation）。
腳本會自我提權用 `esentutl /y ... /vss /d` 從磁碟快照複製出來。這是必經之路，不是備案。

失敗訊息都以 `ERROR:` 開頭：
- `NO_LOG` — 找不到遊戲日誌，遊戲從沒跑過或裝在別處
- `NO_URL` — 快取裡沒有祈願網址，請使用者在遊戲內開一次祈願紀錄
- `LOCKED_NO_ADMIN` — UAC 被拒或 VSS 失敗，請使用者改成關掉遊戲後重跑

提權子行程的輸出讀不到，診斷看 `vss.log`（裡面的 `elevated=` 可確認是否真的提權成功）。

## 步驟 2：拉紀錄

用 `getConfigList` 動態列出卡池，**再聯集 `KNOWN_EXTRA_TYPES`**——實測 getConfigList 只回
「目前開著的」池，會漏掉 400（角色活動祈願-2）與 500（集錄祈願）。已探過 600~5000
沒有其他隱藏 id，不用再擴。

**三、四、五星全收**，不做過濾。增量合併進 `records_<UID>.json`，**只增不減**。
官方 API 只回得到近半年，舊紀錄過期就永久消失，所以這個檔越早開始累積越完整。
**永遠不要覆寫或刪除它。**

請求間隔 0.6 秒，別調小。

## 步驟 3：抓頭像

祈願 API 回的 `item_id` 是空字串，只能**用繁中名稱**對應圖鑑。
資料源是 `gi.yatta.moe`（`ambr.top` 的 DNS 已失效，別再用）。

四星與五星都抓（本機實例 78 個）。下載原圖到 `icons/` 給報表用，
同時產 24px WebP base64 進 `icon_map.json` 給 widget 用。

**圖鑑是每次執行即時抓的，新角色上架就會自動有圖，不需要使用者手動維護。**
真正需要人工更新的只有 `data/standard_pool.json`（判「歪」用的常駐池名單），跟圖片無關。

查不到的名字會**退成灰色圓標、名字照抓到的顯示**，不會壞掉也不會被吃掉。
這條有確定性防線：`tests/test_icon_fallback.py`，改渲染前後都要跑。

## 步驟 4：分析出圖

產出 `stats_<UID>.json`、`report_<UID>.html`、`widget_<UID>.html`。

報表有三種檢視，按鈕即時切換，**靠 CSS `order` 重排而不是複製 DOM**
（297 列複製三份太蠢，改版時別退回去）：
- `five` — 只看五星
- `split` — 五星在上，四星沉到下方並插入「以下為四星」分隔線
- `merge` — 四五星依時間交錯成單一時間軸

報表右側是常駐清冊側欄（`stats["inventory"]`），四個區塊各自列出每個名字抽到幾個：
五星角色／五星武器／四星角色／四星武器。**跨卡池合計**——「這隻抽到幾個」問的是總數。
四星那兩塊跟著檢視切換一起隱藏，`five` 檢視就真的只剩五星。
側欄 sticky 且自行捲動，920px 以下自動改為堆疊在下方。

**報表要直接開瀏覽器給使用者看**：`Start-Process chrome.exe <報表路徑>`。
把 `file:///` 連結貼進對話沒用，有些 agent 客戶端會自己接走，開不到外部瀏覽器。

widget 固定顯示：各池五星長條（每池最近 6 次）＋四星常客榜（前 5 名）。
**呈現方式看執行環境有沒有內嵌渲染工具**：
- 有的話（Claude Code 的 `mcp__visualize__show_widget`）：讀 `widget_<UID>.html`，
  原封不動當 `widget_code` 傳進去。不要自己重寫或順手美化。
- 沒有的話（Codex CLI 或直接跑腳本）：跳過 widget，直接開報表，
  重點數字用文字講。`widget_<UID>.html` 是片段不是完整網頁，單獨開會沒有樣式。

## 語言（改動前先讀）

**統計層完全不碰語言。** `stats.json` 只存 key 與數字（`luck_key="lucky"`、
`kind="soft"`、pool key `character`），文字一律在渲染時查 `scripts/i18n.py`。
好處是換語言不用重跑分析，資料檔也不會被某一種語言綁死。
**不要為了省事把翻好的字串寫回 stats。**

`fetch.py` **強制用 `lang=zh-tw` 抓紀錄**，不跟著玩家的遊戲語言跑。API 會照 lang
回傳角色名與 `item_type`，英文客戶端會回 `Character`／`Weapon`——那會讓圖鑑對照
與「角色/武器」分類同時失準。顯示語言另外由 i18n 決定，兩者不要混在一起。

角色武器的英文名是從 yatta 圖鑑的 en 版拿的，用 **icon 檔名當鍵**接回繁中名
（`奧黛塔` → `UI_AvatarIcon_Aino` → `Odette`）。查不到就沿用原名。

新增語言＝在 `i18n.py` 的 `S` 與 `LUCK` 加一組、把代碼加進 `LANGS`，其餘不用動。

## 跨 agent（Claude Code / Codex CLI）

四個腳本都是獨立 CLI，跟 agent 無關。唯一的差別在步驟 4 的呈現方式（見上）。

`install.ps1` 用**目錄 junction** 把同一份 repo 掛進 `~/.claude/skills` 與
`~/.codex/skills`。用 junction 不用 symlink 是因為 symlink 需要管理員權限或開發者模式，
junction 不用。單一來源，`git pull` 一次更新所有 agent。

SKILL.md 裡**不要寫死 `~/.claude` 路徑**，會讓 Codex 那邊的使用者照著跑就錯。

## 判定規則（改動前先讀）

**歐非要看「每個限定五星花幾抽」，不是「每個五星花幾抽」。**
後者不含歪掉的成本，歪再多都反映不出來。基準：
- 每個五星 62.3 抽
- 每個限定五星 90.3 抽（5.0 起捕獲明光把 UP 綜合機率拉到 55%）
- 93.45 抽是 5.0 之前經典 50/50 的舊值，只在分析更早的資料時才該用

**「歪」怎麼判**：抽到的五星在常駐池名單裡就是歪。名單是 `data/standard_pool.json`
**聯集使用者自己在常駐池（gacha_type 200）抽到的五星**——限定角色永遠不會出現在常駐池，
所以聯集不會誤判，而且會自我修正。

**四星不算歪不歪**：四星的 UP 判定需要逐期卡池名單，本機沒有那份資料。
只給「出了幾個、隔多久出一個、誰出最多」，**不要假裝算得出四星的 50/50**。

**角色池要合併 301 和 400**：同一個「角色活動祈願」拆成兩條並行池，保底共通。

**長條分母**：五星用各池硬保底（角色/常駐 90、武器 80），四星一律 10。
兩者混用同一個分母會讓四星全部縮成一小截。

## widget 大小紀律

widget 要逐字讀進上下文才能傳給 `show_widget`，**必須壓在 25000 字元以內**。
現況 23 KB，**已經很接近上限**，再加東西前務必先產出後量位元組數。

守住體積靠三件事：
1. 圖示 base64 在 `<style>` 裡每個只定義一次，用 class 引用（同一角色會出現很多次）
2. 每列樣式抽成 class，不寫 inline（重複 20 幾次差一倍體積）
3. 每池只顯示最近 6 次、四星只給前 5 名榜單

**四星逐筆列表刻意不進 widget**（297 列＋59 個圖示約 53 KB，必爆），只放在報表。

## 常見誤判

- 「抓不到網址」第一個確認**使用者有沒有在遊戲內開過祈願紀錄**，不是腳本壞了。
- 快取被鎖是常態（遊戲行程整場獨占），**不是**祈願頁面沒關。叫使用者關頁面沒有用。
- `Start-Process -Verb RunAs -ArgumentList` 傳陣列**不會自動加引號**，含空白的路徑
  （`Genshin Impact game`）會被切斷。已改成單一字串並自行加引號，別改回陣列。
- HTML 裡的進度條若用 `<span>`，一定要 `display:block`，否則 `height:100%` 無效、
  長條完全不顯示（非替換行內元素不吃 height）。這個 bug 看原始碼看不出來，只能開瀏覽器。
- `records_*.json` 比官方網頁少是正常的（官方只留近半年，本機留全部）；反過來才是 bug。
- 本機統計會跟「提瓦特小助手」之類的 App 對不上，因為那邊是雲端累積的全歷史。
  **保底進度、最近幾筆出貨抽數應該要完全一致**，不一致才是真的有問題。
