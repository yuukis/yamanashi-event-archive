# Yamanashi Tech Events Archive

Markdown + YAML front matter のイベント原本から、[Yamanashi Tech Events API](https://github.com/yuukis/yamanashi-event-api)
が読み込める archive index JSON を生成するリポジトリです。

## ディレクトリ

- `archive.yaml`: archive index のスキーマバージョンです。`source` は生成時に
  GitHub Actions の環境変数、またはローカルの Git 情報から補完されます。
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

`archive_source_key` は生成時に取得したリポジトリ名を使います。

生成される `source` は、GitHub Actions では `GITHUB_REPOSITORY`、
`GITHUB_SERVER_URL`、`GITHUB_REF_NAME` から作られます。ローカル実行時は
`git remote get-url origin` と現在の Git ブランチから補完されます。

## イベント原本

```markdown
---
title: 山梨Web勉強会 第1回
event_url: https://example.com/archive/yamanashi-web/2012-05-19-001
started_at: 2012-05-19T14:00:00+09:00
ended_at: 2012-05-19T17:00:00+09:00
updated_at: 2012-05-18T20:00:00+09:00
open_status: close
place: 山梨県立図書館
address: 山梨県甲府市北口2-8-1
---
山梨Web勉強会の初回イベント。
```

`group_key`、日付、serial はファイルパス
`content/events/{group_key}/{YYYY-MM-DD}-{serial}.md` から補完されます。
本文は `description` が未指定の場合に使われます。
`updated_at` はビルド時刻から補完されないため、原本サイトの更新日時、
公開日時、または取得できない場合は `started_at` を明示してください。

## 検証

```bash
python3 -m unittest discover -s tests
```
