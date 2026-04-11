#!/usr/bin/env python3
"""
GitHub Models API (Copilot) を使って programs.json を自動更新するスクリプト。
GitHub Actions の GITHUB_TOKEN（models: read 権限）で動作します。
"""

import json
import os
import sys
import datetime
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai パッケージがインストールされていません", file=sys.stderr)
    sys.exit(1)

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
    return f"""あなたは日本のテレビ番組情報の専門家です。
{season} の地上波主要6チャンネルの夜間ドラマ・バラエティ番組情報を JSON で提供してください。

## チャンネル ID
{ch_list}

## 出力ルール
- JSON のみ出力し、説明文は不要
- キー名は以下のスキーマに従うこと
- `day` は "月" "火" "水" "木" "金" "土" "日" のいずれか
- `startTime` / `endTime` は "HH:MM" 形式（例: "21:00", "22:54", "24:20"）
- `startHour` 18〜25 の範囲内の番組を対象にすること
- 各チャンネルから 1〜3 番組程度、合計 15〜20 番組を選定すること
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


def call_github_models(client: OpenAI, prompt: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "日本のテレビ番組情報の専門家として、正確な番組情報を JSON 形式のみで出力してください。"
                    "JSON 以外のテキストは絶対に含めないでください。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    return json.loads(raw)


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN が設定されていません", file=sys.stderr)
        sys.exit(1)

    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    # 現在のデータを読み込む
    with open(PROGRAMS_PATH, encoding="utf-8") as f:
        current_data: dict = json.load(f)

    season = get_season_label()
    print(f"🗓  対象シーズン: {season}")

    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=token,
    )

    print("🤖 GitHub Models API へリクエスト中...")
    prompt = build_prompt(season)
    result = call_github_models(client, prompt)

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
