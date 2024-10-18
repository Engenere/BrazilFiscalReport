# Copyright (C) 2024 Engenere - Cristiano Mafra Junior

import xml.etree.ElementTree as ET
from io import BytesIO
from xml.etree.ElementTree import Element

import qrcode
from barcode import Code128
from barcode.writer import SVGWriter

from ..utils import (
    format_cep,
    format_cpf_cnpj,
    format_number,
    format_phone,
    get_date_utc,
    get_tag_text,
)
from ..xfpdf import xFPDF
from .config import DamdfeConfig
from .damdfe_conf import URL, tp_ambiente, tp_emissao, tp_emitente


def extract_text(node: Element, tag: str) -> str:
    return get_tag_text(node, URL, tag)


class Damdfe(xFPDF):
    def __init__(self, xml, config: DamdfeConfig = None):
        super().__init__(unit="mm", format="A4")
        config = config if config is not None else DamdfeConfig()
        self.set_margins(
            left=config.margins.left, top=config.margins.top, right=config.margins.right
        )
        self.set_auto_page_break(auto=False, margin=config.margins.bottom)
        self.set_title("DAMDFE")
        self.logo_image = config.logo
        self.receipt_pos = config.receipt_pos
        self.default_font = config.font_type.value
        self.price_precision = config.decimal_config.price_precision
        self.quantity_precision = config.decimal_config.quantity_precision

        root = ET.fromstring(xml)
        self.inf_mdfe = root.find(f"{URL}infMDFe")
        self.prot_mdfe = root.find(f"{URL}protMDFe")
        self.emit = root.find(f"{URL}emit")
        self.ide = root.find(f"{URL}ide")
        self.inf_modal = root.find(f"{URL}infModal")
        self.inf_doc = root.find(f"{URL}infDoc")
        self.tot = root.find(f"{URL}tot")
        self.inf_mdfe_supl = root.find(f"{URL}infMDFeSupl")
        self.key_mdfe = self.inf_mdfe.attrib.get("Id")[4:]
        self.protocol = extract_text(self.prot_mdfe, "nProt")
        self.dh_recebto, self.hr_recebto = get_date_utc(
            extract_text(self.prot_mdfe, "dhRecbto")
        )

        self.percurso_str = ""
        for per in self.ide:
            self.per = extract_text(per, "UFPer")
            if self.percurso_str:
                self.percurso_str += " / "
            self.percurso_str += self.per
        # Remove a barra extra no final
        if self.percurso_str.endswith(" / "):
            self.percurso_str = self.percurso_str[:-3]

        self.add_page(orientation="P")
        self._draw_void_watermark()
        self._draw_receipt()
        self._draw_header()
        self._draw_voucher_information()
        self._draw_insurance_information()

    def _draw_void_watermark(self):
        """
        Draw a watermark on the DAMDFE when the protocol is not available or
        when the environment is homologation.
        """
        is_production_environment = extract_text(self.ide, "tpAmb") == "1"
        is_protocol_available = bool(self.prot_mdfe)

        # Exit early if no watermark is needed
        if is_production_environment and is_protocol_available:
            return

        self.set_font(self.default_font, "B", 60)
        watermark_text = "SEM VALOR FISCAL"
        width = self.get_string_width(watermark_text)
        self.set_text_color(r=220, g=150, b=150)
        height = 15
        page_width = self.w
        page_height = self.h
        x_center = (page_width - width) / 2
        y_center = (page_height + height) / 2
        with self.rotation(55, x_center + (width / 2), y_center - (height / 2)):
            self.text(x_center, y_center, watermark_text)
        self.set_text_color(r=0, g=0, b=0)

    def draw_vertical_lines_left(self, start_y, end_y, num_lines=None):
        half_page_width = self.epw / 2 - 0.25
        col_width = half_page_width / num_lines
        for i in range(1, num_lines + 1):
            x_line = self.l_margin + i * col_width
            self.line(x1=x_line, y1=start_y, x2=x_line, y2=end_y)

    def draw_vertical_lines_right(self, start_y, end_y, num_lines=None):
        half_page_width = self.epw / 2 - 0.25
        col_width = half_page_width / num_lines
        start_x = self.l_margin + half_page_width
        for i in range(1, num_lines + 1):
            x_line = start_x + i * col_width
            self.line(x1=x_line, y1=start_y, x2=x_line, y2=end_y)

    # Linhas Verticais - Metodo Responsavél
    # pelas linhas verticas da sessão de informações do DAMDFE
    def draw_vertical_lines(self, x_start_positions, y_start, y_end, x_margin):
        for x in x_start_positions:
            self.line(x1=x_margin + x, y1=y_start, x2=x_margin + x, y2=y_end)

    def _draw_receipt(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        self.model = extract_text(self.ide, "mod")
        self.serie = extract_text(self.ide, "serie")
        self.n_mdf = extract_text(self.ide, "nMDF")
        self.dt, self.hr = get_date_utc(extract_text(self.ide, "dhEmi"))
        self.uf_carreg = extract_text(self.ide, "UFIni")
        self.uf_descarreg = extract_text(self.ide, "UFFim")
        self.tp_emi = tp_emissao[extract_text(self.ide, "tpEmis")]
        self.dt_inicio, self.hr_inicio = get_date_utc(
            extract_text(self.ide, "dhIniViagem")
        )
        self.tp_emit = tp_emitente[extract_text(self.ide, "tpEmit")]
        self.tp_amb = tp_ambiente[extract_text(self.prot_mdfe, "tpAmb")]

        cep = format_cep(extract_text(self.emit, "CEP"))
        fone = format_phone(extract_text(self.emit, "fone"))
        emit_info = (
            f"{extract_text(self.emit, 'xNome')}\n"
            f"{extract_text(self.emit, 'xLgr')} "
            f"{extract_text(self.emit, 'nro')}\n"
            f"{extract_text(self.emit, 'xBairro')} "
            f"{cep}\n"
            f"{extract_text(self.emit, 'xMun')} - "
            f"{extract_text(self.emit, 'UF')}\n"
            f"CNPJ:{extract_text(self.emit, 'CNPJ')} "
            f"IE:{extract_text(self.emit, 'IE')}\n"
            f"RNTRC:{extract_text(self.inf_modal, 'RNTRC')} "
            f"TELEFONE:{fone}"
        )

        self.set_dash_pattern(dash=0, gap=0)
        self.set_font(self.default_font, "", 7)
        self.rect(x=x_margin, y=y_margin, w=page_width - 0.5, h=88, style="")
        h_logo = 18
        w_logo = 18
        y_logo = y_margin
        if self.logo_image:
            self.image(
                name=self.logo_image,
                x=x_margin + 2,
                y=y_logo + 2,
                w=w_logo + 2,
                h=h_logo + 2,
                keep_aspect_ratio=True,
            )
        self.set_xy(x=x_margin + 25, y=y_margin + 5)
        self.multi_cell(w=60, h=3, text=emit_info, border=0, align="L")

        x_middle = x_margin + (page_width - 0.5) / 2
        self.line(x_middle, y_margin, x_middle, y_margin + 88)

        y_middle = y_margin + 25
        self.line(x_margin, y_middle, x_middle, y_middle)
        self.set_xy(x=x_margin, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="DAMDFE - Documento Auxiliar do "
            "Manifesto de Documentos Fiscais Eletrônicos",
            border=0,
            align="C",
        )

        y_middle = y_margin + 28
        self.line(x_margin, y_middle, x_middle, y_middle)
        self.set_font(self.default_font, "", 6)

        self.draw_vertical_lines(
            x_start_positions=[13, 21, 32, 38, 58, 73],
            y_start=y_middle,
            y_end=y_middle + 7,
            x_margin=x_margin,
        )

        # Informações do DAMDF
        # Modelo
        self.set_xy(x=x_margin + 1, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="MODELO",
            border=0,
            align="L",
        )
        self.set_xy(x=x_margin + 4, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.model,
            border=0,
            align="L",
        )
        # Série
        self.set_xy(x=x_margin + 13, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="SÉRIE",
            border=0,
            align="L",
        )
        self.set_xy(x=x_margin + 15, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.serie,
            border=0,
            align="L",
        )
        # Número
        self.set_xy(x=x_margin + 21, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="NÚMERO",
            border=0,
            align="L",
        )
        self.set_xy(x=x_margin + 24, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.n_mdf,
            border=0,
            align="L",
        )

        # FL
        self.set_xy(x=x_margin + 33, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="FL",
            border=0,
            align="L",
        )
        # Teste
        self.set_xy(x=x_margin + 33, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text="1/1",
            border=0,
            align="L",
        )

        # DATA E HORA DE EMISSÃO
        self.set_xy(x=x_margin + 39, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="DATA E HORA",
            border=0,
            align="L",
        )
        self.set_xy(x=x_margin + 38, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=f"{self.dt} {self.hr}",
            border=0,
            align="L",
        )

        # UF CARREG
        self.set_xy(x=x_margin + 59, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="UF CARREG",
            border=0,
            align="L",
        )
        self.set_xy(x=x_margin + 63, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.uf_carreg,
            border=0,
            align="L",
        )

        # UF DESCARREG
        self.set_xy(x=x_margin + 77, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="UF DESCARREG",
            border=0,
            align="L",
        )
        self.set_xy(x=x_margin + 84, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.uf_descarreg,
            border=0,
            align="L",
        )

        # QR_CODE
        self.qr_code = extract_text(self.inf_mdfe_supl, "qrCodMDFe")
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1,
        )
        qr.add_data(self.qr_code)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img_bytes = qr_img.get_image()

        num_x = x_margin + 135
        num_y = self.l_margin + 3
        num_w = 28
        num_h = 28
        self.image(qr_img_bytes, x=num_x + 1, y=num_y + 1, w=num_w - 2, h=num_h - 2)

        svg_img_bytes = BytesIO()
        Code128(self.key_mdfe, writer=SVGWriter()).write(svg_img_bytes)
        self.image(svg_img_bytes, x=x_margin + 108 + 1, y=num_y + 35, w=82, h=12.5)

        self.set_font(self.default_font, "", 6.5)
        self.set_xy(x=x_middle + 6, y=y_middle + 23)
        self.multi_cell(
            w=100,
            h=3,
            text="Chave de acesso para consulta de "
            "autenticidade no site "
            "mdfe-portal.sefaz.rs.gov.br ou da Sefaz",
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_middle + 25, y=y_middle + 28)
        self.multi_cell(
            w=100,
            h=3,
            text=self.key_mdfe,
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "B", 6)
        self.set_xy(x=x_middle + 28, y=y_middle + 32)
        self.multi_cell(
            w=100,
            h=3,
            text="PROTOCOLO DE AUTORIZAÇÃO DE USO",
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "", 6)
        self.set_xy(x=x_middle + 32, y=y_middle + 35)
        self.multi_cell(
            w=100,
            h=3,
            text=f"{self.protocol} {self.dh_recebto} {self.hr_recebto}",
            border=0,
            align="L",
        )

        y_middle = y_margin + 35
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.draw_vertical_lines(
            x_start_positions=[24, 64],
            y_start=y_middle,
            y_end=y_middle + 7,
            x_margin=x_margin,
        )

        # Informações de Emissão
        # FORMA DE EMISSÃO
        self.set_xy(x=x_margin, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="FORMA DE EMISSÃO",
            border=0,
            align="L",
        )
        self.set_xy(x=x_margin + 6, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.tp_emi,
            border=0,
            align="L",
        )

        # PREVISÃO DE INICIO DA VIAGEM
        self.set_xy(x=x_margin + 25, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="PREVISÃO DE INICIO DA VIAGEM",
            border=0,
            align="L",
        )

        self.set_xy(x=x_margin + 32.5, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=f"{self.dt_inicio} {self.hr_inicio}",
            border=0,
            align="L",
        )

        # INSC. SUFRAMA
        self.set_xy(x=x_margin + 73, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="INSC. SUFRAMA",
            border=0,
            align="L",
        )

        y_middle = y_margin + 42
        self.line(x_margin, y_middle, x_middle, y_middle)
        self.draw_vertical_lines(
            x_start_positions=[44, 70],
            y_start=y_middle,
            y_end=y_middle + 8,
            x_margin=x_margin,
        )

        # Informações Emitente
        # TIPO DO EMITENTE
        self.set_xy(x=x_margin + 11, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="TIPO DO EMITENTE",
            border=0,
            align="L",
        )

        self.set_xy(x=x_margin + 1.5, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.tp_emit,
            border=0,
            align="L",
        )

        # TIPO DO AMBIENTE
        self.set_xy(x=x_margin + 46, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="TIPO DO AMBIENTE",
            border=0,
            align="L",
        )

        self.set_xy(x=x_margin + 50, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.tp_amb,
            border=0,
            align="L",
        )

        # CARGA POSTERIOR
        self.set_xy(x=x_margin + 73, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="CARGA POSTERIOR",
            border=0,
            align="L",
        )

        y_middle = y_margin + 50
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)

    def _draw_header(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        x_middle = x_margin + (page_width - 0.5) / 2
        y_middle = y_margin + 10
        self.line(x_margin, y_middle, x_middle, y_middle)
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin - 2, y=y_middle - 2)
        self.multi_cell(
            w=100, h=0, text="MODAL RODOVIÁRIO DE CARGA", border=0, align="C"
        )

        y_middle = y_margin + 15
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=x_margin - 2, y=y_middle - 2)
        self.multi_cell(w=100, h=0, text="INFORMAÇÕES PARA ANTT", border=0, align="C")
        self.draw_vertical_lines_left(
            start_y=y_margin + 15, end_y=y_margin + 15 + 7, num_lines=4
        )
        self.qtd_nfe = extract_text(self.tot, "qNFe")
        self.qtd_carga = extract_text(self.tot, "qCarga")
        self.valor_carga = format_number(extract_text(self.tot, "vCarga"), precision=2)
        self.placa = extract_text(self.inf_modal, "placa")
        self.modal_uf = extract_text(self.inf_modal, "UF")
        self.rntrc = extract_text(self.inf_modal, "RNTRC")
        self.renavam = extract_text(self.inf_modal, "RENAVAM")
        self.cpf_condutor = format_cpf_cnpj(extract_text(self.inf_modal, "CPF"))
        self.nome_condutor = extract_text(self.inf_modal, "xNome")
        # Informações para ANTT
        # QTD. CT-e
        self.set_font(self.default_font, "", 6.5)
        self.set_xy(x=x_margin, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="QTD. CT-e",
            border=0,
            align="L",
        )

        # Vê qual TAG tem essa informação
        self.set_xy(x=x_margin, y=y_middle + 4)
        self.multi_cell(
            w=100,
            h=3,
            text="",
            border=0,
            align="L",
        )

        # QTD. NF-e
        self.set_xy(x=x_margin + 25, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="QTD. NF-e",
            border=0,
            align="l",
        )

        self.set_xy(x=x_margin + 25, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.qtd_nfe,
            border=0,
            align="L",
        )

        # PESO TOTAL
        self.set_xy(x=x_margin + 50, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="PESO TOTAL",
            border=0,
            align="L",
        )

        self.set_xy(x=x_margin + 50, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.qtd_carga,
            border=0,
            align="L",
        )

        # VALOR TOTAL
        self.set_xy(x=x_margin + 75, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="VALOR TOTAL",
            border=0,
            align="L",
        )

        self.set_xy(x=x_margin + 75, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=f"R$ {self.valor_carga}",
            border=0,
            align="L",
        )

        y_middle = y_margin + 22
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)

        y_middle = y_margin + 26
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=x_margin - 2, y=y_middle - 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(w=100, h=0, text="VEÍCULOS", border=0, align="C")
        self.draw_vertical_lines_left(
            start_y=y_margin + 26, end_y=y_margin + 26 + 17, num_lines=4
        )

        # Informações do Veiculos
        # PLACA
        self.set_xy(x=x_margin, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="PLACA",
            border=0,
            align="L",
        )
        self.set_font(self.default_font, "", 7)
        self.set_xy(x=x_margin, y=y_middle + 4)
        self.multi_cell(
            w=100,
            h=3,
            text=self.placa,
            border=0,
            align="L",
        )

        # UF
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 25, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="UF",
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=x_margin + 25, y=y_middle + 4)
        self.multi_cell(
            w=100,
            h=3,
            text=self.modal_uf,
            border=0,
            align="L",
        )

        # RNTRC
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 50, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="RNTRC",
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=x_margin + 50, y=y_middle + 4)
        self.multi_cell(
            w=100,
            h=3,
            text=self.rntrc,
            border=0,
            align="L",
        )

        # RENAVAM
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 75, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="RENAVAM",
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=x_margin + 75, y=y_middle + 4)
        self.multi_cell(
            w=100,
            h=3,
            text=self.renavam,
            border=0,
            align="L",
        )

        self.set_xy(x=page_width / 2 - 2, y=y_middle - 2)
        self.multi_cell(w=100, h=0, text="CONDUTORES", border=0, align="C")
        y_middle = y_margin + 29
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.draw_vertical_lines_right(
            start_y=y_margin + 26, end_y=y_margin + 26 + 17, num_lines=2
        )

        # Informações do Condutores
        # CPF
        self.set_xy(x=y_middle + 26, y=y_middle - 2.8)
        self.multi_cell(
            w=100,
            h=3,
            text="CPF",
            border=0,
            align="L",
        )

        self.set_xy(x=y_middle + 26, y=y_middle + 0.5)
        self.multi_cell(
            w=100,
            h=3,
            text=self.cpf_condutor,
            border=0,
            align="L",
        )

        # CONDUTORES
        self.set_xy(x=y_middle + 76, y=y_middle - 2.8)
        self.multi_cell(
            w=100,
            h=3,
            text="CONDUTORES",
            border=0,
            align="L",
        )

        self.set_xy(x=y_middle + 76, y=y_middle + 0.5)
        self.multi_cell(
            w=100,
            h=3,
            text=self.nome_condutor,
            border=0,
            align="L",
        )

        y_middle = y_margin + 60
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)

    def _draw_voucher_information(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        self.rect(x=x_margin, y=y_margin + 10.5, w=page_width - 0.5, h=40, style="")

        y_middle = y_margin + 14.5
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=(page_width - 40) / 2, y=y_middle - 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(
            w=100, h=0, text="INFORMAÇÕES DE VALE PEDÁGIO", border=0, align="L"
        )
        self.draw_vertical_lines_left(
            start_y=y_margin + 14.5, end_y=y_margin + 14.5 + 4, num_lines=2
        )
        self.draw_vertical_lines_right(
            start_y=y_margin + 14.5, end_y=y_margin + 14.5 + 4, num_lines=2
        )

        # Informações de Vale Pedágio
        # CPF
        self.set_font(self.default_font, "B", 6)
        self.set_xy(x=x_margin + 12, y=y_middle + 1)
        self.multi_cell(
            w=100,
            h=3,
            text="CNPJ DA FORNECEDORA",
            border=0,
            align="L",
        )

        # CPF/CNPJ DO RESPONSÁVEL
        self.set_xy(x=x_margin + 59, y=y_middle + 1)
        self.multi_cell(
            w=100,
            h=3,
            text="CPF/CNPJ DO RESPONSÁVEL",
            border=0,
            align="L",
        )

        # NÚMERO DO COMPROVANTE
        self.set_xy(x=y_middle + 15, y=y_middle + 1)
        self.multi_cell(
            w=100,
            h=3,
            text="NÚMERO DO COMPROVANTE",
            border=0,
            align="L",
        )

        # VALOR DO VALE-PEDÁGIO
        self.set_xy(x=y_middle + 67, y=y_middle + 1)
        self.multi_cell(
            w=100,
            h=3,
            text="VALOR DO VALE-PEDÁGIO",
            border=0,
            align="L",
        )

        y_middle = y_margin + 18.5
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)

        y_middle = y_margin + 31.5
        self.set_font(self.default_font, "B", 7)
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=(page_width - 18) / 2, y=y_middle - 2)
        self.multi_cell(w=100, h=0, text="PERCURSO", border=0, align="L")
        self.set_xy(x=x_margin, y=y_middle + 1.5)
        self.set_font(self.default_font, "", 6.5)
        self.multi_cell(w=100, h=0, text=self.percurso_str, border=0, align="L")

        y_middle = y_margin + 35.5
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)

        y_middle = y_margin + 40.5
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=(page_width - 50) / 2, y=y_middle - 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(
            w=100, h=0, text="INFORMAÇÕES DA COMPOSIÇÃO DA CARGA", border=0, align="L"
        )
        self.draw_vertical_lines(
            x_start_positions=[30, 92, 130],
            y_start=y_middle,
            y_end=y_middle + 4,
            x_margin=x_margin,
        )
        self.set_font(self.default_font, "", 5.5)
        # INFORMAÇÕES DA COMPOSIÇÃO DA CARGA
        # MUNICÍPIO
        self.set_xy(x=x_margin, y=y_middle + 1)
        self.multi_cell(
            w=100,
            h=3,
            text="MUNICÍPIO",
            border=0,
            align="L",
        )

        # Informações dos Docs. Fiscais Vinculados ao Manifesto
        self.set_xy(x=x_margin + 30, y=y_middle + 1)
        self.multi_cell(
            w=100,
            h=3,
            text="INFORMAÇÕES DOS DOCS. FISCAIS VINCULADOS AO MANIFESTO",
            border=0,
            align="L",
        )

        # MUNICÍPIO
        self.set_xy(x=x_margin + 92, y=y_middle + 1)
        self.multi_cell(
            w=100,
            h=3,
            text="MUNICÍPIO",
            border=0,
            align="L",
        )

        # Informações dos Docs. Fiscais Vinculados ao Manifesto
        self.set_xy(x=x_margin + 130, y=y_middle + 1)
        self.multi_cell(
            w=100,
            h=3,
            text="INFORMAÇÕES DOS DOCS. FISCAIS VINCULADOS AO MANIFESTO",
            border=0,
            align="L",
        )

        y_middle = y_margin + 44.5
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)

    def _draw_insurance_information(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        self.rect(x=x_margin, y=y_margin + 6, w=page_width - 0.5, h=44, style="")
        y_middle = y_margin + 9
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=(page_width - 45) / 2, y=y_middle - 1.5)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(
            w=100, h=0, text="INFORMAÇÕES SOBRE OS SEGUROS", border=0, align="L"
        )

        self.rect(x=x_margin, y=y_margin + 50, w=page_width - 0.5, h=45, style="")
        y_middle = y_margin + 55
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=(page_width - 80) / 2, y=y_middle - 2)
        self.multi_cell(
            w=100,
            h=0,
            text="INFORMAÇÕES COMPLEMENTARES DE INTERESSE DO CONTRIBUINTE",
            border=0,
            align="L",
        )

        self.rect(x=x_margin, y=y_margin + 95, w=page_width - 0.5, h=45, style="")
        y_middle = y_margin + 100
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=(page_width - 65) / 2, y=y_middle - 2)
        self.multi_cell(
            w=100,
            h=0,
            text="INFORMAÇÕES ADICIONAIS DE INTERESSE DO FISCO",
            border=0,
            align="L",
        )
