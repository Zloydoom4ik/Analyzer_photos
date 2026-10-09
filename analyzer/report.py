"""Write the report page: report/index.html with the duplicates shown as pictures."""
from html import escape
from pathlib import Path

from . import config
from .groups import SAME_PICTURE, SAME_PICTURE_DISTANCE, SIMILAR, distance, identical_file_sets, place_matrix
from .scan import preview_path

STYLE = """
:root { --bg: #f6f7f9; --card: #ffffff; --text: #1c2330; --muted: #6b7686; --line: #d9dee6;
        --exact: #1f7a4d; --same: #1d5fa8; --similar: #a15c00; --hot: #fde8e8; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #12161d; --card: #1b212b; --text: #e6e9ee; --muted: #94a0b0; --line: #2d3644;
          --exact: #5fd39a; --same: #7db6f5; --similar: #f0b35a; --hot: #4a2424; } }
* { box-sizing: border-box; }
body { margin: 0; padding: 24px; background: var(--bg); color: var(--text);
       font: 15px/1.45 system-ui, "Segoe UI", sans-serif; }
h1 { margin: 0 0 4px; font-size: 24px; }
h2 { margin: 36px 0 12px; font-size: 19px; }
p.note { margin: 0 0 12px; color: var(--muted); max-width: 900px; }
.numbers { display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0; }
.numbers a, .numbers div { background: var(--card); border: 1px solid var(--line); border-radius: 8px;
                           padding: 10px 16px; color: inherit; text-decoration: none; max-width: 260px; }
.numbers b { display: block; font-size: 22px; }
.exact { color: var(--exact); } .same { color: var(--same); } .similar { color: var(--similar); }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; background: var(--card); }
th, td { border: 1px solid var(--line); padding: 5px 9px; text-align: center; white-space: nowrap; }
th.place, td.place { text-align: left; }
td.zero { color: var(--muted); }
td.shared { background: var(--hot); font-weight: 600; }
td small { color: var(--similar); font-weight: 400; }
.group { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 12px; margin: 0 0 14px; }
.group h3 { margin: 0 0 10px; font-size: 15px; font-weight: 600; }
.members { display: flex; flex-wrap: wrap; gap: 12px; }
figure { margin: 0; width: 230px; }
figure img { display: block; width: 230px; height: 172px; object-fit: contain; background: #000; border-radius: 4px; }
figcaption { margin-top: 5px; font-size: 13px; overflow-wrap: anywhere; }
figcaption b { display: block; }
figcaption span { color: var(--muted); display: block; }
"""


def _places(files):
    return len({f["place"] for f in files})


def _figure(image, first):
    if image is first:
        relation = ""
    elif image["sha256"] == first["sha256"]:
        relation = "<span>тот же файл, что первый</span>"
    else:
        relation = f"<span>отличие от первого: {distance(image['phash'], first['phash'])} из 64</span>"
    megabytes = f"{image['bytes'] / 1e6:.1f} МБ".replace(".", ",")
    size = f"{image['width']}×{image['height']}, " if image["width"] else ""
    return (
        f'<figure><a href="{escape(Path(image["path"]).as_uri())}">'
        f'<img loading="lazy" src="thumbs/{preview_path(image["sha256"]).name}" alt=""></a>'
        f'<figcaption><b>{escape(image["place"])}</b>{escape(image["name"])}'
        f'<span>{size}{megabytes}</span>{relation}</figcaption></figure>'
    )


def _card(number, files):
    files = sorted(files, key=lambda f: (f["place"], f["name"]))
    where = f"в {_places(files)} точках" if _places(files) > 1 else "в одной точке"
    return (f'<div class="group"><h3>№ {number} · файлов: {len(files)}, {where}</h3>'
            f'<div class="members">{"".join(_figure(f, files[0]) for f in files)}</div></div>')


def _section(anchor, css, title, note, parts):
    cards = "".join(_card(n, files) for n, files in enumerate(parts, 1)) or '<p class="note">Нет.</p>'
    return f'<h2 id="{anchor}" class="{css}">{title}: {len(parts)}</h2><p class="note">{note}</p>{cards}'


def _matrix(images, groups):
    places, matrix = place_matrix(images, groups)
    head = "".join(f"<th>{n}</th>" for n in range(1, len(places) + 1))
    rows = []
    for number, a in enumerate(places, 1):
        cells = []
        for b in places:
            certain, similar = matrix[a][b]
            if not certain and not similar:
                cells.append('<td class="zero">·</td>')
                continue
            text = str(certain) if certain else ""
            if similar:
                text += f" <small>+{similar}</small>"
            cells.append(f'<td class="{"shared" if a != b else ""}">{text}</td>')
        rows.append(f'<tr><th>{number}</th><td class="place">{escape(a)}</td>{"".join(cells)}</tr>')
    return (f'<div class="scroll"><table><tr><th>№</th><th class="place">Точка</th>{head}</tr>'
            f'{"".join(rows)}</table></div>')


def summary(images, groups):
    """The four lists the report is built from, each a list of file lists."""
    identical = identical_file_sets(images)
    return {
        "between": [files for files in identical if _places(files) > 1],
        "within": [files for files in identical if _places(files) == 1],
        "resized": [g["members"] for g in groups if g["level"] == SAME_PICTURE],
        "similar": [g["members"] for g in groups if g["level"] == SIMILAR],
    }


def write_report(images, groups, source, similar_distance):
    """Write report/index.html and return its path."""
    parts = summary(images, groups)
    page = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Дубликаты фото</title><style>{STYLE}</style></head><body>
<h1>Дубликаты фото</h1>
<p class="note">Папка: {escape(str(source))}. Проверено файлов: {len(images)}, точек: {len({i["place"] for i in images})}.
Каждый файл сравнён с каждым.</p>
<div class="numbers">
  <a href="#between"><b>{len(parts["between"])}</b><span class="exact">одинаковых файлов в разных точках</span></a>
  <a href="#within"><b>{len(parts["within"])}</b><span class="exact">одинаковых файлов внутри одной точки</span></a>
  <a href="#resized"><b>{len(parts["resized"])}</b><span class="same">та же картинка, но файлы разные</span></a>
  <a href="#similar"><b>{len(parts["similar"])}</b><span class="similar">похожих кадров — проверить глазами</span></a>
</div>
<p class="note">Каждая цифра — число картинок. Нажми на цифру, чтобы перейти к списку. Нажатие на картинку открывает исходный файл.</p>

<h2>Точка × точка</h2>
<p class="note">На пересечении двух разных точек — сколько у них общих картинок (одинаковые файлы и та же картинка
в разных файлах); мелким <span class="similar">+N</span> — сколько ещё похожих кадров. На диагонали — то же внутри одной точки.</p>
{_matrix(images, groups)}

{_section("between", "exact", "Одинаковые файлы в разных точках",
          "Файлы совпадают байт в байт и лежат минимум в двух точках. Один номер — один файл и все места, где он лежит.",
          parts["between"])}
{_section("within", "exact", "Одинаковые файлы внутри одной точки",
          "Файлы совпадают байт в байт и лежат в одной и той же точке несколько раз.", parts["within"])}
{_section("resized", "same", "Та же картинка, но файлы разные",
          f"Картинка одна, а файлы разные: перцептивный хеш отличается не больше чем на {SAME_PICTURE_DISTANCE} из 64, "
          f"а SHA-256 у файлов разный. Чаще всего это другой размер, но размер может быть и одинаковым — например, "
          f"файл пересохранили. Здесь показаны все файлы такой картинки, поэтому одинаковые файлы из первых двух "
          f"списков могут встретиться тут ещё раз.", parts["resized"])}
{_section("similar", "similar", "Похожие кадры — проверить глазами",
          f"Отпечатки картинок отличаются на {SAME_PICTURE_DISTANCE + 1}–{similar_distance} из 64. Обычно это тот же кадр "
          f"с небольшим отличием: соседний снимок серии, обрезка. Программа не уверена, решать тебе.", parts["similar"])}
</body></html>
"""
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.REPORT_DIR / "index.html"
    path.write_text(page, encoding="utf-8")
    return path
