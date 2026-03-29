import re
import warnings
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

from ..dacte.generate_qrcode import draw_qr_code
from ..utils import (
    format_cep,
    format_cpf_cnpj,
    format_number,
    format_phone,
    get_date_utc,
    get_tag_text,
)
from ..xfpdf import xFPDF
from .config import DanfceConfig

URL = ".//{http://www.portalfiscal.inf.br/nfe}"


def extract_text(node: Element | None, tag: str) -> str:
    if node is None:
        return ""
    return get_tag_text(node, URL, tag)


class Danfce(xFPDF):
    def __init__(self, xml: str, config: DanfceConfig | None = None):
        super().__init__(unit="mm", format=(80, 300))

        self.config = config if config is not None else DanfceConfig()
        self.set_margins(
            left=self.config.margins.left,
            top=self.config.margins.top,
            right=self.config.margins.right,
        )
        self.set_auto_page_break(auto=True, margin=self.config.margins.bottom)
        self.set_title("DANFCe")

        self.logo_image = self.config.logo
        self.default_font = self.config.font_type.value
        self.price_precision = self.config.decimal_config.price_precision
        self.quantity_precision = self.config.decimal_config.quantity_precision

        root = ET.fromstring(xml)
        self.inf_nfe = root.find(f"{URL}infNFe")
        self.prot_nfe = root.find(f"{URL}protNFe")
        self.inf_nfe_supl = root.find(f"{URL}infNFeSupl")

        self.emit = root.find(f"{URL}emit")
        self.ide = root.find(f"{URL}ide")
        self.dest = root.find(f"{URL}dest")
        self.total = root.find(f"{URL}total")
        self.pag = root.find(f"{URL}pag")
        self.det = root.findall(f"{URL}det")
        self.inf_adic = root.find(f"{URL}infAdic")

        self.key_nfe = (
            self.inf_nfe.attrib.get("Id")[3:] if self.inf_nfe is not None else ""
        )

        self.add_page()
        self._draw_header()
        self._draw_items()
        self._draw_totals()
        # self._draw_payments()
        # self._draw_footer()

    def _draw_header(self) -> None:
        emit_name = extract_text(self.emit, "xNome")
        cep = format_cep(extract_text(self.emit, "CEP"))
        fone = format_phone(extract_text(self.emit, "fone"))
        cnpj_cpf = format_cpf_cnpj(
            extract_text(self.emit, "CNPJ") or extract_text(self.emit, "CPF")
        )

        address_lines = [
            f"{extract_text(self.emit, 'xLgr')}, {extract_text(self.emit, 'nro')}",
            extract_text(self.emit, "xBairro"),
            (
                f"{extract_text(self.emit, 'xMun')} - "
                f"{extract_text(self.emit, 'UF')} {cep}"
            ),
            f"Fone: {fone}",
        ]
        address = "\n".join(line for line in address_lines if line.strip())

        if self.logo_image:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                self.image(
                    self.logo_image,
                    x=self.l_margin,
                    y=self.t_margin,
                    w=15,
                    h=15,
                    keep_aspect_ratio=True,
                )
            self.set_y(self.t_margin + 16)

        self.set_font(self.default_font, "B", 10)
        for line in self._wrap_text(emit_name, self._content_width()):
            self.cell(
                w=0,
                h=4,
                text=line,
                border=0,
                new_x="LMARGIN",
                new_y="NEXT",
                align="C",
            )

        self.set_font(self.default_font, "", 8)
        for line in address.split("\n"):
            if line.strip():
                for wrapped in self._wrap_text(line, self._content_width()):
                    self.cell(
                        w=0,
                        h=3,
                        text=wrapped,
                        border=0,
                        new_x="LMARGIN",
                        new_y="NEXT",
                        align="C",
                    )

        for info_line in [f"CNPJ/CPF: {cnpj_cpf}"]:
            for wrapped in self._wrap_text(info_line, self._content_width()):
                self.cell(
                    w=0,
                    h=3,
                    text=wrapped,
                    border=0,
                    new_x="LMARGIN",
                    new_y="NEXT",
                    align="C",
                )
        ie = extract_text(self.emit, "IE")
        if ie:
            for wrapped in self._wrap_text(f"IE: {ie}", self._content_width()):
                self.cell(
                    w=0,
                    h=3,
                    text=wrapped,
                    border=0,
                    new_x="LMARGIN",
                    new_y="NEXT",
                    align="C",
                )

        self.ln(1)
        self.set_font(self.default_font, "B", 8)
        title = (
            "DANFE NFC-e - Documento Auxiliar da Nota Fiscal de Consumidor Eletrônica"
        )
        for line in self._wrap_text(title, self._content_width()):
            self.cell(
                w=0,
                h=4,
                text=line,
                border=0,
                new_x="LMARGIN",
                new_y="NEXT",
                align="C",
            )

        n_nf = extract_text(self.ide, "nNF")
        serie = extract_text(self.ide, "serie")
        dt_emi, hr_emi = get_date_utc(extract_text(self.ide, "dhEmi"))
        self.set_font(self.default_font, "", 7)
        header_line = f"NFC-e Nº {n_nf}   Série {serie}   Emissão: {dt_emi} {hr_emi}"
        for line in self._wrap_text(header_line, self._content_width()):
            self.cell(
                w=0,
                h=3,
                text=line,
                border=0,
                new_x="LMARGIN",
                new_y="NEXT",
                align="C",
            )

        tp_amb = extract_text(self.ide, "tpAmb")
        if tp_amb != "1":
            self.set_font(self.default_font, "B", 7)
            msg = "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
            for line in self._wrap_text(msg, self._content_width()):
                self.cell(
                    w=0,
                    h=3,
                    text=line,
                    border=0,
                    new_x="LMARGIN",
                    new_y="NEXT",
                    align="C",
                )

        self.ln(1)
        self._draw_line()

        dest_name = extract_text(self.dest, "xNome")
        if dest_name:
            self.set_font(self.default_font, "", 7)
            dest_id = format_cpf_cnpj(
                extract_text(self.dest, "CPF") or extract_text(self.dest, "CNPJ")
            )
            self.multi_cell(
                w=0,
                h=3,
                text=f"Consumidor: {dest_name}  {dest_id}",
                border=0,
                align="L",
            )
            self.ln(1)
            self._draw_line()

    def _draw_items(self) -> None:
        self.set_font(self.default_font, "B", 7)
        self.cell(
            w=0,
            h=4,
            text="ITENS DA NFC-e",
            border=0,
            new_x="LMARGIN",
            new_y="NEXT",
            align="L",
        )
        self._draw_line()

        for _det in self.det:
            prod = _det.find(f"{URL}prod")
            if prod is None:
                continue

            code = extract_text(prod, "cProd")
            desc = extract_text(prod, "xProd")
            q_com = format_number(extract_text(prod, "qCom"), self.quantity_precision)
            u_com = extract_text(prod, "uCom")
            v_un = format_number(extract_text(prod, "vUnCom"), self.price_precision)
            v_tot = format_number(extract_text(prod, "vProd"), self.price_precision)

            self.set_font(self.default_font, "B", 7)
            for line in self._wrap_text(desc, self._content_width()):
                self.cell(
                    w=0,
                    h=3,
                    text=line,
                    border=0,
                    new_x="LMARGIN",
                    new_y="NEXT",
                    align="L",
                )

            self.set_font(self.default_font, "", 7)
            info = (
                f"Cód: {code}  "
                f"Qtd: {q_com} {u_com}  "
                f"V.Un: {v_un}  "
                f"V.Tot: {v_tot}"
            )
            for line in self._wrap_text(info, self._content_width()):
                self.cell(
                    w=0,
                    h=3,
                    text=line,
                    border=0,
                    new_x="LMARGIN",
                    new_y="NEXT",
                    align="L",
                )

            self.ln(1)
            self._draw_line()

    def _draw_totals(self) -> None:
        if self.total is None:
            return

        v_prod = format_number(extract_text(self.total, "vProd"), precision=2)
        v_desc = format_number(extract_text(self.total, "vDesc"), precision=2)
        v_outro = format_number(extract_text(self.total, "vOutro"), precision=2)
        v_nf = format_number(extract_text(self.total, "vNF"), precision=2)

        self.set_font(self.default_font, "B", 8)
        self.multi_cell(
            w=self._content_width(),
            h=4,
            text=f"TOTAL R$ {v_nf}",
            border=0,
            align="R",
        )

        self.set_font(self.default_font, "", 7)
        self.multi_cell(
            w=self._content_width(),
            h=3,
            text=(
                f"Sub-total: R$ {v_prod}   "
                f"Descontos: R$ {v_desc}   "
                f"Outros acréscimos: R$ {v_outro}"
            ),
            border=0,
            align="R",
        )

        self.ln(1)
        self._draw_line()

    def _draw_payments(self) -> None:
        if self.pag is None:
            return

        self._ensure_space(30)

        self.set_font(self.default_font, "B", 7)
        self.multi_cell(
            w=self._content_width(), h=4, text="Pagamentos", border=0, align="L"
        )
        self.set_font(self.default_font, "", 7)

        det_pags = self.pag.findall(f"{URL}detPag")
        for det in det_pags:
            t_pag = extract_text(det, "tPag")
            v_pag = format_number(extract_text(det, "vPag"), precision=2)
            self.multi_cell(
                w=self._content_width(),
                h=3,
                text=f"Forma {t_pag}: R$ {v_pag}",
                border=0,
                align="L",
            )

        v_troco = extract_text(self.pag, "vTroco")
        if v_troco:
            v_troco = format_number(v_troco, precision=2)
            self.multi_cell(
                w=self._content_width(),
                h=3,
                text=f"Troco: R$ {v_troco}",
                border=0,
                align="L",
            )

        self.ln(1)
        self._draw_line()

    def _draw_footer(self) -> None:
        self._ensure_space(60)

        self.ln(1)
        self._draw_line()
        y_start = self.get_y() + 1

        box_size = 24  # mm
        x_qr = self.l_margin
        y_qr = y_start + 4

        qr_code = extract_text(self.inf_nfe_supl, "qrCode")
        if qr_code:
            x_offset = x_qr
            y_offset = y_qr - self.t_margin
            draw_qr_code(
                self, qr_code, 0, x_offset, y_offset, box_size=box_size, border=2
            )

        text_x = x_qr + box_size + 3
        text_w = self._content_width() - (box_size + 3)
        self.set_xy(text_x, y_start)

        url_chave = extract_text(self.inf_nfe_supl, "urlChave")
        self.set_font(self.default_font, "", 6)
        header = "Consulte pela Chave de Acesso em"
        self.multi_cell(text_w, 3, header, border=0, align="L")
        if url_chave:
            self.multi_cell(text_w, 3, url_chave, border=0, align="L")

        dest_name = extract_text(self.dest, "xNome")
        dest_id = format_cpf_cnpj(
            extract_text(self.dest, "CPF") or extract_text(self.dest, "CNPJ")
        )
        if dest_name or dest_id:
            consumidor_line = f"CONSUMIDOR: {dest_id} {dest_name}".strip()
            self.multi_cell(text_w, 3, consumidor_line, border=0, align="L")

        n_nf = extract_text(self.ide, "nNF")
        serie = extract_text(self.ide, "serie")
        dt_emi, hr_emi = get_date_utc(extract_text(self.ide, "dhEmi"))
        id_line = f"NFC-e nº {n_nf}  Série {serie}  Emissão: {dt_emi} {hr_emi}"
        self.multi_cell(text_w, 3, id_line, border=0, align="L")

        if self.prot_nfe is not None:
            dt_aut, hr_aut = get_date_utc(extract_text(self.prot_nfe, "dhRecbto"))
            protocol = extract_text(self.prot_nfe, "nProt")
            self.multi_cell(
                text_w,
                3,
                f"Protocolo de autorização: {protocol}",
                border=0,
                align="L",
            )
            self.multi_cell(
                text_w,
                3,
                f"Data de autorização: {dt_aut} {hr_aut}",
                border=0,
                align="L",
            )

        v_tot_trib = format_number(extract_text(self.total, "vTotTrib"), precision=2)
        y_after_text = self.get_y()
        y_block_bottom = max(y_qr + box_size, y_after_text)
        if v_tot_trib and v_tot_trib != "0,00":
            self.set_xy(self.l_margin, y_block_bottom + 2)
            self.set_font(self.default_font, "", 6)
            self.multi_cell(
                w=self._content_width(),
                h=3,
                text=(
                    "Tributos Totais Incidentes (Lei 12.741/2012): " f"R$ {v_tot_trib}"
                ),
                border=0,
                align="L",
            )

        inf_cpl = extract_text(self.inf_adic, "infCpl")
        if inf_cpl:
            self.ln(1)
            self.set_font(self.default_font, "", 6)
            inf_cpl = " ".join(re.split(r"\s+", inf_cpl.strip(), flags=re.UNICODE))
            self.multi_cell(
                w=self._content_width(),
                h=3,
                text=inf_cpl,
                border=0,
                align="L",
            )

        self._draw_void_watermark()

    def _content_width(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def _wrap_text(self, text: str, max_width: float) -> list[str]:
        if not text:
            return []
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if not current:
                current = word
                continue
            if self.get_string_width(candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _ensure_space(self, required_height: float) -> None:
        available = self.h - self.b_margin - self.get_y()
        if required_height > 0 and available < required_height:
            self.add_page()

    def _draw_line(self) -> None:
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.1)
        self.line(
            self.l_margin,
            self.get_y(),
            self.w - self.r_margin,
            self.get_y(),
        )
        self.ln(0.5)

    def _draw_void_watermark(self) -> None:
        """
        Desenha watermark quando cancelada ou em homologação/sem protocolo.
        Para cupom, o texto é mais discreto, no rodapé.
        """

        is_production_environment = extract_text(self.ide, "tpAmb") == "1"
        is_protocol_available = bool(self.prot_nfe)

        watermark_text = None
        if self.config.watermark_cancelled:
            if is_production_environment:
                watermark_text = "CANCELADA"
            else:
                watermark_text = "CANCELADA - SEM VALOR FISCAL"
        elif not is_production_environment or not is_protocol_available:
            watermark_text = "SEM VALOR FISCAL"

        if watermark_text:
            self.ln(1)
            self.set_font(self.default_font, "B", 6)
            self.set_text_color(200, 100, 100)
            self.multi_cell(
                w=self._content_width(),
                h=3,
                text=watermark_text,
                border=0,
                align="C",
            )
            self.set_text_color(0, 0, 0)
