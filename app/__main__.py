"""PNBA のコマンド。

  python -m app serve            Web アプリを起動（定時実行つき）
  python -m app run              今すぐ1回（収集 → 選定 → 保存 → 通知）
  python -m app run --dry-run    保存も通知もせず、選んだ記事を JSON で出す
  python -m app collect          収集だけ（カテゴリごとの件数を確認）
"""
import argparse
import json
import sys

from . import config, db, settings


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m app", description="PNBA — Personal News Broadcast Application")
    sub = p.add_subparsers(dest="cmd")
    sp = sub.add_parser("serve", help="Web アプリを起動")
    sp.add_argument("--host", default=config.HOST)
    sp.add_argument("--port", type=int, default=config.PORT)
    sp.add_argument("--no-scheduler", action="store_true", help="定時実行を止める")
    rp = sub.add_parser("run", help="今すぐ1回実行")
    rp.add_argument("--dry-run", action="store_true", help="保存・通知せず JSON を出力")
    sub.add_parser("collect", help="収集だけ")
    args = p.parse_args(argv)

    db.init()
    if args.cmd == "serve":
        if not config.PASSWORD and not config.is_local_host(args.host):
            sys.exit("PNBA_PASSWORD を設定していないので、外から開ける形（--host {}）では起動しません。\n"
                     "パスワードを設定するか、--host 127.0.0.1 で起動してください。".format(args.host))
        import uvicorn
        from .web import create_app
        uvicorn.run(create_app(start_scheduler=not args.no_scheduler), host=args.host, port=args.port,
                    proxy_headers=True, forwarded_allow_ips="*" if config.is_local_host(args.host) else None)
    elif args.cmd == "run":
        from . import pipeline
        picks = pipeline.run(trigger="cli", dry_run=args.dry_run)
        if args.dry_run:
            print(json.dumps(picks, ensure_ascii=False, indent=2))
        else:
            print(f"{len(picks or [])}本配信")
    elif args.cmd == "collect":
        from .collect import collect
        src = settings.get("sources")
        arts = collect(src)
        print(f"{len(arts)}件")
        for cat in src["categories"]:
            print(f"  {cat}: {sum(a['category'] == cat for a in arts)}件")
    else:
        p.print_help()


if __name__ == "__main__":
    main()
