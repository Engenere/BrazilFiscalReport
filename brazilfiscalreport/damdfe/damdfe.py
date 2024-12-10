# Copyright (C) 2024 Engenere - Cristiano Mafra Junior

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from io import BytesIO
from xml.etree.ElementTree import Element

from barcode.codex import Code128
from barcode.writer import SVGWriter

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
from .config import DamdfeConfig, EmissionType, ModalType
from .damdfe_conf import (
    TP_AMBIENTE,
    TP_EMISSAO,
    TP_EMITENTE,
    TP_MODAL,
    URL,
)


def extract_text(node: Element, tag: str) -> str:
    return get_tag_text(node, URL, tag)


class Damdfe(xFPDF):
    def __init__(self, xml, config: DamdfeConfig = None):
        super().__init__(unit="mm", format="A4")
        self.config = config if config is not None else DamdfeConfig()
        self.set_margins(
            left=self.config.margins.left,
            top=self.config.margins.top,
            right=self.config.margins.right,
        )
        self.set_auto_page_break(auto=False, margin=self.config.margins.bottom)
        self.set_title("DAMDFE")
        self.logo_image = self.config.logo
        self.default_font = self.config.font_type.value
        self.price_precision = self.config.decimal_config.price_precision
        self.quantity_precision = self.config.decimal_config.quantity_precision

        root = ET.fromstring(xml)
        self.inf_adic = root.find(f"{URL}infAdic")
        self.inf_seg = root.find(f"{URL}infSeg")
        self.disp = root.find(f"{URL}disp")
        self.inf_mdfe = root.find(f"{URL}infMDFe")
        self.prot_mdfe = root.find(f"{URL}protMDFe")
        self.emit = root.find(f"{URL}emit")
        self.ide = root.find(f"{URL}ide")
        self.inf_modal = root.find(f"{URL}infModal")
        self.inf_doc = root.find(f"{URL}infDoc")
        self.inf_mun_descarga = root.find(f"{URL}infMunDescarga")
        self.tot = root.find(f"{URL}tot")
        self.ferrov = root.find(f"{URL}ferrov")
        self.aquav = root.find(f"{URL}aquav")
        self.inf_mdfe_supl = root.find(f"{URL}infMDFeSupl")
        self.key_mdfe = self.inf_mdfe.attrib.get("Id")[4:]
        self.protocol = extract_text(self.prot_mdfe, "nProt")
        self.dh_recebto, self.hr_recebto = get_date_utc(
            extract_text(self.prot_mdfe, "dhRecbto")
        )
        self.tp_emis = extract_text(self.ide, "tpEmis")
        self.add_page(orientation="P")
        self._draw_void_watermark()
        self._draw_contingency_watermark()
        self._draw_header()
        self._draw_body_info()
        self._draw_voucher_information()
        self._draw_insurance_information()

    def _build_chCTe_str(self):
        self.chCTe_str = []
        for chCTe in self.inf_mun_descarga:
            chCTe_value = extract_text(chCTe, "chCTe")
            if chCTe_value:
                self.chCTe_str.append(chCTe_value)
        return self.chCTe_str

    def _build_chnfe_str(self):
        self.chNFe_str = []
        for chnfe in self.inf_mun_descarga:
            chNFe_value = extract_text(chnfe, "chNFe")
            if chNFe_value:
                self.chNFe_str.append(chNFe_value)
        return self.chNFe_str

    def _build_term_carreg_carga(self):
        self.term_carreg_carga = []
        for infTermCarreg in self.aquav:
            cTermCarreg = extract_text(infTermCarreg, "cTermCarreg")
            xTermCarreg = extract_text(infTermCarreg, "xTermCarreg")
            self.term_carreg_carga.append((cTermCarreg, xTermCarreg))
        return self.term_carreg_carga

    def _build_term_descarreg_carga(self):
        self.term_descarreg_carga = []
        for infTermDescarreg in self.aquav:
            cTermDescarreg = extract_text(infTermDescarreg, "cTermDescarreg")
            xTermDescarreg = extract_text(infTermDescarreg, "xTermDescarreg")
            self.term_descarreg_carga.append((cTermDescarreg, xTermDescarreg))
        return self.term_descarreg_carga

    def _build_inf_unid_carga(self):
        self.inf_unid_carga = []
        for infUnidCargaVazia in self.aquav:
            idUnidCargaVazia = extract_text(infUnidCargaVazia, "idUnidCargaVazia")
            tpUnidCargaVazia = extract_text(infUnidCargaVazia, "tpUnidCargaVazia")
            self.inf_unid_carga.append((idUnidCargaVazia, tpUnidCargaVazia))
        return self.inf_unid_carga

    def _build_inf_unid_transp(self):
        self.inf_unid_transp = []
        for infUnidTranspVazia in self.aquav:
            idUnidTranspVazia = extract_text(infUnidTranspVazia, "idUnidTranspVazia")
            tpUnidTranspVazia = extract_text(infUnidTranspVazia, "tpUnidTranspVazia")
            self.inf_unid_transp.append((idUnidTranspVazia, tpUnidTranspVazia))
        return self.inf_unid_transp

    def _build_ferrov_str(self):
        self.ferrov_str = []
        for vag in self.ferrov:
            vag_serie = extract_text(vag, "serie")
            vag_nvag = extract_text(vag, "nVag")
            vag_seq = extract_text(vag, "nSeq")
            vag_tu = extract_text(vag, "TU")
            self.ferrov_str.append((vag_serie, vag_nvag, vag_seq, vag_tu))
        return self.ferrov_str

    def _build_percurso_str(self):
        self.percurso_str = ""
        for per in self.ide:
            self.per = extract_text(per, "UFPer")
            if self.percurso_str:
                self.percurso_str += " / "
            self.percurso_str += self.per
        # Remove a barra extra no final
        if self.percurso_str.endswith(" / "):
            self.percurso_str = self.percurso_str[:-3]
        return self.percurso_str

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

    def _draw_contingency_watermark(self):
        """
        Draw a contingency watermark on the DAMDFE
        """
        tp_emiss = EmissionType(TP_EMISSAO[extract_text(self.ide, "tpEmis")])
        if tp_emiss != EmissionType.CONTINGENCIA:
            return
        self.set_font(self.default_font, "B", 60)
        first_part = "EMISSÃO EM"
        second_part = "CONTINGÊNCIA"
        width = self.get_string_width("CONTINGÊNCIA ")
        self.set_text_color(r=150, g=150, b=150)
        height = 15
        page_width = self.w
        page_height = self.h
        x_center = (page_width - width) / 2
        y_center = (page_height + height) / 2
        with self.rotation(0, x_center + (width / 2), y_center - (height / 2)):
            self.text(x_center + 18, y_center + 5, first_part)
            self.text(x_center + 3, y_center + 23, second_part)
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

    def draw_vertical_lines(self, x_start_positions, y_start, y_end, x_margin):
        """
        Vertical Lines - Method Responsible
        for the vertical lines in the information section of the DAMDFE
        """
        for x in x_start_positions:
            self.line(x1=x_margin + x, y1=y_start, x2=x_margin + x, y2=y_end)

    def draw_aero_info(self, x_margin, y_margin, y_middle, page_width):
        self.draw_vertical_lines_left(
            start_y=y_margin + 22, end_y=y_margin + 26, num_lines=2
        )
        self.nac = extract_text(self.inf_modal, "nac")
        self.matr = extract_text(self.inf_modal, "matr")
        self.n_voo = extract_text(self.inf_modal, "nVoo")
        self.data_voo, self.hr_voo = get_date_utc(extract_text(self.inf_modal, "dVoo"))
        self.aer_embarque = extract_text(self.inf_modal, "cAerEmb")
        self.aer_destino = extract_text(self.inf_modal, "cAerDes")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin - 235, y=y_middle - 2)  # TODO: Bug x_margin
        self.multi_cell(w=100, h=0, text="AERONAVE", border=0, align="C")
        self.set_xy(x=x_margin + 25, y=y_middle - 2)
        self.multi_cell(w=100, h=0, text="VOO", border=0, align="C")
        self.draw_vertical_lines_left(
            start_y=y_margin + 26, end_y=y_margin + 43, num_lines=4
        )

        self.set_xy(x=x_margin, y=y_middle)
        self.multi_cell(w=100, h=3, text="NACIONALIDADE", border=0, align="L")
        self.set_font(self.default_font, "", 7)
        self.set_xy(x=x_margin, y=y_middle + 4)
        self.multi_cell(w=100, h=3, text=self.nac, border=0, align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 25, y=y_middle)
        self.multi_cell(w=100, h=3, text="MATRÍCULA", border=0, align="L")
        self.set_font(self.default_font, "", 7)
        self.set_xy(x=x_margin + 25, y=y_middle + 4)
        self.multi_cell(w=100, h=3, text=self.matr, border=0, align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 50, y=y_middle)
        self.multi_cell(w=100, h=3, text="NÚMERO", border=0, align="L")
        self.set_font(self.default_font, "", 7)
        self.set_xy(x=x_margin + 50, y=y_middle + 4)
        self.multi_cell(w=100, h=3, text=self.n_voo, border=0, align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + 75, y=y_middle)
        self.multi_cell(w=100, h=3, text="DATA", border=0, align="L")
        self.set_font(self.default_font, "", 7)
        self.set_xy(x=x_margin + 75, y=y_middle + 4)
        self.multi_cell(w=100, h=3, text=self.data_voo, border=0, align="L")

        self.set_xy(x=page_width / 2 - 2, y=y_middle - 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(w=100, h=0, text="AERÓDRONO", border=0, align="C")
        y_middle = y_margin + 29
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.draw_vertical_lines_right(
            start_y=y_margin + 26, end_y=y_margin + 43, num_lines=2
        )

        self.set_xy(x=y_middle + 26, y=y_middle - 2.8)
        self.multi_cell(w=100, h=3, text="EMBARQUE", border=0, align="L")
        self.set_font(self.default_font, "", 7)
        self.set_xy(x=y_middle + 26, y=y_middle + 0.5)
        self.multi_cell(w=100, h=3, text=self.aer_embarque, border=0, align="L")

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=y_middle + 76, y=y_middle - 2.8)
        self.multi_cell(w=100, h=3, text="DESTINO", border=0, align="L")
        self.set_font(self.default_font, "", 7)
        self.set_xy(x=y_middle + 76, y=y_middle + 0.5)
        self.multi_cell(w=100, h=3, text=self.aer_destino, border=0, align="L")

    def draw_rodoviario_info(self, x_margin, y_margin, y_middle, page_width):
        self.multi_cell(w=100, h=0, text="VEÍCULOS", border=0, align="C")
        self.draw_vertical_lines_left(
            start_y=y_margin + 26, end_y=y_margin + 43, num_lines=4
        )
        position_dict = {
            5: 25,
            6: 25,
            7: 25,
            8: 24,
            9: 24,
            10: 23,
        }
        position = position_dict.get(self.config.margins.left)
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

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin + position, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="UF",
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=x_margin + position, y=y_middle + 4)
        self.multi_cell(
            w=100,
            h=3,
            text=self.modal_uf,
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "B", 7)
        if self.config.margins.left in [10, 9, 8]:
            self.set_xy(x=x_margin + 24 + position, y=y_middle)
        else:
            self.set_xy(x=x_margin + 25 + position, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="RNTRC",
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        if self.config.margins.left in [10, 9, 8]:
            self.set_xy(x=x_margin + 24 + position, y=y_middle + 4)
        else:
            self.set_xy(x=x_margin + 25 + position, y=y_middle + 4)
        self.multi_cell(
            w=100,
            h=3,
            text=self.rntrc,
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "B", 7)
        if self.config.margins.left in [10, 9, 8]:
            self.set_xy(x=x_margin + 48 + position, y=y_middle)
        else:
            self.set_xy(x=x_margin + 50 + position, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="RENAVAM",
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        if self.config.margins.left in [10, 9, 8]:
            self.set_xy(x=x_margin + 48 + position, y=y_middle + 4)
        else:
            self.set_xy(x=x_margin + 50 + position, y=y_middle + 4)
        self.multi_cell(
            w=100,
            h=3,
            text=self.renavam,
            border=0,
            align="L",
        )

        self.set_xy(x=(page_width / 2) + 6, y=y_middle - 2)
        self.multi_cell(w=100, h=0, text="CONDUTORES", border=0, align="C")
        y_middle = y_margin + 29
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.draw_vertical_lines_right(
            start_y=y_margin + 26, end_y=y_margin + 43, num_lines=2
        )

        position_middle_dict = {
            5: 26,
            6: 25,
            7: 24,
            8: 23,
            9: 22,
            10: 21,
        }
        position_middle = position_middle_dict.get(self.config.margins.left)

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=y_middle + position_middle, y=y_middle - 2.8)
        self.multi_cell(
            w=100,
            h=3,
            text="CPF",
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=y_middle + position_middle, y=y_middle + 0.5)
        self.multi_cell(
            w=100,
            h=3,
            text=self.cpf_condutor,
            border=0,
            align="L",
        )

        position_condutores_dict = {
            5: 76,
            6: 74,
            7: 72,
            8: 71,
            9: 69,
            10: 68,
        }
        position_condutores = position_condutores_dict.get(self.config.margins.left)

        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=y_middle + position_condutores, y=y_middle - 2.8)
        self.multi_cell(
            w=100,
            h=3,
            text="CONDUTORES",
            border=0,
            align="L",
        )

        self.set_font(self.default_font, "", 7)
        self.set_xy(x=y_middle + position_condutores, y=y_middle + 0.5)
        self.multi_cell(
            w=100,
            h=3,
            text=self.nome_condutor,
            border=0,
            align="L",
        )

    def draw_ferroviario_info(self, x_margin, y_margin, y_middle, page_width):
        self._build_ferrov_str()
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin - 210, y=y_middle - 2)  # TODO: Bug x_margin
        self.multi_cell(w=100, h=0, text="INFORMAÇÕES DOS VAGÕES", border=0, align="C")
        self.draw_vertical_lines_left(
            start_y=y_margin + 26, end_y=y_margin + 43, num_lines=4
        )
        self.set_xy(x=x_margin, y=y_middle)
        self.multi_cell(w=100, h=3, text="SÉRIE DE IDENT.", border=0, align="L")

        self.set_xy(x=x_margin + 25, y=y_middle)
        self.multi_cell(w=100, h=3, text="NÚM. IDENT.", border=0, align="L")

        self.set_xy(x=x_margin + 50, y=y_middle)
        self.multi_cell(w=100, h=3, text="SEQ", border=0, align="L")

        self.set_xy(x=x_margin + 75, y=y_middle)
        self.multi_cell(w=100, h=3, text="TON. ÚTIL", border=0, align="L")

        self.set_xy(x=page_width / 2 + 7, y=y_middle - 2)
        self.multi_cell(w=100, h=0, text="INFORMAÇÕES DOS VAGÕES", border=0, align="C")
        y_middle = y_margin + 29
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.draw_vertical_lines_right(
            start_y=y_margin + 26, end_y=y_margin + 43, num_lines=4
        )
        self.set_xy(x=y_middle + 26, y=y_middle - 2.8)
        self.multi_cell(w=100, h=3, text="SÉRIE DE IDENT.", border=0, align="L")

        self.set_xy(x=y_middle + 51, y=y_middle - 2.8)
        self.multi_cell(w=100, h=3, text="NÚM. IDENT.", border=0, align="L")

        self.set_xy(x=y_middle + 76, y=y_middle - 2.8)
        self.multi_cell(w=100, h=3, text="SEQ", border=0, align="L")

        self.set_xy(x=y_middle + 101, y=y_middle - 2.8)
        self.multi_cell(w=100, h=3, text="TON. ÚTIL", border=0, align="L")
        # TODO: Resolver Bug do espaçamento que fica em branco
        y_offset_left = y_middle + 0.5
        line_count = 0
        max_lines_left = 5
        for _, (vag_serie, vag_nvag, vag_seq, vag_tu) in enumerate(self.ferrov_str):
            if line_count >= max_lines_left:
                break

            self.set_font(self.default_font, "", 6.5)

            self.set_xy(x=x_margin, y=y_offset_left)
            self.multi_cell(w=25, h=-3, text=vag_serie, border=0, align="L")

            self.set_xy(x=x_margin + 25, y=y_offset_left)
            self.multi_cell(w=25, h=-3, text=vag_nvag, border=0, align="L")

            self.set_xy(x=x_margin + 50, y=y_offset_left)
            self.multi_cell(w=25, h=-3, text=vag_seq, border=0, align="L")

            self.set_xy(x=x_margin + 75, y=y_offset_left)
            self.multi_cell(w=25, h=-3, text=vag_tu, border=0, align="L")

            y_offset_left += 3
            line_count += 1
        if line_count < len(self.ferrov_str):
            y_offset_right = y_middle + 0.5
            remaining_lines = self.ferrov_str[line_count:]
            max_lines_rigth = 4
            line_count = 0
            for _, (vag_serie, vag_nvag, vag_seq, vag_tu) in enumerate(remaining_lines):
                if line_count >= max_lines_rigth:
                    break

                self.set_font(self.default_font, "", 6.5)

                self.set_xy(x=x_margin + 120, y=y_offset_right)
                self.multi_cell(w=25, h=2, text=vag_serie, border=0, align="L")

                self.set_xy(x=x_margin + 145, y=y_offset_right)
                self.multi_cell(w=25, h=2, text=vag_nvag, border=0, align="L")

                self.set_xy(x=x_margin + 170, y=y_offset_right)
                self.multi_cell(w=25, h=2, text=vag_seq, border=0, align="L")

                self.set_xy(x=x_margin + 195, y=y_offset_right)
                self.multi_cell(w=25, h=2, text=vag_tu, border=0, align="L")
                y_offset_right += 3
                line_count += 1

    def draw_aquaviario_info(self, x_margin, y_margin, y_middle, page_width):
        self._build_term_carreg_carga()
        self._build_term_descarreg_carga()
        self.set_font(self.default_font, "B", 7)
        self.set_xy(x=x_margin - 245, y=y_middle - 2)
        self.multi_cell(w=100, h=0, text="DADOS DO TERMINAL", border=0, align="C")

        self.set_xy(x=x_margin, y=y_middle)
        self.multi_cell(w=100, h=3, text="CARREGAMENTO", border=0, align="L")

        self.set_xy(x=page_width / 2 - 2, y=y_middle - 2)
        y_middle = y_margin + 29
        self.set_xy(x=page_width / 2 + 5, y=y_middle - 6)
        self.multi_cell(w=100, h=3, text="DADOS DO TERMINAL", border=0, align="L")

        self.set_xy(x=page_width / 2 + 5, y=y_middle - 3)
        self.multi_cell(w=100, h=3, text="DESCARREGAMENTO", border=0, align="L")

        # TODO: BUG DE ESPAÇAMENTO VÊ COMO CORRIGIR ISSO
        y = 78.5
        for _, (cTermCarreg, xTermCarreg) in enumerate(self.term_carreg_carga):
            self.set_font(self.default_font, "", 6.5)
            self.set_xy(x=x_margin, y=y)
            self.multi_cell(w=100, h=-26, text=cTermCarreg, border=0, align="L")

            self.set_xy(x=x_margin + 25, y=y)
            self.multi_cell(w=100, h=-26, text=xTermCarreg, border=0, align="L")
            y += 2
        y_2 = 47.5
        for _, (cTermDescarreg, xTermDescarreg) in enumerate(self.term_descarreg_carga):
            self.set_font(self.default_font, "", 6.5)
            self.set_xy(x=page_width / 2 + 5, y=y_2 + 14)
            self.multi_cell(w=100, h=4, text=cTermDescarreg, border=0, align="L")

            self.set_xy(x=page_width / 2 + 25, y=y_2 + 14)
            self.multi_cell(w=100, h=4, text=xTermDescarreg, border=0, align="L")
            y_2 += 2

    def _draw_header(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        self.model = extract_text(self.ide, "mod")
        self.serie = extract_text(self.ide, "serie")
        self.n_mdf = extract_text(self.ide, "nMDF")
        self.dt, self.hr = get_date_utc(extract_text(self.ide, "dhEmi"))
        self.emission_datetime = datetime.strptime(
            f"{self.dt} {self.hr}", "%d/%m/%Y %H:%M:%S"
        )
        deadline_datetime = self.emission_datetime + timedelta(hours=168)
        self.formatted_deadline = deadline_datetime.strftime("%d/%m/%Y %H:%M")
        self.uf_carreg = extract_text(self.ide, "UFIni")
        self.uf_descarreg = extract_text(self.ide, "UFFim")
        self.tp_emi = TP_EMISSAO[extract_text(self.ide, "tpEmis")]
        self.dt_inicio, self.hr_inicio = get_date_utc(
            extract_text(self.ide, "dhIniViagem")
        )
        self.tp_emit = TP_EMITENTE[extract_text(self.ide, "tpEmit")]
        self.tp_emit_chave = extract_text(self.ide, "tpEmit")
        self.tp_amb = TP_AMBIENTE[extract_text(self.ide, "tpAmb")]

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
        self.line(x_margin, y_middle, x_middle, y_middle)  # Aqui
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
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
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
        qr_code = extract_text(self.inf_mdfe_supl, "qrCodMDFe")

        num_x = 140
        num_y = 1
        draw_qr_code(self, qr_code, 0, num_x, num_y, box_size=25, border=3)

        svg_img_bytes = BytesIO()
        w_options = {
            "module_width": 0.3,
        }
        Code128(self.key_mdfe, writer=SVGWriter()).write(
            fp=svg_img_bytes,
            options=w_options,
            text="",
        )
        self.set_font(self.default_font, "", 6.5)
        self.set_xy(x=x_margin + 100, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text="CONTROLE DO FISCO",
            border=0,
            align="L",
        )
        margins_offset = {1: 8, 2: 8, 3: 7, 4: 7, 5: 6, 6: 6, 7: 5.5, 8: 5, 9: 4, 10: 4}
        x_offset = margins_offset.get(self.config.margins.right)
        self.image(
            svg_img_bytes, x=x_middle + x_offset, y=self.t_margin + 32, w=86.18, h=17.0
        )

        self.set_font(self.default_font, "", 6.5)
        self.set_xy(x=x_middle + 25, y=y_middle + 23)
        self.multi_cell(
            w=100,
            h=3,
            text="Consulta em https://dfe-portal.svrs.rs.gov.br/MDFE/Consulta",
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
        if self.tp_emis == "1":
            self.set_xy(x=x_middle + 32, y=y_middle + 35)
            self.multi_cell(
                w=100,
                h=3,
                text=f"{self.protocol} {self.dh_recebto} {self.hr_recebto}",
                border=0,
                align="L",
            )
        else:
            self.set_xy(x=x_middle + 22, y=y_middle + 34)
            self.multi_cell(
                w=100,
                h=3,
                text="EMISSÃO EM CONTINGÊNCIA. Obrigatória a autorização em",
                border=0,
                align="L",
            )
            self.set_xy(x=x_middle + 26, y=y_middle + 36)
            self.multi_cell(
                w=100,
                h=3,
                text=f"168 horas após esta emissão ({self.formatted_deadline})",
                border=0,
                align="L",
            )

        y_middle = y_margin + 35
        self.line(x_margin, y_middle, x_middle, y_middle)
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
        if self.tp_emit_chave == "3":
            self.set_xy(x=x_margin, y=y_middle + 3)
            self.multi_cell(
                w=100,
                h=2,
                text="PRESTADOR DE SERVIÇO DE TRANSPORTE",
                border=0,
                align="L",
            )
            self.set_xy(x=x_margin + 3.5, y=y_middle + 6)
            self.multi_cell(
                w=100,
                h=2,
                text="TRANSPORTE (CT-e GLOBALIZADO)",
                border=0,
                align="L",
            )
        else:
            self.set_xy(x=x_margin, y=y_middle + 3)
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

    def _draw_body_info(self):
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
            start_y=y_margin + 15, end_y=y_margin + 22, num_lines=4
        )
        self.qtd_nfe = extract_text(self.tot, "qNFe")
        self.qtd_cte = extract_text(self.tot, "qCTe")
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

        self.set_xy(x=x_margin, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.qtd_cte,
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
        self.tp_modal = ModalType(TP_MODAL[extract_text(self.ide, "modal")])

        if self.tp_modal == ModalType.RODOVIARIO:
            self.draw_rodoviario_info(x_margin, y_margin, y_middle, page_width)

        if self.tp_modal == ModalType.AEREO:
            self.draw_aero_info(x_margin, y_margin, y_middle, page_width)

        if self.tp_modal == ModalType.FERROVIARIO:
            self.draw_ferroviario_info(x_margin, y_margin, y_middle, page_width)

        if self.tp_modal == ModalType.AQUAVIARIO:
            self.draw_aquaviario_info(x_margin, y_margin, y_middle, page_width)

        y_middle = y_margin + 60
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)

    def _draw_voucher_information(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        self.mun_descarregamento = extract_text(self.inf_doc, "xMunDescarga")
        self.cnpj_forn = extract_text(self.inf_modal, "CNPJForn")
        self.cnpj_pag = extract_text(self.inf_modal, "CNPJPg")
        self.num_comra = extract_text(self.inf_modal, "nCompra")
        self.valor_pedagio = format_number(
            extract_text(self.inf_modal, "vValePed"), precision=2
        )

        if self.tp_modal == ModalType.RODOVIARIO:
            self.rect(x=x_margin, y=y_margin + 10.5, w=page_width - 0.5, h=30, style="")
            y_middle = y_margin + 14.5
            self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
            self.set_xy(x=(page_width - 40) / 2, y=y_middle - 2)
            self.set_font(self.default_font, "B", 7)
            self.multi_cell(
                w=100, h=0, text="INFORMAÇÕES DE VALE PEDÁGIO", border=0, align="L"
            )
            self.draw_vertical_lines_left(
                start_y=y_margin + 14.5, end_y=y_margin + 18.5, num_lines=2
            )
            self.draw_vertical_lines_right(
                start_y=y_margin + 14.5, end_y=y_margin + 18.5, num_lines=2
            )

            position_rodoviario_dict = {
                5: 59,
                6: 58,
                7: 57,
                8: 57,
                9: 55,
                10: 55,
            }
            position_rodoviario = position_rodoviario_dict.get(self.config.margins.left)

            # Informações de Vale Pedágio
            # CPF
            self.set_font(self.default_font, "B", 6.5)
            self.set_xy(x=x_margin + 12, y=y_middle + 1)
            self.multi_cell(
                w=100,
                h=3,
                text="CNPJ DA FORNECEDORA",
                border=0,
                align="L",
            )
            self.set_font(self.default_font, "", 6.5)
            self.set_xy(x=x_margin + 17, y=y_middle + 5)
            self.multi_cell(
                w=100,
                h=3,
                text=self.cnpj_forn,
                border=0,
                align="L",
            )

            # CPF/CNPJ DO RESPONSÁVEL
            self.set_font(self.default_font, "B", 6.5)
            self.set_xy(x=x_margin + position_rodoviario, y=y_middle + 1)
            self.multi_cell(
                w=100,
                h=3,
                text="CPF/CNPJ DO RESPONSÁVEL",
                border=0,
                align="L",
            )
            self.set_font(self.default_font, "", 6.5)
            self.set_xy(x=x_margin + position_rodoviario + 7, y=y_middle + 5)
            self.multi_cell(
                w=100,
                h=3,
                text=self.cnpj_pag,
                border=0,
                align="L",
            )

            position_rodoviario_middle_dict = {
                5: 15,
                6: 15,
                7: 14,
                8: 14,
                9: 11,
                10: 11,
            }
            position__middle_rodoviario = position_rodoviario_middle_dict.get(
                self.config.margins.left
            )

            # NÚMERO DO COMPROVANTE
            self.set_font(self.default_font, "B", 6.5)
            self.set_xy(x=y_middle + position__middle_rodoviario, y=y_middle + 1)
            self.multi_cell(
                w=100,
                h=3,
                text="NÚMERO DO COMPROVANTE",
                border=0,
                align="L",
            )

            self.set_font(self.default_font, "", 6.5)
            self.set_xy(x=y_middle + position__middle_rodoviario + 6, y=y_middle + 5)
            self.multi_cell(
                w=100,
                h=3,
                text=self.num_comra,
                border=0,
                align="L",
            )

            position_vale_pedagio_middle_dict = {
                5: 67,
                6: 67,
                7: 65,
                8: 65,
                9: 60,
                10: 58,
            }
            position__vale_pedagio_rodoviario = position_vale_pedagio_middle_dict.get(
                self.config.margins.left
            )

            # VALOR DO VALE-PEDÁGIO
            self.set_font(self.default_font, "B", 6.5)
            self.set_xy(x=y_middle + position__vale_pedagio_rodoviario, y=y_middle + 1)
            self.multi_cell(
                w=100,
                h=3,
                text="VALOR DO VALE-PEDÁGIO",
                border=0,
                align="L",
            )

            self.set_font(self.default_font, "", 6.5)
            self.set_xy(
                x=y_middle + position__vale_pedagio_rodoviario + 8, y=y_middle + 5
            )
            if self.valor_pedagio >= "1":
                self.multi_cell(
                    w=100,
                    h=3,
                    text=f"R$ {self.valor_pedagio}",
                    border=0,
                    align="L",
                )

            y_middle = y_margin + 18.5
            self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        elif self.tp_modal == ModalType.AQUAVIARIO:
            self._build_inf_unid_carga()
            self._build_inf_unid_transp()
            self.rect(x=x_margin, y=y_margin + 7.5, w=page_width - 0.5, h=33, style="")
            y_middle = y_margin + 11.5
            self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
            self.set_xy(x=(page_width - 50) / 2, y=y_middle - 2)
            self.set_font(self.default_font, "B", 7)
            self.multi_cell(
                w=100,
                h=0,
                text="INFORMAÇÕES DA COMPOSIÇÃO DA CARGA",
                border=0,
                align="L",
            )
            self.draw_vertical_lines_left(
                start_y=y_margin + 11.5, end_y=y_margin + 24.5, num_lines=2
            )
            self.draw_vertical_lines_right(
                start_y=y_margin + 11.5, end_y=y_margin + 24.5, num_lines=2
            )

            # UNIDADE DE TRANSPORTE
            self.set_font(self.default_font, "B", 6)
            self.set_xy(x=x_margin + 12, y=y_middle + 1)
            self.multi_cell(
                w=100,
                h=3,
                text="UNIDADE DE TRANSPORTE",
                border=0,
                align="L",
            )

            # UNIDADE DE CARGA
            self.set_xy(x=x_margin + 59, y=y_middle + 1)
            self.multi_cell(
                w=100,
                h=3,
                text="UNIDADE DE CARGA",
                border=0,
                align="L",
            )

            # UNIDADE DE TRANSPORTE
            self.set_xy(x=y_middle + 15, y=y_middle + 1)
            self.multi_cell(
                w=100,
                h=3,
                text="UNIDADE DE TRANSPORTE",
                border=0,
                align="L",
            )

            # UNIDADE DE CARGA
            self.set_xy(x=y_middle + 67, y=y_middle + 1)
            self.multi_cell(
                w=100,
                h=3,
                text="UNIDADE DE CARGA",
                border=0,
                align="L",
            )
            for idx, (idUnidTransp, tpUnidTransp) in enumerate(self.inf_unid_transp):
                y_offset = 83 + idx
                self.set_xy(x=x_margin, y=y_offset + 8)
                self.multi_cell(
                    w=100,
                    h=3,
                    text=idUnidTransp,
                    border=0,
                    align="L",
                )
                self.set_xy(x=x_margin + 50, y=y_offset + 8)
                self.multi_cell(
                    w=100,
                    h=3,
                    text=tpUnidTransp,
                    border=0,
                    align="L",
                )
            for idx, (idUnidCarga, tpUnidCarga) in enumerate(self.inf_unid_carga):
                y_offset = 84 + idx
                self.set_xy(x=x_margin + 100, y=y_offset + 8)
                self.multi_cell(
                    w=100,
                    h=3,
                    text=idUnidCarga,
                    border=0,
                    align="L",
                )
                self.set_xy(x=x_margin + 150, y=y_offset + 8)
                self.multi_cell(
                    w=100,
                    h=3,
                    text=tpUnidCarga,
                    border=0,
                    align="L",
                )

            y_middle = y_margin + 15.5
            self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        else:
            self.rect(x=x_margin, y=y_margin + 10.5, w=page_width - 0.5, h=21, style="")
        y_middle = (
            y_margin + 31.5
            if self.tp_modal == ModalType.RODOVIARIO
            or self.tp_modal == ModalType.AQUAVIARIO
            else y_margin + 15.5
        )
        self.set_font(self.default_font, "B", 7)
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=(page_width - 18) / 2, y=y_middle - 2)
        self.multi_cell(w=100, h=0, text="PERCURSO", border=0, align="L")
        self.set_xy(x=x_margin, y=y_middle + 1.5)
        self.set_font(self.default_font, "", 6.5)
        self.percurso_str = self._build_percurso_str()
        self.multi_cell(w=100, h=0, text=self.percurso_str, border=0, align="L")

        y_middle = (
            y_margin + 35.5
            if self.tp_modal == ModalType.RODOVIARIO
            or self.tp_modal == ModalType.AQUAVIARIO
            else y_margin + 19.5
        )
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)

        y_middle = (
            y_margin + 40.5
            if self.tp_modal == ModalType.RODOVIARIO
            or self.tp_modal == ModalType.AQUAVIARIO
            else y_margin + 23.5
        )
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=(page_width - 50) / 2, y=y_middle - 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(
            w=100, h=0, text="INFORMAÇÕES DA COMPOSIÇÃO DA CARGA", border=0, align="L"
        )
        self.draw_vertical_lines(
            x_start_positions=[30, 92, 125],
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
        self.set_xy(x=x_margin + 125, y=y_middle + 1)
        self.multi_cell(
            w=100,
            h=3,
            text="INFORMAÇÕES DOS DOCS. FISCAIS VINCULADOS AO MANIFESTO",
            border=0,
            align="L",
        )
        current_y = y_middle + 4
        current_x_left = x_margin
        line_height = 4
        num_lines = 0
        self.chNFe_str = self._build_chnfe_str()
        self.chCTe_str = self._build_chCTe_str()
        num_lines = 0
        if (
            self.tp_modal == ModalType.RODOVIARIO
            or self.tp_modal == ModalType.AQUAVIARIO
        ):
            current_y = y_margin + 44.5
            self.rect(x=x_margin, y=y_margin + 40.5, w=page_width - 0.5, h=4, style="")
        else:
            current_y = y_margin + 27.5
        content_height = 0
        if self.chNFe_str:
            for i in range(0, len(self.chNFe_str), 2):
                self.set_xy(x=current_x_left, y=current_y)
                self.multi_cell(
                    w=211,
                    h=line_height,
                    text=self.mun_descarregamento,
                    border=0,
                    align="L",
                )
                self.set_xy(x=current_x_left + 30, y=current_y)
                self.multi_cell(
                    w=211,
                    h=line_height,
                    text=self.chNFe_str[i],
                    border=0,
                    align="L",
                )
                if i + 1 < len(self.chNFe_str):
                    self.set_xy(x=x_margin + 92, y=current_y)
                    self.multi_cell(
                        w=211,
                        h=line_height,
                        text=self.mun_descarregamento,
                        border=0,
                        align="L",
                    )
                    self.set_xy(x=x_margin + 125, y=current_y)
                    self.multi_cell(
                        w=211,
                        h=line_height,
                        text=self.chNFe_str[i + 1],
                        border=0,
                        align="L",
                    )
                num_lines += 1 if i + 1 >= len(self.chNFe_str) else 2
                current_y += line_height
                content_height += line_height
        elif self.chCTe_str:
            for i in range(0, len(self.chCTe_str), 2):
                self.set_xy(x=current_x_left, y=current_y)
                self.multi_cell(
                    w=211,
                    h=line_height,
                    text=self.mun_descarregamento,
                    border=0,
                    align="L",
                )
                self.set_xy(x=current_x_left + 30, y=current_y)
                self.multi_cell(
                    w=211,
                    h=line_height,
                    text=self.chCTe_str[i],
                    border=0,
                    align="L",
                )
                if i + 1 < len(self.chCTe_str):
                    self.set_xy(x=x_margin + 92, y=current_y)
                    self.multi_cell(
                        w=211,
                        h=line_height,
                        text=self.mun_descarregamento,
                        border=0,
                        align="L",
                    )
                    self.set_xy(x=x_margin + 125, y=current_y)
                    self.multi_cell(
                        w=211,
                        h=line_height,
                        text=self.chCTe_str[i + 1],
                        border=0,
                        align="L",
                    )
                num_lines += 1 if i + 1 >= len(self.chCTe_str) else 2
                current_y += line_height
                content_height += line_height
        if content_height > 0:
            if (
                self.tp_modal == ModalType.RODOVIARIO
                or self.tp_modal == ModalType.AQUAVIARIO
            ):
                rect_y_start = y_margin + 44.5
            else:
                rect_y_start = y_margin + 27.5
            rect_height = content_height
            self.rect(
                x=x_margin,
                y=rect_y_start,
                w=page_width - 0.5,
                h=rect_height,
                style="",
            )

    def _draw_insurance_information(self):
        x_margin = self.l_margin
        y_margin = self.y
        page_width = self.epw

        self.fisco = extract_text(self.inf_adic, "infAdFisco")
        self.obs = extract_text(self.inf_adic, "infCl")
        self.seguradora_nome = extract_text(self.inf_seg, "xSeg")
        self.cnpj_segurado = extract_text(self.inf_seg, "CNPJ")
        self.n_apol = extract_text(self.inf_seg, "nApol")
        self.nome_averbacao = extract_text(self.inf_seg, "nAver")

        self.rect(
            x=x_margin,
            y=y_margin,
            w=page_width - 0.5,
            h=44,
            style="",
        )
        y_middle = y_margin + 8
        self.line(x_margin, y_middle - 4, x_margin + page_width - 0.5, y_middle - 4)
        self.set_xy(x=(page_width - 45) / 2, y=y_middle - 6)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(
            w=100, h=0, text="INFORMAÇÕES SOBRE OS SEGUROS", border=0, align="L"
        )
        self.set_font(self.default_font, "", 6)
        self.set_xy(x=x_margin, y=y_middle)
        if self.seguradora_nome:
            self.multi_cell(
                w=100,
                h=0,
                text=f"NOME: {self.seguradora_nome}  CNPJ: {self.cnpj_segurado}",
                border=0,
                align="L",
            )
        self.set_xy(x=x_margin, y=y_middle + 4)
        if self.n_apol:
            self.multi_cell(
                w=100,
                h=0,
                text=f"APÓLICE: {self.n_apol}  AVERBAÇÃO: {self.nome_averbacao}",
                border=0,
                align="L",
            )

        self.rect(
            x=x_margin,
            y=y_margin + 40,
            w=page_width - 0.5,
            h=45,
            style="",
        )
        y_middle = y_margin + 44
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=(page_width - 80) / 2, y=y_middle - 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(
            w=100,
            h=0,
            text="INFORMAÇÕES COMPLEMENTARES DE INTERESSE DO CONTRIBUINTE",
            border=0,
            align="L",
        )
        self.set_font(self.default_font, "", 6)
        self.set_xy(x=x_margin, y=y_middle + 3)
        self.multi_cell(
            w=100,
            h=3,
            text=self.obs,
            border=0,
            align="L",
        )

        self.rect(
            x=x_margin,
            y=y_margin + 85,
            w=page_width - 0.5,
            h=45,
            style="",
        )
        y_middle = y_margin + 90
        self.line(x_margin, y_middle, x_margin + page_width - 0.5, y_middle)
        self.set_xy(x=(page_width - 65) / 2, y=y_middle - 2)
        self.set_font(self.default_font, "B", 7)
        self.multi_cell(
            w=100,
            h=0,
            text="INFORMAÇÕES ADICIONAIS DE INTERESSE DO FISCO",
            border=0,
            align="L",
        )
        self.set_font(self.default_font, "", 6)
        self.set_xy(x=x_margin, y=y_middle)
        self.multi_cell(
            w=100,
            h=3,
            text=self.fisco,
            border=0,
            align="L",
        )
