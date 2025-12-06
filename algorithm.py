"""
Text shuffling and reconstruction helpers for the English guessing game.

The module handles three main concerns:
1) Normalize an input sentence by lowercasing and stripping punctuation while keeping
   a record of where punctuation once existed so the UI can show placeholders.
2) Combine articles (a, an, the) with the following word before shuffling to honor
   the "article + noun" grouping rule.
3) Persist and reload past prompts so players can revisit older challenges.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

ARTICLES = {"a", "an", "the"}
# Punctuation characters whose locations should be remembered and removed from the
# normalized text presented to the player.
PUNCTUATION_PATTERN = r"[\.!?,;:'\"\-–—…\(\)\[\]\{\}/\\]"


@dataclass
class PunctuationHint:
    index: int
    symbol: str


@dataclass
class ShuffleResult:
    original_text: str
    normalized_text: str
    tokens: List[str]
    shuffled_tokens: List[str]
    punctuation: List[PunctuationHint] = field(default_factory=list)

    def hint_string(self) -> str:
        """Render the shuffled tokens separated by " / " as required."""
        return " / ".join(self.shuffled_tokens)

    def punctuation_mask(self, placeholder: str = "▢") -> str:
        """Return a mask string showing where punctuation originally existed.

        The length equals the normalized text length with spaces intact. Any index
        that previously held punctuation is replaced with the given placeholder,
        letting the UI display positional hints above the typing field.
        """
        mask = list(self.normalized_text)
        for hint in self.punctuation:
            if hint.index < len(mask):
                mask[hint.index] = placeholder
        return "".join(mask)


def normalize_and_tokenize(text: str) -> tuple[str, List[str], List[PunctuationHint]]:
    """Lowercase text, remove punctuation, and split into grouped tokens.

    Returns a tuple of the normalized text (punctuation removed), grouped tokens,
    and a list of punctuation hints that preserve where punctuation once existed.
    """
    lowered = text.lower()
    punctuation_matches = [
        PunctuationHint(match.start(), match.group())
        for match in re.finditer(PUNCTUATION_PATTERN, lowered)
    ]
    # Remove punctuation completely for the playable text shown to the user.
    normalized = re.sub(PUNCTUATION_PATTERN, "", lowered)
    raw_tokens = normalized.split()

    tokens: List[str] = []
    idx = 0
    while idx < len(raw_tokens):
        word = raw_tokens[idx]
        if word in ARTICLES and idx + 1 < len(raw_tokens):
            tokens.append(f"{word} {raw_tokens[idx + 1]}")
            idx += 2
        else:
            tokens.append(word)
            idx += 1
    return normalized, tokens, punctuation_matches


def shuffle_tokens(tokens: Sequence[str], seed: int | None = None) -> List[str]:
    """Return a new list of tokens in random order.

    A seed can be provided for reproducible shuffles when storing history.
    """
    rng = random.Random(seed)
    shuffled = list(tokens)
    rng.shuffle(shuffled)
    return shuffled


def create_shuffle(text: str, seed: int | None = None) -> ShuffleResult:
    """Create a full shuffle package from the user's input text."""
    normalized, tokens, punctuation = normalize_and_tokenize(text)
    shuffled_tokens = shuffle_tokens(tokens, seed)
    return ShuffleResult(
        original_text=text,
        normalized_text=normalized,
        tokens=list(tokens),
        shuffled_tokens=shuffled_tokens,
        punctuation=punctuation,
    )


def save_entry(entry: ShuffleResult, storage_path: str | Path = "history.json") -> None:
    """Persist the shuffle entry so players can revisit it later."""
    path = Path(storage_path)
    existing: List[dict] = []
    if path.exists():
        existing = json.loads(path.read_text())

    payload = {
        "original_text": entry.original_text,
        "normalized_text": entry.normalized_text,
        "tokens": entry.tokens,
        "shuffled_tokens": entry.shuffled_tokens,
        "punctuation": [{"index": p.index, "symbol": p.symbol} for p in entry.punctuation],
    }
    existing.append(payload)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2))


def load_history(storage_path: str | Path = "history.json") -> List[ShuffleResult]:
    """Load all stored shuffle entries from disk."""
    path = Path(storage_path)
    if not path.exists():
        return []
    raw_entries = json.loads(path.read_text())
    results: List[ShuffleResult] = []
    for item in raw_entries:
        results.append(
            ShuffleResult(
                original_text=item["original_text"],
                normalized_text=item["normalized_text"],
                tokens=list(item["tokens"]),
                shuffled_tokens=list(item["shuffled_tokens"]),
                punctuation=[PunctuationHint(**hint) for hint in item.get("punctuation", [])],
            )
        )
    return results


def reconstruct_attempt(user_input: str, punctuation: Iterable[PunctuationHint]) -> str:
    """Insert placeholder punctuation marks back into a player's attempt.

    The reconstruction allows the frontend to display where punctuation should
    appear relative to the player's ongoing typing.
    """
    chars = list(user_input)
    for hint in punctuation:
        if hint.index <= len(chars):
            chars.insert(hint.index, hint.symbol)
    return "".join(chars)


if __name__ == "__main__":
    example = "There is a train."
    result = create_shuffle(example, seed=42)
    print("Original:", example)
    print("Normalized:", result.normalized_text)
    print("Grouped tokens:", result.tokens)
    print("Shuffled hint:", result.hint_string())
    print("Punctuation mask:", result.punctuation_mask())
