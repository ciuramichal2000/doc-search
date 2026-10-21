# doc-search

A small full-text search engine written from scratch: an inverted index with word positions, **BM25** ranking (rare words count for more, long repetitive documents do not win), `"exact phrase"` queries, `-excluded` words, diacritic-insensitive matching (`zazolc` finds `zażółć`), result snippets around the match, update and delete of documents, and save/load as JSON.

```
python -m docsearch index ./docs index.json
python -m docsearch search index.json 'invoice "bank transfer" -draft'
python -m pytest
```

Pure Python standard library. Built with AI coding assistance; the tests check ranking, phrases, exclusion, Polish letters, snippets and persistence.
