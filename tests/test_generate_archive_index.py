import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from scripts.generate_archive_index import build_index


class GenerateArchiveIndexTest(unittest.TestCase):
    def test_builds_api_compatible_archive_index(self):
        root = Path(tempfile.mkdtemp())
        (root / "content/communities").mkdir(parents=True)
        (root / "content/events/yamanashi-web").mkdir(parents=True)
        (root / "archive.yaml").write_text(
            """schema_version: "1.0"
source:
  type: archive_index
  name: yamanashi-event-archive
  url: https://github.com/yuukis/yamanashi-event-archive
  ref: main
""",
            encoding="utf-8",
        )
        (root / "content/communities/yamanashi-web.md").write_text(
            """---
key: yamanashi-web
title: 山梨Web勉強会
url: https://example.com/yamanashi-web
---
山梨県内のWeb制作・Web開発勉強会です。
""",
            encoding="utf-8",
        )
        (root / "content/events/yamanashi-web/2012-05-19-001.md").write_text(
            """---
title: 山梨Web勉強会 第1回
event_url: https://example.com/archive/yamanashi-web/2012-05-19-001
started_at: 2012-05-19T14:00:00+09:00
ended_at: 2012-05-19T17:00:00+09:00
open_status: close
---
山梨Web勉強会の初回イベント。
""",
            encoding="utf-8",
        )

        index = build_index(
            Namespace(
                config=root / "archive.yaml",
                communities=root / "content/communities",
                events=root / "content/events",
                output=root / "public/index.json",
                generated_at="2026-06-30T00:00:00+09:00",
            )
        )

        self.assertEqual(index["schema_version"], "1.0")
        self.assertEqual(index["source"]["name"], "yamanashi-event-archive")
        self.assertEqual(index["source"]["url"], "https://github.com/yuukis/yamanashi-event-archive")
        self.assertEqual(index["communities"][0]["key"], "yamanashi-web")
        self.assertEqual(index["communities"][0]["description"], "山梨県内のWeb制作・Web開発勉強会です。")
        self.assertEqual(
            index["events"][0]["uid"],
            "yamanashi-web-2012-05-19-001@yamanashi-event-archive",
        )
        self.assertEqual(index["events"][0]["group_key"], "yamanashi-web")
        self.assertEqual(index["events"][0]["group_name"], "山梨Web勉強会")
        self.assertEqual(index["events"][0]["updated_at"], "2026-06-30T00:00:00+09:00")
        self.assertEqual(index["events"][0]["description"], "山梨Web勉強会の初回イベント。")


if __name__ == "__main__":
    unittest.main()
