#!/usr/bin/env python3
"""
Claude Code CLI（サブスクリプション）を使って kuchikomi.json を自動更新するスクリプト。
CLAUDE_CODE_OAUTH_TOKEN 環境変数が必要です。
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
KUCHIKOMI_PATH = REPO_ROOT / "kuchikomi.json"
PROGRAMS_PATH = REPO_ROOT / "programs.json"


def build_prompt() -> str:
    # programs.json からタイトル一覧を取得
    try:
        with open(PROGRAMS_PATH, encoding="utf-8") as f:
            programs_data = json.load(f)
        titles = [p["title"] for p in programs_data.get("programs", []) if "title" in p]
    except Exception:
        titles = []

    title_list = "\n".join(f"- {t}" for t in titles) if titles else "(programs.json から取得できませんでした)"

    return f"""日本のテレビ番組の口コミ分析専門家として、正確な口コミ情報を JSON 形式のみで出力してください。

重要: text フィールドの内容は必ず日本語で記述してください。英語や他の言語での出力は禁止です。

## 対象番組
{title_list}

## 出力ルール
- JSON のみ出力し、説明文は不要。前後に日本語の解説文を入れないこと
- 各番組について、最新の視聴者反応を反映した口コミを生成すること
- sentiment は "positive" / "negative" / "mixed" のいずれか
- text は感情を示す絵文字で始まり、20〜80文字程度にすること
- 10〜15エントリを生成すること

## 出力スキーマ
{{
  "entries": [
    {{
      "title": "番組タイトル（日本語）",
      "sentiment": "positive | negative | mixed",
      "text": "🌟 口コミ本文（日本語、20〜80文字）"
    }}
  ]
}}

## 注意事項
- **すべての文字列値は日本語で記述すること**
- sentiment キーのみ英語（positive/negative/mixed）
- 既存の番組タイトルはそのまま使用すること"""


def extract_json(text: str) -> dict:
    """Claude の出力テキストから JSON オブジェクト/配列を抽出して返す。"""
    # 1. マークダウンコードフェンスを除去
    text = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", text)

    # 2. 前後の空白を除去
    stripped = text.strip()

    # 3. 高速パス: テキスト全体が有効な JSON の場合
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 4. フォールバック: JSON オブジェクト/配列の開始位置を探索
    decoder = json.JSONDecoder()

    m = re.search(r"[{[]", stripped)
    if not m:
        raise ValueError("モデル出力に JSON オブジェクト/配列が見つかりませんでした")

    # 4a. raw_decode でパース
    try:
        obj, _ = decoder.raw_decode(stripped, m.start())
        return obj
    except json.JSONDecodeError:
        pass

    # 4b. ネスト対応の括弧追跡
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

    # 4c. 最後の閉じ括弧をフォールバック
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

    # 既存データを読み込む
    try:
        with open(KUCHIKOMI_PATH, encoding="utf-8") as f:
            current_data = json.load(f)
        if not isinstance(current_data, list):
            raise ValueError("kuchikomi.json must be a JSON array")
    except Exception:
        current_data = []

    print("🤖 Claude Code へリクエスト中...")
    prompt = build_prompt()
    result = call_claude(prompt)

    entries = result.get("entries", [])
    if not entries:
        print("Error: 口コミデータが取得できませんでした", file=sys.stderr)
        sys.exit(1)

    # 不正な sentiment を除外
    valid_sentiments = {"positive", "negative", "mixed"}
    valid_entries = [e for e in entries if isinstance(e, dict) and e.get("sentiment") in valid_sentiments]
    if len(valid_entries) < len(entries):
        print(f"⚠️  不正な sentiment を {len(entries) - len(valid_entries)} 件除外しました")

    # kuchikomi.json を更新
    if not dry_run:
        with open(KUCHIKOMI_PATH, "w", encoding="utf-8") as f:
            json.dump(valid_entries, f, ensure_ascii=False, indent=2)
            f.write("\n")

        print(f"✅ kuchikomi.json を更新しました")
        print(f"📊 エントリ数: {len(valid_entries)} 件")
    else:
        print("🧪 ドライラン: ファイルへの書き込みをスキップしました")
        print(f"📊 取得エントリ数: {len(valid_entries)} 件")
        for e in valid_entries[:5]:
            print(f"  [{e.get('sentiment')}] {e.get('title')}: {e.get('text', '')[:50]}")


if __name__ == "__main__":
    main()
