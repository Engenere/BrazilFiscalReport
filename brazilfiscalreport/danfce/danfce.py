import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

from fpdf.enums import Align

from ..generate_qrcode import draw_qr_code
from ..utils import (
    chunks,
    format_cep,
    format_cpf_cnpj,
    format_number,
    get_date_utc,
    get_tag_text,
    to_float,
)
from ..xfpdf import xFPDF
from .config import DanfceConfig
from .danfce_conf import (
    CONTINGENCY_NOTICE,
    HOMOLOGATION_NOTICE,
    NO_ICMS_CREDIT_NOTICE,
    PENDING_AUTH_NOTICE,
    TITLE,
    TOTAL_ADDITIONS,
    TOTAL_DEDUCTIONS,
    TP_EMISSAO_NORMAL,
    TP_PAGAMENTO,
    UNREPORTED_TAX,
    URL,
)

# Altura de uma linha de texto do bloco de itens.
ITEM_LINE_HEIGHT = 3.5
# Largura da coluna de código do produto.
ITEM_CODE_WIDTH = 17
# Largura das colunas dos operadores "x" e "=" da sublinha de valores.
ITEM_OPERATOR_WIDTH = 4
# Lado do QR Code, como fração da largura útil — mesma proporção do ACBr.
# Era fixo em 36mm, o que deixava o módulo do QR com 0,68mm numa NFC-e
# típica: 5,4 pontos numa térmica de 203 DPI, no limite da leitura.
QR_CODE_RATIO = 0.7
# Resolução da imagem do QR, em pixels por módulo.
QR_CODE_BOX_SIZE = 10
# Caixa em que a logo do emitente é encaixada, preservando a proporção.
LOGO_MAX_HEIGHT = 14
LOGO_MAX_WIDTH_RATIO = 0.5
# Limite clássico de página do PDF (200 polegadas). O fpdf2 não o valida,
# mas os leitores tratam mal o que passa disso.
MAX_PAGE_HEIGHT = 5080
# Altura de página usada quando o cupom não cabe numa bobina única.
PAGINATED_PAGE_HEIGHT = 300


def extract_text(node: Element | None, tag: str) -> str:
    if node is None:
        return ""
    # O strip é obrigatório: qrCode/urlChave costumam vir em CDATA indentado,
    # e a indentação acabaria dentro do payload do QR Code.
    return (get_tag_text(node, URL, tag) or "").strip()


class Danfce(xFPDF):
    def __init__(self, xml, config: DanfceConfig | None = None, _probe_height=None):
        self.config = config if config is not None else DanfceConfig()
        page_height = self._resolve_page_height(xml, _probe_height)

        super().__init__(unit="mm", format=(self.config.paper_width, page_height))
        self.set_margins(
            left=self.config.margins.left,
            top=self.config.margins.top,
            right=self.config.margins.right,
        )
        # Numa bobina contínua não existe página seguinte para onde quebrar.
        self.set_auto_page_break(
            auto=not self.continuous, margin=self.config.margins.bottom
        )
        self.set_title("DANFCe")
        self.default_font = self.config.font_type.value
        self.price_precision = self.config.decimal_config.price_precision
        self.quantity_precision = self.config.decimal_config.quantity_precision
        self.root = ET.fromstring(xml)
        self.data = self._parse_xml()

        self.add_page()
        self._draw_header()
        self._draw_items()
        self._draw_totals()
        self._draw_payments()
        self._draw_additional_info()
        self._draw_footer()
        # Por último, para ficar sobre o conteúdo.
        self._draw_watermark()

    # --- Altura da bobina ---

    def _resolve_page_height(self, xml, probe_height):
        """
        Decide a altura da página e se o cupom quebra em páginas.

        Uma bobina térmica é contínua: o cupom tem o tamanho do que foi
        impresso e é cortado no fim. O padrão, então, é uma página única
        com a altura exata do conteúdo, medida numa primeira passagem —
        mesma solução do DANFCe do ACBr (`EndlessHeight` + `DoublePass`).

        Só há duas exceções: quando o chamador fixa `paper_height`, e
        quando o conteúdo passa do limite de página do PDF (uma NFC-e
        aceita até 990 itens, o que daria metros de bobina).
        """
        if probe_height is not None:
            self.continuous = True
            return probe_height

        if self.config.paper_height is not None:
            self.continuous = False
            return self.config.paper_height

        probe = type(self)(xml, self.config, _probe_height=MAX_PAGE_HEIGHT)
        height = probe.get_y() + probe.b_margin
        self.continuous = height <= MAX_PAGE_HEIGHT
        return height if self.continuous else PAGINATED_PAGE_HEIGHT

    def ensure_space(self, height):
        # Sem página seguinte, não há o que reservar.
        if self.continuous:
            return False
        return super().ensure_space(height)

    # --- Leitura do XML ---

    def _parse_xml(self):
        """Centraliza a leitura do XML: o desenho só consome o dict daqui."""
        inf_nfe = self.root.find(f"{URL}infNFe")
        if inf_nfe is None:
            raise ValueError("XML inválido para o DANFC-e: grupo infNFe é obrigatório.")

        ide = self.root.find(f"{URL}ide")
        emit = self.root.find(f"{URL}emit")
        dest = self.root.find(f"{URL}dest")
        total = self.root.find(f"{URL}total")
        pag = self.root.find(f"{URL}pag")
        inf_adic = self.root.find(f"{URL}infAdic")
        inf_nfe_supl = self.root.find(f"{URL}infNFeSupl")
        prot = self.root.find(f"{URL}protNFe")
        dets = self.root.findall(f"{URL}det")

        key_nfe = (inf_nfe.attrib.get("Id") or "")[3:]
        dt_emi, hr_emi = get_date_utc(extract_text(ide, "dhEmi"))
        dt_aut, hr_aut = get_date_utc(extract_text(prot, "dhRecbto"))

        items = self._parse_items(dets)
        totals = self._parse_totals(total, dets, len(items))

        return {
            "notices": self._parse_notices(ide, prot),
            "issuer": {
                "name": extract_text(emit, "xNome") or "-",
                "fant": extract_text(emit, "xFant") or "-",
                "id": self._format_person_id(emit),
                "ie": extract_text(emit, "IE") or "-",
                "address": self._format_address(emit),
                "neighborhood": self._format_neighborhood(emit),
            },
            "identification_info": (
                f"Número: {extract_text(ide, 'nNF')}"
                f"  Série: {extract_text(ide, 'serie')}"
                f"  Emissão: {dt_emi} {hr_emi}".strip()
            ),
            "items": items,
            "totals": totals,
            "payments": self._parse_payments(pag),
            "change": format_number(extract_text(pag, "vTroco"), self.price_precision),
            "consumer": self._parse_consumer(dest),
            "additional_info": self._format_additional_info(inf_adic),
            "footer": {
                "key": " ".join(chunks(key_nfe, 4)),
                "qr_code": extract_text(inf_nfe_supl, "qrCode"),
                "url": extract_text(inf_nfe_supl, "urlChave"),
                "authorized": prot is not None,
                "protocol": extract_text(prot, "nProt"),
                "authorized_at": f"{dt_aut} {hr_aut}".strip(),
            },
        }

    def _format_additional_info(self, inf_adic):
        """Mensagem do contribuinte, com o separador do emitente virando linha."""
        text = extract_text(inf_adic, "infCpl")
        separator = self.config.line_break_char
        if text and separator:
            text = text.replace(separator, "\n")
        return text

    def _parse_notices(self, ide, prot):
        """Avisos que tiram o valor fiscal do cupom, impressos sob o título."""
        notices = []
        if extract_text(ide, "tpAmb") == "2":
            notices.append(HOMOLOGATION_NOTICE)
        tp_emis = extract_text(ide, "tpEmis")
        if tp_emis and tp_emis != TP_EMISSAO_NORMAL:
            notices.append(CONTINGENCY_NOTICE)
        if prot is None:
            notices.append(PENDING_AUTH_NOTICE)
        return notices

    def _parse_items(self, dets):
        items = []
        for det in dets:
            prod = det.find(f"{URL}prod")
            if prod is None:
                continue
            items.append(
                {
                    "code": extract_text(prod, "cProd") or "-",
                    "description": extract_text(prod, "xProd") or "-",
                    "quantity": format_number(
                        extract_text(prod, "qCom"), self.quantity_precision
                    ),
                    "unit": extract_text(prod, "uCom") or "-",
                    "unit_value": format_number(
                        extract_text(prod, "vUnCom"), self.price_precision
                    ),
                    "total_value": format_number(
                        extract_text(prod, "vProd"), self.price_precision
                    ),
                }
            )
        return items

    def _parse_totals(self, total, dets, item_count):
        additions = sum(to_float(extract_text(total, tag)) for tag in TOTAL_ADDITIONS)
        deductions = sum(to_float(extract_text(total, tag)) for tag in TOTAL_DEDUCTIONS)

        # vTotTrib pode vir só nos itens; o manual aceita as duas origens.
        taxes = to_float(extract_text(total, "vTotTrib"))
        if not taxes:
            taxes = sum(
                to_float(extract_text(det.find(f"{URL}imposto"), "vTotTrib"))
                for det in dets
            )

        def money(value):
            return format_number(str(value), self.price_precision)

        return {
            "products": money(to_float(extract_text(total, "vProd"))),
            "payable": money(to_float(extract_text(total, "vNF"))),
            # Zerado significa "não informado", não "sem imposto": imprimir
            # 0,00 seria afirmar algo que o XML não diz.
            "taxes": money(taxes) if taxes else UNREPORTED_TAX,
            "item_quantity": str(item_count),
            # Vazio quando não há valor, para o desenho suprimir a linha.
            "increase": money(additions) if additions else "",
            "discount": money(deductions) if deductions else "",
        }

    def _parse_payments(self, pag):
        payments = []
        if pag is None:
            return payments
        for payment in pag.findall(f"{URL}detPag"):
            t_pag = extract_text(payment, "tPag")
            payments.append(
                {
                    # xPag descreve o meio de pagamento quando tPag=99.
                    "type": extract_text(payment, "xPag")
                    or TP_PAGAMENTO.get(t_pag, "Outros"),
                    "value": format_number(
                        extract_text(payment, "vPag"), self.price_precision
                    ),
                }
            )
        return payments

    def _parse_consumer(self, dest):
        credentials = self._format_person_id(dest)
        if not credentials:
            return {"credentials": "", "address": "", "neighborhood": ""}
        name = extract_text(dest, "xNome")
        return {
            "credentials": f"{credentials}  {name}".strip(),
            "address": self._format_address(dest),
            "neighborhood": self._format_neighborhood(dest),
        }

    @staticmethod
    def _format_person_id(node):
        """Rótulo + documento do emitente ou do consumidor, quando houver."""
        for label, tag in (("CNPJ", "CNPJ"), ("CPF", "CPF")):
            value = extract_text(node, tag)
            if value:
                return f"{label}: {format_cpf_cnpj(value)}"
        foreign = extract_text(node, "idEstrangeiro")
        return f"Id. Estrangeiro: {foreign}" if foreign else ""

    @staticmethod
    def _format_address(node):
        parts = (
            extract_text(node, "xLgr"),
            extract_text(node, "nro"),
            extract_text(node, "xCpl"),
        )
        return ", ".join(part for part in parts if part) or "-"

    @staticmethod
    def _format_neighborhood(node):
        city = "/".join(
            part
            for part in (extract_text(node, "xMun"), extract_text(node, "UF"))
            if part
        )
        cep = extract_text(node, "CEP")
        parts = (
            extract_text(node, "xBairro"),
            city,
            format_cep(cep) if cep else "",
        )
        return " - ".join(part for part in parts if part) or "-"

    # --- Funções Auxiliares ---

    def _draw_split_row(
        self,
        left_text,
        right_text,
        left_font="",
        right_font="B",
        size=7,
    ):
        """
        Helper para padronizar linhas divididas em duas colunas
        (Ex: CNPJ | IE, Qtd | Valor).
        """
        # A coluna da direita leva só o que o valor precisa (no máximo metade
        # da largura útil); o resto fica com o rótulo, que é quem costuma
        # transbordar em bobinas estreitas.
        self.set_font(self.default_font, right_font, size)
        # +3 = os 2mm que o long_field reserva internamente, mais 1mm de
        # calha; com folga zero o arredondamento chega a cortar o valor.
        right_width = min(self.get_string_width(right_text) + 3, self.epw * 0.5)
        left_width = self.epw - right_width

        # O rótulo quebra em linhas em vez de ser truncado: textos exigidos
        # por lei (Lei 12.741/2012) não podem sair pela metade em bobina
        # estreita. O valor fica na primeira linha.
        self.set_font(self.default_font, left_font, size)
        left_lines = self.wrap_text(left_text, left_width) or [""]

        for index, line in enumerate(left_lines):
            self.set_xy(self.l_margin, self.get_y())

            self.set_font(self.default_font, left_font, size)
            self.cell(w=left_width, h=3, text=line, border=0, align="L")

            self.set_font(self.default_font, right_font, size)
            self.cell(
                w=right_width,
                h=3,
                text=self.long_field(text=right_text, limit=right_width)
                if index == 0
                else "",
                border=0,
                align="R",
                new_x="LMARGIN",
                new_y="NEXT",
            )

    def _draw_centered_text(self, text, font_style="", size=8, add_ln=0):
        """Helper para imprimir múltiplos textos centralizados de forma padronizada."""
        self._draw_flow_text(text, "C", 4, font_style, size, add_ln)

    def _draw_left_text(self, text, font_style="", size=8, add_ln=0):
        """Helper para imprimir múltiplos textos alinhados à esquerda."""
        self._draw_flow_text(text, "L", 3, font_style, size, add_ln)

    def _draw_flow_text(self, text, align, line_height, font_style, size, add_ln):
        if not text:
            return
        self.set_font(self.default_font, font_style, size)
        for line in self.wrap_text(text, self.epw):
            self.cell(
                w=0,
                h=line_height,
                text=line,
                border=0,
                new_x="LMARGIN",
                new_y="NEXT",
                align=align,
            )
        if add_ln:
            self.ln(add_ln)

    def _draw_line(self):
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.1)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(0.5)

    # --- Blocos do documento ---

    def _draw_logo(self):
        if not self.config.logo:
            return
        self.image(
            self.config.logo,
            x=Align.C,
            w=self.epw * LOGO_MAX_WIDTH_RATIO,
            h=LOGO_MAX_HEIGHT,
            keep_aspect_ratio=True,
        )
        self.ln(1)

    def _draw_watermark(self):
        if not self.config.watermark_cancelled:
            return
        text = "CANCELADA"
        font_size = 40
        self.set_font(self.default_font, "B", font_size)
        width = self.get_string_width(text)
        x = (self.w - width) / 2
        y = self.h / 2
        with (
            self.local_context(fill_opacity=0.35, text_color=(128, 128, 128)),
            self.rotation(55, x + width / 2, y),
        ):
            self.text(x, y, text)

    def _draw_header(self):
        issuer = self.data["issuer"]

        self._draw_logo()
        self._draw_centered_text(issuer["fant"], font_style="B", add_ln=2)
        self._draw_left_text(issuer["name"], add_ln=2)
        self._draw_split_row(
            issuer["id"], f"IE: {issuer['ie']}", left_font="", right_font=""
        )

        self._draw_left_text(f"End.: {issuer['address']}", size=7)
        self._draw_left_text(f"Bairro: {issuer['neighborhood']}", size=7, add_ln=1)

        self._draw_line()
        self._draw_centered_text(TITLE, font_style="B")
        self._draw_centered_text(NO_ICMS_CREDIT_NOTICE, size=7, add_ln=1)

        for notice in self.data["notices"]:
            self._draw_centered_text(notice, font_style="B")
        if self.data["notices"]:
            self.ln(1)

    def _wrap_item(self, code, description, bold):
        """Quebra código e descrição nas respectivas colunas, com a fonte do item."""
        self.set_font(self.default_font, "B" if bold else "", 7)
        code_lines = self.wrap_text(code, ITEM_CODE_WIDTH) or [""]
        desc_lines = self.wrap_text(description, self.epw - ITEM_CODE_WIDTH - 1) or [""]
        return code_lines, desc_lines

    def _draw_item_cells(
        self,
        code_lines,
        desc_lines,
        quant,
        uom,
        unit_val,
        total_amount,
        fill=False,
    ):
        x0 = self.l_margin
        w = self.epw
        h = ITEM_LINE_HEIGHT
        y0 = self.get_y()
        num_lines = max(len(code_lines), len(desc_lines))

        if fill:
            self.set_fill_color(242, 242, 242)
            self.rect(x0, y0, w, (num_lines + 1) * h, style="DF")
            self.set_fill_color(255, 255, 255)

        # Renderiza a coluna do Código
        y_temp = y0
        for line in code_lines:
            self.set_xy(x0 + 1, y_temp)
            self.cell(w=ITEM_CODE_WIDTH, h=h, text=line, align="L")
            y_temp += h

        # Renderiza a coluna da Descrição
        y_temp = y0
        for line in desc_lines:
            self.set_xy(x0 + ITEM_CODE_WIDTH + 1, y_temp)
            self.cell(w=w - ITEM_CODE_WIDTH - 1, h=h, text=line, align="L")
            y_temp += h

        # Define a posição Y da sublinha (Qtde / Valor)
        y1 = y0 + (num_lines * h)

        col_qtd, col_vunit, col_vtotal = self.amount_columns
        block = col_qtd + col_vunit + col_vtotal + 2 * ITEM_OPERATOR_WIDTH
        # Encosta o bloco à direita; a folga que sobrar vira recuo à esquerda.
        x = max(x0, x0 + w - block)

        for width, text, align in (
            (col_qtd, f"{quant} {uom}", "L"),
            (ITEM_OPERATOR_WIDTH, "x", "C"),
            (col_vunit, unit_val, "R"),
            (ITEM_OPERATOR_WIDTH, "=", "C"),
            (col_vtotal, total_amount, "R"),
        ):
            self.set_xy(x, y1)
            self.cell(w=width, h=h, text=text, align=align)
            x += width

        # Atualiza a posição final do cursor para que o próximo item ou o
        # totalizador sejam desenhados logo abaixo do bloco.
        self.set_y(y1 + h)

    def _draw_items_header(self):
        code_lines, desc_lines = self._wrap_item("Código", "Descrição", bold=True)
        self._draw_item_cells(
            code_lines,
            desc_lines,
            "Qtde",
            "Un",
            "Valor Unitário",
            "Valor Total",
            fill=True,
        )

    def _measure_amount_columns(self):
        """
        Larguras da sublinha "qtde un x unitário = total".

        Medidas sobre o conteúdo mais largo do documento (cabeçalho incluso)
        em vez de frações fixas da bobina: assim as colunas ficam alinhadas
        entre os itens e nenhuma invade a vizinha em bobinas estreitas.
        """
        rows = [(("Qtde", "Un", "Valor Unitário", "Valor Total"), "B")]
        rows += [
            (
                (
                    item["quantity"],
                    item["unit"],
                    item["unit_value"],
                    item["total_value"],
                ),
                "",
            )
            for item in self.data["items"]
        ]

        widths = [0.0, 0.0, 0.0]
        for (quant, uom, unit_val, total_val), style in rows:
            self.set_font(self.default_font, style, 7)
            for index, text in enumerate((f"{quant} {uom}", unit_val, total_val)):
                widths[index] = max(widths[index], self.get_string_width(text) + 1)

        # Não deixa o bloco passar da largura útil quando o conteúdo é enorme.
        available = self.epw - 2 * ITEM_OPERATOR_WIDTH
        if sum(widths) > available:
            factor = available / sum(widths)
            widths = [width * factor for width in widths]
        return widths

    def _draw_items(self):
        self.amount_columns = self._measure_amount_columns()
        self._draw_items_header()

        for item in self.data["items"]:
            code_lines, desc_lines = self._wrap_item(
                item["code"], item["description"], bold=False
            )
            # O bloco é desenhado em coordenadas absolutas, que não sobrevivem
            # à quebra automática do fpdf2: reserva o espaço antes (+0.5mm do
            # traço separador) e repete o cabeçalho na página nova.
            block_height = (max(len(code_lines), len(desc_lines)) + 1) * (
                ITEM_LINE_HEIGHT
            ) + 0.5
            if self.ensure_space(block_height):
                self._draw_items_header()
                self.set_font(self.default_font, "", 7)

            self._draw_item_cells(
                code_lines,
                desc_lines,
                item["quantity"],
                item["unit"],
                item["unit_value"],
                item["total_value"],
            )
            self._draw_line()

    def _draw_totals(self):
        totals = self.data["totals"]

        self._draw_split_row("QTD. TOTAL DE ITENS", totals["item_quantity"])
        self._draw_split_row("VALOR TOTAL R$:", totals["products"])

        if totals["discount"]:
            self._draw_split_row("DESCONTO R$:", totals["discount"])

        if totals["increase"]:
            self._draw_split_row("ACRÉSCIMO R$:", totals["increase"])

        self._draw_split_row(
            "VALOR A PAGAR R$:", totals["payable"], left_font="B", right_font="B"
        )
        self.ln(1)

    def _draw_payments(self):
        self._draw_split_row(
            "FORMA DE PAGAMENTO", "Valor Pago", left_font="B", right_font="B"
        )
        self.ln(2)

        for payment in self.data["payments"]:
            self._draw_split_row(
                payment["type"],
                payment["value"],
                left_font="",
                right_font="",
                size=8,
            )
            self.ln(2)

        self._draw_split_row(
            "TROCO R$:",
            self.data["change"],
            left_font="B",
            right_font="B",
            size=8,
        )
        self.ln(2)

        self._draw_split_row(
            "Informação dos Tributos Totais Incidentes",
            self.data["totals"]["taxes"],
            left_font="",
            right_font="",
            size=8,
        )
        self._draw_left_text("(Lei Federal 12.741/2012)", size=8, add_ln=1)

        self._draw_line()

    def _draw_additional_info(self):
        """Mensagem de interesse do contribuinte (infAdic/infCpl)."""
        if not self.data["additional_info"]:
            return
        self._draw_left_text(self.data["additional_info"], size=7, add_ln=1)
        self._draw_line()

    def _draw_footer(self):
        footer = self.data["footer"]
        consumer = self.data["consumer"]

        self._draw_centered_text(self.data["identification_info"], add_ln=1)
        self._draw_centered_text("Via Consumidor", font_style="B", add_ln=1)
        self._draw_line()

        self._draw_centered_text("Consulte pela chave de acesso em:")
        if footer["url"]:
            self._draw_centered_text(footer["url"], size=7)
        self.ln(1)

        self._draw_centered_text("CHAVE DE ACESSO", font_style="B")
        self._draw_centered_text(footer["key"], size=7)
        self._draw_line()
        self.ln(1)

        if consumer["credentials"]:
            self._draw_centered_text("CONSUMIDOR", font_style="B", add_ln=1)
            self._draw_centered_text(consumer["credentials"], add_ln=1)
            self._draw_centered_text(f"End.: {consumer['address']}")
            self._draw_centered_text(f"Bairro: {consumer['neighborhood']}", add_ln=1)
        else:
            self._draw_centered_text(
                "CONSUMIDOR NÃO IDENTIFICADO", font_style="B", size=7, add_ln=1
            )

        self._draw_line()
        self.ln(1)

        qr_size = self.epw * QR_CODE_RATIO
        # O QR Code é posicionado em coordenada absoluta, então precisa caber
        # inteiro — junto da legenda acima e do protocolo abaixo.
        self.ensure_space(qr_size + 18)
        self._draw_centered_text("Consulta via leitor de QR Code", add_ln=1)

        if footer["qr_code"]:
            y_top = self.get_y()
            # draw_qr_code desenha em (x_offset + 1, t_margin + y_offset + 1).
            draw_qr_code(
                self,
                footer["qr_code"],
                0,
                self.l_margin + (self.epw - qr_size) / 2 - 1,
                y_top - self.t_margin - 1,
                box_size=QR_CODE_BOX_SIZE,
                border=2,
                size=qr_size,
            )
            self.set_y(y_top + qr_size + 4)
        else:
            self.ln(4)

        if footer["authorized"]:
            self._draw_centered_text("Protocolo de Autorização")
            self._draw_centered_text(f"{footer['protocol']}  {footer['authorized_at']}")
        else:
            self._draw_centered_text(PENDING_AUTH_NOTICE, font_style="B")
