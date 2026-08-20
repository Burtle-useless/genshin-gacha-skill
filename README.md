# genshin-gacha-skill

An agent skill that pulls your **Genshin Impact wish history** straight out of the game's
own web cache, keeps a local archive that never forgets, and renders it as a report.

Works with [Claude Code](https://claude.com/claude-code) and
[Codex CLI](https://github.com/openai/codex) — same `SKILL.md`, same scripts. The four
scripts are plain CLIs, so you can also just run them yourself.

繁體中文說明在 [SKILL.md](SKILL.md)（那份同時是給 agent 讀的指令文件）。

## Why another wish tracker

Most tools assume `data_2` is readable. It usually is not: **`GenshinImpact.exe` holds an
exclusive lock on it for the entire session**, so a plain read fails with a sharing
violation. This skill elevates once and copies the file out of a VSS snapshot instead, so
**you never have to close the game**.

The other difference is the archive. The official API only returns roughly the last six
months. This skill merges every fetch into a local JSON that is **append-only** — the
earlier you start, the more history you keep that the API can no longer give you.

## Requirements

- Windows (reading the game cache and VSS are Windows-specific)
- Python 3.9+ with `requests` and `pillow`
- No API keys, no accounts, nothing to sign up for

```powershell
python -m pip install requests pillow
```

## Install

```powershell
git clone https://github.com/Burtle-useless/genshin-gacha-skill.git
cd genshin-gacha-skill
.\install.ps1              # links into whichever agent dirs you already have
.\install.ps1 -Codex       # or target one explicitly
.\install.ps1 -Claude -Force
```

`install.ps1` creates a directory **junction** (not a symlink — junctions do not need
admin rights) from `~/.claude/skills/` or `~/.codex/skills/` to the clone, so one
`git pull` updates every agent.

## Usage

Open the wish history screen in-game once so the URL lands in the cache, then:

```powershell
.\scripts\get_url.ps1      # 1. pull the authkey URL out of the cache (one UAC prompt)
python .\scripts\fetch.py  # 2. fetch every banner, merge into the local archive
python .\scripts\icons.py  # 3. download 4/5-star icons (only needed for new characters)
python .\scripts\analyze.py  # 4. compute stats, write the report
```

Or just ask your agent: *"analyse my Genshin wishes"*.

Everything lands in `%LOCALAPPDATA%\genshin-gacha\`.

### Options

| Flag | Values | Meaning |
|---|---|---|
| `--lang` | `zh`, `en` | Overrides the configured language |
| `--view` | `five`, `split`, `merge` | Default view when the report opens |

Set the permanent language in [`data/config.json`](data/config.json), or via the
`GENSHIN_GACHA_LANG` environment variable. Precedence: `--lang` > env var > config > `zh`.

Character and weapon names are translated too, joined through the icon id, so an English
report says *Sucrose* and *Skyward Atlas* rather than the Chinese names.

## What you get

- **Luck rating** measured against the right baseline (see below)
- Per-banner five-star timeline with 50/50 outcomes marked
- Four-star timeline, toggleable: five-star only, four-star split out, or merged by time
- A sidebar inventory: how many of each character and weapon you pulled, 4★ and 5★ split
- Frequent four-star ranking
- A self-contained dark HTML report, plus a compact panel for agents that can render
  inline widgets

## The one number people get wrong

Luck is judged on **pulls per featured five-star**, not pulls per five-star.

Pulls per five-star (~62.3 on the character banner) ignores the cost of losing 50/50s, so
someone who loses every coin flip can still look average. The number that reflects what a
featured character actually costs is:

- **90.3 pulls** per featured five-star, since Capturing Radiance (5.0+) raised the
  consolidated featured rate to 55%
- 93.45 pulls under the classic 50/50, for records that predate 5.0

Ratings: Blessed (<0.80x), Lucky (<0.92x), Balanced (<1.08x), Unlucky (<1.20x), Cursed.
The middle band is deliberately narrow — small samples swing hard.

## Limitations

- **Windows only.**
- The API window is about six months. Anything older is gone unless you already archived it.
- **Four-star 50/50 is not computed.** Working out whether a four-star was featured needs
  per-banner rate-up lists that this tool does not have, so it reports counts and
  intervals only rather than guessing.
- "Lost 50/50" is decided by checking the five-star against the standard pool, seeded from
  [`data/standard_pool.json`](data/standard_pool.json) and unioned with whatever you have
  pulled from the standard banner. Add newly added standard characters there.
- Icons come from `gi.yatta.moe`. Characters released before the catalog updates fall back
  to a grey placeholder with the name still shown — covered by
  [`tests/test_icon_fallback.py`](tests/test_icon_fallback.py).

## Privacy

Your UID, authkey and wish records never leave your machine. They live in
`%LOCALAPPDATA%\genshin-gacha\` and are not part of this repository. The only network
calls are to HoYoverse's own wish API and to `gi.yatta.moe` for icons.

## License

[MIT](LICENSE)
