"""Name normalization shared by adapters (matching) and core (search). Research R7."""

import re

from anyascii import anyascii

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
_PUNCT = re.compile(r"[.'’\-,]")


def normalize_name(s: str) -> str:
    folded = _PUNCT.sub(" ", anyascii(s).lower())
    return " ".join(tok for tok in folded.split() if tok not in _SUFFIXES)


def name_words(s: str) -> list[str]:
    return normalize_name(s).split()
