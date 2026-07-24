"""CLI: rebuild showcase DB and optionally launch tiqo on it."""

from __future__ import annotations

import argparse
import os


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="tiqo showcase (demo) database")
    parser.add_argument(
        "--run",
        action="store_true",
        help="After seeding, launch the app on the demo DB",
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Only recreate demo.db (default if --run is omitted)",
    )
    args = parser.parse_args(argv)

    from app.dev.showcase_db import reset_showcase_db, showcase_db_path

    path = reset_showcase_db()
    print(f"Showcase DB ready: {path}")
    print(
        "Contains: дерево Английский, «Сегодня» (daily/weekly/monthly), "
        "«В работе» (те же задачи), Помодоро, чек-лист с выполненным/открытым примером."
    )

    if args.run and not args.seed_only:
        os.environ["TIQO_DB"] = str(path)
        from app.ui.main import main as app_main

        return app_main()

    print("Open with:")
    print(f"  TIQO_DB={showcase_db_path()} uv run tiqo")
    print("Or:")
    print("  uv run tiqo-demo --run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
