"""[S] Recognition of object names: the same object is often written in several ways.

Names are compared after normalisation: case and punctuation, a parenthesised acronym, generic words ("Compound
Protocol" = "Compound"), a deployment suffix ("X on Ethereum") and versions ("Uniswap v3" = "Uniswap"). Anonymous or
generic names ("DeFi protocol D", "Swap") do not identify an object and are discarded.
"""

from __future__ import annotations

import re
from typing import Optional

from .models import DomainObject

GENERIC_WORDS = {"protocol", "protocols", "finance", "fi", "network", "dao", "labs", "platform", "app",
                 "the", "project", "io", "com", "org", "xyz"}
GENERIC_TERMS = {"defi", "protocol", "protocols", "platform", "platforms", "application", "applications", "app",
                 "dapp", "dex", "exchange", "swap", "bridge", "lending", "borrowing", "pool", "pools", "vault",
                 "vaults", "farm", "wallet", "oracle", "stablecoin", "token", "project", "startup", "start",
                 "up", "decentralized", "decentralised", "finance", "financial", "service", "market", "amm",
                 "yield", "aggregator", "insurance", "derivative", "derivatives", "the", "a", "an", "of", "new",
                 "crypto", "blockchain", "smart", "contract", "fund", "company", "provider"}
_ROMAN = re.compile(r"\b(?:II|III|IV|V|VI)\b")
_ACRONYM = re.compile(r"^[A-Z0-9][A-Za-z0-9.\-]{0,7}$")
_VERSION = re.compile(r"\b(?:v(?:ersion)?\s?\d+(?:\.\d+)*|\d+(?:\.\d+)+)\b", re.IGNORECASE)
_ANONYMOUS = [
    re.compile(r"^\d+\s*[–-]\s*[A-Z]{1,3}$"),
    re.compile(r"\b(?:provider|protocol|platform|project|application|app|dex|exchange|pool|vault|company|"
               r"start-?up|firm|bank|lender|borrower)\s+(?:[A-Z]|\d+|\d+\s*[–-]\s*[A-Z]{1,3})$", re.IGNORECASE),
    re.compile(r"^(?:proposed|hypothetical|anonymous|unnamed|example|sample|generic|our|their)\b", re.IGNORECASE),
]


def _key(name: str) -> str:
    return " ".join(name.split()).casefold()


def acronyms(name: str) -> list[str]:
    return [m.strip() for m in re.findall(r"\(([^)]*)\)", name)
            if _ACRONYM.match(m.strip()) and sum(ch.isupper() for ch in m) >= 2]


def _join_single_letters(words: list[str]) -> list[str]:
    out: list[str] = []
    run: list[str] = []
    for w in words + [""]:
        if len(w) == 1 and w.isalpha():
            run.append(w)
            continue
        out.extend(["".join(run)] if len(run) >= 3 else run)
        run = []
        if w:
            out.append(w)
    return out


def name_keys(name: str) -> set[str]:
    keys = {_key(name)}
    s = re.sub(r"\([^)]*\)", " ", name)
    s = re.sub(r"\s+on\s+[A-Z][\w\s.-]*$", " ", s)
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", s)
    s = _ROMAN.sub(" ", _VERSION.sub(" ", s))
    s = re.sub(r"\b[vV]\s?\d+\b", " ", s)
    s = re.sub(r"\s\d{1,2}\s*$", " ", s)
    words = _join_single_letters([w for w in re.split(r"[^0-9a-z]+", s.casefold()) if w])
    core = [w for w in words if w not in GENERIC_WORDS]
    if core or words:
        keys.add(" ".join(core or words))
    return keys


def same_object(a: list[str], b: list[str]) -> bool:
    """True when two lists of names (name and aliases) designate the same object."""
    ka = set().union(*(name_keys(n) for n in a if n.strip()))
    kb = set().union(*(name_keys(n) for n in b if n.strip()))
    acr_a = {_key(x) for n in a for x in acronyms(n)}
    acr_b = {_key(x) for n in b for x in acronyms(n)}
    return bool(ka & kb) or bool({_key(n) for n in a} & acr_b) or bool({_key(n) for n in b} & acr_a)


def find_registered(objects: dict[str, DomainObject], names: list[str]) -> Optional[DomainObject]:
    for obj in objects.values():
        if same_object(names, [obj.name, *obj.aliases]):
            return obj
    return None


def is_generic(name: str) -> bool:
    n = name.strip()
    words = re.findall(r"[a-z0-9]+", n.casefold())
    if len(n) < 2 or not words:
        return True
    return all(w in GENERIC_TERMS for w in words) or any(p.search(n) for p in _ANONYMOUS)
