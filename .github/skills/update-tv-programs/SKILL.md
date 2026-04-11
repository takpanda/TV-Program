---
name: update-tv-programs
description: 'Update programs.json for the weekly TV schedule page. Use when: adding missing dramas, updating airing times, fixing wrong channel/time data, populating a new season, or when user says "掲載して", "追加して", "更新して", "番組表を更新", "ドラマを網羅". Covers research, verification, editing, and validation.'
argument-hint: 'Season or time range to update (e.g., "2026春 20〜23時", "月曜帯")'
---

# TV Programs Update Skill

番組情報を調査・確認し、`programs.json` を正確に更新するワークフロー。

## 対象ファイル

| ファイル | 役割 |
|---|---|
| `programs.json` | 番組データ（チャンネル・曜日・時刻・タイトル） |
| `index.html` | 表示ロジック（`settings.startHour`/`endHour` で表示範囲を制御） |

## Step 1: 現状把握

まず `programs.json` の `settings` と `channels` を確認する。

```bash
python3 -c "
import json
d = json.load(open('programs.json'))
print('settings:', d['settings'])
print('channels:', [c['id'] for c in d['channels']])
print('programs:', len(d['programs']))
for p in sorted(d['programs'], key=lambda x: (['月','火','水','木','金','土','日'].index(x['day']), x['startTime'])):
    print(f\"  {p['day']} {p['startTime']} {p['channel']:10} {p['title']}\")
"
```

確認すべき点：
- `startHour` / `endHour` で掲載範囲を把握（例: 20〜25時）
- `channels` に登録されているチャンネルIDのみ掲載対象

## Step 2: 不足番組のリサーチ

### 優先調査先

1. **TVer カテゴリページ**: `https://tver.jp/categories/drama`
   - 「●曜日放送」セクション、「春の新ドラマ【第1話】」セクションを確認
   - 各シリーズページの「配信予定」欄で放送曜日・時間帯が確認できる

2. **TVer 曜日別特集ページ**:
   - `https://tver.jp/specials/drama26_start4/spring26_mon` （月〜日に置換）
   - 各曜日の新ドラマ一覧と放送局が対応

3. **各局公式ドラマページ**:
   - テレ朝: `https://www.tv-asahi.co.jp/drama/` の「レギュラー」セクション
   - 各番組の放送時間が「火曜 よる9時〜」形式で明記されている

### TVer シリーズページの読み方

シリーズページ（`https://tver.jp/series/XXXXXX`）を開くと：
- エピソード一覧の「配信予定」欄 → `4月14日(火)21:00〜21:54` 形式で放送時間を確認できる
- 局名も明記される（日テレ / フジテレビ / テレ東 など）

## Step 3: 放送時間の確認と除外判定

### 掲載条件（すべて満たす必要あり）

| 条件 | 詳細 |
|---|---|
| 放送局 | `programs.json` の `channels` に登録されているID |
| 放送時間 | `startHour`〜`endHour` 内（例: 20:00〜23:00） |
| 番組種別 | ドラマ（バラエティ・情報番組は除外） |

### よくある除外パターン

- **深夜枠**（23時以降）: TVer で「深夜24時〜」「よる11時15分〜」と表記
- **ローカル局**: 中京テレビ・読売テレビ・カンテレ（関西テレビ）など → channels 未登録
- **短尺ドラマ**（15〜30分枠）: ほぼ深夜枠。放送時間を必ず確認
- **冬ドラマの継続枠**: 終了済みの番組が検索結果に残る場合あり → 放送終了日を確認

### 時間の曖昧さに注意

TVer のエピソードページ「〇月〇日(日)放送分」は放送日だが放送時間ではない。
**必ず** 「配信予定」 or 公式局ページで開始時刻を確認する。

## Step 4: programs.json の更新

### エントリ形式

```json
{
  "title": "番組タイトル",
  "channel": "チャンネルID",
  "day": "曜日（月〜日）",
  "startTime": "21:00",
  "endTime": "21:54",
  "memo": "局名 曜日時間帯 ／ スタート日"
}
```

### チャンネルID 対応表

| id | 局名 |
|---|---|
| `nhk1` | NHK総合 |
| `ntv` | 日テレ（読売テレビ制作も `ntv`） |
| `tbs` | TBS |
| `fuji` | フジテレビ |
| `tv_asahi` | テレ朝 |
| `tv_tokyo` | テレ東 |

### 時刻表記

- 23時台以降は24時間制（23:00〜23:54）
- 翌0時以降は25時間制（24:00 = 翌0時、25:00 = 翌1時）

## Step 5: 検証

```bash
python3 -c "
import json
d = json.load(open('programs.json'))
print('Valid JSON, programs:', len(d['programs']))
for p in sorted(d['programs'], key=lambda x: (['月','火','水','木','金','土','日'].index(x['day']), x['startTime'])):
    print(f\"  {p['day']} {p['startTime']} {p['channel']:10} {p['title']}\")
"
```

問題なければ完了。

## 判断ログ（更新時に残すと便利）

各番組について以下を記録する（memoフィールドや作業ノートに）：

```
番組名: ○○○
チャンネル: フジテレビ
放送時間: 火曜 21:00〜21:54
確認根拠: TVer シリーズページ「4月14日(火)21:00〜21:54 配信予定」
掲載可否: ✅ 掲載
```

## 参照リソース

- [除外番組リスト（前セッション確認済み）](./references/excluded-programs.md)
