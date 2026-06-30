# Yamanashi Event Archive

Markdown + YAML front matter のイベント原本から、`yamanashi-event-api`
が読み込める archive index JSON を生成するリポジトリです。

## ディレクトリ

- `archive.yaml`: archive index のメタデータです。`source.name` は API の
  `/groups` で `archive_source` として使われます。`source.url` は
  `archive_url` として使われます。
- `content/communities/*.md`: `/groups` に出すコミュニティ原本です。
- `content/events/{group_key}/{YYYY-MM-DD}-{serial}.md`: イベント原本です。
- `public/index.json`: 生成された archive index です。GitHub Pages ではこの
  ディレクトリを公開します。

## 生成

```bash
python3 scripts/generate_archive_index.py
```

生成されるイベント `uid` は次の形式です。

```text
{group_key}-{YYYY-MM-DD}-{serial}@{archive_source_key}
```

`archive_source_key` は `archive.yaml` の `source.key` があればそれを使い、
なければ `source.name` を使います。

## イベント原本

```markdown
---
title: 山梨Web勉強会 第1回
event_url: https://example.com/archive/yamanashi-web/2012-05-19-001
started_at: 2012-05-19T14:00:00+09:00
ended_at: 2012-05-19T17:00:00+09:00
open_status: close
place: 山梨県立図書館
address: 山梨県甲府市北口2-8-1
---
山梨Web勉強会の初回イベント。
```

`group_key`、日付、serial はファイルパス
`content/events/{group_key}/{YYYY-MM-DD}-{serial}.md` から補完されます。
本文は `description` が未指定の場合に使われます。

## 検証

```bash
python3 -m unittest discover -s tests
```
