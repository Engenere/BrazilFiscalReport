"""
xFPDF — classe base do DANFSe (port fiel do xfpdf.py original + extras).

Mantém a API original:
    - core_fonts_encoding = "cp1252"
    - long_field(text, limit, font_size, font_style)
    - text_box(text, text_align, h_line, x, y, w, h, border)

E adiciona utilitários alinhados à NT 008 usados pela camada de renderização
refatorada:
    - shade_rect()    -> sombreamento cinza 5%
    - divider()       -> linha divisória de bloco (0,5pt)
    - page_border()   -> borda da página (1pt)
"""

from __future__ import annotations

from fpdf import FPDF

from .fonts import COLOR_SHADING, LINE_BORDER_MM, LINE_DIVIDER_MM


class xFPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.core_fonts_encoding = "cp1252"
        # Definido pela subclasse Danfse; fallback seguro.
        self.default_font = getattr(self, "default_font", "helvetica")

    # -- API original -------------------------------------------------------

    def long_field(self, text="", limit=0, font_size=None, font_style=""):
        """Trunca ``text`` para caber em ``limit`` (mm), acrescentando '...'.

        Port fiel do original: tenta cortar por palavras; se não couber nem
        uma palavra, corta caractere a caractere. Restaura a fonte ao final.
        """
        if not text or limit <= 0:
            return ""

        prev_font = (self.font_family, self.font_style, self.font_size_pt)
        try:
            if font_size:
                self.set_font(self.default_font, font_style, font_size)

            safe_limit = limit - 2

            if self.get_string_width(text) <= safe_limit:
                return text

            words = text.split()
            while words and self.get_string_width(" ".join(words) + "...") > safe_limit:
                words.pop()

            if words:
                return " ".join(words) + "..."

            while text and self.get_string_width(text + "...") > safe_limit:
                text = text[:-1]
            return text + "..." if text else ""
        finally:
            self.set_font(*prev_font)

    def text_box(self, text, text_align, h_line, x, y, w, h, border=False):
        """Desenha texto centralizado verticalmente numa caixa (port fiel)."""
        if border:
            self.rect(x=x, y=y, w=w, h=h)
        lines = self.multi_cell(
            w=w,
            h=h_line,
            text=text,
            border=0,
            align="C",
            fill=False,
            dry_run=True,
            output="LINES",
        )
        total_text_height = len(lines) * h_line
        start_y = y + (h - total_text_height) / 2
        self.set_xy(x=x, y=start_y)
        self.multi_cell(
            w=w, h=h_line, text=text, border=0, align=text_align, fill=False
        )

    # -- extras NT 008 ------------------------------------------------------

    def shade_rect(self, x, y, w, h):
        """Preenche um retângulo com o cinza 5% da NT 008."""
        self.set_fill_color(*COLOR_SHADING)
        self.rect(x=x, y=y, w=w, h=h, style="F")

    def divider(self, x1, y, x2):
        """Linha divisória de bloco (0,5pt)."""
        self.set_line_width(LINE_DIVIDER_MM)
        self.set_dash_pattern(dash=0, gap=0)
        self.line(x1=x1, y1=y, x2=x2, y2=y)

    def page_border(self, x, y, w, h):
        """Borda externa da página (1pt)."""
        self.set_line_width(LINE_BORDER_MM)
        self.set_dash_pattern(dash=0, gap=0)
        self.rect(x=x, y=y, w=w, h=h)
        self.set_line_width(LINE_DIVIDER_MM)
