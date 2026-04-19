"""Card image rendering at 300 DPI for print-on-demand poker cards.

Card geometry (defaults target MakePlayingCards poker spec, which most services share):
  - Finished card: 2.5" x 3.5"      (750 x 1050 px at 300 DPI)
  - Bleed canvas: 2.75" x 3.75"     (825 x 1125 px at 300 DPI)
  - Safe zone: 0.1" inside finished edge

All fonts are auto-resolved from common macOS / Linux locations; override with --font.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .latin import Card, Deck, N

# Palette -- kept muted so the numerals dominate.
INK = (24, 24, 28)
MUTED = (110, 110, 115)
HAIRLINE = (180, 176, 168)
PAPER = (250, 246, 236)
ACCENT = (118, 52, 48)  # deep oxblood; the only non-neutral hue


@dataclass
class CardGeometry:
    dpi: int = 300
    finished_w_in: float = 2.5
    finished_h_in: float = 3.5
    bleed_in: float = 0.125
    safe_in: float = 0.1

    @property
    def w(self) -> int:
        return int(round((self.finished_w_in + 2 * self.bleed_in) * self.dpi))

    @property
    def h(self) -> int:
        return int(round((self.finished_h_in + 2 * self.bleed_in) * self.dpi))

    @property
    def bleed_px(self) -> int:
        return int(round(self.bleed_in * self.dpi))

    @property
    def safe_inset_px(self) -> int:
        return self.bleed_px + int(round(self.safe_in * self.dpi))


_FONT_CANDIDATES_SERIF = [
    "/System/Library/Fonts/Supplemental/Baskerville.ttc",
    "/System/Library/Fonts/NewYork.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
]
_FONT_CANDIDATES_MONO = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]
_FONT_CANDIDATES_SANS = [
    "/System/Library/Fonts/Supplemental/Futura.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _first_existing(paths: list[str]) -> str | None:
    for p in paths:
        if Path(p).exists():
            return p
    return None


@dataclass
class Fonts:
    serif_path: str | None
    mono_path: str | None
    sans_path: str | None

    def serif(self, size: int) -> ImageFont.FreeTypeFont:
        if self.serif_path:
            return ImageFont.truetype(self.serif_path, size=size)
        return ImageFont.load_default()

    def mono(self, size: int) -> ImageFont.FreeTypeFont:
        if self.mono_path:
            return ImageFont.truetype(self.mono_path, size=size)
        return ImageFont.load_default()

    def sans(self, size: int) -> ImageFont.FreeTypeFont:
        if self.sans_path:
            return ImageFont.truetype(self.sans_path, size=size)
        return ImageFont.load_default()


def resolve_fonts(
    serif_override: str | None = None,
    mono_override: str | None = None,
    sans_override: str | None = None,
) -> Fonts:
    return Fonts(
        serif_path=serif_override or _first_existing(_FONT_CANDIDATES_SERIF),
        mono_path=mono_override or _first_existing(_FONT_CANDIDATES_MONO),
        sans_path=sans_override or _first_existing(_FONT_CANDIDATES_SANS),
    )


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


# Icosahedron (d20) geometry transcribed from d20.svg's compound path.
# The SVG uses a nonzero fill-rule with one outer silhouette wound
# opposite to 10 inner triangular faces, so the faces "cut" out of the
# silhouette and the negative space between them reads as the wireframe.
# Coordinates are in the SVG's viewBox (0..100). Bezier corner-smoothing
# points are preserved to keep the subtle rounded corners faithful.
_D20_CENTER: tuple[float, float] = (50.0, 50.45)
_D20_RADIUS: float = 48.15  # half of silhouette height (top-to-bottom)

_D20_SILHOUETTE: tuple[tuple[float, float], ...] = (
    (91.9, 74.7), (92.0, 74.5), (92.0, 74.4), (92.0, 74.3), (92.0, 74.2),
    (92.0, 74.0), (92.0, 73.9), (92.0, 73.7), (92.0, 27.2), (92.0, 27.1),
    (92.0, 27.0), (92.0, 26.9), (92.0, 26.8), (92.0, 26.7), (92.0, 26.6),
    (92.0, 26.5), (91.9, 26.3), (91.9, 26.2), (91.8, 26.1), (91.8, 26.0),
    (91.7, 25.9), (91.5, 25.8), (91.4, 25.8), (50.9, 2.3),  (49.1, 2.3),
    (8.8, 25.6),  (8.6, 25.7),  (8.5, 25.7),  (8.4, 25.8),  (8.3, 25.9),
    (8.2, 26.0),  (8.1, 26.1),  (8.0, 26.2),  (8.0, 26.3),  (7.9, 26.4),
    (7.9, 26.5),  (7.9, 26.6),  (7.9, 26.7),  (7.9, 26.8),  (7.9, 26.9),
    (7.9, 27.0),  (7.9, 27.1),  (7.9, 73.6),  (7.9, 73.9),  (7.9, 74.0),
    (8.0, 74.3),  (8.2, 74.6),  (8.2, 74.7),  (8.4, 75.0),  (8.6, 75.2),
    (8.7, 75.2),  (8.8, 75.2),  (49.1, 98.5), (49.2, 98.6), (49.3, 98.6),
    (49.4, 98.6), (49.5, 98.6), (49.6, 98.6), (49.7, 98.6), (49.9, 98.6),
    (50.1, 98.6), (50.2, 98.6), (50.4, 98.6), (50.5, 98.6), (50.6, 98.6),
    (50.7, 98.6), (50.8, 98.5), (91.1, 75.2), (91.2, 75.2), (91.3, 75.2),
    (91.4, 75.1), (91.5, 75.0), (91.6, 74.9), (91.7, 74.8), (91.8, 74.7),
)

_D20_FACES: tuple[tuple[tuple[float, float], ...], ...] = (
    ((11.9, 37.6), (23.1, 65.4), (22.7, 66.3), (12.4, 70.6), (11.5, 70.0), (11.5, 37.7)),
    ((69.9, 65.2), (30.1, 65.2), (29.5, 64.2), (49.4, 29.7), (50.5, 29.7), (70.4, 64.2)),
    ((25.6, 61.6), (12.7, 29.7), (13.3, 28.8), (45.5, 27.2), (46.1, 28.2), (26.7, 61.7)),
    ((69.5, 70.0), (50.5, 93.4), (49.5, 93.4), (30.5, 70.0), (31.0, 68.9), (69.0, 68.9)),
    ((73.3, 61.7), (53.9, 28.2), (54.5, 27.2), (86.7, 28.8), (87.3, 29.7), (74.4, 61.6)),
    ((51.8, 22.8), (51.8, 8.2),  (52.8, 7.6),  (82.0, 24.5), (81.9, 24.9), (52.4, 23.4)),
    ((47.5, 23.4), (18.0, 24.9), (17.9, 24.5), (47.2, 7.7),  (48.2, 8.3),  (48.2, 22.8)),
    ((25.5, 69.7), (41.6, 89.6), (41.3, 89.9), (15.0, 74.7), (15.1, 73.5), (24.8, 69.5)),
    ((75.2, 69.5), (84.9, 73.5), (85.0, 74.7), (58.6, 89.9), (58.3, 89.6), (74.4, 69.7)),
    ((87.6, 70.6), (77.3, 66.3), (76.9, 65.4), (88.1, 37.6), (88.5, 37.7), (88.5, 70.0)),
)


def _draw_d20(img: Image.Image, cx: float, cy: float, r: float, color: tuple[int, int, int]) -> None:
    """Render a d20 by replaying d20.svg's compound path.

    ``r`` is the silhouette circumradius (half the top-to-bottom height).
    Drawn at 4x and downsampled for smooth anti-aliased edges.
    """
    SCALE = 4
    pad = max(2, int(r * 0.05)) * SCALE
    half = int(r * SCALE) + pad
    box = half * 2
    aa = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    d = ImageDraw.Draw(aa)

    svg_scale = (r * SCALE) / _D20_RADIUS
    csx, csy = _D20_CENTER

    def xf(pt: tuple[float, float]) -> tuple[float, float]:
        return (half + (pt[0] - csx) * svg_scale, half + (pt[1] - csy) * svg_scale)

    fill_rgba = (*color, 255)
    d.polygon([xf(p) for p in _D20_SILHOUETTE], fill=fill_rgba)
    # Overwrite (not composite) each face back to transparent — this replicates
    # the SVG's nonzero-rule "cut" of the faces out of the silhouette.
    for face in _D20_FACES:
        d.polygon([xf(p) for p in face], fill=(0, 0, 0, 0))

    small = aa.resize((box // SCALE, box // SCALE), Image.LANCZOS)
    img.paste(small, (int(cx - small.width / 2), int(cy - small.height / 2)), small)


def render_card_front(card: Card, fonts: Fonts, geom: CardGeometry) -> Image.Image:
    img = Image.new("RGB", (geom.w, geom.h), PAPER)
    draw = ImageDraw.Draw(img)

    safe = geom.safe_inset_px
    inner = (safe, safe, geom.w - safe, geom.h - safe)

    draw.rectangle(inner, outline=INK, width=4)
    draw.rectangle(
        (safe + 10, safe + 10, geom.w - safe - 10, geom.h - safe - 10),
        outline=HAIRLINE,
        width=1,
    )

    # --- Header ---
    wordmark_font = fonts.serif(46)
    wordmark = "SECRET ROLL"
    wm_w, wm_h = _text_size(draw, wordmark, wordmark_font)
    wm_y = safe + 22
    draw.text(((geom.w - wm_w) // 2, wm_y), wordmark, font=wordmark_font, fill=INK)

    d20_cy = wm_y + wm_h + 48
    _draw_d20(img, geom.w / 2, d20_cy, 18, ACCENT)

    id_font = fonts.sans(22)
    id_text = f"No. {card.card_id:02d} / {3 * N}"
    id_w, id_h = _text_size(draw, id_text, id_font)
    id_y = d20_cy + 32
    draw.text(((geom.w - id_w) // 2, id_y), id_text, font=id_font, fill=MUTED)

    header_bottom = id_y + id_h + 18

    # --- Table ---
    table_top = header_bottom
    table_bottom = geom.h - safe - 55
    table_left = safe + 40
    table_right = geom.w - safe - 40
    table_w = table_right - table_left
    table_h = table_bottom - table_top

    n_rows = N + 1  # 1 header + 20 data
    row_h = table_h / n_rows
    col_mid = table_left + table_w / 2
    rolled_cx = table_left + table_w / 4
    secret_cx = table_left + 3 * table_w / 4

    # Header row
    header_font = fonts.sans(22)
    for label, cx in [("ROLLED", rolled_cx), ("SECRET", secret_cx)]:
        lw, lh = _text_size(draw, label, header_font)
        draw.text((cx - lw / 2, table_top + (row_h - lh) / 2 - 2), label, font=header_font, fill=MUTED)

    header_row_bottom = table_top + row_h
    draw.line([(table_left, header_row_bottom), (table_right, header_row_bottom)], fill=INK, width=2)
    # Column divider starts below the SAID/ROLLED labels
    draw.line([(col_mid, header_row_bottom), (col_mid, table_bottom)], fill=HAIRLINE, width=1)

    num_font = fonts.mono(28)
    rolled_font = fonts.mono(30)

    for i in range(N):
        y_top = header_row_bottom + i * row_h
        y_bot = header_row_bottom + (i + 1) * row_h
        y_mid = (y_top + y_bot) / 2

        if i > 0:
            draw.line(
                [(table_left + 20, y_top), (table_right - 20, y_top)],
                fill=HAIRLINE,
                width=1,
            )

        rolled_text = str(i + 1)
        secret_text = str(card.mapping[i])
        rw, rh = _text_size(draw, rolled_text, num_font)
        sw, sh = _text_size(draw, secret_text, rolled_font)
        draw.text((rolled_cx - rw / 2, y_mid - rh / 2 - 3), rolled_text, font=num_font, fill=MUTED)
        draw.text((secret_cx - sw / 2, y_mid - sh / 2 - 3), secret_text, font=rolled_font, fill=INK)

    return img


def _sample_border_color(art: Image.Image) -> tuple[int, int, int]:
    """Take the median RGB from the outermost ~0.3% band on all four edges,
    skipping the corner regions where decorative badges often sit.

    Narrow-band sampling captures the thin outer frame the eye actually reads as
    the background color, rather than the darker decorative filigree just inside.
    """
    px = art.convert("RGB").load()
    w, h = art.size
    band_h = max(1, int(h * 0.003))
    band_w = max(1, int(w * 0.003))
    rs: list[int] = []
    gs: list[int] = []
    bs: list[int] = []

    def _add(x: int, y: int) -> None:
        r, g, b = px[x, y]
        rs.append(r); gs.append(g); bs.append(b)

    for y in list(range(band_h)) + list(range(h - band_h, h)):
        for x in range(int(w * 0.15), int(w * 0.85)):
            _add(x, y)
    for x in list(range(band_w)) + list(range(w - band_w, w)):
        for y in range(int(h * 0.15), int(h * 0.85)):
            _add(x, y)

    rs.sort(); gs.sort(); bs.sort()
    mid = len(rs) // 2
    return rs[mid], gs[mid], bs[mid]


def render_card_back_from_art(
    art_path: Path,
    geom: CardGeometry,
    art_inset_in: float = 0.08,
) -> Image.Image:
    """Build a card back from user-supplied art.

    The art is scaled to fit inside (finished_area - 2 * art_inset_in) and
    centered, leaving a visible colored band between the art and the cut edge
    plus the full bleed beyond the cut. ``art_inset_in`` controls how much
    colored padding surrounds the art inside the finished card.
    """
    art = Image.open(art_path).convert("RGB")

    border = _sample_border_color(art)
    canvas = Image.new("RGB", (geom.w, geom.h), border)

    inset_px = int(round(art_inset_in * geom.dpi))
    target_w = int(round(geom.finished_w_in * geom.dpi)) - 2 * inset_px
    target_h = int(round(geom.finished_h_in * geom.dpi)) - 2 * inset_px

    aw, ah = art.size
    scale = min(target_w / aw, target_h / ah)
    new_size = (int(round(aw * scale)), int(round(ah * scale)))
    art_resized = art.resize(new_size, Image.LANCZOS)

    x = (geom.w - new_size[0]) // 2
    y = (geom.h - new_size[1]) // 2
    canvas.paste(art_resized, (x, y))
    return canvas


def render_card_back(fonts: Fonts, geom: CardGeometry) -> Image.Image:
    img = Image.new("RGB", (geom.w, geom.h), PAPER)
    draw = ImageDraw.Draw(img)

    safe = geom.safe_inset_px
    draw.rectangle((safe, safe, geom.w - safe, geom.h - safe), outline=INK, width=4)
    draw.rectangle(
        (safe + 10, safe + 10, geom.w - safe - 10, geom.h - safe - 10),
        outline=HAIRLINE,
        width=1,
    )

    cx, cy = geom.w / 2, geom.h / 2
    _draw_d20(img, cx, cy - 30, 140, ACCENT)

    wordmark_font = fonts.serif(72)
    subtitle_font = fonts.sans(32)

    wm = "SECRET ROLL"
    ww, wh = _text_size(draw, wm, wordmark_font)
    wm_y = cy + 150
    draw.text((cx - ww // 2, wm_y), wm, font=wordmark_font, fill=INK)

    sub = "LOOKUP DECK"
    sw, sh = _text_size(draw, sub, subtitle_font)
    sub_y = wm_y + wh + 48
    draw.text((cx - sw // 2, sub_y), sub, font=subtitle_font, fill=MUTED)

    return img


def render_deck(
    deck: Deck,
    out_dir: Path,
    geom: CardGeometry,
    fonts: Fonts,
    art_back_path: Path | None = None,
    art_inset_in: float = 0.08,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    fronts: list[Image.Image] = []
    front_paths: list[Path] = []
    for card in deck.cards:
        img = render_card_front(card, fonts, geom)
        path = out_dir / f"card_front_{card.card_id:02d}.png"
        img.save(path, dpi=(geom.dpi, geom.dpi), optimize=True)
        fronts.append(img)
        front_paths.append(path)

    back = render_card_back(fonts, geom)
    back_path = out_dir / "card_back.png"
    back.save(back_path, dpi=(geom.dpi, geom.dpi), optimize=True)

    art_back_out: Path | None = None
    if art_back_path is not None:
        art_back = render_card_back_from_art(art_back_path, geom, art_inset_in=art_inset_in)
        art_back_out = out_dir / "card_back_art.png"
        art_back.save(art_back_out, dpi=(geom.dpi, geom.dpi), optimize=True)

    # A sheet contact-print of all 60 fronts on a single PNG -- handy for visual
    # review. 6 cols x 10 rows at 1/4 scale fits on-screen easily.
    contact_path = out_dir / "deck_contact_sheet.png"
    cols, rows = 6, 10
    pad = 12
    thumb_w, thumb_h = geom.w // 4, geom.h // 4
    sheet_w = cols * thumb_w + (cols + 1) * pad
    sheet_h = rows * thumb_h + (rows + 1) * pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), PAPER)
    for idx, front in enumerate(fronts):
        r, c = divmod(idx, cols)
        x = pad + c * (thumb_w + pad)
        y = pad + r * (thumb_h + pad)
        sheet.paste(front.resize((thumb_w, thumb_h), Image.LANCZOS), (x, y))
    sheet.save(contact_path, optimize=True)

    return {
        "front_paths": [str(p) for p in front_paths],
        "back_path": str(back_path),
        "art_back_path": str(art_back_out) if art_back_out else None,
        "contact_sheet_path": str(contact_path),
        "dimensions_px": [geom.w, geom.h],
        "dpi": geom.dpi,
    }
