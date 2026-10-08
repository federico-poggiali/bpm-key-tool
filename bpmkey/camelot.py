from __future__ import annotations

import re
from typing import Optional

_NOTE_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_MAJOR = {0: 8, 7: 9, 2: 10, 9: 11, 4: 12, 11: 1, 6: 2, 1: 3, 8: 4, 3: 5, 10: 6, 5: 7}
_MINOR = {9: 8, 4: 9, 11: 10, 6: 11, 1: 12, 8: 1, 3: 2, 10: 3, 5: 4, 0: 5, 7: 6, 2: 7}

_KEY_RE = re.compile(
    r"^\s*([A-Ga-g])\s*([#♯b♭]?)\s*(m|min|minor|maj|major|M)?\s*$", re.IGNORECASE
)


def to_camelot(key) -> Optional[str]:
    """Normalise 'Em', 'C#m', 'F♯', 'Bb minor', ('A','minor') or '8A' to Camelot."""
    if key is None:
        return None
    if isinstance(key, (tuple, list)) and len(key) == 2:
        tonic, scale = key
        key = f"{tonic} {scale}"
    s = str(key).strip().replace("♯", "#").replace("♭", "b")
    if not s:
        return None
    m = re.fullmatch(r"(1[0-2]|[1-9])\s*([ABab])", s)
    if m:  # already Camelot
        return f"{int(m.group(1))}{m.group(2).upper()}"
    m = _KEY_RE.match(s)
    if not m:
        return None
    note, acc, mode = m.group(1), m.group(2), m.group(3) or ""
    pc = _NOTE_PC[note.upper()]
    if acc == "#":
        pc += 1
    elif acc.lower() == "b" and acc != "B":
        pc -= 1
    pc %= 12
    # Case-sensitive 'M' (major) vs 'm' (minor) must be checked before lowercasing
    minor = mode in ("m",) or mode.lower() in ("min", "minor")
    if mode == "M":
        minor = False
    elif not mode and note.islower():
        minor = False
    table = _MINOR if minor else _MAJOR
    return f"{table[pc]}{'A' if minor else 'B'}"


def open_key_to_camelot(ok) -> Optional[str]:
    """Open Key ('3d' = D major, '5m' = C minor) -> Camelot. Same wheel, rotated by 7."""
    m = re.fullmatch(r"(1[0-2]|[1-9])\s*([dmDM])", str(ok or "").strip())
    if not m:
        return None
    n = (int(m.group(1)) + 6) % 12 + 1
    return f"{n}{'B' if m.group(2).lower() == 'd' else 'A'}"
