from wikitext_converter.coc_to_wiki import convert


def test_convert():
    assert convert("tests/data/heart sutra.docx") == "tests/data/heart sutra_wiki.txt"
