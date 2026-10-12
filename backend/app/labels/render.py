"""Draw the labels for a Brother QL, 62 mm roll at 300 dpi: 696 px wide, 1 px = 1 dot.

Pure black on white, no grey (thermal printers dither it), thick rules, smallest text 26 px.
Text is drawn without anti-aliasing, so what the preview shows is exactly what gets printed."""
import io
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

from app.labels.data import LabelData, LabelTrack

W, H = 696, 472  # 62 x 40 mm at 300 dpi
MARGIN = 20
RULE = 6
MIN_SIZE = 26  # about 2.2 mm
FONTS = Path(__file__).parent / "fonts"
SANS, MONO = "DejaVuSans-Bold.ttf", "DejaVuSansMono-Bold.ttf"
ELLIPSIS = "…"

# (font size, most lines) to try in order; the first that fits wins, the last gets cut with "…".
Fit = list[tuple[int, int]]


@dataclass
class Rendered:
    kind: str  # "main" or "tracks"
    name: str  # file name stem, e.g. "tracks-1"
    png: bytes


@lru_cache(maxsize=64)
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def _line_height(size: int) -> int:
    return round(size * 1.2)


class Canvas:
    def __init__(self) -> None:
        self.img = Image.new("L", (W, H), 255)
        self.draw = ImageDraw.Draw(self.img)
        self.draw.fontmode = "1"  # no anti-aliasing: every pixel is black or white

    def width(self, text: str, name: str, size: int) -> float:
        return self.draw.textlength(text, font=_font(name, size))

    def text(self, xy: tuple[int, int], text: str, name: str, size: int, fill: int = 0) -> None:
        self.draw.text(xy, text, font=_font(name, size), fill=fill)

    def rule(self, y: int) -> int:
        self.draw.rectangle([MARGIN, y, W - MARGIN - 1, y + RULE - 1], fill=0)
        return y + RULE

    def wrap(self, text: str, name: str, size: int, width: int) -> list[str]:
        lines: list[str] = []
        current = ""
        for word in text.split():
            trial = f"{current} {word}".strip()
            if self.width(trial, name, size) <= width:
                current = trial
                continue
            if current:
                lines.append(current)
            current = word
            while self.width(current, name, size) > width and len(current) > 1:  # one huge word
                cut = len(current) - 1
                while cut > 1 and self.width(current[:cut], name, size) > width:
                    cut -= 1
                lines.append(current[:cut])
                current = current[cut:]
        if current:
            lines.append(current)
        return lines

    def ellipsize(self, text: str, name: str, size: int, width: int) -> str:
        if self.width(text, name, size) <= width:
            return text
        while text and self.width(text + ELLIPSIS, name, size) > width:
            text = text[:-1]
        return text.rstrip() + ELLIPSIS

    def fit(self, text: str, name: str, width: int, options: Fit) -> tuple[list[str], int, bool]:
        """Lines and font size for `text`, and whether it had to be cut to fit."""
        for size, max_lines in options:
            lines = self.wrap(text, name, size, width)
            if len(lines) <= max_lines:
                return lines, size, False
        size, max_lines = options[-1]
        full = self.wrap(text, name, size, width)
        # the last line carries the cut: keep everything that did not fit in it, then trim
        lines = full[:max_lines - 1] + [self.ellipsize(" ".join(full[max_lines - 1:]), name, size, width)]
        return lines, size, True

    def block(self, y: int, text: str, name: str, width: int, options: Fit, warn, what: str,
              x: int = MARGIN) -> int:
        lines, size, cut = self.fit(text, name, width, options)
        if cut:
            warn(f"{what} was too long and has been cut")
        for line in lines:
            self.text((x, y), line, name, size)
            y += _line_height(size)
        return y

    def png(self) -> bytes:
        out = io.BytesIO()
        self.img.convert("1", dither=Image.Dither.NONE).save(out, format="PNG", dpi=(300, 300))
        return out.getvalue()


def _qr(canvas: Canvas, url: str, x: int, y: int, size: int = 144) -> int:
    """Draw a QR code in a rounded frame with its top-right corner at (x, y). Returns the frame size."""
    qr = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    scale = max(3, size // len(matrix))
    side = len(matrix) * scale
    pad, frame = 5, 4
    total = side + 2 * (pad + frame)
    left = x - total
    canvas.draw.rounded_rectangle([left, y, x - 1, y + total - 1], radius=14, outline=0, width=frame)
    for r, row in enumerate(matrix):
        for c, dark in enumerate(row):
            if dark:
                px, py = left + frame + pad + c * scale, y + frame + pad + r * scale
                canvas.draw.rectangle([px, py, px + scale - 1, py + scale - 1], fill=0)
    return total


def render_main(d: LabelData, warn) -> bytes:
    canvas = Canvas()
    def shown(field: str) -> bool:
        value = d.qr_url if field == "qr" else getattr(d, field)
        return field not in d.hidden and bool(value)

    right = W - MARGIN
    qr_size = 0
    if shown("qr"):
        qr_size = _qr(canvas, d.qr_url, right, MARGIN)
    text_w = right - MARGIN - (qr_size + 16 if qr_size else 0)

    y = MARGIN
    artist_fit: Fit = [(s, 1) for s in range(64, 43, -4)] + [(s, 2) for s in range(52, 35, -4)]
    y = canvas.block(y, d.artist.upper(), SANS, text_w, artist_fit, warn, "The artist")
    label_line = " · ".join(
        p for p in ((d.label or "").upper() if shown("label") else "",
                    f"Cat# {d.catno}" if shown("catno") else "") if p)
    if label_line:
        y = canvas.block(y + 4, label_line, MONO, text_w, [(s, 1) for s in (30, 28, 26)], warn,
                         "The label line")
    title_fit: Fit = [(s, 1) for s in range(40, 31, -2)] + [(s, 2) for s in range(32, 25, -2)]
    y = canvas.block(y + 4, d.title, SANS, text_w, title_fit, warn, "The title")
    y = max(y, MARGIN + qr_size) + 10

    parts = [d.year if shown("year") else None, d.country if shown("country") else None,
             ", ".join(d.styles) if shown("styles") else None]
    info = " · ".join(p for p in parts if p)
    if info:
        y = canvas.rule(y) + 10
        info_fit: Fit = [(s, 1) for s in (32, 30, 28, 26)] + [(26, 2)]
        y = canvas.block(y, info, SANS, W - 2 * MARGIN, info_fit, warn, "The info line") + 6
    if shown("note") and d.note:
        y = canvas.rule(y) + 10
        room = H - MARGIN - y
        note_fit: Fit = [(s, max(1, room // _line_height(s))) for s in (32, 30, 28, 26)]
        if room < _line_height(MIN_SIZE):
            warn("The note does not fit on the label")
        else:
            canvas.block(y, d.note, SANS, W - 2 * MARGIN, note_fit, warn, "The note")
    elif y > H - MARGIN:
        warn("The label is too full: hide a field")
    return canvas.png()


# ---- tracks label ----
SIDE_W = 64  # the black block that carries the side letter
GAP = 16


def side_of(position: str) -> str:
    letters = re.match(r"[A-Za-z]+", position)
    if letters:
        return letters.group(0).upper()
    return re.split(r"[-./]", position)[0] or "·"


def _shows(t: LabelTrack, field: str) -> bool:
    return field not in t.hidden and bool(getattr(t, field))


def _row_height(t: LabelTrack) -> int:
    return _line_height(30) + (_line_height(26) if _shows(t, "note") else 0) + 10


def _group_height(tracks: list[LabelTrack]) -> int:
    return max(sum(_row_height(t) for t in tracks), 62)  # room for the side letter


def _page_height(groups: list[tuple[str, list[LabelTrack]]]) -> int:
    return sum(_group_height(tracks) for _, tracks in groups) + 12 * (len(groups) - 1)


def _paginate(entries: list[LabelTrack]) -> list[list[tuple[str, list[LabelTrack]]]]:
    """Pages of (side, tracks): a side that runs over continues, with its block, on the next label."""
    limit = H - 2 * MARGIN
    pages: list[list[tuple[str, list[LabelTrack]]]] = [[]]
    for t in entries:
        side = side_of(t.position)
        page = pages[-1]
        if page and page[-1][0] == side:
            page[-1][1].append(t)
        else:
            page.append((side, [t]))
        if len(page) > 1 or len(page[0][1]) > 1:  # a lone track always fits
            if _page_height(page) > limit:
                page[-1][1].pop()
                if not page[-1][1]:
                    page.pop()
                pages.append([(side, [t])])
    return pages


def _render_tracks_page(groups: list[tuple[str, list[LabelTrack]]], warn) -> bytes:
    canvas = Canvas()
    x = MARGIN + SIDE_W + GAP
    width = W - MARGIN - x
    all_tracks = [t for _, tracks in groups for t in tracks]
    pos_w = int(max(canvas.width(t.position, MONO, 30) for t in all_tracks)) + 16
    show_bpm = any(_shows(t, "bpm") for t in all_tracks)
    show_key = any(_shows(t, "key") for t in all_tracks)
    bpm_w, key_w = (112 if show_bpm else 0), (84 if show_key else 0)
    y = MARGIN
    for side, tracks in groups:
        top = y
        for t in tracks:
            canvas.text((x, y), t.position, MONO, 30)
            col = x + pos_w
            if _shows(t, "bpm"):
                canvas.text((col, y), t.bpm, MONO, 30)
            col += bpm_w
            if _shows(t, "key"):
                canvas.text((col, y), t.key, MONO, 30)
            col += key_w
            if _shows(t, "tags") and t.tags:
                text = ", ".join(t.tags)
                shown = canvas.ellipsize(text, SANS, 26, x + width - col)
                if shown != text:
                    warn(f"Tags of {t.position} were too long and have been cut")
                canvas.text((col, y + 3), shown, SANS, 26)
            y += _line_height(30)
            if _shows(t, "note"):
                shown = canvas.ellipsize(t.note, SANS, 26, width)
                if shown != t.note:
                    warn(f"The note of {t.position} was too long and has been cut")
                canvas.text((x, y), shown, SANS, 26)
                y += _line_height(26)
            y += 10
        block_h = _group_height(tracks) - 6
        canvas.draw.rectangle([MARGIN, top, MARGIN + SIDE_W - 1, top + block_h - 1], fill=0)
        size = 44 if len(side) == 1 else 34 if len(side) == 2 else 26
        label_w = canvas.width(side, SANS, size)
        canvas.text((MARGIN + int((SIDE_W - label_w) / 2), top + 6), side, SANS, size, fill=255)
        y = top + block_h + 6 + 12
    return canvas.png()


def render_tracks(d: LabelData, warn) -> list[bytes]:
    entries = [t for t in d.tracks if not t.skip]
    if not entries:
        return []
    pages = _paginate(entries)
    if len(pages) > 1:
        warn(f"The tracks need {len(pages)} labels")
    return [_render_tracks_page(groups, warn) for groups in pages]


def render(d: LabelData) -> tuple[list[Rendered], list[str]]:
    """Both labels as PNGs, plus anything the person should look at before printing."""
    warnings: list[str] = []

    def warn_in(prefix: str):
        def warn(message: str) -> None:
            text = f"{prefix}: {message}"
            if text not in warnings:
                warnings.append(text)
        return warn

    out = [Rendered("main", "main", render_main(d, warn_in("Main label")))]
    pages = render_tracks(d, warn_in("Tracks label"))
    for i, png in enumerate(pages, start=1):
        out.append(Rendered("tracks", f"tracks-{i}" if len(pages) > 1 else "tracks", png))
    return out, warnings
