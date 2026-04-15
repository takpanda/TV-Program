#!/usr/bin/env python3
"""
Claude Code CLI（サブスクリプション）を使って programs.json を自動更新するスクリプト。
CLAUDE_CODE_OAUTH_TOKEN 環境変数が必要です。
"""

import json
import os
import subprocess
import sys
import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PROGRAMS_PATH = REPO_ROOT / "programs.json"

CHANNELS = {
    "nhk1":     "NHK総合",
    "ntv":      "日テレ",
    "tbs":      "TBS",
    "fuji":     "フジ",
    "tv_asahi": "テレ朝",
    "tv_tokyo": "テレ東",
}


def get_season_label() -> str:
    today = datetime.date.today()
    year = today.year
    month = today.month
    if 1 <= month <= 3:
        season = "冬"
    elif 4 <= month <= 6:
        season = "春"
    elif 7 <= month <= 9:
        season = "夏"
    else:
        season = "秋"
    return f"{year}年{season}クール"


def build_prompt(season: str) -> str:
    ch_list = "\n".join(f'- "{cid}": "{name}"' for cid, name in CHANNELS.items())
    return f"""日本のテレビ番組情報の専門家として、正確な番組情報を JSON 形式のみで出力してください。JSON 以外のテキストは絶対に含めないでください。

{season} の地上波主要6チャンネルの夜間ドラマ・バラエティ番組情報を JSON で提供してください。

## チャンネル ID
{ch_list}

## 出力ルール
- JSON のみ出力し、説明文は不要
- キー名は以下のスキーマに従うこと
- `day` は "月" "火" "水" "木" "金" "土" "日" のいずれか
- `startTime` / `endTime` は "HH:MM" 形式（例: "21:00", "22:54", "24:20"）
- `startTime` が 18:00〜25:59 の範囲内の番組を対象にすること
- 20:00〜21:59 開始のドラマは省略せずすべて含めること（チャンネル・曜日を問わない）
- 上記以外の時間帯の番組は各チャンネルから代表的なものを選定すること
- `memo` には "放送局 曜日時間帯 ／ 初回放送日（例: 4/7スタート）" を記載すること

## 出力スキーマ
{{
  "season_title": "週間テレビ番組表（{season}）",
  "programs": [
    {{
      "title": "番組タイトル",
      "channel": "チャンネルID",
      "day": "曜日",
      "startTime": "HH:MM",
      "endTime": "HH:MM",
      "memo": "備考"
    }}
  ]
}}
"""


def call_claude(prompt: str) -> dict:
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        check=True,
    )
    raw = result.stdout.strip()
    # ```json ... ``` のコードブロックで囲まれている場合は除去
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


def main() -> None:
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        print("Error: CLAUDE_CODE_OAUTH_TOKEN が設定されていません", file=sys.stderr)
        sys.exit(1)

    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    # 現在のデータを読み込む
    with open(PROGRAMS_PATH, encoding="utf-8") as f:
        current_data: dict = json.load(f)

    season = get_season_label()
    print(f"🗓  対象シーズン: {season}")

    print("🤖 Claude Code へリクエスト中...")
    prompt = build_prompt(season)
    result = call_claude(prompt)

    programs = result.get("programs", [])
    if not programs:
        print("Error: 番組データが取得できませんでした", file=sys.stderr)
        sys.exit(1)

    # 不正なチャンネル ID を除外
    valid_programs = [p for p in programs if p.get("channel") in CHANNELS]
    if len(valid_programs) < len(programs):
        print(
            f"⚠️  不正なチャンネル ID を {len(programs) - len(valid_programs)} 件除外しました"
        )

    # programs.json を更新
    if not dry_run:
        season_title = result.get("season_title", f"週間テレビ番組表（{season}）")
        current_data["settings"]["title"] = season_title
        current_data["programs"] = valid_programs

        with open(PROGRAMS_PATH, "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
            f.write("\n")

        # Actions の環境変数ファイルへシーズン名を書き込む
        env_file = os.environ.get("GITHUB_ENV")
        if env_file:
            with open(env_file, "a", encoding="utf-8") as ef:
                ef.write(f"UPDATE_SEASON={season}\n")

        print(f"✅ programs.json を更新しました")
        print(f"📺 番組数: {len(valid_programs)} 件")
    else:
        print("🧪 ドライラン: ファイルへの書き込みをスキップしました")
        print(f"📺 取得番組数: {len(valid_programs)} 件")
        for p in valid_programs:
            print(f"  [{p.get('channel')}] {p.get('day')} {p.get('startTime')} {p.get('title')}")


if __name__ == "__main__":
    main()
