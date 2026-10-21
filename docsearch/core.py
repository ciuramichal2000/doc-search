"""A small full-text search engine: inverted index with positions, BM25 ranking, "phrase" queries and -excluded words.
Diacritic-insensitive, so 'zażółć' is found by 'zazolc'."""
import json
import math
import os
import re
import unicodedata
from collections import Counter
from typing import Dict, List, Tuple

STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "is", "it", "i", "w", "z", "na", "do", "oraz", "i", "oraz", "sie", "nie", "to"}
K1, B = 1.5, 0.75


def fold(text: str) -> str:
    """Lower case and strip diacritics WITHOUT changing the text length, so offsets stay valid for snippets."""
    out = []
    for c in text:
        if c in "łŁ":
            out.append("l")
        else:
            d = unicodedata.normalize("NFKD", c)
            out.append(d[0].lower() if d else c.lower())
    return "".join(out)


def tokenize(text: str) -> List[Tuple[str, int]]:
    """(token, start offset in the text); stop words dropped but positions keep counting real words."""
    return [(m.group(), m.start()) for m in re.finditer(r"[a-z0-9]+", fold(text)) if m.group() not in STOP]


class Index:
    def __init__(self):
        self.docs: Dict[str, dict] = {}
        self.postings: Dict[str, Dict[str, List[int]]] = {}

    # ---- writing
    def add(self, doc_id: str, text: str) -> None:
        if doc_id in self.docs:
            self.remove(doc_id)
        toks = tokenize(text)
        self.docs[doc_id] = {"text": text, "len": len(toks)}
        for pos, (tok, _) in enumerate(toks):
            self.postings.setdefault(tok, {}).setdefault(doc_id, []).append(pos)

    def remove(self, doc_id: str) -> None:
        self.docs.pop(doc_id, None)
        for tok in list(self.postings):
            self.postings[tok].pop(doc_id, None)
            if not self.postings[tok]:
                del self.postings[tok]

    # ---- reading
    def _bm25(self, term: str, doc_id: str, avg: float) -> float:
        tf = len(self.postings.get(term, {}).get(doc_id, ()))
        if not tf:
            return 0.0
        n, df = len(self.docs), len(self.postings[term])
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        return idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * self.docs[doc_id]["len"] / avg))

    def _has_phrase(self, doc_id: str, words: List[str]) -> bool:
        first = self.postings.get(words[0], {}).get(doc_id, [])
        return any(all(p + i in set(self.postings.get(w, {}).get(doc_id, ())) for i, w in enumerate(words)) for p in first)

    def search(self, query: str, limit: int = 10) -> List[dict]:
        phrases = [[t for t, _ in tokenize(p)] for p in re.findall(r'"([^"]+)"', query)]
        rest = re.sub(r'"[^"]+"', " ", query)
        excluded = {t for w in re.findall(r"(?<!\S)-(\S+)", rest) for t, _ in tokenize(w)}
        terms = [t for w in re.findall(r"(?<!\S)(?!-)\S+", rest) for t, _ in tokenize(w)]
        phrases = [p for p in phrases if p]
        wanted = list(dict.fromkeys(terms + [w for p in phrases for w in p]))
        if not wanted or not self.docs:
            return []
        avg = sum(d["len"] for d in self.docs.values()) / len(self.docs) or 1.0
        candidates = {d for t in wanted for d in self.postings.get(t, {})}
        results = []
        for doc_id in candidates:
            if any(doc_id in self.postings.get(t, {}) for t in excluded):
                continue
            if not all(self._has_phrase(doc_id, p) for p in phrases):
                continue
            score = sum(self._bm25(t, doc_id, avg) for t in wanted)
            results.append({"id": doc_id, "score": round(score, 4), "snippet": self._snippet(doc_id, wanted)})
        results.sort(key=lambda r: (-r["score"], r["id"]))
        return results[:limit]

    def _snippet(self, doc_id: str, terms: List[str], width: int = 60) -> str:
        text = self.docs[doc_id]["text"]
        hit = next((off for tok, off in tokenize(text) if tok in terms), 0)
        start = max(0, hit - width // 2)
        piece = re.sub(r"\s+", " ", text[start:start + width * 2]).strip()
        return ("..." if start else "") + piece + ("..." if start + width * 2 < len(text) else "")

    # ---- persistence
    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"docs": self.docs, "postings": self.postings}, f, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "Index":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        idx = cls()
        idx.docs, idx.postings = data["docs"], data["postings"]
        return idx

    def add_directory(self, root: str, extensions=(".txt", ".md")) -> int:
        n = 0
        for folder, _, files in os.walk(root):
            for name in sorted(files):
                if name.lower().endswith(extensions):
                    path = os.path.join(folder, name)
                    with open(path, encoding="utf-8", errors="replace") as f:
                        self.add(os.path.relpath(path, root).replace(os.sep, "/"), f.read())
                    n += 1
        return n
