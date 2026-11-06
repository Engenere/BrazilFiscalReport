# Copyright (C) 2026 Engenere - Antônio S. Pereira Neto <neto@engenere.one>

# DANFE Simplificado - Etiqueta (NT 2020.004 v1.10; MOC 7.0 Anexo II, item
# 3.12). The norm sets no layout, only the minimum fields: paper at least
# 55 mm wide, fonts of 6 pt or more with bold uppercase field titles, and the
# access key with its barcode at the top right corner.

import warnings
import xml.etree.ElementTree as ET
from io import BytesIO
from xml.etree.ElementTree import Element

from barcode.codex import Code128
from barcode.writer import SVGWriter

from ..utils import (
    chunks,
    format_cep,
    format_cpf_cnpj,
    format_number,
    get_date_utc,
    get_tag_text,
)
from ..xfpdf import xFPDF
from .config import DanfeEtiquetaConfig
from .danfe_conf import URL

MIN_PAPER_WIDTH = 55
# MOC 7.0 Anexo II, chapter 2: the Code 128C of the 44-digit access key has 297
# modules, quiet zones of 10 modules included, and is at least 6 cm wide and
# 0.8 cm high on non-impact printers. A key with letters (alphanumeric CNPJ)
# needs more modules.
BARCODE_QUIET_ZONE_MODULES = 10
MIN_BARCODE_WIDTH = 60
BARCODE_HEIGHT = 10
# 0.25 mm is 2 dots of the 203 dpi thermal printers used for labels; narrower
# modules round to uneven bars there and the barcode stops being read.
BARCODE_MODULE_WIDTH = 0.25
TITLE_LINES = [("DANFE", 10), ("SIMPLIFICADO -", 7), ("ETIQUETA", 7)]
MIN_FONT_SIZE = 6
# Below this usable width the fields of a row are stacked, one per row.
NARROW_WIDTH = 70

LABEL_SIZE = 6
VALUE_SIZE = 8
SECTION_SIZE = 7
ITEM_SIZE = 7
PADDING = 0.8


def extract_text(node: Element | None, tag: str) -> str:
    return get_tag_text(node, URL, tag)


def line_height(font_size):
    return font_size * 0.3528 * 1.2


def format_quantity(value):
    """Quantity with up to 4 decimals and no trailing zeros, e.g. 1 or 2,5."""
    formatted = format_number(value, precision=4)
    return formatted.rstrip("0").rstrip(",") if "," in formatted else formatted


class DanfeEtiqueta(xFPDF):
    def __init__(self, xml, config: DanfeEtiquetaConfig = None):
        config = config if config is not None else DanfeEtiquetaConfig()
        if config.paper_width < MIN_PAPER_WIDTH:
            raise ValueError(
                f"DANFE Simplificado - Etiqueta requires paper at least "
                f"{MIN_PAPER_WIDTH} mm wide (NT 2020.004)."
            )
        super().__init__(unit="mm", format=(config.paper_width, config.paper_height))
        self.config = config
        self.set_margins(
            left=config.margins.left,
            top=config.margins.top,
            right=config.margins.right,
        )
        self.set_auto_page_break(auto=False, margin=config.margins.bottom)
        self.c_margin = 0
        self.default_font = config.font_type.value
        self.set_title("DANFE Simplificado - Etiqueta")

        root = ET.fromstring(xml)
        self.inf_nfe = root.find(f"{URL}infNFe")
        self.prot_nfe = root.find(f"{URL}protNFe")
        self.ide = root.find(f"{URL}ide")
        self.emit = root.find(f"{URL}emit")
        self.dest = root.find(f"{URL}dest")
        self.entrega = root.find(f"{URL}entrega")
        self.total = root.find(f"{URL}ICMSTot")
        self.det = root.findall(f"{URL}det")
        self.key_nfe = self.inf_nfe.attrib.get("Id")[3:]
        self.tp_emis = extract_text(self.ide, "tpEmis")

        self.add_page()
        self._draw_watermark()
        self._draw_header()
        self._draw_contingency()
        self._draw_logo()
        self._draw_emitter()
        self._draw_recipient()
        if config.display_total:
            self._draw_total()
        if config.display_items:
            self._draw_items()

    # Building blocks

    def _wrap(self, text, width, size, style=""):
        self.set_font(self.default_font, style, size)
        return self.wrap_text(text, width) or [""]

    def _draw_lines(self, lines, x, y, w, size, style="", align="L"):
        self.set_font(self.default_font, style, size)
        for line in lines:
            self.set_xy(x, y)
            self.cell(w, line_height(size), line, align=align)
            y += line_height(size)
        return y

    def _draw_section(self, title):
        self.set_font(self.default_font, "B", SECTION_SIZE)
        y = self.get_y() + 1
        self.set_xy(self.l_margin, y)
        self.cell(self.epw, line_height(SECTION_SIZE), title)
        self.set_xy(self.l_margin, y + line_height(SECTION_SIZE))

    def _draw_row(self, cells):
        """
        Draw a row of boxed fields across the page. Each cell is
        (title, value, weight) or (title, value, weight, value_style); the
        value wraps and the row takes the height of its tallest cell. On
        narrow paper each field gets a row of its own.
        """
        if len(cells) > 1 and self.epw < NARROW_WIDTH:
            for cell in cells:
                self._draw_row([cell])
            return
        total_weight = sum(cell[2] for cell in cells)
        prepared = []
        height = 0
        for title, value, weight, *style in cells:
            w = self.epw * weight / total_weight
            inner_w = w - 2 * PADDING
            style = style[0] if style else ""
            title_lines = self._wrap(title, inner_w, LABEL_SIZE, "B")
            lines = self._wrap(value, inner_w, VALUE_SIZE, style)
            height = max(
                height,
                2 * PADDING
                + len(title_lines) * line_height(LABEL_SIZE)
                + len(lines) * line_height(VALUE_SIZE),
            )
            prepared.append((title_lines, lines, style, w))

        x, y = self.l_margin, self.get_y()
        for title_lines, lines, style, w in prepared:
            self.rect(x, y, w, height)
            inner_w = w - 2 * PADDING
            value_y = self._draw_lines(
                title_lines, x + PADDING, y + PADDING, inner_w, LABEL_SIZE, "B"
            )
            self._draw_lines(lines, x + PADDING, value_y, inner_w, VALUE_SIZE, style)
            x += w
        self.set_xy(self.l_margin, y + height)

    # Header: title, barcode, access key, protocol and identification

    def _draw_header(self):
        modules = len(Code128(self.key_nfe).build()[0]) + 2 * BARCODE_QUIET_ZONE_MODULES
        module = min(BARCODE_MODULE_WIDTH, self.epw / modules)
        barcode_w = modules * module
        title_w = self.epw - barcode_w
        title_lines = self._fit_lines(TITLE_LINES, title_w - 2 * PADDING)
        title_beside = title_lines is not None

        # The barcode goes in the top right corner, with the title beside it
        # when there is room (MOC 7.0 Anexo II, item 3.12.2).
        y = self.get_y()
        height = BARCODE_HEIGHT + 2 * PADDING
        if title_beside:
            self.rect(self.l_margin, y, title_w, height)
            content_h = sum(line_height(size) for _, size in title_lines)
            line_y = y + (height - content_h) / 2
            for text, size in title_lines:
                line_y = self._draw_lines(
                    [text],
                    self.l_margin + PADDING,
                    line_y,
                    title_w - 2 * PADDING,
                    size,
                    "B",
                    "C",
                )
        self.rect(self.l_margin + title_w, y, barcode_w, height)
        self._draw_barcode(self.l_margin + title_w, y + PADDING, barcode_w, module)
        self.set_xy(self.l_margin, y + height)
        if not title_beside:
            lines = self._wrap(
                "DANFE SIMPLIFICADO - ETIQUETA", self.epw - 2 * PADDING, 9, "B"
            )
            height = 2 * PADDING + len(lines) * line_height(9)
            y = self.get_y()
            self.rect(self.l_margin, y, self.epw, height)
            self._draw_lines(
                lines,
                self.l_margin + PADDING,
                y + PADDING,
                self.epw - 2 * PADDING,
                9,
                "B",
                "C",
            )
            self.set_xy(self.l_margin, y + height)

        self._draw_row([("CHAVE DE ACESSO", " ".join(chunks(self.key_nfe, 4)), 1, "B")])
        self._draw_row([self._protocol()])

        nr_nota = f"{int(extract_text(self.ide, 'nNF') or 0):011,}".replace(",", ".")
        dt_emi, _ = get_date_utc(extract_text(self.ide, "dhEmi"))
        tp_nf = extract_text(self.ide, "tpNF")
        operation = {"0": "0 - ENTRADA", "1": "1 - SAÍDA"}.get(tp_nf, tp_nf)
        self._draw_row(
            [
                ("OPERAÇÃO", operation, 3),
                ("NÚMERO", nr_nota, 3.5, "B"),
                ("SÉRIE", extract_text(self.ide, "serie"), 1.5),
                ("EMISSÃO", dt_emi, 3),
            ]
        )

    def _fit_lines(self, lines, width):
        """
        Each (text, size) in bold at its size, shrunk down to 6 pt to fit
        `width`; None when some text does not fit even at 6 pt.
        """
        fitted = []
        for text, size in lines:
            while True:
                self.set_font(self.default_font, "B", size)
                if self.get_string_width(text) <= width:
                    fitted.append((text, size))
                    break
                if size <= MIN_FONT_SIZE:
                    return None
                size = max(size - 0.5, MIN_FONT_SIZE)
        return fitted

    def _protocol(self):
        """Title, value and weight of the authorization protocol field."""
        if self.prot_nfe is not None:
            n_prot = extract_text(self.prot_nfe, "nProt")
            dt, hr = get_date_utc(extract_text(self.prot_nfe, "dhRecbto"))
            return "PROTOCOLO DE AUTORIZAÇÃO DE USO", f"{n_prot} - {dt} {hr}", 1
        if self.tp_emis == "4":
            return "PROTOCOLO DE AUTORIZAÇÃO DO EPEC", self.config.epec_protocol, 1
        return "PROTOCOLO DE AUTORIZAÇÃO DE USO", "", 1

    def _draw_barcode(self, x, y, width, module):
        if width < MIN_BARCODE_WIDTH:
            warnings.warn(
                f"The barcode of the access key is {width:.1f} mm wide, below "
                f"the {MIN_BARCODE_WIDTH} mm of the MOC 7.0 Anexo II; use wider "
                "paper.",
                UserWarning,
                stacklevel=4,
            )
        svg = BytesIO()
        Code128(self.key_nfe, writer=SVGWriter()).write(
            svg,
            options={
                "write_text": False,
                "module_width": module,
                "quiet_zone": BARCODE_QUIET_ZONE_MODULES * module,
            },
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            self.image(svg, x=x, y=y, w=width, h=BARCODE_HEIGHT)

    # Situation of the NF-e

    def _draw_contingency(self):
        if self.tp_emis in ("", "1"):
            return
        title = "DANFE EM CONTINGÊNCIA"
        if self.tp_emis == "4":
            title += " - EPEC"
        dt, hr = get_date_utc(extract_text(self.ide, "dhCont"))
        # Ajuste SINIEF 07/05, cláusula décima primeira, § 11: start date and
        # reason of the contingency.
        detail = f"INÍCIO: {dt} {hr}  MOTIVO: {extract_text(self.ide, 'xJust')}"
        self._draw_row([(title, detail, 1)])

    def _draw_watermark(self):
        is_production = extract_text(self.ide, "tpAmb") == "1"
        is_authorized = self.prot_nfe is not None or (
            self.tp_emis == "4" and bool(self.config.epec_protocol)
        )
        if self.config.watermark_cancelled:
            text = "CANCELADA" if is_production else "CANCELADA - SEM VALOR FISCAL"
        elif not is_production or not is_authorized:
            text = "SEM VALOR FISCAL"
        else:
            return
        font_size = 30 if len(text) < 20 else 20
        self.set_font(self.default_font, "B", font_size)
        width = self.get_string_width(text)
        x = (self.w - width) / 2
        y = self.h / 2
        with (
            self.local_context(text_color=(220, 150, 150)),
            self.rotation(55, x + width / 2, y),
        ):
            self.text(x, y, text)

    def _draw_logo(self):
        """Brand logo centered between the header and the issuer data, as in
        the marketplace shipping labels. The NT sets only the minimum fields,
        so the logo is an optional extra."""
        if not self.config.logo:
            return
        y = self.get_y() + 1
        self.image(
            self.config.logo,
            x=self.l_margin,
            y=y,
            w=self.epw,
            h=self.config.logo_height,
            keep_aspect_ratio=True,
        )
        self.set_xy(self.l_margin, y + self.config.logo_height)

    # Emitter, recipient, total and items

    @staticmethod
    def _id_field(node):
        cnpj = extract_text(node, "CNPJ")
        if cnpj:
            return "CNPJ", format_cpf_cnpj(cnpj)
        cpf = extract_text(node, "CPF")
        if cpf:
            return "CPF", format_cpf_cnpj(cpf)
        return "ID ESTRANGEIRO", extract_text(node, "idEstrangeiro")

    def _draw_emitter(self):
        self._draw_section("DADOS DO EMITENTE")
        self._draw_row([("NOME/RAZÃO SOCIAL", extract_text(self.emit, "xNome"), 1)])
        id_title, id_value = self._id_field(self.emit)
        self._draw_row(
            [
                (id_title, id_value, 4.5),
                ("INSCRIÇÃO ESTADUAL", extract_text(self.emit, "IE"), 4),
                ("UF", extract_text(self.emit, "UF"), 1.5),
            ]
        )

    def _draw_recipient(self):
        self._draw_section("DADOS DO DESTINATÁRIO/REMETENTE")
        self._draw_row([("NOME/RAZÃO SOCIAL", extract_text(self.dest, "xNome"), 1)])
        id_title, id_value = self._id_field(self.dest)
        self._draw_row(
            [
                (id_title, id_value, 4.5),
                ("INSCRIÇÃO ESTADUAL", extract_text(self.dest, "IE"), 4),
                ("UF", extract_text(self.dest, "UF"), 1.5),
            ]
        )
        if self.config.display_delivery_address:
            title, address = self._delivery_address()
            self._draw_row([(title, address, 1)])

    def _delivery_address(self):
        if self.entrega is not None:
            node, title = self.entrega, "ENDEREÇO DE ENTREGA"
        else:
            node, title = self.dest, "ENDEREÇO"
        parts = []
        receiver = extract_text(node, "xNome") if node is self.entrega else ""
        if receiver and receiver != extract_text(self.dest, "xNome"):
            parts.append(receiver)
        street = ", ".join(
            filter(None, [extract_text(node, "xLgr"), extract_text(node, "nro")])
        )
        city = "/".join(
            filter(None, [extract_text(node, "xMun"), extract_text(node, "UF")])
        )
        cep = extract_text(node, "CEP")
        parts += [
            street,
            extract_text(node, "xCpl"),
            extract_text(node, "xBairro"),
            city,
            f"CEP {format_cep(cep)}" if cep else "",
        ]
        return title, " - ".join(filter(None, parts))

    def _draw_total(self):
        v_nf = format_number(extract_text(self.total, "vNF"), precision=2)
        self._draw_row([("VALOR TOTAL DA NOTA FISCAL", f"R$ {v_nf}", 1, "B")])

    def _draw_items(self):
        self._draw_section("DADOS DOS PRODUTOS / SERVIÇOS")
        widths = [w * self.epw for w in (0.22, 0.58, 0.20)]
        titles = ["CÓDIGO", "DESCRIÇÃO", "QTD."]
        header_h = 2 * PADDING + line_height(LABEL_SIZE)
        x, y = self.l_margin, self.get_y()
        for title, w in zip(titles, widths, strict=True):
            self.rect(x, y, w, header_h)
            self._draw_lines(
                [title], x + PADDING, y + PADDING, w - 2 * PADDING, LABEL_SIZE, "B"
            )
            x += w
        y += header_h

        rows = []
        for det in self.det:
            prod = det.find(f"{URL}prod")
            q_com = format_quantity(extract_text(prod, "qCom"))
            texts = [
                extract_text(prod, "cProd"),
                extract_text(prod, "xProd"),
                f"{q_com} {extract_text(prod, 'uCom')}",
            ]
            cells = [
                self._wrap(text, w - 2 * PADDING, ITEM_SIZE)
                for text, w in zip(texts, widths, strict=True)
            ]
            height = 2 * PADDING + max(len(c) for c in cells) * line_height(ITEM_SIZE)
            rows.append((cells, height))

        bottom = self.h - self.b_margin
        more_h = 2 * PADDING + line_height(ITEM_SIZE)
        for index, (cells, height) in enumerate(rows):
            remaining = len(rows) - index
            # Keep room for the "e mais N itens" line unless this is the last row.
            needed = height if remaining == 1 else height + more_h
            if y + needed > bottom:
                self.rect(self.l_margin, y, self.epw, more_h)
                self._draw_lines(
                    [f"E MAIS {remaining} ITEM(NS) NÃO LISTADO(S)"],
                    self.l_margin + PADDING,
                    y + PADDING,
                    self.epw - 2 * PADDING,
                    ITEM_SIZE,
                    "B",
                )
                y += more_h
                break
            x = self.l_margin
            for lines, w, align in zip(cells, widths, ("L", "L", "R"), strict=True):
                self.rect(x, y, w, height)
                self._draw_lines(
                    lines,
                    x + PADDING,
                    y + PADDING,
                    w - 2 * PADDING,
                    ITEM_SIZE,
                    "",
                    align,
                )
                x += w
            y += height
        self.set_xy(self.l_margin, y)
