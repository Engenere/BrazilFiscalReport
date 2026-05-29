import pytest

from brazilfiscalreport.xfpdf import xFPDF

# Caracteres tipográficos comuns em texto colado do Word/email que existem em
# cp1252 (WinAnsiEncoding) mas NÃO em latin-1, e portanto quebravam o pipeline
# de encoding das core fonts do fpdf2 com seu default ("latin-1").
# Regression guard para o bug reportado em issue #162.
CP1252_TYPOGRAPHIC_CHARS = [
    "–",  # en-dash –
    "—",  # em-dash —
    "‘",  # left single quote ‘
    "’",  # right single quote ’
    "“",  # left double quote “
    "”",  # right double quote ”
    "…",  # horizontal ellipsis …
    "•",  # bullet •
    " ",  # non-breaking space
    "€",  # euro sign €
    "™",  # trademark sign ™
]


@pytest.mark.parametrize("char", CP1252_TYPOGRAPHIC_CHARS)
def test_xfpdf_renders_cp1252_chars_with_core_font(char):
    pdf = xFPDF()
    pdf.add_page()
    pdf.set_font("Times", "", 12)
    pdf.cell(w=100, h=8, text=f"x{char}y")


def test_xfpdf_core_fonts_encoding_is_cp1252():
    assert xFPDF().core_fonts_encoding == "cp1252"
