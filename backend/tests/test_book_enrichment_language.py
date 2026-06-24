from app.services.book_enrichment import _pick_library_doc, _to_open_library_language


def test_to_open_library_language_maps_polish():
    assert _to_open_library_language("pl") == "pol"


def test_pick_library_doc_prefers_matching_language():
    docs = [
        {"title": "Solaris", "language": ["eng"]},
        {"title": "Solaris", "language": ["pol"]},
    ]
    picked = _pick_library_doc(docs, "pol")
    assert picked is docs[1]


def test_pick_library_doc_skips_english_when_polish_requested():
    docs = [{"title": "Solaris", "language": ["eng"]}]
    assert _pick_library_doc(docs, "pol") is None


def test_pick_library_doc_returns_first_when_no_language_filter():
    docs = [{"title": "Solaris", "language": ["eng"]}]
    assert _pick_library_doc(docs, None) is docs[0]
