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
