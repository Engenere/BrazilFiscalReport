from fpdf import FPDF


class xFPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.core_fonts_encoding = "cp1252"

    def long_field(self, text="", limit=0, font_size=None, font_style=""):
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

    def wrap_text(self, text="", width=0):
        """
        Quebra o texto nas linhas que cabem em `width`, com a fonte corrente.

        Diferente de um split por espaços, delega ao fpdf2 e portanto também
        parte palavras que não cabem sozinhas na largura (código de barras,
        URL, etc.), em vez de deixá-las transbordar a coluna.
        """
        if not text or width <= 0:
            return []
        # `multi_cell` desconta `c_margin` de cada lado; aqui a largura já é a
        # útil, então zeramos a margem para não quebrar antes da hora.
        prev_c_margin = self.c_margin
        self.c_margin = 0
        try:
            return self.multi_cell(w=width, text=text, dry_run=True, output="LINES")
        finally:
            self.c_margin = prev_c_margin

    def space_left(self):
        """Altura livre entre o cursor e a margem inferior."""
        return self.h - self.b_margin - self.get_y()

    def ensure_space(self, height):
        """
        Abre uma página nova se `height` não couber no que resta da atual.

        Usar antes de blocos desenhados em coordenadas absolutas, que não
        sobrevivem à quebra automática de página do fpdf2.
        """
        if height > 0 and self.space_left() < height:
            self.add_page()
            return True
        return False

    def text_box(self, text, text_align, h_line, x, y, w, h, border=False):
        if border:
            self.rect(
                x=x,
                y=y,
                w=w,
                h=h,
            )
        lines = self.multi_cell(
            w=w,
            h=h_line,
            text=text,
            border=0,
            align="C",
            fill=False,
            split_only=False,
            dry_run=True,
            output=("LINES"),
        )
        total_text_height = len(lines) * h_line
        # Calculates the initial vertical position to center the text in the box
        start_y = y + (h - total_text_height) / 2
        self.set_xy(x=x, y=start_y)
        self.multi_cell(
            w=w, h=h_line, text=text, border=0, align=text_align, fill=False
        )
