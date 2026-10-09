"""Find duplicate photos across place folders.

    python main.py <folder> [--subfolder photos] [--similar 12]

<folder> holds one folder per place; pictures may lie at any depth inside a place folder.
--subfolder  take only the pictures under this subfolder of each place (for example: photos, or posts)
--similar    how many of the 64 bits of the picture fingerprint may differ for a "similar frame" candidate
"""
import argparse
import sys
from pathlib import Path

from analyzer import db
from analyzer.groups import SIMILAR_DISTANCE, find_groups
from analyzer.report import summary, write_report
from analyzer.scan import scan


def main():
    parser = argparse.ArgumentParser(description="Find duplicate photos across place folders.")
    parser.add_argument("folder", type=Path, help="folder that holds one folder per place")
    parser.add_argument("--subfolder", help="take only this subfolder of each place, e.g. photos")
    parser.add_argument("--similar", type=int, default=SIMILAR_DISTANCE,
                        help=f"differing fingerprint bits allowed for a similar frame (default {SIMILAR_DISTANCE})")
    args = parser.parse_args()
    folder = args.folder.resolve()
    if not folder.is_dir():
        sys.exit(f"Нет такой папки: {folder}")

    with db.connect() as conn:
        db.ensure_schema(conn)
        print(f"Папка: {folder}")
        found, fingerprinted, forgotten = scan(conn, folder, args.subfolder)
        print(f"Файлов найдено: {found}; обработано сейчас: {fingerprinted}; убрано из базы: {forgotten}")

        images = db.all_images(conn)
        groups = find_groups(images, args.similar)
        db.save_groups(conn, groups)

    parts = summary(images, groups)
    print(f"Точек: {len({i['place'] for i in images})}")
    print(f"Одинаковых файлов в разных точках:        {len(parts['between'])}")
    print(f"Одинаковых файлов внутри одной точки:     {len(parts['within'])}")
    print(f"Та же картинка, но файлы разные:          {len(parts['resized'])}")
    print(f"Похожих кадров (проверить глазами):       {len(parts['similar'])}")
    print(f"Отчёт: {write_report(images, groups, folder, args.similar)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
