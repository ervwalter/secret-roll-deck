"""CLI entrypoint: `secret-roll generate` and `secret-roll verify`."""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

from .latin import Deck, build_deck, verify_deck, write_deck
from .render import CardGeometry, render_deck, resolve_fonts


def _cmd_generate(args: argparse.Namespace) -> int:
    seed = args.seed if args.seed is not None else secrets.randbits(64)
    out_dir = Path(args.out_dir)

    print(f"Generating deck with seed={seed}")
    deck = build_deck(seed)
    report = verify_deck(deck)
    if not report["ok"]:
        print("Deck verification FAILED:", file=sys.stderr)
        for e in report["errors"]:
            print(f"  - {e}", file=sys.stderr)
        return 2
    print(f"Deck verified: {report['deck_size']} cards, "
          f"each actual value appears {report['expected_per_value_per_column']}x per column.")

    json_path, csv_path = write_deck(deck, out_dir)
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")

    geom = CardGeometry(dpi=args.dpi, bleed_in=args.bleed_inches)
    fonts = resolve_fonts(
        serif_override=args.serif_font,
        mono_override=args.mono_font,
        sans_override=args.sans_font,
    )
    missing = [name for name, p in [("serif", fonts.serif_path), ("mono", fonts.mono_path), ("sans", fonts.sans_path)] if p is None]
    if missing:
        print(f"WARNING: no TTF found for: {', '.join(missing)}. Falling back to Pillow's default bitmap font (low quality).", file=sys.stderr)

    art_back_path = Path(args.art_back) if args.art_back else None
    if art_back_path and not art_back_path.exists():
        print(f"ERROR: art-back file not found: {art_back_path}", file=sys.stderr)
        return 3

    print(f"Rendering cards at {geom.w}x{geom.h} px, {geom.dpi} DPI, bleed={geom.bleed_in}\"...")
    if art_back_path:
        print(f"Using art back: {art_back_path}")
    info = render_deck(deck, out_dir, geom, fonts, art_back_path=art_back_path, art_inset_in=args.art_inset_inches)
    msg = f"Wrote {len(info['front_paths'])} front PNGs + back PNG"
    if info.get("art_back_path"):
        msg += " + alternate art back"
    msg += f" + contact sheet to {out_dir}/"
    print(msg)
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    deck = Deck.from_json_path(Path(args.deck_json))
    report = verify_deck(deck)
    print(f"Deck size: {report['deck_size']}")
    print(f"N: {report['n']}")
    print(f"Expected per-value-per-column: {report['expected_per_value_per_column']}")
    if report["ok"]:
        print("OK: deck is balanced and well-formed.")
        return 0
    print("FAILED:", file=sys.stderr)
    for e in report["errors"]:
        print(f"  - {e}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="secret-roll", description="Generate a secret-roll lookup card deck.")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Build deck + render cards")
    g.add_argument("--seed", type=int, default=None, help="Deterministic seed (default: random)")
    g.add_argument("--out-dir", default="out", help="Output directory (default: ./out)")
    g.add_argument("--dpi", type=int, default=300, help="Render DPI (default: 300)")
    g.add_argument("--bleed-inches", type=float, default=0.125, help="Bleed on each side in inches (default: 0.125)")
    g.add_argument("--art-back", default=None, help="Path to a custom card-back image (auto-fits with matched-color bleed)")
    g.add_argument("--art-inset-inches", type=float, default=0.08, help="Colored padding around the art inside the finished card (default: 0.08)")
    g.add_argument("--serif-font", default=None, help="Override serif TTF path")
    g.add_argument("--mono-font", default=None, help="Override mono TTF path")
    g.add_argument("--sans-font", default=None, help="Override sans TTF path")
    g.set_defaults(func=_cmd_generate)

    v = sub.add_parser("verify", help="Re-verify a deck.json file")
    v.add_argument("deck_json", help="Path to deck.json")
    v.set_defaults(func=_cmd_verify)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
