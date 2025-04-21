# Copyright (C) 2024 Engenere - Cristiano Mafra Junior

import re
import textwrap
import xml.etree.ElementTree as ET
from io import BytesIO
from xml.etree.ElementTree import Element

from barcode.codex import Code128
from barcode.writer import SVGWriter

from ..utils import (
    format_cep,
    format_cpf_cnpj,
    format_number,
    format_phone,
    format_xDime,
    get_date_utc,
    get_tag_text,
)
from ..xfpdf import xFPDF
from .config import DacteConfig, ModalType, ReceiptPosition
from .dacte_conf import (
    RESP_FATURAMENTO,
    TP_CODIGO_MEDIDA,
    TP_CTE,
    TP_FERROV_EMITENTE,
    TP_ICMS,
    TP_MANUSEIO,
    TP_MODAL,
    TP_SERVICO,
    TP_TOMADOR,
    TP_TRAFICO,
    URL,
)
from .generate_qrcode import draw_qr_code


def extract_text(node: Element, tag: str) -> str:
    return get_tag_text(node, URL, tag)


class Dacte(xFPDF):
    def __init__(self, xml, config: DacteConfig = None):
        super().__init__(unit="mm", format="A4")
        config = config if config is not None else DacteConfig()
        self.set_margins(
            left=config.margins.left, top=config.margins.top, right=config.margins.right
        )
        self.set_auto_page_break(auto=False, margin=config.margins.bottom)
        self.set_title("DACTE")
        self.logo_image = config.logo
        self.receipt_pos = config.receipt_pos
        self.default_font = config.font_type.value
        self.price_precision = config.decimal_config.price_precision
        self.quantity_precision = config.decimal_config.quantity_precision

        root = ET.fromstring(xml)
        self.inf_cte = root.find(f"{URL}infCte")
        self.prot_cte = root.find(f"{URL}protCTe")
        self.emit = root.find(f"{URL}emit")
        self.ide = root.find(f"{URL}ide")
        self.dest = root.find(f"{URL}dest")
        self.exped = root.find(f"{URL}exped")
        self.receb = root.find(f"{URL}receb")
        self.rem = root.find(f"{URL}rem")
        self.outros = root.find(f"{URL}toma4")
        self.inf_prot = root.find(f"{URL}infProt")
        self.inf_cte_supl = root.find(f"{URL}infCTeSupl")
        self.tomador = root.find(f"{URL}toma3") or self.outros
        self.inf_carga = root.find(f"{URL}infCarga")
        self.inf_doc = root.find(f"{URL}infDoc")
        self.v_prest = root.find(f"{URL}vPrest")
        self.inf_modal = root.find(f"{URL}infModal")
        self.imp = root.find(f"{URL}imp")
        self.compl = root.find(f"{URL}compl")
        self.aquav = root.find(f"{URL}aquav")
        self.ferrov = root.find(f"{URL}ferrov")

        self.obs_dacte_list = []
        for obs in self.compl:
            self.x_texto = extract_text(obs, "xTexto")
            self.x_texto = " ".join(
                re.split(r"\s+", self.x_texto.strip(), flags=re.UNICODE)
            )
            self.obs_dacte_list.append(self.x_texto)

        self.page_lines = 0
        self.inf_carga_list = []
        for infQ in self.inf_carga:
            self.c_unid = extract_text(infQ, "cUnid")
            self.tp_media = extract_text(infQ, "tpMed")
            self.q_carga = extract_text(infQ, "qCarga")
            self.inf_carga_list.append((self.c_unid, self.tp_media, self.q_carga))

        self.inf_doc_list = []
        for chave in self.inf_doc:
            self.chave = extract_text(chave, "chave")
            self.inf_doc_list.append(self.chave)

        self.comp_list = []
        for comp in self.v_prest.findall(f"{URL}Comp"):
            self.xNome = extract_text(comp, "xNome")
            self.vComp = extract_text(comp, "vComp")
            self.comp_list.append((self.xNome, self.vComp))

        # extract orientation
        tpImp = extract_text(self.ide, "tpImp")
        if tpImp == "1":
            self.orientation = "P"
        else:
            self.orientation = "L"
            # force receipt position
            # landscape support only left receipt
            self.receipt_pos = ReceiptPosition.LEFT

        self.recibo_text = self._get_receipt_text()
        self.nr_dacte = extract_text(self.ide, "nCT")
        self.serie_cte = extract_text(self.ide, "serie")
        self.key_cte = self.inf_cte.attrib.get("Id")[3:]
        self.tp_cte = TP_CTE[extract_text(self.ide, "tpCTe")]
        self.tp_serv = TP_SERVICO[extract_text(self.ide, "tpServ")]
        self.prot_uso = self._get_usage_protocol()
        self.mod = extract_text(self.ide, "mod")
        self.nct = extract_text(self.ide, "nCT")
        self.toma = TP_TOMADOR[extract_text(self.tomador, "toma")]
        self.cfop = extract_text(self.ide, "CFOP")
        self.nat_op = extract_text(self.ide, "natOp")

        self.add_page(orientation=self.orientation)
        self._draw_receipt()
        self._draw_header()
        self._draw_recipient_sender(config)
        self._draw_service_recipient(config)
        self._draw_service_fee_value()
        self._draw_documents_obs()
        self._draw_specific_data(config)
        self._draw_void_watermark()
        self._add_new_page(config)

    def _get_usage_protocol(self):
        dt, hr = get_date_utc(extract_text(self.prot_cte, "dhRecbto"))
        protocol = extract_text(self.prot_cte, "nProt")
        prot_text = f"{protocol} - {dt} {hr}"
        return prot_text

    def _get_receipt_text(self):
        return (
            "DECLARO QUE RECEBI OS VOLUMES DESTE CONHECIMENTO "
            "EM PERFEITO ESTADO PELO QUE DOU POR "
            "CUMPRIDO O PRESENTE CONTRATO DE TRANSPORTE"
        )

    def _draw_void_watermark(self):
        if extract_text(self.ide, "tpAmb") == "2":
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

    def _draw_dashed_line(self, distance):
        self.set_dash_pattern(dash=0.2, gap=0.8)
        if self.orientation == "P":
            self.line(
                x1=self.l_margin,
                y1=distance,
                x2=self.w - self.r_margin,
                y2=distance,
            )
        else:
            self.line(
                x1=distance,
                y1=self.t_margin,
                x2=distance,
                y2=self.h - self.b_margin,
            )
        self.set_dash_pattern(dash=0, gap=0)

    def _draw_receipt(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw
        w_date_field = 40
        line_height = 8
        cell_height = -5

        def draw_vertical_lines(start_y, end_y):
            col_width = page_width / 4
            x_line1 = x_margin + col_width
            x_line2 = x_margin + 2 * col_width
            x_line3 = x_margin + 3 * col_width

            self.line(x1=x_line1, x2=x_line1, y1=start_y, y2=end_y)
            self.line(x1=x_line2, x2=x_line2, y1=start_y, y2=end_y)
            self.line(x1=x_line3, x2=x_line3, y1=start_y, y2=end_y)

            return x_line1, x_line2, x_line3

        self._draw_dashed_line(distance=y_margin + 21)
        self.set_dash_pattern(dash=0, gap=0)

        self.rect(x=x_margin, y=y_margin, w=page_width - 0.5, h=3, style="")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=x_margin, y=y_margin)
        self.cell(
            w=page_width - 2 * x_margin, h=3, text=self.recibo_text, border=0, align="L"
        )

        h_recibo = 17
        self.rect(
            x=x_margin, y=y_margin + 3.5, w=page_width - 0.5, h=h_recibo, style=""
        )

        x_line1, x_line2, x_line3 = draw_vertical_lines(
            y_margin + 3.5, y_margin + h_recibo + 3.5
        )

        y_start = y_margin + 10
        self.line(x1=x_margin, x2=x_line1, y1=y_start + 2, y2=y_start + 2)

        self.set_font(self.default_font, "B", 8)
        self.set_xy(x=x_margin + 2, y=y_start)
        self.cell(w=w_date_field, h=cell_height, text="NOME", border=0, align="L")

        self.set_xy(x=x_margin + 2, y=y_start + line_height)
        self.cell(w=w_date_field, h=cell_height, text="RG", border=0, align="L")

        self.set_xy(x=x_line1 + 7.5, y=y_start + 11)
        self.cell(
            w=w_date_field,
            h=cell_height,
            text="ASSINATURA / CARIMBO",
            border=0,
            align="L",
        )

        self.set_xy(x=x_line2 + 10, y=y_start)
        self.cell(
            w=w_date_field, h=cell_height, text="CHEGADA DATA/HORA", border=0, align="L"
        )

        self.set_xy(x=x_line2 + 10, y=y_start + line_height)
        self.cell(
            w=w_date_field, h=cell_height, text="SAÍDA DATA/HORA", border=0, align="L"
        )

        self.set_xy(x=x_line3 + 23, y=y_start - 2)
        self.set_font(self.default_font, "B", 10)
        self.cell(w=w_date_field, h=cell_height, text="CT-E", border=0, align="L")

        self.set_xy(x=x_line3 + 5, y=y_start + 2)
        self.set_font(self.default_font, "", 7)
        self.cell(
            w=w_date_field, h=cell_height, text="NRO. DOCUMENTO", border=0, align="L"
        )

        self.set_xy(x=x_line3 + 5, y=y_start + line_height)
        self.cell(w=w_date_field, h=cell_height, text="SÉRIE", border=0, align="L")

        self.set_xy(x=x_line3 + 35, y=y_start + 2)
        self.set_font(self.default_font, "B", 7)
        self.cell(
            w=w_date_field, h=cell_height, text=self.nr_dacte, border=0, align="L"
        )

        self.set_xy(x=x_line3 + 38, y=y_start + line_height)
        self.cell(
            w=w_date_field, h=cell_height, text=self.serie_cte, border=0, align="L"
        )

    def _draw_header(self):
        x_margin = self.l_margin
        y_margin = self.y
        section_start_y = y_margin + 4
        w_rect = (self.epw / 2) - 33
        h_rect = 27
        self.emit_name = extract_text(self.emit, "xNome")
        self.cep = format_cep(extract_text(self.emit, "CEP"))
        self.fone = format_phone(extract_text(self.emit, "fone"))
        self.modal = TP_MODAL[extract_text(self.ide, "modal")]
        self.mod = extract_text(self.ide, "mod")
        self.serie = extract_text(self.ide, "serie")
        self.nct = extract_text(self.ide, "nCT")
        self.dt, self.hr = get_date_utc(extract_text(self.ide, "dhEmi"))
        self.protocol = extract_text(self.prot_cte, "nProt")
        self.dh_recebto, hr_recebto = get_date_utc(
            extract_text(self.prot_cte, "dhRecbto")
        )
        self.emit_cnpj = format_cpf_cnpj(extract_text(self.emit, "CNPJ"))
        address = (
            f"CNPJ: {self.emit_cnpj} IE: {extract_text(self.emit, 'IE')}\n"
            f"{extract_text(self.emit, 'xLgr')}, "
            f"{extract_text(self.emit, 'nro')}\n"
            f"{extract_text(self.emit, 'xBairro')}\n"
            f"{extract_text(self.emit, 'xMun')} - "
            f"{extract_text(self.emit, 'UF')}\n"
            f"{self.cep}\nFone: {self.fone}"
        )
        self.rect(x=x_margin, y=section_start_y, w=(self.epw / 2) - 33, h=h_rect)
        h_logo = 8
        w_logo = 8
        y_logo = y_margin
        if self.logo_image:
            self.image(
                name=self.logo_image,
                x=x_margin,
                y=y_logo + 10,
                w=w_logo + 10,
                h=h_logo + 10,
                keep_aspect_ratio=True,
            )
            x_text = x_margin + 4
            y_text = y_logo + 6
            w_text = w_rect
        else:
            x_text = x_margin + 2
            y_text = y_margin + 6
            w_text = w_rect - 4
        self.set_font(self.default_font, "B", 9)
        self.set_xy(x=x_text, y=y_text)
        self.multi_cell(w=w_text, h=5, text=self.emit_name, border=0, align="C")
        self.set_font(self.default_font, "", 8)
        self.set_xy(x=x_text - 3, y=y_text + 6)
        self.multi_cell(w=w_text + 10, h=3, text=address, border=0, align="C")

        y_margin = self.l_margin + 22
        y_start = self.y + 4
        y_margin_ret = self.l_margin + (self.epw / 2) - 33
        w_rect = 53
        h_rect = 11

        self.rect(x=y_margin_ret, y=section_start_y, w=w_rect, h=h_rect)
        self.set_font(self.default_font, "B", 10)
        self.set_xy(x=y_margin_ret - 9, y=y_start - 29)
        self.multi_cell(w=y_margin_ret, h=4, text="DACTE", align="C", border=0)
        self.set_font(self.default_font, "", 6)
        self.set_xy(x=y_margin_ret - 9, y=y_start - 25)
        self.multi_cell(
            w=y_margin_ret,
            h=2,
            text="DOCUMENTO AUXILIAR DO CONHECIMENTO\nDE TRANSPORTE ELETRÔNICO",
            align="C",
        )

        self.rect(x=y_margin_ret + w_rect, y=section_start_y, w=31, h=11, style="")

        self.set_font(self.default_font, "", 8)
        self.set_xy(y_margin_ret + 55, section_start_y + 2)
        self.multi_cell(w=31 - 4, h=1, text="MODAL", align="C")
        self.set_xy(y_margin_ret + 55, section_start_y + 2)
        self.set_font(self.default_font, "B", 8)
        self.multi_cell(w=31 - 4, h=11, text=self.modal, align="C")

        section_start_y += 11

        self.rect(x=y_margin_ret, y=section_start_y, w=84, h=11, style="")

        col_width = (206 - (x_margin + 112)) / 5
        x_line_1 = x_margin + 70 + col_width
        x_line_2 = x_margin + 70 + 2 * col_width
        x_line_3 = x_margin + 70 + 3 * col_width
        x_line_4 = x_margin + 70 + 4 * col_width
        x_line_5 = x_margin + 70 + 4 * col_width
        self.line(
            x1=x_line_1 - 5,
            x2=x_line_1 - 5,
            y1=section_start_y,
            y2=section_start_y + 11,
        )
        self.line(
            x1=x_line_2 - 5,
            x2=x_line_2 - 5,
            y1=section_start_y,
            y2=section_start_y + 11,
        )
        self.line(
            x1=x_line_3 - 8,
            x2=x_line_3 - 8,
            y1=section_start_y,
            y2=section_start_y + 11,
        )
        self.line(x1=x_line_4, x2=x_line_4, y1=section_start_y, y2=section_start_y + 11)
        self.line(x1=x_line_5, x2=x_line_5, y1=section_start_y, y2=section_start_y + 11)

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_1 - 25, section_start_y + 2)
        self.multi_cell(w=31 - 4, h=1, text="MODELO", align="C")
        self.set_xy(x_line_1 - 25, section_start_y + 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(w=31 - 4, h=11, text=self.mod, align="C")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_2 - 28, section_start_y + 2)
        self.multi_cell(w=31 - 4, h=1, text="SÉRIE", align="C")
        self.set_xy(x_line_2 - 28, section_start_y + 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(w=31 - 4, h=11, text=self.serie, align="C")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_3 - 29, section_start_y + 2)
        self.multi_cell(w=31 - 4, h=1, text="NÚMERO", align="C")
        self.set_xy(x_line_3 - 29, section_start_y + 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(w=31 - 4, h=11, text=self.nct, align="C")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_4 - 27, section_start_y + 2)
        self.multi_cell(w=31 - 4, h=2.5, text="DATA E HORA\nDE EMISSÃO", align="C")
        self.set_xy(x_line_4 - 27, section_start_y + 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(w=31 - 4, h=13, text=f"{self.dt} {self.hr}", align="C")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_5 - 9, section_start_y + 2)
        self.multi_cell(w=31 - 4, h=2, text="FL", align="C")
        self.set_xy(x_line_5 - 9, section_start_y + 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(w=31 - 1, h=11, text=f"{self.page_no()}/{{nb}}", align="C")

        section_start_y += 11
        y = section_start_y + 0.5
        w = 82
        h = 11.5
        self.rect(x=y_margin_ret, y=section_start_y, w=84, h=10, style="")
        svg_img_bytes = BytesIO()
        Code128(self.key_cte, writer=SVGWriter()).write(svg_img_bytes)
        self.image(svg_img_bytes, x=y_margin_ret + 1, y=y, w=w, h=h)

        section_start_y += 10

        self.set_font(self.default_font, "", 8)
        self.rect(x=y_margin_ret, y=section_start_y, w=84, h=10, style="")
        self.set_xy(x_line_5 - 55, section_start_y + 2)
        self.multi_cell(w=45, h=0, text="CHAVE DE ACESSO", align="C")
        self.set_xy(x_line_5 - 70, section_start_y + 2)
        self.set_font(self.default_font, "B", 8)
        self.multi_cell(w=75, h=11, text=self.key_cte, align="C")
        section_start_y += 10

        self.rect(x=y_margin_ret, y=section_start_y, w=84, h=9, style="")
        self.set_xy(x=y_margin_ret, y=section_start_y)
        self.multi_cell(
            w=85, h=10, text="CONSULTA EM http://www.cte.fazenda.gov.br", align="C"
        )
        section_start_y += 9

        self.set_font(self.default_font, "", 8)
        self.rect(x=y_margin_ret, y=section_start_y, w=84, h=10, style="")
        self.set_xy(x=y_margin_ret, y=section_start_y)
        self.multi_cell(w=85, h=4, text="PROTOCOLO DE AUTORIZAÇÃO DE USO", align="C")
        self.set_xy(x=y_margin_ret, y=section_start_y)
        self.set_font(self.default_font, "B", 8)
        self.multi_cell(
            w=86,
            h=14,
            text=f"{self.protocol} {self.dh_recebto} {hr_recebto}",
            align="C",
        )

        section_start_y += 10
        self.set_font(self.default_font, "", 8)
        self.rect(
            x=self.l_margin,
            y=section_start_y - 34,
            w=(self.epw / 2) - 33,
            h=8,
            style="",
        )
        self.set_xy(x=self.l_margin, y=section_start_y - 34)
        self.multi_cell(w=85, h=4, text="TIPO DO CT-E", align="L")
        self.set_xy(x=self.l_margin, y=section_start_y - 34)
        self.set_font(self.default_font, "B", 8)
        self.multi_cell(w=85, h=10, text=self.tp_cte, align="L")

        section_start_y += 8

        self.set_font(self.default_font, "", 8)
        self.rect(
            x=self.l_margin,
            y=section_start_y - 34,
            w=(self.epw / 2) - 33,
            h=8,
            style="",
        )
        self.set_xy(x=self.l_margin, y=section_start_y - 34)
        self.multi_cell(w=85, h=4, text="TIPO DO SERVIÇO", align="L")
        self.set_xy(x=self.l_margin, y=section_start_y - 34)
        self.set_font(self.default_font, "B", 8)
        self.multi_cell(w=85, h=10, text=self.tp_serv, align="L")

        section_start_y += 8

        self.set_font(self.default_font, "", 8)
        self.rect(
            x=self.l_margin,
            y=section_start_y - 34,
            w=(self.epw / 2) - 33,
            h=9,
            style="",
        )
        self.set_xy(x=self.l_margin, y=section_start_y - 34)
        self.multi_cell(w=85, h=4, text="TOMADOR DO SERVIÇO", align="L")
        self.set_xy(x=self.l_margin, y=section_start_y - 34)
        self.set_font(self.default_font, "B", 8)
        self.multi_cell(w=85, h=10, text=self.toma, align="L")

        section_start_y += 9

        self.set_font(self.default_font, "", 8)
        self.rect(
            x=self.l_margin,
            y=section_start_y - 34,
            w=(self.epw / 2) - 33,
            h=9,
            style="",
        )
        self.set_xy(x=self.l_margin, y=section_start_y - 34)
        self.multi_cell(w=85, h=4, text="CFOP - NATUREZA DA PRESTAÇÃO", align="L")
        self.set_font(self.default_font, "B", 7)
        cfop_text = f"{self.cfop} - {self.nat_op}"

        wrapped_lines = textwrap.wrap(cfop_text, width=42)
        cfop_text_wrapped = "\n".join(wrapped_lines)

        self.set_xy(x=self.l_margin, y=section_start_y - 30)
        self.multi_cell(w=200, h=2.5, text=cfop_text_wrapped, align="L")

        qr_code = extract_text(self.inf_cte_supl, "qrCodCTe")
        x_offset = 88  # Ajuste se necessário
        y_offset = 32  # Ajuste se necessário

        # Chamada correta para o método
        draw_qr_code(self, qr_code, y_margin_ret, x_offset, y_offset, box_size=38)

    def _draw_recipient_sender(self, config):
        self.mun_ini = extract_text(self.ide, "xMunIni")
        self.mun_fim = extract_text(self.ide, "xMunFim")
        self.est_inico = extract_text(self.ide, "UFIni")
        self.est_fim = extract_text(self.ide, "UFFim")

        # Função para extrair dados de uma entidade do XML
        def extract_entity_data(node, prefix):
            """Extrai todos os campos padrão de uma entidade (pessoa) do XML"""
            if node is None:
                empty_data = {
                    f"{prefix}_{field}": ""
                    for field in [
                        "nome",
                        "loga",
                        "nro",
                        "bairro",
                        "mun",
                        "cnpj",
                        "pais",
                        "cep",
                        "ie",
                        "fone",
                        "uf",
                    ]
                }
                for field, value in empty_data.items():
                    setattr(self, field, value)
                return

            # Extrai os dados básicos da entidade
            setattr(self, f"{prefix}_nome", extract_text(node, "xNome"))
            setattr(self, f"{prefix}_loga", extract_text(node, "xLgr"))
            setattr(self, f"{prefix}_nro", extract_text(node, "nro"))
            setattr(self, f"{prefix}_bairro", extract_text(node, "xBairro"))
            setattr(self, f"{prefix}_mun", extract_text(node, "xMun"))
            setattr(self, f"{prefix}_cnpj", format_cpf_cnpj(extract_text(node, "CNPJ")))
            setattr(self, f"{prefix}_pais", extract_text(node, "xPais"))
            setattr(self, f"{prefix}_cep", format_cep(extract_text(node, "CEP")))
            setattr(self, f"{prefix}_ie", extract_text(node, "IE"))
            setattr(self, f"{prefix}_fone", format_phone(extract_text(node, "fone")))
            setattr(self, f"{prefix}_uf", extract_text(node, "UF"))

        # Extrai dados de todas as entidades
        extract_entity_data(self.rem, "rem")
        extract_entity_data(self.dest, "dest")
        extract_entity_data(self.exped, "exped")
        extract_entity_data(self.receb, "receb")
        extract_entity_data(self.outros, "outros")

        # Mapeamento de tipos de tomador para prefixos de atributos
        tomador_map = {
            "REMETENTE": "rem",
            "EXPEDIDOR": "exped",
            "RECEBEDOR": "receb",
            "DESTINATÁRIO": "dest",
            "OUTRO": "outros",
        }

        # Determina o prefixo correto com base no tipo de tomador,
        # padrão para "rem" se não encontrado
        entity_prefix = tomador_map.get(self.toma, "rem")

        # Define os dados do tomador copiando os atributos da entidade correspondente
        for field in [
            "nome",
            "loga",
            "nro",
            "bairro",
            "mun",
            "cnpj",
            "pais",
            "cep",
            "ie",
            "fone",
            "uf",
        ]:
            value = getattr(self, f"{entity_prefix}_{field}", "")
            setattr(self, f"tomador_{field}", value)

        x_margin = self.l_margin
        y_margin = 75
        page_width = 155

        self.set_margins(
            left=config.margins.left, top=config.margins.top, right=config.margins.right
        )
        margins_to_y = {
            2: y_margin + 10,
            3: y_margin + 11,
            4: y_margin + 12,
            5: y_margin + 13,
            6: y_margin + 14,
            7: y_margin + 15,
            8: y_margin + 16,
            9: y_margin + 17,
            10: y_margin + 18,
        }
        section_start_y = margins_to_y[config.margins.left]

        self.rect(
            x=x_margin, y=section_start_y, w=self.epw - 0.1 * x_margin, h=7, style=""
        )
        col_width = (page_width - x_margin) / 2
        x_line_middle = x_margin + col_width + 20

        self.line(
            x1=x_line_middle,
            x2=x_line_middle,
            y1=section_start_y + 7,
            y2=section_start_y,
        )

        self.set_font(self.default_font, "", 8)
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.multi_cell(w=0, h=0, text="INÍCIO DA PRESTAÇÃO", align="L")
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.set_font(self.default_font, "B", 8)
        self.multi_cell(w=0, h=6, text=f"{self.mun_ini} - {self.est_inico}", align="L")

        self.set_font(self.default_font, "", 8)
        self.set_xy(x_line_middle, section_start_y + 2)
        self.multi_cell(w=0, h=0, text="TÉRMINO DA PRESTAÇÃO", align="L")
        self.set_xy(x_line_middle, section_start_y + 2)
        self.set_font(self.default_font, "B", 8)
        self.multi_cell(w=0, h=6, text=f"{self.mun_fim} - {self.est_fim}", align="L")

        self.rect(
            x=x_margin, y=section_start_y, w=self.epw - 0.1 * x_margin, h=24, style=""
        )
        col_width = (page_width - x_margin) / 2
        x_line_middle = x_margin + col_width + 20
        self.line(
            x1=x_line_middle,
            x2=x_line_middle,
            y1=section_start_y + 48,
            y2=section_start_y,
        )

        # Remetente
        self.set_font(self.default_font, "", 7)
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.multi_cell(w=0, h=15, text="REMETENTE ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=self.l_margin + 16, y=section_start_y + 2)
        self.multi_cell(w=0, h=15, text=f"{self.rem_nome}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.multi_cell(
            w=0,
            h=21,
            text="ENDEREÇO ",
            align="L",
        )

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=self.l_margin + 16, y=section_start_y + 2)
        self.multi_cell(
            w=0,
            h=21,
            text=f"{self.rem_loga}, {self.rem_bairro}, {self.rem_nro}",
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.multi_cell(w=0, h=28, text="MUNICÍPIO ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=self.l_margin + 16, y=section_start_y + 2)
        self.multi_cell(w=0, h=28, text=f"{self.rem_mun}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.multi_cell(w=0, h=35, text="CNPJ/CPF ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=self.l_margin + 16, y=section_start_y + 2)
        self.multi_cell(w=0, h=35, text=f"{self.rem_cnpj}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.multi_cell(w=0, h=41, text="PAÍS ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=self.l_margin + 16, y=section_start_y + 2)
        self.multi_cell(w=0, h=41, text=f"{self.rem_pais}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle - 25, section_start_y + 2)
        self.multi_cell(w=0, h=25, text="CEP ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle - 18, section_start_y + 2)
        if len(self.rem_cep.strip()) == 9:
            self.multi_cell(w=0, h=25, text=f"{self.rem_cep}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle - 25, section_start_y + 2)
        self.multi_cell(w=0, h=31, text="IE ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle - 20, section_start_y + 2)
        self.multi_cell(w=0, h=31, text=f"{self.rem_ie}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle - 29, section_start_y + 2)
        self.multi_cell(w=0, h=38, text="FONE ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle - 20, section_start_y + 2)
        self.multi_cell(w=0, h=38, text=f"{self.rem_fone}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle, section_start_y + 2)
        self.multi_cell(w=0, h=15, text="DESTINATÁRIO ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 22, section_start_y + 2)
        self.multi_cell(w=0, h=15, text=f"{self.dest_nome}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle, section_start_y + 2)
        self.multi_cell(
            w=0,
            h=21,
            text="ENDEREÇO ",
            align="L",
        )

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 22, section_start_y + 2)
        self.multi_cell(
            w=0,
            h=21,
            text=f"{self.dest_loga}, {self.dest_bairro}, {self.dest_nro}",
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle, section_start_y + 2)
        self.multi_cell(w=0, h=28, text="MUNICÍPIO ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 22, section_start_y + 2)
        self.multi_cell(w=0, h=28, text=f"{self.dest_mun}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle, section_start_y + 2)
        self.multi_cell(w=0, h=35, text="CNPJ/CPF ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 22, section_start_y + 2)
        self.multi_cell(w=0, h=35, text=f"{self.dest_cnpj}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle, section_start_y + 2)
        self.multi_cell(w=0, h=41, text="PAÍS ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 22, section_start_y + 2)
        self.multi_cell(w=0, h=41, text=f"{self.dest_pais}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle + 70, section_start_y + 2)
        self.multi_cell(w=0, h=25, text="CEP ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 77, section_start_y + 2)
        if len(self.dest_cep.strip()) == 9:
            self.multi_cell(w=0, h=25, text=f"{self.dest_cep}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle + 70, section_start_y + 2)
        self.multi_cell(w=0, h=31, text="IE ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 75, section_start_y + 2)
        self.multi_cell(w=0, h=31, text=f"{self.dest_ie}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle + 60, section_start_y + 2)
        self.multi_cell(w=0, h=38, text="FONE ", align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 67, section_start_y + 2)
        self.multi_cell(w=0, h=38, text=f"{self.dest_fone}", align="L")

        section_start_y += 24

        self.rect(
            x=x_margin, y=section_start_y, w=self.epw - 0.1 * x_margin, h=24, style=""
        )
        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle, section_start_y + 2)
        self.multi_cell(w=0, h=3, text="RECEBEDOR", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 20, section_start_y + 2)
        self.multi_cell(w=0, h=3, text=f"{self.receb_nome}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle, section_start_y + 2)
        self.multi_cell(w=0, h=10, text="ENDEREÇO", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 20, section_start_y + 2)
        self.multi_cell(
            w=0,
            h=10.6,
            text=f"{self.receb_loga} {self.receb_bairro} {self.receb_nro}",
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle, section_start_y + 2)
        self.multi_cell(w=0, h=17, text="MUNICÍPIO", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 20, section_start_y + 2)
        self.multi_cell(w=0, h=18.2, text=f"{self.receb_mun}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle, section_start_y + 2)
        self.multi_cell(w=0, h=25, text="CNPJ/CPF", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 20, section_start_y + 2)
        self.multi_cell(w=0, h=25.8, text=f"{self.receb_cnpj}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle, section_start_y + 2)
        self.multi_cell(w=0, h=32, text="PAÍS", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 20, section_start_y + 2)
        self.multi_cell(w=0, h=33.4, text=f"{self.receb_pais}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle + 70, section_start_y + 2)
        self.multi_cell(w=0, h=20, text="CEP", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 77, section_start_y + 2)
        if len(self.receb_cep.strip()) == 9:
            self.multi_cell(w=0, h=20, text=f"{self.receb_cep}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle + 70, section_start_y + 2)
        self.multi_cell(w=0, h=27, text="IE", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 75, section_start_y + 2)
        self.multi_cell(w=0, h=26.6, text=f"{self.receb_ie}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle + 60, section_start_y + 2)
        self.multi_cell(w=0, h=34, text="FONE", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle + 67, section_start_y + 2)
        self.multi_cell(w=0, h=34, text=f"{self.receb_fone}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.multi_cell(w=0, h=3, text="EXPEDIDOR", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=self.l_margin + 16, y=section_start_y + 2)
        self.multi_cell(w=0, h=3, text=f"{self.exped_nome}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.multi_cell(w=0, h=10, text="ENDEREÇO", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=self.l_margin + 16, y=section_start_y + 2)
        self.multi_cell(
            w=0,
            h=10.6,
            text=f"{self.exped_loga} {self.exped_bairro} {self.exped_nro}",
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.multi_cell(w=0, h=17, text="MUNICÍPIO", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=self.l_margin + 16, y=section_start_y + 2)
        self.multi_cell(w=0, h=18.2, text=f"{self.exped_mun}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.multi_cell(w=0, h=25, text="CNPJ/CPF", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=self.l_margin + 16, y=section_start_y + 2)
        self.multi_cell(w=0, h=25.8, text=f"{self.exped_cnpj}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=self.l_margin, y=section_start_y + 2)
        self.multi_cell(w=0, h=32, text="PAÍS", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=self.l_margin + 16, y=section_start_y + 2)
        self.multi_cell(w=0, h=33.4, text=f"{self.exped_pais}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle - 25, section_start_y + 2)
        self.multi_cell(w=0, h=20, text="CEP", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle - 18, section_start_y + 2)
        if len(self.exped_cep.strip()) == 9:
            self.multi_cell(w=0, h=20, text=f"{self.exped_cep}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle - 25, section_start_y + 2)
        self.multi_cell(w=0, h=27, text="IE", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle - 20, section_start_y + 2)
        self.multi_cell(w=0, h=27, text=f"{self.exped_ie}", align="L")

        self.set_font(self.default_font, "", 7)
        self.set_xy(x_line_middle - 29, section_start_y + 2)
        self.multi_cell(w=0, h=34, text="FONE", align="L")
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x_line_middle - 20, section_start_y + 2)
        self.multi_cell(w=0, h=34, text=f"{self.exped_fone}", align="L")

    def _draw_service_recipient(self, config):
        self.inf_carga_nome = extract_text(self.inf_carga, "proPred")
        self.inf_carga_car = extract_text(self.inf_carga, "xOutCat")
        self.inf_carga_valor = format_number(
            extract_text(self.inf_carga, "vCarga"), precision=2
        )
        self.inf_carga_peso = format_number(
            extract_text(self.inf_carga, "qCarga"), precision=2
        )

        self.inf_unid = extract_text(self.inf_carga, "cUnid")

        self.inf_carga_q = extract_text(self.inf_carga, "qCarga")

        x_margin = self.l_margin
        y_margin = 123
        page_width = self.epw

        self.set_margins(
            left=config.margins.left, top=config.margins.top, right=config.margins.right
        )
        margins_to_y = {
            2: y_margin + 10,
            3: y_margin + 11,
            4: y_margin + 12,
            5: y_margin + 13,
            6: y_margin + 14,
            7: y_margin + 15,
            8: y_margin + 16,
            9: y_margin + 17,
            10: y_margin + 18,
        }
        section_start_y = margins_to_y[config.margins.left]

        self.rect(
            x=x_margin, y=section_start_y, w=page_width - 0.1 * x_margin, h=10, style=""
        )

        self.set_font(self.default_font, "", 7.6)
        self.set_xy(x_margin, section_start_y)
        self.multi_cell(w=0, h=4, text="TOMADOR DO SERVIÇO ", align="L")

        self.set_font(self.default_font, "B", 7.6)
        self.set_xy(x_margin + 32, section_start_y)
        self.multi_cell(w=0, h=4, text=f"{self.tomador_nome}", align="L")

        self.set_font(self.default_font, "", 7.6)
        self.set_xy(x_margin, section_start_y)
        self.multi_cell(w=0, h=10, text="ENDEREÇO ", align="L")

        self.set_font(self.default_font, "B", 7.6)
        self.set_xy(x_margin + 16, section_start_y)
        self.multi_cell(
            w=0,
            h=10,
            text=f"{self.tomador_loga}  {self.tomador_nro}  {self.tomador_bairro}",
            align="L",
        )

        self.set_font(self.default_font, "", 7.6)
        self.set_xy(x_margin, section_start_y)
        self.multi_cell(w=0, h=16, text="CNPJ/CPF ", align="L")

        self.set_font(self.default_font, "B", 7.6)
        self.set_xy(x_margin + 14, section_start_y)
        self.multi_cell(w=0, h=16, text=f"{self.tomador_cnpj}", align="L")

        self.set_font(self.default_font, "", 7.6)
        self.set_xy(x_margin + 85, section_start_y)
        self.multi_cell(w=0, h=16, text="IE ", align="L")

        self.set_font(self.default_font, "B", 7.6)
        self.set_xy(x_margin + 89, section_start_y)
        self.multi_cell(w=0, h=16, text=f"{self.tomador_ie}", align="L")

        self.set_font(self.default_font, "", 7.6)
        self.set_xy(x_margin + 115, section_start_y)
        self.multi_cell(w=0, h=16, text="PAÍS ", align="L")

        self.set_font(self.default_font, "B", 7.6)
        self.set_xy(x_margin + 122, section_start_y)
        self.multi_cell(w=0, h=16, text=f"{self.tomador_pais}", align="L")

        self.set_font(self.default_font, "", 7.6)
        self.set_xy(x_margin + 150, section_start_y)
        self.multi_cell(w=0, h=16, text="FONE ", align="L")

        self.set_font(self.default_font, "B", 7.6)
        self.set_xy(x_margin + 158, section_start_y)
        self.multi_cell(w=0, h=16, text=f"{self.tomador_fone}", align="L")

        self.set_font(self.default_font, "", 7.6)
        self.set_xy(x_margin + 100, section_start_y)
        self.multi_cell(w=0, h=4, text="MUNICÍPIO ", align="L")

        self.set_font(self.default_font, "B", 7.6)
        self.set_xy(x_margin + 116, section_start_y)
        self.multi_cell(w=0, h=4, text=f"{self.tomador_mun}", align="L")

        self.set_font(self.default_font, "", 7.6)
        self.set_xy(x_margin + 150, section_start_y)
        self.multi_cell(w=0, h=4, text="UF ", align="L")

        self.set_font(self.default_font, "B", 7.6)
        self.set_xy(x_margin + 154, section_start_y)
        self.multi_cell(w=0, h=4, text=f"{self.tomador_uf}", align="L")

        self.set_font(self.default_font, "", 7.6)
        self.set_xy(x_margin + 160, section_start_y)
        self.multi_cell(w=0, h=4, text="CEP ", align="L")

        self.set_font(self.default_font, "B", 7.6)
        self.set_xy(x_margin + 166, section_start_y)
        self.multi_cell(w=0, h=4, text=f"{self.tomador_cep}", align="L")

        section_start_y += 10

        self.rect(
            x=x_margin, y=section_start_y, w=page_width - 0.1 * x_margin, h=10, style=""
        )
        col_width = (page_width - (x_margin - 20)) / 2
        x_line_1 = x_margin - 53 + col_width
        x_line_2 = (x_margin - 53 + 2 * col_width) - 10
        x_line_3 = x_margin - 53 + 3 * col_width
        self.line(
            x1=x_line_1 + 30,
            x2=x_line_1 + 30,
            y1=section_start_y,
            y2=section_start_y + 10,
        )
        self.line(x1=x_line_2, x2=x_line_2, y1=section_start_y, y2=section_start_y + 10)
        self.line(x1=x_line_3, x2=x_line_3, y1=section_start_y, y2=section_start_y + 10)

        self.set_xy(x_margin, section_start_y)
        self.set_font(self.default_font, "", 7)
        self.multi_cell(w=0, h=4, text="PRODUTO PREDOMINANTE", align="L")
        self.set_xy(x_margin, section_start_y)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(w=0, h=14, text=self.inf_carga_nome, align="L")

        self.set_xy(x_line_1 + 30, section_start_y)
        self.set_font(self.default_font, "", 7)
        self.multi_cell(w=0, h=4, text="OUTRAS CARACTERÍSTICAS DA CARGA", align="L")
        self.set_xy(x_line_1 + 30, section_start_y)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(w=0, h=14, text=self.inf_carga_car, align="L")

        self.set_xy(x_line_2, section_start_y)
        self.set_font(self.default_font, "", 7)
        self.multi_cell(w=0, h=4, text="VALOR TOTAL DA MERCADORIA", align="L")
        self.set_xy(x_line_2, section_start_y)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(w=0, h=14, text=f"R$ {self.inf_carga_valor}", align="L")

        section_start_y += 10

        self.rect(
            x=x_margin, y=section_start_y, w=page_width - 0.1 * x_margin, h=10, style=""
        )
        col_width = (page_width - (x_margin + 2)) / 4
        x_line_1 = x_margin - 55 + col_width
        x_line_2 = x_margin - 30 + 2 * col_width
        x_line_3 = x_margin - 40 + 3 * col_width
        x_line_4 = x_margin - 40 + 4 * col_width
        self.line(
            x1=x_line_1 + 34,
            x2=x_line_1 + 34,
            y1=section_start_y,
            y2=section_start_y + 10,
        )
        self.line(x1=x_line_2, x2=x_line_2, y1=section_start_y, y2=section_start_y + 10)
        self.line(x1=x_line_3, x2=x_line_3, y1=section_start_y, y2=section_start_y + 10)
        self.line(x1=x_line_4, x2=x_line_4, y1=section_start_y, y2=section_start_y + 10)

        x_positions = [0, x_line_1 + 34, x_line_2, x_line_3, x_line_4]
        titles = [
            "PESO (Kg)",
            "TP MED /UN. MED",
            "TP MED /UN. MED",
            "CUBAGEM (M³)",
            "QUANTIDADE DE VOLUMES",
        ]

        for i, title in enumerate(titles):
            self.set_xy(self.l_margin + x_positions[i], section_start_y)
            self.set_font(self.default_font, "", 7.6)
            self.multi_cell(w=0, h=4, text=title, align="L")
        section_start_y += 5
        for item in self.inf_carga_list:
            c_unid, tp_media, q_carga = item
            if c_unid == "01" and q_carga > "0":
                value_index = 0
            elif c_unid == "03" and tp_media.strip().upper() == "PARES":
                value_index = 1
            elif c_unid == "00" and q_carga > "0":
                value_index = 2
            elif c_unid == "00" and tp_media in ["M3", "m3"]:
                value_index = 3
            elif c_unid == "03" and q_carga > "0":
                value_index = 4
            else:
                continue

            self.set_xy(self.l_margin + x_positions[value_index], section_start_y)
            self.set_font(self.default_font, "B", 7)
            self.multi_cell(
                w=0, h=4, text=f"{q_carga} {TP_CODIGO_MEDIDA[c_unid]}", align="L"
            )

    def draw_section(self, y, height, text, align="C"):
        self.rect(x=self.l_margin, y=y, w=self.epw - 0.1 * self.l_margin, h=3, style="")
        self.set_xy(x=self.l_margin, y=y + 3)
        self.cell(w=self.epw - 2 * self.l_margin, h=-3, text=text, align=align)
        return y + height

    def _draw_service_fee_value(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw
        self.cst = extract_text(self.imp, "CST")
        self.vbc = format_number(extract_text(self.imp, "vBC"), precision=2)
        self.p_icms = format_number(extract_text(self.imp, "pICMS"), precision=2)
        self.v_icms = format_number(extract_text(self.imp, "vICMS"), precision=2)
        self.v_icms_st = format_number(extract_text(self.imp, "vICMS"), precision=2)
        self.p_red_bc = format_number(extract_text(self.imp, "pRedBC"), precision=2)
        self.rntrc = extract_text(self.inf_modal, "RNTRC")
        self.x_obs = extract_text(self.compl, "compl")
        self.v_tpprest = format_number(
            extract_text(self.v_prest, "vTPrest"), precision=2
        )
        self.v_rec = format_number(extract_text(self.v_prest, "vRec"), precision=2)

        section_start_y = y_margin + 1

        self.set_font(self.default_font, "", 6.5)
        section_start_y = self.draw_section(
            section_start_y, 3, "COMPONENTES DO VALOR DA PRESTAÇÃO DO SERVIÇO"
        )
        self.rect(
            x=x_margin, y=section_start_y, w=page_width - 0.1 * x_margin, h=18, style=""
        )

        col_width = (page_width - 2 * x_margin) / 4
        for i in range(1, 4):
            x_line = x_margin + i * col_width
            self.line(x1=x_line, x2=x_line, y1=section_start_y, y2=section_start_y + 18)

        self.set_font(self.default_font, "", 8)

        # Desenha os títulos "NOME" e "VALOR" para as 3 colunas
        titles = ["NOME", "VALOR"]
        for col in range(3):
            nome_x = x_margin + col * col_width
            valor_x = nome_x + col_width / 2

            # Imprime os títulos
            self.set_xy(nome_x, section_start_y + 2)
            self.cell(w=col_width / 2, h=4, text=titles[0], align="L")
            self.set_xy(valor_x, section_start_y + 2)
            self.cell(w=col_width / 2, h=4, text=titles[1], align="L")

        # Distribuir os componentes em 3 colunas com 3 linhas cada
        col1 = self.comp_list[:3]  # Primeiros 3 componentes
        col2 = self.comp_list[3:6]  # Próximos 3 componentes
        col3 = self.comp_list[6:9]  # Últimos 3 componentes

        # Altura inicial para começo dos dados
        data_y = section_start_y + 6

        # Função auxiliar para imprimir uma coluna de componentes
        def print_column(components, x_start):
            current_y = data_y
            for comp in components:
                self.set_xy(x_start, current_y)
                self.cell(w=col_width / 2, h=4, text=comp[0], align="L")
                self.set_xy(x_start + col_width / 2, current_y)
                self.cell(w=col_width / 2, h=4, text=comp[1], align="L")
                current_y += 4  # Incrementa a posição Y para o próximo item

        # Imprime cada coluna
        print_column(col1, x_margin)  # Primeira coluna
        print_column(col2, x_margin + col_width)  # Segunda coluna
        print_column(col3, x_margin + 2 * col_width)  # Terceira coluna

        self.set_font(self.default_font, "", 8)
        self.set_xy(x_margin + 3 * col_width, section_start_y)
        self.multi_cell(w=col_width, h=4, text="VALOR TOTAL DO SERVIÇO", align="L")
        self.set_font(self.default_font, "B", 8)
        self.set_xy(x_margin + 3 * col_width, section_start_y + 4)
        self.multi_cell(w=col_width, h=4, text=f"R$ {self.v_tpprest}", align="L")

        self.line(
            x1=x_margin + 3 * col_width,
            x2=self.w - self.r_margin - 1,
            y1=section_start_y + 10,
            y2=section_start_y + 10,
        )

        self.set_font(self.default_font, "", 8)
        self.set_xy(x_margin + 3 * col_width, section_start_y + 9)
        self.multi_cell(w=col_width, h=8, text="VALOR TOTAL A RECEBER", align="L")
        self.set_font(self.default_font, "B", 8)
        self.set_xy(x_margin + 3 * col_width, section_start_y + 13)
        self.multi_cell(w=col_width, h=7, text=f"R$ {self.v_rec}", align="L")

        section_start_y += 18

        self.set_font(self.default_font, "", 6.5)
        section_start_y = self.draw_section(
            section_start_y, 18, "INFORMAÇÕES RELATIVAS AO IMPOSTO"
        )
        self.cst_desc = TP_ICMS[extract_text(self.imp, "CST")]
        self.rect(
            x=x_margin,
            y=section_start_y - 15,
            w=page_width - 0.1 * x_margin,
            h=15,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 6
        for i in range(1, 6):
            x_line = x_margin + i * col_width
            self.line(x1=x_line, x2=x_line, y1=section_start_y - 15, y2=section_start_y)

        tax_titles = [
            "SITUAÇÃO TRIBUTÁRIA",
            "BASE DE CALCULO",
            "ALÍQ ICMS",
            "VALOR ICMS",
            "% RED. BC ICMS",
            "ICMS ST",
        ]
        tax_values = [
            f"{self.cst} - {self.cst_desc}",
            f"{self.vbc}",
            f"{self.p_icms}",
            f"{self.v_icms}",
            f"{self.p_red_bc}",
            f"{self.v_icms_st}",
        ]

        for i, (title, value) in enumerate(zip(tax_titles, tax_values)):
            self.set_xy(x_margin + i * col_width, section_start_y - 15)
            self.multi_cell(w=col_width, h=4, text=title, align="L")
            self.set_font(self.default_font, "B", 6)
            self.set_xy(x_margin + i * col_width, section_start_y - 11)
            self.multi_cell(w=col_width, h=4, text=value, align="L")
            self.set_font(self.default_font, "", 6)

    def _draw_documents_obs(self):
        x_margin = self.l_margin
        page_width = self.epw
        self.set_font(self.default_font, "", 7)
        section_start_y = self.get_y() + 7
        section_start_y = self.draw_section(
            section_start_y, 43, "DOCUMENTOS ORIGINÁRIOS"
        )
        self.rect(
            x=x_margin,
            y=section_start_y - 40,
            w=page_width - 0.1 * x_margin,
            h=40,
            style="",
        )
        col_width = (page_width - 2 * x_margin) / 2
        half_col_width = col_width / 3
        x_line_middle = x_margin + col_width

        self.line(
            x1=x_line_middle,
            x2=x_line_middle,
            y1=section_start_y - 40,
            y2=section_start_y,
        )

        self.set_font(self.default_font, "", 6)
        self.set_xy(x_margin, section_start_y - 37)
        self.multi_cell(w=half_col_width, h=0, text="TIPO DOC", align="L")
        self.set_xy(x_margin + half_col_width - 18, section_start_y - 37)
        self.multi_cell(w=half_col_width, h=0, text="CNPJ/CHAVE", align="L")
        self.set_xy(x_margin + 2 * half_col_width, section_start_y - 37)
        self.set_font(self.default_font, "", 5.5)
        self.multi_cell(w=half_col_width, h=0, text="SÉRIE/NRO. DOCUMENTO", align="L")

        self.set_font(self.default_font, "", 6)
        self.set_xy(x_line_middle, section_start_y - 37)
        self.multi_cell(w=half_col_width, h=0, text="TIPO DOC", align="L")
        self.set_xy(x_line_middle + half_col_width - 20, section_start_y - 37)
        self.multi_cell(w=half_col_width, h=0, text="CNPJ/CHAVE", align="L")
        self.set_xy(x_line_middle + 2 * half_col_width, section_start_y - 37)
        self.set_font(self.default_font, "", 5.5)
        self.multi_cell(w=half_col_width, h=0, text="SÉRIE/NRO. DOCUMENTO", align="L")

        y_offset_left = section_start_y - 36
        y_offset_right = section_start_y - 36
        lines_per_block = 12
        self.max_lines_per_page = 24
        current_line_left = 0
        current_line_right = 0
        in_right_block = False

        for index, chave in enumerate(self.inf_doc_list):
            self.page_lines = index
            if self.page_lines >= self.max_lines_per_page:
                break

            if current_line_left == lines_per_block:
                current_line_left = 0
                in_right_block = True
                self.set_xy(x_line_middle, y_offset_right)

            if in_right_block:
                x_start = x_line_middle
                y_offset = y_offset_right
            else:
                x_start = x_margin
                y_offset = y_offset_left

            self.set_xy(x_start, y_offset)
            self.set_font(self.default_font, "B", 6)
            self.multi_cell(w=half_col_width, h=4, text="NFE", align="L")

            self.set_xy(x_start + half_col_width - 20, y_offset)
            self.multi_cell(w=half_col_width + 23, h=4, text=chave, align="L")

            key_nfe_1 = chave[22:25]
            key_nfe_2 = chave[25:34]
            key_nfe_format = f"{key_nfe_1}/{key_nfe_2}"

            self.set_font(self.default_font, "B", 6)
            self.set_xy(x_start + 2 * half_col_width + 3, y_offset)
            self.multi_cell(w=half_col_width, h=4, text=key_nfe_format, align="L")

            y_offset += 3
            if in_right_block:
                current_line_right += 1
                y_offset_right = y_offset
            else:
                current_line_left += 1
                y_offset_left = y_offset

            if (
                not in_right_block
                and current_line_left == 0
                and self.page_lines == lines_per_block
            ):
                y_offset_right = section_start_y - 33

        self.set_font(self.default_font, "", 7)
        text_width = page_width - 0.1 * x_margin
        max_characters = 350
        combined_obs = " ".join(self.obs_dacte_list)
        section_start_y = self.draw_section(section_start_y, 18, "OBSERVAÇÕES")
        initial_y = section_start_y - 15

        self.set_xy(x_margin, initial_y)
        text_to_draw = combined_obs[:max_characters]
        self.remaining_text = combined_obs[max_characters:]
        self.text_exceeds_limit = len(combined_obs) > max_characters

        self.multi_cell(w=text_width, h=3, text=text_to_draw, align="L")
        calculated_height = self.get_y() - initial_y

        rectangle_height = max(calculated_height, 10)
        self.set_xy(x_margin, initial_y)
        self.rect(x=x_margin, y=initial_y, w=text_width, h=rectangle_height)

    def draw_aereo_info(self, config):
        x_margin = self.l_margin
        page_width = self.epw
        self.nOCA = extract_text(self.inf_modal, "nOCA")
        self.CL = extract_text(self.inf_modal, "CL")
        self.cTar = extract_text(self.inf_modal, "cTar")
        self.vTar = format_number(extract_text(self.inf_modal, "vTar"), precision=2)
        self.nMinu = extract_text(self.inf_modal, "nMinu")
        self.cInfManu = TP_MANUSEIO.get(
            extract_text(self.inf_modal, "cInfManu"), "Não Informado"
        )
        self.dPrevAereo = extract_text(self.inf_modal, "dPrevAereo")
        self.xDime = format_xDime(extract_text(self.inf_modal, "xDime"))
        section_start_y = self.get_y() + 7
        section_start_y = self.draw_section(
            section_start_y,
            13,
            "DADOS ESPECÍFICOS DO MODAL AÉREO",
        )
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 4
        for i in range(1, 4):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        self.set_font(self.default_font, "", 6)
        road_titles = [
            "NÚMERO OPERACIONAL AÉREO",
            "CLASSE",
            "CÓDIGO DA TARIFA",
            "VALOR DA TARIFA",
        ]

        road_values = [
            f"{self.nOCA}",
            f"{self.CL}",
            f"{self.cTar}",
            f"R$ {self.vTar}",
        ]

        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        section_start_y = self.get_y() + 10
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 3
        for i in range(1, 3):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        self.set_font(self.default_font, "", 6)
        road_titles = [
            "NÚMERO DA MINUTA",
            "RETIRA",
            "DADOS RELATIVOS A RETIRADA DA CARGA",
        ]

        road_values = [
            f"{self.nMinu}",
            "",
            "",
        ]

        text_y = section_start_y - 12
        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            x_pos = x_margin + i * col_width
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            if i == 1:
                square_size = 3
                self.rect(x=x_pos + 10, y=text_y + 4, w=square_size, h=square_size)
                self.set_xy(x=x_pos + 14, y=text_y + 3.8)
                self.multi_cell(w=10, h=3, text="SIM", border=0, align="L")

                self.rect(x=x_pos + 25, y=text_y + 4, w=square_size, h=square_size)
                self.set_xy(x=x_pos + 29, y=text_y + 3.8)
                self.multi_cell(w=10, h=3, text="NÃO", border=0, align="L")
            self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        section_start_y = self.get_y() + 10
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 3.3
        for i in range(1, 4):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        self.set_font(self.default_font, "", 6)
        road_titles = [
            "CARACTERÍSTICAS ADICIONAL DO SERVIÇO",
            "DATA PREVISTA DA ENTREGA",
            "INFORMAÇÕES DE MANUSEIO",
            "DIMENSÃO",
        ]

        road_values = [
            "",
            f"{self.dPrevAereo}",
            f"{self.cInfManu}",
            f"{self.xDime}",
        ]

        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            if i == 3:
                self.set_font(self.default_font, "B", 6)
            else:
                self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        self.set_font(self.default_font, "", 7)
        section_start_y = self.get_y()
        section_start_y = self.draw_section(
            section_start_y, 3, "USO EXCLUSIVO DO EMISSOR DO CT-E"
        )
        self.set_margins(
            left=config.margins.left,
            top=config.margins.top,
            right=config.margins.right,
        )
        margins_to_height = {
            2: 15,
            3: 14,
            4: 12,
            5: 11,
            6: 8,
            7: 6,
            8: 4,
            9: 2,
            10: 8,
        }
        rect_height = margins_to_height[config.margins.left]

        self.rect(
            x=x_margin,
            y=section_start_y,
            w=page_width - 0.1 * x_margin,
            h=rect_height,
            style="",
        )

    def draw_ferroviario_info(self, config):
        x_margin = self.l_margin
        page_width = self.epw

        self.tpTraf = TP_TRAFICO[extract_text(self.inf_modal, "tpTraf")]
        self.fluxo = extract_text(self.inf_modal, "fluxo")
        self.vFrete = format_number(extract_text(self.inf_modal, "vFrete"), precision=2)
        self.ferrEmi = TP_FERROV_EMITENTE.get(
            extract_text(self.inf_modal, "ferrEmi"), ""
        )
        self.respFat = RESP_FATURAMENTO.get(extract_text(self.inf_modal, "respFat"), "")

        self.inf_ferroviario1 = []
        self.inf_ferroviario2 = []

        for i, ferrov in enumerate(self.ferrov):
            cnpj = extract_text(ferrov, "CNPJ")
            cInt = extract_text(ferrov, "cInt")
            ie = extract_text(ferrov, "IE")
            xNome = extract_text(ferrov, "xNome")

            if xNome:
                if i % 2 == 0:
                    self.inf_ferroviario1.append(
                        {
                            "cnpj": cnpj if cnpj else "00.000.000/0000-00",
                            "cInt": cInt if cInt else " ",
                            "ie": ie if ie else " ",
                            "xNome": xNome if xNome else " ",
                        }
                    )
                else:
                    self.inf_ferroviario2.append(
                        {
                            "cnpj": cnpj if cnpj else "00.000.000/0000-00",
                            "cInt": cInt if cInt else " ",
                            "ie": ie if ie else " ",
                            "xNome": xNome if xNome else " ",
                        }
                    )

        section_start_y = self.get_y() + 7
        section_start_y = self.draw_section(
            section_start_y,
            13,
            "INFORMAÇÕES ESPECÍFICAS DO MODAL FERROVIÁRIO",
        )
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 5
        for i in range(1, 5):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        self.set_font(self.default_font, "", 6)
        road_titles = [
            "TIPO DE TRÁFICO",
            "FLUXO FERROVIÁRIO",
            "VALOR DO FRETE",
            "FERROVIA EMITENTE DO CT-E",
            "FERROVIA DO FATURAMENTO",
        ]

        road_values = [
            f"{self.tpTraf}",
            f"{self.fluxo}",
            f"R$ {self.vFrete}",
            f"{self.ferrEmi}",
            f"{self.respFat}",
        ]

        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        section_start_y = self.get_y()
        section_start_y = self.draw_section(
            section_start_y,
            13,
            "INFORMAÇÕES DAS FERROVIARIAS ENVOLVIDAS",
        )
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 4
        for i in range(1, 4):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        self.set_font(self.default_font, "", 6)
        road_titles = [
            "CNPJ",
            "COD. INTERNO",
            "IE",
            "RAZÃO SOCIAL",
        ]

        if self.inf_ferroviario1:
            ferro1 = self.inf_ferroviario1[0]
        else:
            ferro1 = {
                "cnpj": "00.000.000/0000-00",
                "cInt": " ",
                "ie": " ",
                "xNome": " ",
            }

        road_values = [
            ferro1["cnpj"],
            ferro1["cInt"],
            ferro1["ie"],
            ferro1["xNome"],
        ]

        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        section_start_y = self.get_y() + 10
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 4
        for i in range(1, 4):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        if self.inf_ferroviario2:
            ferro2 = self.inf_ferroviario2[0]
        else:
            ferro2 = {
                "cnpj": "00.000.000/0000-00",
                "cInt": " ",
                "ie": " ",
                "xNome": " ",
            }

        road_values = [
            ferro2["cnpj"],
            ferro2["cInt"],
            ferro2["ie"],
            ferro2["xNome"],
        ]

        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        self.set_font(self.default_font, "", 7)
        section_start_y = self.get_y()
        section_start_y = self.draw_section(
            section_start_y, 3, "USO EXCLUSIVO DO EMISSOR DO CT-E"
        )
        self.set_margins(
            left=config.margins.left,
            top=config.margins.top,
            right=config.margins.right,
        )
        margins_to_height = {
            2: 12,
            3: 11,
            4: 10,
            5: 9,
            6: 8,
            7: 8,
            8: 7,
            9: 6,
            10: 5,
        }
        rect_height = margins_to_height[config.margins.left]

        self.rect(
            x=x_margin,
            y=section_start_y,
            w=page_width - 0.1 * x_margin,
            h=rect_height,
            style="",
        )

    def draw_aquaviario_info(self, config):
        x_margin = self.l_margin
        page_width = self.epw
        self.nLacre = extract_text(self.inf_modal, "nLacre")
        self.nCont = extract_text(self.inf_modal, "nCont")
        self.xNavio = extract_text(self.inf_modal, "xNavio")
        self.vAFRMM = format_number(extract_text(self.inf_modal, "vAFRMM"), precision=2)

        self.balsas = []
        for balsa in self.aquav:
            xBalsa = extract_text(balsa, "xBalsa")
            if xBalsa:
                self.balsas.append(xBalsa)

        section_start_y = self.get_y() + 7
        section_start_y = self.draw_section(
            section_start_y,
            13,
            "INFORMAÇÕES ESPECÍFICAS DO MODAL AQUAVIÁRIO",
        )
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 2
        for i in range(1, 2):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        self.set_font(self.default_font, "", 6)
        road_titles = [
            "LACRE",
            "IDENTIFICAÇÃO DO CONTAINER",
        ]

        road_values = [
            f"{self.nLacre}",
            f"{self.nCont}",
        ]

        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        section_start_y = self.get_y()
        section_start_y = self.draw_section(
            section_start_y,
            13,
            "INFORMAÇÕES ESPECÍFICAS DO MODAL AQUAVIÁRIO",
        )
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 3
        for i in range(1, 3):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        self.set_font(self.default_font, "", 6)
        road_titles = [
            "IDENTIFICAÇÃO DO NAVIO / REBOCADOR",
            "IDENTIFICAÇÃO DA BALSA",
            "VLR DO AFRMM",
        ]

        road_values = [
            f"{self.xNavio}",
            f"{' '.join(self.balsas)}",
            f"R$ {self.vAFRMM}",
        ]

        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            if i == 3:
                self.set_font(self.default_font, "B", 6)
            else:
                self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        self.set_font(self.default_font, "", 7)
        section_start_y = self.get_y()
        section_start_y = self.draw_section(
            section_start_y, 3, "USO EXCLUSIVO DO EMISSOR DO CT-E"
        )
        self.set_margins(
            left=config.margins.left,
            top=config.margins.top,
            right=config.margins.right,
        )
        margins_to_height = {
            2: 18,
            3: 17,
            4: 15,
            5: 14,
            6: 12,
            7: 11,
            8: 10,
            9: 9,
            10: 9,
        }
        rect_height = margins_to_height[config.margins.left]

        self.rect(
            x=x_margin,
            y=section_start_y,
            w=page_width - 0.1 * x_margin,
            h=rect_height,
            style="",
        )

    def draw_multimodal_info(self, config):
        x_margin = self.l_margin
        page_width = self.epw

        self.COTM = extract_text(self.inf_modal, "COTM")
        self.xSeg = extract_text(self.inf_modal, "xSeg")
        self.CNPJ = extract_text(self.inf_modal, "CNPJ")
        self.nApol = extract_text(self.inf_modal, "nApol")
        self.nAver = extract_text(self.inf_modal, "nAver")

        section_start_y = self.get_y() + 7
        section_start_y = self.draw_section(
            section_start_y,
            13,
            "INFORMAÇÕES E ESPECIFICAÇÕES DO TRANSPORTE MULTIMODAL DE CAMADAS",
        )
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 2
        for i in range(1, 2):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        self.set_font(self.default_font, "", 6)
        road_titles = [
            "Nº DO CERTIFICADO DO OPERADOR DE TRANSPORTE MULTIMODAL",
            "INDICADOR NEGOCIÁVEL",
        ]

        road_values = [
            f"{self.COTM}",
            "",
        ]

        text_y = section_start_y - 12
        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            x_pos = x_margin + i * col_width
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            if i == 1:
                square_size = 3
                self.rect(x=x_pos + 10, y=text_y + 4.5, w=square_size, h=square_size)
                self.set_xy(x=x_pos + 13, y=text_y + 4.5)
                self.multi_cell(w=30, h=3, text="NEGOCIÁVEL", border=0, align="L")

                self.rect(x=x_pos + 35, y=text_y + 4.5, w=square_size, h=square_size)
                self.set_xy(x=x_pos + 38, y=text_y + 4.5)
                self.multi_cell(w=30, h=3, text="NÃO NEGOCIÁVEL", border=0, align="L")
            self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        section_start_y = self.get_y() + 10
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 4
        for i in range(1, 4):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        self.set_font(self.default_font, "", 6)
        road_titles = [
            "CNPJ DA SEGURADO",
            "NOME DA SEGURADO",
            "NÚMERO DA APÓLICE",
            "NÚMERO DE AVERBAÇÃO",
        ]

        road_values = [
            f"{self.CNPJ}",
            f"{self.xSeg}",
            f"{self.nApol}",
            f"{self.nAver}",
        ]

        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        self.set_font(self.default_font, "", 7)
        section_start_y = self.get_y()
        section_start_y = self.draw_section(
            section_start_y, 3, "USO EXCLUSIVO DO EMISSOR DO CT-E"
        )
        self.set_margins(
            left=config.margins.left,
            top=config.margins.top,
            right=config.margins.right,
        )
        margins_to_height = {
            2: 21,
            3: 20,
            4: 18,
            5: 17,
            6: 15,
            7: 14,
            8: 13,
            9: 12,
            10: 11,
        }
        rect_height = margins_to_height[config.margins.left]

        self.rect(
            x=x_margin,
            y=section_start_y,
            w=page_width - 0.1 * x_margin,
            h=rect_height,
            style="",
        )

    def draw_dutoviario_info(self, config):
        x_margin = self.l_margin
        page_width = self.epw

        section_start_y = self.get_y() + 7
        section_start_y = self.draw_section(
            section_start_y,
            13,
            "DADOS ESPECÍFICOS DO MODAL DUTOVIÁRIO",
        )
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 5
        for i in range(1, 5):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        self.set_font(self.default_font, "", 6)
        road_titles = [
            "VALOR UNITÁRIO",
            "VALOR DO FRETE",
            "OUTROS",
            "BASE DE CÁLCULO",
            "ALÍQUOTA",
        ]

        road_values = [
            "",
            "",
            "",
            f"{self.vbc}",
            f"{self.p_icms}",
        ]

        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        section_start_y = self.get_y() + 10
        self.rect(
            x=x_margin,
            y=section_start_y - 10,
            w=page_width - 0.1 * x_margin,
            h=6,
            style="",
        )

        col_width = (page_width - 2 * x_margin) / 6
        for i in range(1, 6):
            x_line = x_margin + i * col_width
            self.line(
                x1=x_line,
                x2=x_line,
                y1=section_start_y - 10,
                y2=section_start_y - 4,
            )

        self.set_font(self.default_font, "", 6)
        road_titles = [
            "VALOR DO IMPOSTO",
            "VALOR TOTAL DO FRETE",
            "OBSERVAÇÕES",
            "SÉRIE",
            "NÚMERO",
            "EMITENTE",
        ]

        road_values = [
            "",
            f"R$ {self.v_tpprest}",
            "",
            f"{self.serie_cte}",
            f"{self.nr_dacte}",
            f"{self.emit_name}",
        ]

        for i, (title, value) in enumerate(zip(road_titles, road_values)):
            self.set_xy(x_margin + i * col_width, section_start_y - 10)
            self.multi_cell(w=col_width, h=3, text=title, align="L")
            if i == 5:
                self.set_font(self.default_font, "B", 6)
            else:
                self.set_font(self.default_font, "B", 7)
            self.set_xy(x_margin + i * col_width, section_start_y - 7)
            self.multi_cell(w=col_width, h=3, text=value, align="L")
            self.set_font(self.default_font, "", 6)

        self.set_font(self.default_font, "", 7)
        section_start_y = self.get_y()
        section_start_y = self.draw_section(
            section_start_y, 3, "USO EXCLUSIVO DO EMISSOR DO CT-E"
        )
        self.set_margins(
            left=config.margins.left,
            top=config.margins.top,
            right=config.margins.right,
        )
        margins_to_height = {
            2: 20,
            3: 19,
            4: 17,
            5: 16,
            6: 13,
            7: 11,
            8: 11,
            9: 9,
            10: 8,
        }
        rect_height = margins_to_height[config.margins.left]

        self.rect(
            x=x_margin,
            y=section_start_y,
            w=page_width - 0.1 * x_margin,
            h=rect_height,
            style="",
        )

    def _draw_specific_data(self, config):
        x_margin = self.l_margin
        page_width = self.epw
        self.tp_modal = ModalType(TP_MODAL[extract_text(self.ide, "modal")])
        if self.tp_modal == ModalType.RODOVIARIO:
            section_start_y = self.get_y() + 7
            section_start_y = self.draw_section(
                section_start_y,
                13,
                "DADOS ESPECÍFICOS DO MODAL RODOVIÁRIO - CARGA FRACIONADA",
            )
            self.rect(
                x=x_margin,
                y=section_start_y - 10,
                w=page_width - 0.1 * x_margin,
                h=10,
                style="",
            )

            col_width = (page_width - 2 * x_margin) / 4
            for i in range(1, 4):
                x_line = x_margin + i * col_width
                self.line(
                    x1=x_line, x2=x_line, y1=section_start_y - 10, y2=section_start_y
                )

            self.set_font(self.default_font, "", 7)
            road_titles = [
                "RNTRC DA EMPRESA",
                "CIOT",
                "DATA PREVISTA DE ENTREGA",
                "ESTE CONHECIMENTO DE TRANSPORTE ATENDE"
                "À LEGISLAÇÃO DE TRANSPORTE RODOVIÁRIO EM VIGOR",
            ]

            road_values = [
                f"{self.rntrc}",
                "",
                "",
                "",
            ]

            for i, (title, value) in enumerate(zip(road_titles, road_values)):
                self.set_xy(x_margin + i * col_width, section_start_y - 10)
                self.multi_cell(w=col_width, h=3, text=title, align="L")
                self.set_font(self.default_font, "B", 7)
                self.set_xy(x_margin + i * col_width, section_start_y - 7)
                self.multi_cell(w=col_width, h=3, text=value, align="L")
                self.set_font(self.default_font, "", 6)

            self.set_font(self.default_font, "", 7)
            section_start_y = self.draw_section(
                section_start_y, 18, "USO EXCLUSIVO DO EMISSOR DO CT-E"
            )
            self.set_margins(
                left=config.margins.left,
                top=config.margins.top,
                right=config.margins.right,
            )
            margins_to_height = {
                2: 23,
                3: 22,
                4: 20,
                5: 18,
                6: 16,
                7: 14,
                8: 12,
                9: 10,
                10: 8,
            }
            rect_height = margins_to_height[config.margins.left]

            self.rect(
                x=x_margin,
                y=section_start_y - 15,
                w=page_width - 0.1 * x_margin,
                h=rect_height,
                style="",
            )
        if self.tp_modal == ModalType.AEREO:
            self.draw_aereo_info(config)
        if self.tp_modal == ModalType.AQUAVIARIO:
            self.draw_aquaviario_info(config)
        if self.tp_modal == ModalType.FERROVIARIO:
            self.draw_ferroviario_info(config)
        if self.tp_modal == ModalType.DUTOVIARIO:
            self.draw_dutoviario_info(config)
        if self.tp_modal == ModalType.MULTIMODAL:
            self.draw_multimodal_info(config)

    # Adicionando outra página
    def _add_new_page(self, config):
        x_margin = self.l_margin
        page_width = self.epw
        line_height = 4

        add_new_page = (
            self.page_lines > 0 and self.page_lines % self.max_lines_per_page == 0
        ) or self.text_exceeds_limit

        if add_new_page:
            self.add_page(orientation=self.orientation)
            self._draw_receipt()
            self._draw_header()
        if self.page_lines > 0 and self.page_lines % self.max_lines_per_page == 0:
            section_start_y = self.get_y() + 2.5
            section_start_y = self.draw_section(
                section_start_y, 43, "DOCUMENTOS ORIGINÁRIOS"
            )
            y_offset_left = section_start_y - 33
            y_offset_right = section_start_y - 33
            current_line_left = 0
            current_line_right = 0
            in_right_block = False

            self.set_font(self.default_font, "", 7)
            col_width = (page_width - 2 * x_margin) / 2
            half_col_width = col_width / 3
            x_line_middle = x_margin + col_width

            total_documents = len(self.inf_doc_list) - self.page_lines
            lines_per_column = (total_documents + 1) // 2
            rectangle_height = total_documents * line_height // 2
            self.rect(
                x=x_margin,
                y=section_start_y - 40,
                w=page_width - 0.1 * x_margin,
                h=rectangle_height + 8,
            )
            self.line(
                x1=x_line_middle,
                x2=x_line_middle,
                y1=section_start_y - 40,
                y2=section_start_y - 32 + rectangle_height,
            )

            self.set_font(self.default_font, "", 6)
            self.set_xy(x_margin, section_start_y - 37)
            self.multi_cell(w=half_col_width, h=0, text="TIPO DOC", align="L")
            self.set_xy(x_margin + half_col_width - 18, section_start_y - 37)
            self.multi_cell(w=half_col_width, h=0, text="CNPJ/CHAVE", align="L")
            self.set_xy(x_margin + 2 * half_col_width, section_start_y - 37)
            self.set_font(self.default_font, "", 5.5)
            self.multi_cell(
                w=half_col_width, h=0, text="SÉRIE/NRO. DOCUMENTO", align="L"
            )

            self.set_font(self.default_font, "", 6)
            self.set_xy(x_line_middle, section_start_y - 37)
            self.multi_cell(w=half_col_width, h=0, text="TIPO DOC", align="L")
            self.set_xy(x_line_middle + half_col_width - 20, section_start_y - 37)
            self.multi_cell(w=half_col_width, h=0, text="CNPJ/CHAVE", align="L")
            self.set_xy(x_line_middle + 2 * half_col_width, section_start_y - 37)
            self.set_font(self.default_font, "", 5.5)
            self.multi_cell(
                w=half_col_width, h=0, text="SÉRIE/NRO. DOCUMENTO", align="L"
            )

            for i, chave in enumerate(self.inf_doc_list):
                if i < self.page_lines:
                    continue

                if current_line_left == lines_per_column:
                    current_line_left = 0
                    in_right_block = True
                    self.set_xy(x_line_middle, y_offset_right)

                if in_right_block:
                    x_start = x_line_middle
                    y_offset = y_offset_right
                else:
                    x_start = x_margin
                    y_offset = y_offset_left

                self.set_xy(x_start, y_offset)
                self.set_font(self.default_font, "B", 6)
                self.multi_cell(w=half_col_width, h=line_height, text="NFE", align="L")

                self.set_xy(x_start + half_col_width - 20, y_offset)
                self.multi_cell(
                    w=half_col_width + 23, h=line_height, text=chave, align="L"
                )

                key_nfe_1 = chave[22:25]
                key_nfe_2 = chave[25:34]
                key_nfe_format = f"{key_nfe_1}/{key_nfe_2}"

                self.set_font(self.default_font, "B", 6)
                self.set_xy(x_start + 2 * half_col_width + 5, y_offset)
                self.multi_cell(
                    w=half_col_width, h=line_height, text=key_nfe_format, align="L"
                )

                y_offset += line_height
                if in_right_block:
                    current_line_right += 1
                    y_offset_right = y_offset
                else:
                    current_line_left += 1
                    y_offset_left = y_offset
        if self.text_exceeds_limit:
            section_start_y = self.get_y() + 3
            self.set_font(self.default_font, "", 7)
            text_width = page_width - 0.1 * x_margin
            section_start_y = self.draw_section(section_start_y, 18, "OBSERVAÇÕES")
            initial_y = section_start_y - 15

            self.set_xy(x_margin, initial_y)

            self.multi_cell(w=text_width, h=3, text=self.remaining_text, align="L")

            self.set_xy(x_margin, initial_y)
            self.set_margins(
                left=config.margins.left,
                top=config.margins.top,
                right=config.margins.right,
            )
            margins_to_height = {
                2: 21,
                3: 19,
                4: 16,
                5: 13,
                6: 10,
                7: 7,
                8: 4,
                9: 2,
                10: -2,
            }
            rect_height = margins_to_height[config.margins.left]
            self.rect(
                x=x_margin, y=initial_y, w=text_width, h=section_start_y + rect_height
            )
