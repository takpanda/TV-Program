---
name: update-kuchikomi
description: "kuchikomi.jsonの口コミデータを最新化する。Use when: 口コミを更新, 最新化, 追加, 放送後の反応を反映, sentimentを修正, ティッカーの内容を変える, 口コミが古い, 新しいドラマの口コミを追加, kuchikomiを編集"
argument-hint: "更新対象のドラマ名 or 'all' for 全件"
---

# update-kuchikomi — 口コミ最新化スキル

`kuchikomi.json` を調査・編集して口コミティッカーの内容を最新の世間の反応に更新する。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `kuchikomi.json` | 口コミデータ（このスキルの編集対象） |
| `programs.json` | 番組マスタ（参照のみ） |
| `script.js` | `buildTicker()` がkuchikomi.jsonを読み込んで表示 |

## kuchikomi.json スキーマ

```json
[
  {
    "title": "ドラマタイトル（programs.jsonのtitleと一致させる）",
    "sentiment": "positive | negative | mixed",
    "text": "🌟 口コミ本文（先頭に sentiment 絵文字を付ける）"
  }
]
```

### sentiment と絵文字の対応

| sentiment | 意味 | 使用絵文字（例） |
|---|---|---|
| `positive` | 好意的・高評価 | 🌟 👍 😍 ✨ 🔥 |
| `negative` | 批判的・低評価 | 👎 😤 💢 |
| `mixed` | 賛否両論・複雑 | 🤔 😅 |

## 手順

### Step 1: 対象ドラマを確認

`programs.json` の `programs` 配列からドラマ一覧を取得。更新対象を特定する。

### Step 2: 口コミ・反応を調査

以下の情報源を Web 検索で確認:
- Filmarks スコア・レビュー件数・clip数
- 視聴率（ビデオリサーチ最新週）
- Twitter/X のハッシュタグ反応
- エンタメニュースサイトの視聴者コメント

取得する情報:
- 放送済みか未放送か（4/11時点）
- Filmarks 評点（あれば）
- 視聴率（あれば）
- 世間の代表的なコメント（好評・批評・賛否の声）

### Step 3: sentiment を判定

| 条件 | sentiment |
|---|---|
| Filmarks 3.0以上 / SNS好評多数 / 視聴率好調 | `positive` |
| Filmarks 2.7以下 / 批判コメント多数 / 視聴率低調 | `negative` |
| 評価が真っ二つ / 良い点も悪い点も同程度 | `mixed` |

### Step 4: text を生成

- **先頭に絵文字** を付ける（sentimentに合わせて選択）
- **20〜60字程度**で端的に
- 具体的な数字（Filmarks点数・clip数・視聴率）があれば含める
- 口語的・SNS的なトーンで書く

### Step 5: kuchikomi.json を更新

- 既存エントリは `title` をキーとして上書き
- 新ドラマは末尾に追加
- 削除するドラマは対象エントリを除去
- JSON構文の正確さを確認（末尾カンマなし）

### Step 6: 確認

```
get_errors kuchikomi.json
```

JSON エラーがないことを確認してタスク完了。

## 件数ガイドライン

- 推奨: **10〜15件**（ティッカーが間延びしない範囲）
- 最低: 5件（ループが不自然にならない最小値）
- 上限: 20件程度まで

## 更新タイミングの目安

| タイミング | 作業内容 |
|---|---|
| クール開始直後（4月上旬） | 初回放送の反応でsentiment初期設定 |
| 3話〜5話時点 | Filmarksスコアが安定してきたら再評価 |
| 最終回後 | 最終評価に更新・終了ドラマは削除 |
