import warnings
from io import BytesIO

from barcode.codex import Code128
from barcode.writer import SVGWriter

from brazilfiscalreport.pdf_element import Element


class DanfeCode(Element):
    def __init__(self, key_nfe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key_nfe = key_nfe

    def render(self):
        super().render()
        # Set the position and size of the image in the PDF
        x = self.x + 0.5
        y = self.y + 0.5
        w = self.w
        h = 12.5
        # Generate a Code128 Barcode as SVG:
        svg_img_bytes = BytesIO()
        Code128(self.key_nfe, writer=SVGWriter()).write(svg_img_bytes)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            self.pdf.image(svg_img_bytes, x=x, y=y, w=w, h=h)
