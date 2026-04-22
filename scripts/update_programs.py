#!/usr/bin/env python3
"""
Claude Code CLI（サブスクリプション）を使って programs.json を自動更新するスクリプト。
CLAUDE_CODE_OAUTH_TOKEN 環境変数が必要です。
"""

import json
import os
import re
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
    return f"""日本のテレビ番組情報の専門家として、正確な番組情報を JSON 形式のみで出力してください。

重要: すべての値（title, memo など）は必ず日本語で記述してください。英語や他の言語での出力は禁止です。

{season} の地上波主要6チャンネルの夜間ドラマ・バラエティ番組情報を JSON で提供してください。

## チャンネル ID
{ch_list}

## 出力ルール
- JSON のみ出力し、説明文は不要。前後に日本語の解説文を入れないこと
- キー名は以下のスキーマに従うこと
- `day` は "月" "火" "水" "木" "金" "土" "日" のいずれか
- `startTime` / `endTime` は "HH:MM" 形式（例: "21:00", "22:54", "24:20"）
- `startTime` が 18:00〜25:59 の範囲内の番組を対象にすること
- 20:00〜21:59 開始のドラマは省略せずすべて含めること（チャンネル・曜日を問わない）
- 上記以外の時間帯の番組は各チャンネルから代表的なものを選定すること
- `memo` には "放送局 曜日時間帯 ／ 初回放送日（例: 4/7スタート）" を記載すること
- **すべての文字列値は日本語で記述すること**

## 出力スキーマ
{{
  "season_title": "週間テレビ番組表（{season}）",
  "programs": [
    {{
      "title": "番組タイトル（日本語）",
      "channel": "チャンネルID",
      "day": "曜日",
      "startTime": "HH:MM",
      "endTime": "HH:MM",
      "memo": "備考（日本語）"
    }}
  ]
}}
"""


def extract_json(text: str) -> dict:
    """Claude の出力テキストから JSON オブジェクト/配列を抽出して返す。

    マークダウンのコードフェンス、前後の説明文、複数 JSON の連結など
    Claude が余分なテキストを出力した場合も堅牢に処理する。
    """
    # 1. マークダウンコードフェンス（```json ... ``` または ``` ... ```）を除去
    text = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", text)

    # 2. 前後の空白を除去
    stripped = text.strip()

    # 3. 高速パス: テキスト全体が有効な JSON の場合
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 4. JSON オブジェクト/配列の開始位置を探索（複数回トライ）
    decoder = json.JSONDecoder()

    # 4a. 最初の { または [ を見つける
    m = re.search(r"[{[]", stripped)
    if not m:
        raise ValueError("モデル出力に JSON オブジェクト/配列が見つかりませんでした")

    # 4b. 見つかった位置から JSON をパース
    try:
        obj, _ = decoder.raw_decode(stripped, m.start())
        return obj
    except json.JSONDecodeError:
        pass

    # 4c. フォールバック: } または ] の位置を推定して切り取る
    #    最初の { から対応する } を探す（ネスト対応）
    start_idx = m.start()
    bracket_char = stripped[start_idx]
    close_char = "}" if bracket_char == "{" else "]"
    depth = 0
    end_idx = start_idx
    for i in range(start_idx, len(stripped)):
        if stripped[i] == bracket_char:
            depth += 1
        elif stripped[i] == close_char:
            depth -= 1
            if depth == 0:
                end_idx = i + 1
                break
    if end_idx > start_idx:
        candidate = stripped[start_idx:end_idx]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 4d. さらにフォールバック: 最後の } または ] を見つける
    last_close = stripped.rfind(close_char)
    if last_close > start_idx:
        candidate = stripped[start_idx:last_close + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"モデル出力を JSON として解析できませんでした。\n"
        f"出力の先頭 800 文字: {stripped[:800]!r}"
    )


def call_claude(prompt: str) -> dict:
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        check=True,
    )
    raw = result.stdout.strip()
    try:
        return extract_json(raw)
    except Exception as exc:
        raise RuntimeError(
            "Claude の出力を JSON として解析できませんでした。\n"
            f"エラー: {exc}\n"
            f"出力の先頭 500 文字: {raw[:500]!r}"
        ) from exc


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
