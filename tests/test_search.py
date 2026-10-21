import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from docsearch import Index, fold, tokenize  # noqa: E402
from docsearch.__main__ import main  # noqa: E402


def build():
    i = Index()
    i.add("a", "The invoice was paid by bank transfer on Monday. The invoice number is 2024-001.")
    i.add("b", "Draft invoice for the customer. Invoice invoice invoice, waiting for approval and a very long list of other words to make this document much longer than the others.")
    i.add("c", "Meeting notes: transfer of the bank account to the new office.")
    i.add("d", "Zażółć gęślą jaźń: faktura za usługi w Łodzi")
    return i


def test_fold_keeps_length_and_removes_diacritics():
    s = "Zażółć gęślą jaźń Łódź"
    assert fold(s) == "zazolc gesla jazn lodz" and len(fold(s)) == len(s)


def test_tokenizer_drops_stop_words_and_keeps_offsets():
    assert tokenize("The cat and the Łódź") == [("cat", 4), ("lodz", 16)]


def test_ranking_prefers_focused_documents_over_long_repetitive_ones():
    hits = build().search("invoice")
    assert [h["id"] for h in hits][:2] == ["a", "b"] or [h["id"] for h in hits][:2] == ["b", "a"]
    assert {h["id"] for h in hits} == {"a", "b"}
    top = build().search("invoice bank transfer")
    assert top[0]["id"] == "a" and top[0]["score"] > top[1]["score"]


def test_rare_word_outweighs_common_word():
    i = Index()
    i.add("1", "report report report report")
    i.add("2", "report zebra")
    i.add("3", "report")
    assert i.search("report zebra")[0]["id"] == "2"


def test_phrase_must_appear_in_that_order_and_adjacent():
    i = build()
    assert [h["id"] for h in i.search('"bank transfer"')] == ["a"]       # c has both words, but in the other order
    # stop words are skipped, so "transfer of the bank" counts as the phrase "transfer bank"
    assert [h["id"] for h in i.search('"transfer bank"')] == ["c"]
    i.add("e", "transfer the money to the bank")                           # another word in between: not a phrase match
    assert [h["id"] for h in i.search('"transfer bank"')] == ["c"]


def test_minus_excludes_documents():
    ids = [h["id"] for h in build().search("invoice -draft")]
    assert ids == ["a"]


def test_search_is_diacritic_insensitive_both_ways():
    assert [h["id"] for h in build().search("zazolc")] == ["d"]
    assert [h["id"] for h in build().search("łodzi")] == ["d"]


def test_snippet_shows_the_neighbourhood_of_the_match():
    s = build().search("approval")[0]["snippet"]
    assert "approval" in s and s.startswith("...")


def test_update_and_remove_change_results():
    i = build()
    i.add("c", "Now this one mentions invoice too")
    assert "c" in [h["id"] for h in i.search("invoice")]
    i.remove("c")
    assert "c" not in [h["id"] for h in i.search("invoice")]
    assert i.search("nothingmatches") == [] and i.search("") == []


def test_save_load_round_trip_and_cli(tmp_path, capsys):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "x.txt").write_text("Faktura VAT za usługi", encoding="utf-8")
    (docs / "y.md").write_text("Umowa najmu lokalu", encoding="utf-8")
    (docs / "z.bin").write_bytes(b"\x00")
    idx = str(tmp_path / "i.json")
    assert main(["index", str(docs), idx]) == 0 and "indexed 2 documents" in capsys.readouterr().out
    assert [h["id"] for h in Index.load(idx).search("uslugi")] == ["x.txt"]
    assert main(["search", idx, "najmu"]) == 0 and "y.md" in capsys.readouterr().out
