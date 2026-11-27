"""PNBA パイプラインのコマンド（pipeline/ で実行）。

  python -m pnba run                     今すぐ1回（収集 → 選定 → 保存 → 通知）
  python -m pnba run --trigger schedule  定時実行（今日の分が済んでいれば何もしない）
  python -m pnba run --dry-run           保存も通知もせず、選んだ記事を JSON で出す
  python -m pnba collect                 収集だけ（カテゴリごとの件数を確認）
  python -m pnba init-db                 テーブルと初期設定を作る
"""
import argparse
import json
import sys

from . import db, settings
from .collect import CollectError
from .llm import LLMError


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m pnba", description="PNBA のパイプライン")
    sub = p.add_subparsers(dest="cmd")
    rp = sub.add_parser("run", help="今すぐ1回実行")
    rp.add_argument("--trigger", default="manual", choices=["manual", "schedule", "web"])
    rp.add_argument("--dry-run", action="store_true", help="保存・通知せず JSON を出力")
    sub.add_parser("collect", help="収集だけ")
    sub.add_parser("init-db", help="テーブルと初期設定を作る")
    args = p.parse_args(argv)

    try:
        if args.cmd == "run":
            from . import pipeline
            picks = pipeline.run(trigger=args.trigger, dry_run=args.dry_run)
            if args.dry_run:
                print(json.dumps(picks, ensure_ascii=False, indent=2))
            elif picks is not None:
                print(f"{len(picks)}本配信")
        elif args.cmd == "collect":
            from .collect import collect
            src = settings.get("sources") if db.config.DATABASE_URL else settings.defaults()["sources"]
            arts = collect(src)
            print(f"{len(arts)}件")
            for cat in src["categories"]:
                print(f"  {cat}: {sum(a['category'] == cat for a in arts)}件")
        elif args.cmd == "init-db":
            db.init()
            settings.seed()
            print("テーブルと初期設定を作りました")
        else:
            p.print_help()
    except (db.DBError, LLMError, CollectError) as e:
        sys.exit(f"エラー: {e}")


if __name__ == "__main__":
    main()
