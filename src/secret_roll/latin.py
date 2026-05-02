"""Latin-square-based secret-roll deck construction.

The deck is 3 independently-sampled 20x20 Latin squares stacked into 60 rows.
Each row is a bijection from "announced" (1..20) to "actual" (1..20). The column
property of a Latin square guarantees each actual value appears exactly once per
column across one square's 20 rows, so across 60 rows each actual value appears
exactly 3 times per announced column -- the strongest fairness guarantee this
deck size admits.

Sampling uses Jacobson-Matthews (Electron. J. Combin. 3 (1996)), which mixes via
moves on a 3D incidence tensor that allows a single "improper" cell of value -1.
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path

N = 20
SQUARES_PER_DECK = 3
DECK_SIZE = N * SQUARES_PER_DECK
ALLOWED_DECK_SIZES = (N, 2 * N, 3 * N)


def _jacobson_matthews(n: int, rng: random.Random, iterations: int | None = None) -> list[list[int]]:
    if iterations is None:
        iterations = max(n**3, 1000)

    L = [[(r + c) % n for c in range(n)] for r in range(n)]
    M = [[[0] * n for _ in range(n)] for _ in range(n)]
    for r in range(n):
        for c in range(n):
            M[r][c][L[r][c]] = 1

    proper = True
    imp: tuple[int, int, int] | None = None
    step = 0

    while step < iterations or not proper:
        step += 1

        if proper:
            while True:
                r = rng.randrange(n)
                c = rng.randrange(n)
                s = rng.randrange(n)
                if M[r][c][s] == 0:
                    break
        else:
            assert imp is not None
            r, c, s = imp

        s_ones = [sp for sp in range(n) if sp != s and M[r][c][sp] == 1]
        c_ones = [cp for cp in range(n) if cp != c and M[r][cp][s] == 1]
        r_ones = [rp for rp in range(n) if rp != r and M[rp][c][s] == 1]

        if proper:
            sp, cp, rp = s_ones[0], c_ones[0], r_ones[0]
        else:
            sp = rng.choice(s_ones)
            cp = rng.choice(c_ones)
            rp = rng.choice(r_ones)

        M[r][c][s] += 1
        M[r][c][sp] -= 1
        M[r][cp][s] -= 1
        M[rp][c][s] -= 1
        M[r][cp][sp] += 1
        M[rp][c][sp] += 1
        M[rp][cp][s] += 1
        M[rp][cp][sp] -= 1

        if M[rp][cp][sp] < 0:
            proper = False
            imp = (rp, cp, sp)
        else:
            proper = True
            imp = None

    L = [[0] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            for s in range(n):
                if M[r][c][s] == 1:
                    L[r][c] = s
                    break
    return L


@dataclass
class Card:
    card_id: int  # 1..60
    mapping: list[int]  # mapping[announced-1] = actual (1..20)


@dataclass
class Deck:
    cards: list[Card]
    seed: int

    def to_json(self) -> str:
        return json.dumps(
            {
                "seed": self.seed,
                "n": N,
                "size": len(self.cards),
                "cards": [{"id": c.card_id, "mapping": c.mapping} for c in self.cards],
            },
            indent=2,
        )

    @classmethod
    def from_json_path(cls, path: Path) -> Deck:
        data = json.loads(path.read_text())
        cards = [Card(card_id=c["id"], mapping=c["mapping"]) for c in data["cards"]]
        return cls(cards=cards, seed=data.get("seed", 0))

    def to_csv_rows(self) -> list[list[str]]:
        header = ["card_id"] + [f"said_{i + 1}" for i in range(N)]
        rows = [header]
        for c in self.cards:
            rows.append([str(c.card_id)] + [str(v) for v in c.mapping])
        return rows


def build_deck(seed: int, num_cards: int = DECK_SIZE) -> Deck:
    """Build a deck of 20, 40, or 60 cards as contiguous 20-card Latin-square subdecks.

    Cards 1-20 come from the first Latin square, 21-40 from the second, 41-60
    from the third. Each contiguous group of 20 is itself a fully-balanced
    subdeck (each actual value appears exactly once per announced column), so a
    smaller deck simply uses fewer subdecks.

    Rows are emitted in Jacobson-Matthews' natural (already-randomized) order --
    the user is expected to shuffle the physical deck before play.
    """
    if num_cards not in ALLOWED_DECK_SIZES:
        raise ValueError(f"num_cards must be one of {ALLOWED_DECK_SIZES}, got {num_cards}")

    num_squares = num_cards // N
    rng = random.Random(seed)

    def _materialize() -> list[list[list[int]]]:
        return [_jacobson_matthews(N, rng) for _ in range(num_squares)]

    def _rows_from(squares: list[list[list[int]]]) -> list[list[int]]:
        return [[v + 1 for v in row] for sq in squares for row in sq]

    squares = _materialize()
    rows = _rows_from(squares)

    # Vanishingly unlikely, but guarantee no duplicate cards within the deck.
    for attempt in range(6):
        if len(set(map(tuple, rows))) == len(rows):
            break
        squares[attempt % num_squares] = _jacobson_matthews(N, rng)
        rows = _rows_from(squares)
    else:
        raise RuntimeError("Could not produce a deck with unique cards after 6 resample rounds")

    cards = [Card(card_id=i + 1, mapping=row) for i, row in enumerate(rows)]
    return Deck(cards=cards, seed=seed)


def verify_deck(deck: Deck) -> dict:
    errors: list[str] = []

    deck_size = len(deck.cards)
    if deck_size not in ALLOWED_DECK_SIZES:
        errors.append(f"expected deck size in {ALLOWED_DECK_SIZES}, got {deck_size}")

    for card in deck.cards:
        if sorted(card.mapping) != list(range(1, N + 1)):
            errors.append(f"card {card.card_id} is not a permutation of 1..{N}: {card.mapping}")

    expected_per_value = max(deck_size // N, 1)
    for col in range(N):
        counts = [0] * (N + 1)
        for card in deck.cards:
            counts[card.mapping[col]] += 1
        for val in range(1, N + 1):
            if counts[val] != expected_per_value:
                errors.append(
                    f"column rolled={col + 1}: secret={val} appears {counts[val]}x "
                    f"(expected {expected_per_value}x)"
                )

    # Each contiguous 20-card subdeck should itself be a balanced Latin square,
    # so that users can take only the first 20 or 40 cards for a thinner deck.
    num_subdecks = deck_size // N
    for sub_idx in range(num_subdecks):
        start = sub_idx * N
        sub = deck.cards[start : start + N]
        if len(sub) != N:
            continue
        for col in range(N):
            col_vals = sorted(card.mapping[col] for card in sub)
            if col_vals != list(range(1, N + 1)):
                errors.append(
                    f"subdeck {sub_idx + 1} (cards {start + 1}-{start + N}): "
                    f"column rolled={col + 1} is not a permutation of 1..{N}"
                )

    seen: set[tuple[int, ...]] = set()
    for card in deck.cards:
        key = tuple(card.mapping)
        if key in seen:
            errors.append(f"duplicate card mapping at id {card.card_id}")
        seen.add(key)

    return {
        "deck_size": deck_size,
        "n": N,
        "expected_per_value_per_column": expected_per_value,
        "errors": errors,
        "ok": not errors,
    }


def write_deck(deck: Deck, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "deck.json"
    csv_path = out_dir / "deck.csv"
    json_path.write_text(deck.to_json())
    with csv_path.open("w", newline="") as f:
        csv.writer(f).writerows(deck.to_csv_rows())
    return json_path, csv_path
