"""Language detection, normalisation, tokenisation (stdlib only)."""
from __future__ import annotations

import re
import unicodedata

_AR_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_TOKEN = re.compile(r"[\w\-]+", re.UNICODE)

STOP = {
    "en": set("a an the of to in on for and or is are be can i my me we our it this that with at by as from do does use using should was were will about any if".split()),
    "ru": set("и в во на по с со к ко о об от для а но или ли я мы мне меня мой моя это этот эта как что можно ли же при из у не да".split()),
    "ar": set("في من على إلى الى عن هل و أو او ما هذا هذه أن ان لا مع كل".split()),
}


def detect_lang(text: str) -> str:
    ar = len(re.findall(r"[؀-ۿ]", text))
    cy = len(re.findall(r"[Ѐ-ӿ]", text))
    la = len(re.findall(r"[A-Za-z]", text))
    best = max((ar, "ar"), (cy, "ru"), (la, "en"))
    return best[1] if best[0] else "en"


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).lower()
    t = _AR_DIACRITICS.sub("", t)
    t = t.replace("ـ", "")
    t = re.sub("[إأآا]", "ا", t)
    t = t.replace("ى", "ي").replace("ة", "ه")
    t = t.replace("ё", "е").replace("’", "'")
    return t


def tokens(text: str) -> list[str]:
    return [m.group(0) for m in _TOKEN.finditer(normalise(text))]


def content_tokens(text: str) -> list[str]:
    stop = STOP["en"] | STOP["ru"] | {normalise(w) for w in STOP["ar"]}
    return [t for t in tokens(text) if t not in stop and len(t) > 1]


_AR_PREFIXES = ("وال", "بال", "فال", "كال", "لل", "ال", "و", "ب", "ل")
_AR_SUFFIXES = ("ات", "ون", "ين", "ها")  # taa marbuta kept: مدرسة (school) != مدرس (teacher)


def stem(tok: str) -> str:
    """Very light, language-specific stemming used ONLY for concept/alias
    matching (not for BM25 over the English cards)."""
    if re.search(r"[\u0600-\u06FF]", tok):
        for p in _AR_PREFIXES:
            if tok.startswith(p) and len(tok) - len(p) >= 3:
                tok = tok[len(p):]
                break
        for sfx in _AR_SUFFIXES:
            if tok.endswith(sfx) and len(tok) - len(sfx) >= 3:
                tok = tok[: -len(sfx)]
                break
        return tok
    if re.search(r"[\u0400-\u04FF]", tok):
        return tok[:5] if len(tok) > 5 else tok
    return tok


def stemmed(text: str) -> list[str]:
    return [stem(t) for t in tokens(text)]
