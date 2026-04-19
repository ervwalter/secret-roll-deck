# secret-roll-deck

Generate a fair-mix lookup card deck for Pathfinder secret d20 rolls.

Players roll a d20 in the open and announce `face, +mod`. The GM draws a card
from this deck and reads the corresponding *secret* value from the table —
translating "11, +14" into whatever `11` maps to on that card, then adding the
modifier. The player can't tell whether they rolled high or low; only the GM
knows the real result.

## Fairness

The deck is 60 cards built from three independently-sampled 20×20 Latin
squares. Each card is a permutation of 1–20 (every rolled number maps to a
unique secret value). Across all 60 cards, every rolled number resolves to each
secret value **exactly 3 times**, so the column mean is exactly 10.5 for every
rolled value — no systematic skew.

Cards 1–20 come from the first Latin square, 21–40 from the second, 41–60 from
the third. **Each contiguous 20-card group is itself a fully-balanced subdeck**,
so if you want a thinner deck, just take the first 20 or first 40 cards and
discard the rest. Shuffle the deck before play.

Latin squares are sampled with the **Jacobson–Matthews** Markov chain (Electron.
J. Combin. 3, 1996) which mixes over the space of 20×20 Latin squares. See
`src/secret_roll/latin.py`.

## Quick start

```sh
uv sync
uv run secret-roll generate --seed 42
```

Outputs in `./out/`:

- `deck.json` — canonical mapping (`{card_id, mapping[20]}`)
- `deck.csv` — spreadsheet view (one row per card)
- `card_front_01.png` … `card_front_60.png` — 825×1125 px @ 300 DPI
- `card_back.png` — clean text-only back
- `deck_contact_sheet.png` — all 60 fronts in a 6×10 grid for review

### Custom card-back art

Supply your own art for the back (the text back is always produced as well):

```sh
uv run secret-roll generate --seed 42 --art-back assets/card-back.png
```

The art is scaled to fit the finished card area minus a small colored inset
(default `0.08"` = ~24 px visible band after cutting). The inset color is
auto-sampled from the outermost pixels of the art so the bleed blends into the
frame. Tune with `--art-inset-inches`.

A sample art file is included at `assets/card-back.png`.

### Verify a saved deck

```sh
uv run secret-roll verify out/deck.json
```

Checks that the deck is 60 unique cards, each a permutation of 1–20, with every
(rolled, secret) pair occurring exactly 3 times, and that each contiguous 20-card
subdeck is also independently balanced.

## Card geometry

Default geometry matches **MakePlayingCards** poker spec (works for
DriveThruCards, GameCrafter, and most services):

- Finished: 2.5"×3.5" (750×1050 px @ 300 DPI)
- Bleed: 1/8" on each side → full canvas 2.75"×3.75" (825×1125 px)
- Safe zone: 0.1" inside the finished edge

Override with `--dpi` and `--bleed-inches`.

## All CLI flags

```
uv run secret-roll generate --help
uv run secret-roll verify out/deck.json
```

## License

MIT — see [LICENSE](LICENSE).
