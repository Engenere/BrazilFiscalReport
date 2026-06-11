"""
DanfseRenderer / Danfse — camada de desenho (FPDF2) do DANFSe v2.0.

Port REFATORADO dos métodos _draw_* do código original. A principal melhoria
é o helper ``_field()``, que substitui o padrão repetitivo do original
(set_font label -> set_xy -> cell -> set_font value -> set_xy -> cell) por
uma única chamada. Isso elimina ~70% das linhas e centraliza a tipografia
da NT 008 (via fonts.NT008Fonts).

Conformidade NT 008:
    - Fontes: Arial (labels) / MS Sans Serif (valores) — ver fonts.py.
    - Sombreamento cinza 5% em cabeçalho, títulos de bloco e campos
      "Emitente" e "Valor Líquido + IBS/CBS".
    - QR Code 1,52x1,52cm.
    - Marca d'água de homologação / cancelamento.
    - Borda da página 1pt, divisórias 0,5pt.
"""

from __future__ import annotations

import io
import os
import xml.etree.ElementTree as ET

import qrcode

from ..xfpdf import xFPDF
from .config import DanfseConfig
from .fonts import COLOR_SHADING, NT008Fonts
from .parser import DanfseParser


class Danfse(xFPDF):
    def __init__(self, xml: str | bytes, config: DanfseConfig | None = None):
        super().__init__(unit="mm", format="A4")
        self.config = config or DanfseConfig()

        self.set_margins(
            left=self.config.margins.left,
            top=self.config.margins.top,
            right=self.config.margins.right,
        )
        self.set_auto_page_break(auto=False, margin=self.config.margins.bottom)
        self.set_title("DANFSE")

        # Tipografia NT 008 (resolve família dos valores com fallback).
        self._nt_fonts = NT008Fonts(
            self,
            custom_font_path=self.config.custom_font_path,
            custom_font_name=self.config.custom_font_name,
        )
        self.default_font = self._nt_fonts.value_family

        self.price_precision = self.config.decimal_config.price_precision
        self.watermark_cancelled = self.config.watermark_cancelled

        # Parse.
        self.root = ET.fromstring(xml)
        self.data = DanfseParser(xml, self.config).parse()

        # Render pipeline.
        self.add_page("P")
        self._draw_void_watermark()
        self._draw_header()
        self._draw_issuer()
        self._draw_taker()
        self._draw_service_provided()
        self._draw_taxes()
        self._draw_amount()
        self._draw_complementary_info()
        if self.config.show_receipt:
            self._draw_canhoto()

        # Borda final da página (1pt).
        self.page_border(x=self.l_margin, y=self.t_margin, w=self.epw, h=self.eph)

    # ======================================================================
    # Helpers de layout
    # ======================================================================

    def _field(
        self, x, y, w, label, value, label_size=6, value_size=8, value_limit=None
    ):
        """Desenha um par rótulo+valor numa célula.

        - label: Arial (helvetica) bold, em cima.
        - value: MS Sans Serif (fallback), logo abaixo na mesma origem.
        - value_limit (mm): se informado, trunca o valor via long_field.
        """
        # Rótulo
        self._nt_fonts.apply(self._nt_fonts.label(label_size))
        self.set_xy(x=x, y=y)
        self.cell(w=w, h=2, text=label, align="L")
        # Valor
        self._nt_fonts.apply(self._nt_fonts.value(value_size))
        text = value if value is not None else "-"
        if value_limit:
            text = self.long_field(text=str(text), limit=value_limit) or text
        self.set_xy(x=x, y=y)
        self.cell(w=w, h=7, text=str(text), align="L")

    def _block_title(self, x, y, text, shaded=True, col_width=None, size=8):
        """Título de bloco (Arial bold) com faixa cinza opcional.

        size: 8pt para blocos largos; 6pt para títulos longos das seções de
        tributos (evita transbordar a coluna, como no código original).
        """
        cw = col_width if col_width is not None else self.epw / 4
        if shaded:
            self.shade_rect(x=self.l_margin + 0.5, y=y - 1.5, w=cw, h=4)
        from .fonts import FontSpec

        self._nt_fonts.apply(FontSpec(self._nt_fonts.LABEL_FAMILY, "B", size))
        self.set_xy(x=x, y=y)
        self.cell(w=cw, h=1, text=text, align="L")

    @property
    def _cols(self):
        """Largura de uma coluna do grid de 4 colunas."""
        return self.epw / 4

    # -- helpers visuais NT 008 (mantidos na classe, não no xFPDF
    #    compartilhado, para não impactar NFe/CTe/MDFe) ------------------

    def shade_rect(self, x, y, w, h):
        """Preenche um retângulo com o cinza 5% da NT 008."""
        self.set_fill_color(*COLOR_SHADING)
        self.rect(x=x, y=y, w=w, h=h, style="F")

    def divider(self, x1, y, x2):
        """Linha divisória de bloco (0,5pt)."""
        self.set_line_width(0.5 * 0.3528)
        self.set_dash_pattern(dash=0, gap=0)
        self.line(x1=x1, y1=y, x2=x2, y2=y)

    def page_border(self, x, y, w, h):
        """Borda externa da página (1pt)."""
        self.set_line_width(1.0 * 0.3528)
        self.set_dash_pattern(dash=0, gap=0)
        self.rect(x=x, y=y, w=w, h=h)
        self.set_line_width(0.5 * 0.3528)

    def _draw_qr(self, data, x, y, size_mm=15.2):
        """Desenha o QR Code no tamanho fixo da NT 008 (1,52x1,52 cm).

        Renderizado localmente (não via generate_qrcode compartilhado, cuja
        assinatura usa box_size como dimensão e não garante 1,52 cm exatos).
        """
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        self.image(buffer, x=x, y=y, w=size_mm, h=size_mm)

    # ======================================================================
    # 0. Marca d'água
    # ======================================================================

    def _draw_void_watermark(self):
        """Marca d'água de situação (NT 008).

        A NT 008 exige, para NFS-e cancelada ou substituída, marca d'água
        DIAGONAL com o texto "CANCELADA" / "SUBSTITUÍDA", fonte Arial,
        tamanho MÍNIMO 50pt e cor CINZA.

        A situação é detectada pelo cStat do XML (101=Cancelada,
        102=Substituída); ``config.watermark_cancelled`` força "CANCELADA".

        Obs.: o aviso de homologação ("NFS-e SEM VALIDADE JURÍDICA") é
        tratado no cabeçalho (texto vermelho), não como marca d'água.
        """
        if self.data.get("is_replaced"):
            text = "SUBSTITUÍDA"
        elif self.data.get("is_cancelled") or self.watermark_cancelled:
            text = "CANCELADA"
        else:
            return

        # NT 008: Arial, mínimo 50pt, cinza, diagonal.
        size = 60  # >= 50pt
        self.set_font("helvetica", "B", size)  # Arial == Helvetica (FPDF2)
        self.set_text_color(180, 180, 180)  # cinza
        width = self.get_string_width(text)
        height = size * 0.25
        x_center = (self.w - width) / 2
        y_center = (self.h + height) / 2
        with self.rotation(55, x_center + width / 2, y_center - height / 2):
            self.text(x_center, y_center, text)
        self.set_text_color(0, 0, 0)

    # ======================================================================
    # 1. Cabeçalho + QR + Identificação
    # ======================================================================

    def _draw_header(self):
        x = self.l_margin
        y = self.y
        pw = self.epw
        cw = self._cols
        d = self.data

        # Faixa cinza superior.
        self.shade_rect(x=x + 0.5, y=y + 0.5, w=pw - 1, h=12.5)

        # Logomarca.
        logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nfse_logo.png")
        if os.path.exists(logo):
            self.image(logo, x=x + 2, y=y + 2, w=42)

        # Título central "DANFSe v2.0".
        self._nt_fonts.apply(self._nt_fonts.header_title())
        self.set_xy(x=x, y=y + 4)
        self.multi_cell(
            w=pw, h=2.5, text="DANFSe v2.0\nDocumento Auxiliar da NFS-e", align="C"
        )

        # Aviso de homologação (vermelho).
        if d.get("is_homologation"):
            self._nt_fonts.apply(self._nt_fonts.warning())
            self.set_text_color(255, 0, 0)
            self.set_xy(x=x, y=y + 9)
            self.cell(w=pw, h=3, text="NFS-e SEM VALIDADE JURÍDICA", align="C")
            self.set_text_color(0, 0, 0)

        # Bloco direito: Município / Ambiente.
        self._nt_fonts.apply(self._nt_fonts.small())
        top_right = (
            f"Município: {d['issuer']['city']}\n"
            f"Ambiente Gerador: {d['ambiente_gerador']}\n"
            f"Tipo de Ambiente: {d['environment_str']}"
        )
        self.set_xy(x=x + pw - 70, y=y + 2)
        self.multi_cell(w=68, h=3, text=top_right, align="R")

        self.divider(x + 2, y + 13, x + pw - 2)

        sy = y + 14
        # Chave de acesso (linha cheia).
        self._field(x + 3, sy, cw * 4, "CHAVE DE ACESSO DA NFS-E", d["key_nfse"])
        # Linha: número | competência | data/hora emissão
        self._field(x + 3, sy + 7, cw, "NÚMERO DA NFS-E", d["nfse_number"])
        self._field(x + cw, sy + 7, cw, "COMPETÊNCIA DA NFS-E", d["compet"])
        self._field(
            x + cw * 2,
            sy + 7,
            cw,
            "DATA E HORA DA EMISSÃO DA NFS-E",
            f"{d['dt_nfse']} {d['hr_nfse']}",
        )
        # Linha: DPS num | serie | data/hora DPS
        self._field(x + 3, sy + 14, cw, "NÚMERO DA DPS", d["dps_number"])
        self._field(x + cw, sy + 14, cw, "SÉRIE DA DPS", d["dps_serie"])
        self._field(
            x + cw * 2,
            sy + 14,
            cw,
            "DATA E HORA DA EMISSÃO DA DPS",
            f"{d['dt_dps']} {d['hr_dps']}",
        )
        # Linha: emitente | situação | finalidade (emitente sombreado).
        self.shade_rect(x=x + 0.5, y=sy + 20.5, w=cw, h=4)
        self._field(x + 3, sy + 21, cw, "EMITENTE DA NFS-E", d["emitente_nfse"])
        self._field(x + cw, sy + 21, cw, "SITUAÇÃO DA NFS-E", d["situacao_nfse"])
        self._field(x + cw * 2, sy + 21, cw, "FINALIDADE", d["finalidade"])

        # QR Code (1,52x1,52cm) no canto direito + legenda abaixo.
        qr_url = f"https://www.nfse.gov.br/ConsultaPublica/?tpc=1&chave={d['key_nfse']}"
        qr_x = x + pw - 17.5
        self._draw_qr(qr_url, qr_x, sy)
        self._nt_fonts.apply(self._nt_fonts.small())
        self.set_xy(x=x + cw * 3 - 8, y=sy + 17)
        self.multi_cell(
            w=cw + 6,
            h=2.4,
            text=(
                "A autenticidade desta NFS-e pode ser verificada pela "
                "leitura deste código QR ou pela consulta da chave de "
                "acesso no portal nacional da NFS-e"
            ),
            align="L",
        )

        self.divider(x + 2, y + 47, x + pw - 2)
        self.y = y + 47

    # ======================================================================
    # 2. Prestador
    # ======================================================================

    def _draw_issuer(self):
        x = self.l_margin
        y = self.y
        pw = self.epw
        cw = self._cols
        iss = self.data["issuer"]
        sy = y + 2

        self._block_title(x + 3, sy, "PRESTADOR / FORNECEDOR")
        self._field(x + cw, sy, cw, "CNPJ / CPF / NIF", iss["id"])
        self._field(
            x + cw * 2,
            sy,
            cw,
            "Indicador Municipal (Inscrição)",
            iss["municipal_registration"],
        )
        self._field(x + cw * 3, sy, cw, "Telefone", iss["phone"])

        self._field(
            x + 3,
            sy + 7,
            cw * 2,
            "Nome / Nome Empresarial",
            iss["name"],
            value_limit=cw * 2,
        )
        self._field(x + cw * 2, sy + 7, cw, "Município / Sigla UF", iss["city"])
        self._field(x + cw * 3, sy + 7, cw, "Código IBGE / CEP", iss["ibge_cep"])

        self._field(
            x + 3, sy + 14, cw * 2, "Endereço", iss["address"], value_limit=cw * 2
        )
        self._field(
            x + cw * 2, sy + 14, cw * 2, "E-mail", iss["email"], value_limit=cw * 2
        )

        self._field(
            x + 3,
            sy + 21,
            cw,
            "Simples Nacional na Data de Competência",
            iss["simples"],
        )
        self._field(
            x + cw * 2,
            sy + 21,
            cw * 2,
            "Regime de Apuração Tributária pelo SN",
            iss["tax_regim"],
            value_limit=cw * 2,
        )

        self.divider(x + 2, y + 32, x + pw - 2)
        self.y = y + 32

    # ======================================================================
    # 3. Tomador (+ Destinatário / Intermediário)
    # ======================================================================

    def _draw_taker(self):
        x = self.l_margin
        y = self.y
        pw = self.epw
        cw = self._cols
        tk = self.data["taker"]
        sy = y + 2

        self._block_title(x + 3, sy, "TOMADOR / ADQUIRENTE")

        if not tk.get("present"):
            self.shade_rect(x=x + 0.5, y=sy + 4, w=pw - 1, h=6)
            self._nt_fonts.apply(self._nt_fonts.value())
            self.set_xy(x=x + 3, y=sy + 5)
            self.cell(
                w=pw - 6,
                h=4,
                text="TOMADOR / ADQUIRENTE NÃO IDENTIFICADO NA NFS-e",
                align="C",
            )
            self.divider(x + 2, y + 16, x + pw - 2)
            self.y = y + 16
            self._draw_intermediary_notice()
            return

        self._field(x + cw, sy, cw, "CNPJ / CPF / NIF", tk["id"])
        self._field(
            x + cw * 2,
            sy,
            cw,
            "Indicador Municipal (Inscrição)",
            tk["municipal_registration"],
        )
        self._field(x + cw * 3, sy, cw, "Telefone", tk["phone"])

        self._field(
            x + 3,
            sy + 7,
            cw * 2,
            "Nome / Nome Empresarial",
            tk["name"],
            value_limit=cw * 2,
        )
        self._field(x + cw * 2, sy + 7, cw, "Município / Sigla UF", tk["city"])
        self._field(x + cw * 3, sy + 7, cw, "Código IBGE / CEP", tk["ibge_cep"])

        self._field(
            x + 3, sy + 14, cw * 2, "Endereço", tk["address"], value_limit=cw * 2
        )
        self._field(
            x + cw * 2, sy + 14, cw * 2, "E-mail", tk["email"], value_limit=cw * 2
        )

        self.y = y + 23
        self._draw_recipient_notice()
        self._draw_intermediary_notice()
        self.divider(x + 2, self.y + 1, x + pw - 2)
        self.y += 1

    def _draw_recipient_notice(self):
        """Bloco Destinatário da Operação (NT 008).

        No caso usual (destinatário = tomador) a NT permite suprimir o bloco
        e imprimir a frase padrão. Quando há destinatário distinto, exibe a
        identificação resumida.
        """
        x = self.l_margin
        rec = self.data.get("recipient", {})
        if rec.get("is_taker") or not rec.get("present"):
            self._nt_fonts.apply(self._nt_fonts.value())
            self.set_xy(x=x + 3, y=self.y + 1)
            self.cell(
                w=0,
                h=3,
                text=("O DESTINATÁRIO É O PRÓPRIO TOMADOR/ADQUIRENTE DO SERVIÇO"),
                align="C",
            )
            self.y += 5
        else:
            self._nt_fonts.apply(self._nt_fonts.label())
            self.set_xy(x=x + 3, y=self.y + 1)
            self.cell(w=0, h=3, text="DESTINATÁRIO DA OPERAÇÃO", align="L")
            self._nt_fonts.apply(self._nt_fonts.value())
            self.set_xy(x=x + 3, y=self.y + 4)
            info = " - ".join(
                p for p in (rec.get("id"), rec.get("name")) if p and p != "-"
            )
            self.cell(w=0, h=3, text=info or "-", align="L")
            self.y += 8

    def _draw_intermediary_notice(self):
        """Aviso/grid do intermediário (port: original só imprimia aviso)."""
        x = self.l_margin
        interm = self.data["intermed"]
        if not interm.get("present"):
            self._nt_fonts.apply(self._nt_fonts.value())
            self.set_xy(x=x + 3, y=self.y + 1)
            self.cell(
                w=0,
                h=3,
                text="INTERMEDIÁRIO DO SERVIÇO NÃO IDENTIFICADO NA NFS-e",
                align="C",
            )
            self.y += 5

    # ======================================================================
    # 4. Serviço prestado
    # ======================================================================

    def _draw_service_provided(self):
        x = self.l_margin
        y = self.y
        pw = self.epw
        cw = self._cols
        sv = self.data["service"]
        sy = y + 5

        self._block_title(x + 3, sy, "SERVIÇO PRESTADO")
        combined = f"{sv['national_tax_code_short']} / {sv['municipal_tax_code']}"
        self._field(
            x + cw, sy, cw, "Código de Tributação Nacional / Municipal", combined
        )
        self._field(x + cw * 2, sy, cw, "Código da NBS", sv["nbs_code"])
        local = f"{sv['place_of_provision']} / {sv['country']}"
        self._field(
            x + cw * 3,
            sy,
            cw,
            "Local da Prestação / Sigla UF / País",
            local,
            value_limit=cw,
        )

        # Descrição (multi_cell).
        self._nt_fonts.apply(self._nt_fonts.label())
        self.set_xy(x=x + 3, y=sy + 7)
        self.cell(w=pw, h=3, text="Descrição do Serviço", align="L")
        self._nt_fonts.apply(self._nt_fonts.value())
        self.set_xy(x=x + 3, y=sy + 10)
        self.multi_cell(w=pw - 6, h=4, text=sv["description"], align="L")

        line_y = max(self.get_y() + 2, sy + 36)
        self.divider(x + 2, line_y, x + pw - 2)
        self.y = line_y + 1

    # ======================================================================
    # 5. Tributos (ISSQN + Federal + IBS/CBS)
    # ======================================================================

    def _draw_taxes(self):
        x = self.l_margin
        y = self.y
        pw = self.epw
        cw = self._cols
        mt = self.data["municipal_taxes"]
        sy = y + 2

        self._block_title(x + 3, sy, "TRIBUTAÇÃO MUNICIPAL (ISSQN)", size=6)

        if mt.get("no_incidence"):
            self._nt_fonts.apply(self._nt_fonts.value())
            self.set_xy(x=x + cw, y=sy)
            self.cell(w=cw * 3, h=7, text="OPERAÇÃO NÃO SUJEITA AO ISSQN", align="L")
        else:
            self._field(
                x + cw, sy - 1, cw, "Tipo de Tributação do ISSQN", mt["issqn_tax_short"]
            )
            mun = mt["city"]
            if mt["country"] and mt["country"] not in mun:
                mun = f"{mun} / {mt['country']}"
            self._field(
                x + cw * 2,
                sy - 1,
                cw * 2,
                "Município / Sigla UF / País de Incidência do ISSQN",
                mun,
            )

            self._field(
                x + 3,
                sy + 11,
                cw,
                "Regime Especial de Tributação do ISSQN",
                mt["special_tax_regim"],
            )
            self._field(
                x + cw, sy + 11, cw, "Tipo de Imunidade do ISSQN", mt["immunity_type"]
            )
            self._field(
                x + cw * 2,
                sy + 11,
                cw,
                "Suspensão da Exigibilidade do ISSQN",
                mt["suspension_issqn"],
            )
            self._field(
                x + cw * 3,
                sy + 11,
                cw,
                "Número Processo Suspensão",
                mt["suspension_number"],
            )

            self._field(
                x + 3, sy + 18, cw, "Benefício Municipal", mt["municipal_benefit"]
            )
            self._field(
                x + cw, sy + 18, cw, "Cálculo do BM", mt["municipal_benefit_math"]
            )
            self._field(
                x + cw * 2,
                sy + 18,
                cw,
                "Total Deduções/Reduções",
                mt["deduct_reduc_amount"],
            )
            self._field(
                x + cw * 3,
                sy + 18,
                cw,
                "Desconto Incondicionado",
                mt["discount_unconditioned"],
            )

            self._field(x + 3, sy + 25, cw, "BC ISSQN", mt["calculation_basis"])
            self._field(x + cw, sy + 25, cw, "Alíquota Aplicada", mt["aliq_applied"])
            self._field(
                x + cw * 2, sy + 25, cw, "Retenção do ISSQN", mt["issqn_retention"]
            )
            self._field(x + cw * 3, sy + 25, cw, "ISSQN Apurado", mt["issqn_cleared"])

        self.divider(x + 2, y + 35, x + pw - 2)

        # Tributação Federal.
        ft = self.data["federal_taxes"]
        fy = sy + 37
        self._block_title(x + 3, fy, "TRIBUTAÇÃO FEDERAL (EXCETO CBS)", size=6)
        self._field(x + cw, fy - 1, cw, "IRRF", ft["irrf"])
        self._field(
            x + cw * 2,
            fy - 1,
            cw,
            "Contribuição Previdenciária - Retida",
            ft["previdenciary_contribution"],
        )
        self._field(
            x + cw * 3,
            fy - 1,
            cw,
            "Contribuições Sociais - Retidas",
            ft["social_contribution"],
        )
        self._field(x + 3, fy + 6, cw, "PIS - Débito Apuração Própria", ft["pis_debit"])
        self._field(
            x + cw, fy + 6, cw, "COFINS - Débito Apuração Própria", ft["cofins_debit"]
        )
        self._field(
            x + cw * 2,
            fy + 6,
            cw,
            "Descrição Contrib. Sociais - Retidas",
            ft["social_description"],
        )

        self.divider(x + 2, y + 55, x + pw - 2)
        self.y = y + 55
        self._draw_ibs_cbs_taxes()

    def _draw_ibs_cbs_taxes(self):
        x = self.l_margin
        y = self.y
        pw = self.epw
        cw = self._cols
        ic = self.data["ibs_cbs_taxes"]
        sy = y + 3

        self._block_title(x + 3, sy, "TRIBUTAÇÃO IBS / CBS", size=6)
        self._field(x + cw, sy - 1, cw, "CST / cClassTrib", ic["cst_cclass"])
        self._field(
            x + cw * 2,
            sy - 1,
            cw * 2,
            "Ind. Operação / Cód. IBGE / Município / UF",
            ic["ind_oper_ibge_mun_uf"],
        )

        self._field(x + 3, sy + 6, cw, "Exclusões e Reduções da BC", ic["excl_red_bc"])
        self._field(
            x + cw, sy + 6, cw, "BC Após Exclusões e Reduções", ic["bc_apos_excl"]
        )
        self._field(
            x + cw * 2,
            sy + 6,
            cw,
            "Red. Alíquota IBS / Mun / CBS",
            ic["red_aliq_ibs_cbs"],
        )
        self._field(
            x + cw * 3, sy + 6, cw, "Alíquota - IBS UF / IBS Mun", ic["aliq_ibs_uf_mun"]
        )

        self._field(
            x + 3, sy + 13, cw, "Alíq. Efetiva Municipal - IBS", ic["aliq_efet_mun_ibs"]
        )
        self._field(
            x + cw,
            sy + 13,
            cw,
            "Valor Apurado Municipal - IBS",
            ic["valor_apurado_mun_ibs"],
        )
        self._field(
            x + cw * 2,
            sy + 13,
            cw,
            "Alíq. Efetiva Estadual - IBS",
            ic["aliq_efet_est_ibs"],
        )
        self._field(
            x + cw * 3,
            sy + 13,
            cw,
            "Valor Apurado Estadual - IBS",
            ic["valor_apurado_est_ibs"],
        )

        self._field(
            x + 3,
            sy + 20,
            cw,
            "Valor Total Apurado - IBS",
            ic["valor_total_apurado_ibs"],
        )
        self._field(x + cw, sy + 20, cw, "Alíquota - CBS", ic["aliq_cbs"])
        self._field(
            x + cw * 2, sy + 20, cw, "Alíquota Efetiva - CBS", ic["aliq_efet_cbs"]
        )
        self._field(
            x + cw * 3,
            sy + 20,
            cw,
            "Valor Total Apurado - CBS",
            ic["valor_total_apurado_cbs"],
        )

        self.divider(x + 2, y + 30, x + pw - 2)
        self.y = y + 30

    # ======================================================================
    # 6. Totais
    # ======================================================================

    def _draw_amount(self):
        x = self.l_margin
        y = self.y
        pw = self.epw
        cw = self._cols
        tv = self.data["total_value"]
        sy = y + 3

        self._block_title(x + 3, sy, "VALOR TOTAL DA NFS-E")
        self._field(
            x + cw, sy - 1, cw, "VALOR DA OPERAÇÃO / SERVIÇO", tv["service_amount"]
        )
        self._field(
            x + cw * 2,
            sy - 1,
            cw,
            "Desconto Incondicionado",
            tv["discount_unconditioned"],
        )
        self._field(
            x + cw * 3, sy - 1, cw, "Desconto Condicionado", tv["discount_conditioned"]
        )

        self._field(
            x + 3,
            sy + 6,
            cw,
            "Total das Retenções (ISSQN / Federais)",
            tv["total_retentions"],
        )
        self._field(x + cw, sy + 6, cw, "VALOR LÍQUIDO DA NFS-e", tv["net_value"])
        self._field(x + cw * 2, sy + 6, cw, "Total do IBS/CBS", tv["total_ibs_cbs"])

        # Campo destacado (sombreado) — Valor líquido + IBS/CBS.
        self.shade_rect(x=x + cw * 3, y=sy + 5.5, w=cw, h=11)
        self._field(
            x + cw * 3,
            sy + 6,
            cw,
            "VALOR LÍQUIDO DA NFS-e + IBS/CBS",
            tv["net_value_ibs_cbs"],
        )

        self.divider(x + 2, y + 18, x + pw - 2)
        self.y = y + 18

    # ======================================================================
    # 7. Informações complementares
    # ======================================================================

    def _draw_complementary_info(self):
        x = self.l_margin
        y = self.y
        sy = y + 2
        self._block_title(x + 3, sy, "INFORMAÇÕES COMPLEMENTARES")
        self._nt_fonts.apply(self._nt_fonts.value(7))
        self.set_xy(x=x + 3, y=sy + 4)
        self.multi_cell(
            w=self.epw - 6, h=2.5, text=self.data["complementary_info"], align="L"
        )
        self.y = self.get_y() + 1

    # ======================================================================
    # 8. Canhoto (opcional)
    # ======================================================================

    def _draw_canhoto(self):
        x = self.l_margin
        y = self.y
        pw = self.epw
        cw = self._cols
        d = self.data
        sy = y + 3

        self.divider(x + 2, y + 1, x + pw - 2)
        self._block_title(
            x + 3,
            sy,
            "RECEBEMOS O SERVIÇO DESCRITO NESTA NFS-e",
            shaded=False,
            col_width=cw * 2,
        )
        self._field(x + 3, sy + 6, cw, "Data de Cientificação", "")
        self._field(x + cw, sy + 6, cw, "Identificação / Assinatura", "")
        self._field(
            x + cw * 2,
            sy + 6,
            cw * 2,
            "Nº NFS-e / Chave",
            f"{d['nfse_number']} / {d['key_nfse']}",
            value_limit=cw * 2,
        )
        self.divider(x + 2, sy + 16, x + pw - 2)
        self.y = sy + 16


def generate_danfse(
    xml: str | bytes, output_path: str, config: DanfseConfig | None = None
) -> str:
    """Atalho: gera o PDF do DANFSe e salva em output_path."""
    doc = Danfse(xml, config)
    doc.output(output_path)
    return output_path
