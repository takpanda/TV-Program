#!/usr/bin/env python3
"""
extract_json() のユニットテスト。
"""

import json
import sys
import unittest
from pathlib import Path

# scripts/ ディレクトリを import パスに追加
sys.path.insert(0, str(Path(__file__).parent))

from update_programs import extract_json


class TestExtractJson(unittest.TestCase):
    """extract_json() のテストケース"""

    # --- 正常系 ---

    def test_plain_json_object(self):
        """純粋な JSON オブジェクト文字列を正しく解析できること"""
        text = '{"season_title": "テスト", "programs": []}'
        result = extract_json(text)
        self.assertEqual(result["season_title"], "テスト")
        self.assertEqual(result["programs"], [])

    def test_plain_json_array(self):
        """純粋な JSON 配列文字列を正しく解析できること"""
        text = '[{"title": "ドラマA"}, {"title": "ドラマB"}]'
        result = extract_json(text)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_json_with_markdown_fence(self):
        """```json ... ``` で囲まれた出力を正しく解析できること"""
        text = '```json\n{"season_title": "春クール", "programs": []}\n```'
        result = extract_json(text)
        self.assertEqual(result["season_title"], "春クール")

    def test_json_with_plain_fence(self):
        """``` ... ``` で囲まれた出力を正しく解析できること"""
        text = '```\n{"programs": [{"title": "番組X"}]}\n```'
        result = extract_json(text)
        self.assertEqual(result["programs"][0]["title"], "番組X")

    def test_json_with_leading_text(self):
        """JSON の前に説明文がある場合も正しく解析できること"""
        text = 'こちらが番組情報です。\n{"season_title": "夏クール", "programs": []}'
        result = extract_json(text)
        self.assertEqual(result["season_title"], "夏クール")

    def test_json_with_trailing_text(self):
        """JSON の後に説明文がある場合も正しく解析できること"""
        text = '{"season_title": "秋クール", "programs": []}\n以上が番組情報です。'
        result = extract_json(text)
        self.assertEqual(result["season_title"], "秋クール")

    def test_json_with_both_leading_and_trailing_text(self):
        """JSON の前後に説明文がある場合も正しく解析できること"""
        text = '以下の JSON をご確認ください。\n{"programs": []}\nご確認よろしくお願いします。'
        result = extract_json(text)
        self.assertEqual(result["programs"], [])

    def test_extra_data_null_before_json(self):
        """'null' + JSON が連結された場合（Extra data エラーの典型）を正しく解析できること"""
        text = 'null\n{"season_title": "冬クール", "programs": []}'
        result = extract_json(text)
        self.assertEqual(result["season_title"], "冬クール")

    def test_extra_data_true_before_json(self):
        """'true' + JSON が連結された場合も正しく解析できること"""
        text = 'true\n{"programs": []}'
        result = extract_json(text)
        self.assertEqual(result["programs"], [])

    def test_whitespace_around_json(self):
        """前後に空白・改行がある場合も正しく解析できること"""
        text = '\n\n  {"programs": [{"title": "テスト"}]}  \n\n'
        result = extract_json(text)
        self.assertEqual(result["programs"][0]["title"], "テスト")

    # --- 異常系 ---

    def test_no_json_raises(self):
        """JSON が含まれないテキストは ValueError を送出すること"""
        with self.assertRaises(ValueError):
            extract_json("JSON は含まれていません。普通のテキストです。")

    def test_empty_string_raises(self):
        """空文字列は ValueError を送出すること"""
        with self.assertRaises(ValueError):
            extract_json("")


if __name__ == "__main__":
    unittest.main()
