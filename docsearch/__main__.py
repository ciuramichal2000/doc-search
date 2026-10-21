"""python -m docsearch index ./docs index.json   |   python -m docsearch search index.json 'invoice "bank transfer" -draft'"""
import sys

from .core import Index


def main(argv=None) -> int:
    a = sys.argv[1:] if argv is None else argv
    if len(a) == 3 and a[0] == "index":
        idx = Index()
        n = idx.add_directory(a[1])
        idx.save(a[2])
        print("indexed %d documents, %d distinct words" % (n, len(idx.postings)))
        return 0
    if len(a) >= 3 and a[0] == "search":
        hits = Index.load(a[1]).search(" ".join(a[2:]))
        for h in hits:
            print("%-30s %7.3f  %s" % (h["id"], h["score"], h["snippet"]))
        print("%d result(s)" % len(hits))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
