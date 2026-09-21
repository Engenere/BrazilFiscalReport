import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

from ..generate_qrcode import draw_qr_code
from ..utils import (
    chunks,
    format_cep,
    format_cpf_cnpj,
    format_number,
    get_date_utc,
    get_tag_text,
)
from ..xfpdf import xFPDF
from .config import DanfceConfig

URL = ".//{http://www.portalfiscal.inf.br/nfe}"

TP_PAGAMENTO = {
    "01": "Dinheiro",
    "02": "Cheque",
    "03": "Cartão de Crédito",
    "04": "Cartão de Débito",
    "05": "Cartão da Loja / Crediário",
    "10": "Vale Alimentação",
    "11": "Vale Refeição",
    "12": "Vale Presente",
    "13": "Vale Combustível",
    "14": "Duplicata Mercantil",
    "15": "Boleto Bancário",
    "16": "Depósito Bancário",
    "17": "PIX Dinâmico",
    "18": "Transferência Bancária / Carteira Digital",
    "19": "Programa de Fidelidade / Cashback / Crédito Virtual",
    "20": "PIX Estático",
    "21": "Crédito em Loja",
    "22": "Pagamento Eletrônico não Informado",
    "90": "Sem Pagamento",
    "91": "Pagamento Posterior",
    "99": "Outros",
}


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
        self.default_font = self.config.font_type.value
        self.price_precision = self.config.decimal_config.price_precision
        self.quantity_precision = self.config.decimal_config.quantity_precision
        self.orientation = "P"
        self.root = ET.fromstring(xml)
        self.add_page(orientation=self.orientation)
        self.colw = self._content_width() / 2
        self.data = self._parse_xml()

        self._draw_header()
        self._draw_items()
        self._draw_totals()
        self._draw_payments()
        self._draw_footer()

    def _money(self, value):
        if value in (None, ""):
            return "-"
        return f"R$ {format_number(value, self.price_precision)}"

    def _parse_xml(self):
        """Centralize all XML tags here."""

        def format_address(tag):
            return (
                ", ".join(
                    part
                    for part in (text(tag, "xLgr"), text(tag, "nro"), text(tag, "xCpl"))
                    if part
                )
                or "-"
            )

        def format_neighborhood(tag):
            city = (
                "/".join(part for part in (text(tag, "xMun"), text(tag, "UF")) if part)
                or "-"
            )

            return " - ".join(
                part
                for part in (
                    text(tag, "xBairro"),
                    city,
                    format_cep(text(tag, "CEP")) or "-",
                )
                if part and part != "-"
            )

        def format_person_id(tag):
            cpf = text(tag, "CPF")
            cnpj = text(tag, "CNPJ")
            label = "CPF" if cpf else "CNPJ"
            cpf_cnpj_person = format_cpf_cnpj(cpf or cnpj)

            return f"{label}: {cpf_cnpj_person}".strip()

        self.inf_nfe = self.root.find(f"{URL}infNFe")
        if self.inf_nfe is None:
            raise ValueError("XML inválido para o DANFC-e: grupo infNFe é obrigatório.")

        self.ide = self.root.find(f"{URL}ide")
        self.inf_nfe_supl = self.root.find(f"{URL}infNFeSupl")
        self.emit = self.root.find(f"{URL}emit")
        self.dest = self.root.find(f"{URL}dest")
        self.total = self.root.find(f"{URL}total")
        self.pag = self.root.find(f"{URL}pag")
        self.det = self.root.findall(f"{URL}det")
        self.inf_adic = self.root.find(f"{URL}infAdic")
        self.prot_nfe = self.root.find(f"{URL}protNFe")

        title = (
            "DANFE NFC-e - Documento Auxiliar da Nota Fiscal de Consumidor Eletrônica"
        )
        self.key_nfe = (
            self.inf_nfe.attrib.get("Id")[3:] if self.inf_nfe is not None else ""
        )

        def text(node, tag):
            return extract_text(node, tag)

        emit = self.emit
        dest = self.dest
        ide = self.ide
        total = self.total
        inf_supl = self.inf_nfe_supl
        prot = self.prot_nfe

        emit_id = format_person_id(emit)

        items = []
        for det in self.det:
            prod = det.find(f"{URL}prod")
            if prod is None:
                continue
            items.append(
                {
                    "code": text(prod, "cProd") or "-",
                    "description": text(prod, "xProd") or "-",
                    "quantity": format_number(
                        text(prod, "qCom"), self.quantity_precision
                    ),
                    "unit": text(prod, "uCom") or "-",
                    "unit_value": format_number(
                        text(prod, "vUnCom"), self.price_precision
                    ),
                    "total_value": format_number(
                        text(prod, "vProd"), self.price_precision
                    ),
                }
            )

        v_frete = float(get_tag_text(total, URL, "vFrete")) or 0
        v_seg = float(get_tag_text(total, URL, "vSeg")) or 0
        v_outro = float(get_tag_text(total, URL, "vOutro")) or 0
        v_desc = float(get_tag_text(total, URL, "vDesc")) or 0

        v_increase = v_frete + v_seg + v_outro

        payments = []
        if self.pag is not None:
            for payment in self.pag.findall(f"{URL}detPag"):
                payments.append(
                    {
                        "type": text(payment, "tPag") or "-",
                        "value": format_number(
                            text(payment, "vPag"), self.price_precision
                        ),
                    }
                )

        cpf = text(dest, "CPF")
        cnpj = text(dest, "CNPJ")

        if cpf or cnpj:
            consumer_name = text(dest, "xNome")
            consumer_id = format_person_id(dest)
            id_consumer = f"{consumer_id}  {consumer_name}".strip()
        else:
            id_consumer = ""

        dt_emi, hr_emi = get_date_utc(text(ide, "dhEmi"))
        dt_aut, hr_aut = get_date_utc(text(prot, "dhRecbto"))

        n_nf = text(ide, "nNF")
        serie = text(ide, "serie")
        nfc_info = f"Número: {n_nf}  Série: {serie}  Emissão: {dt_emi} {hr_emi}".strip()

        nfce_key = " ".join(chunks(self.key_nfe, 4))

        return {
            "title": title,
            "environment": text(ide, "tpAmb"),
            "authorized": prot is not None,
            "issuer": {
                "name": text(emit, "xNome") or "-",
                "fant": text(emit, "xFant") or "-",
                "id": emit_id,
                "ie": text(emit, "IE") or "-",
                "address": format_address(emit),
                "neighborhood": format_neighborhood(emit),
            },
            "identification_info": nfc_info,
            "items": items,
            "totals": {
                "products": format_number(text(total, "vProd"), self.price_precision),
                "invoice": self._money(text(total, "vNF")),
                "taxes": format_number(
                    text(total, "vTotTrib") or "0", self.price_precision
                ),
                "item_quantity": format_number(
                    str(len(items)), self.quantity_precision
                ),
                "increase": format_number(str(v_increase), self.price_precision)
                if v_increase > 0
                else 0,
                "discount": format_number(str(v_desc), self.price_precision)
                if v_desc > 0
                else 0,
            },
            "payments": payments,
            "change": format_number(text(self.pag, "vTroco"), self.price_precision),
            "consumer": {
                "credentials": id_consumer,
                "address": format_address(dest),
                "neighborhood": text(dest, "xBairro") or "-",
            },
            "footer": {
                "key": nfce_key,
                "qr_code": text(inf_supl, "qrCode"),
                "url": text(inf_supl, "urlChave"),
                "protocol": text(prot, "nProt"),
                "authorized_at": f"{dt_aut} {hr_aut}".strip(),
            },
        }

    # --- Funções Auxiliares ---

    def _draw_split_row(
        self,
        left_text: str,
        right_text: str,
        left_font: str = "",
        right_font: str = "B",
        size: int = 7,
    ) -> None:
        """
        Helper para padronizar linhas divididas em duas colunas
        (Ex: CNPJ | IE, Qtd | Valor).
        """
        y_id = self.get_y()
        content_width = self._content_width()
        left_width = content_width * 0.68
        right_width = content_width - left_width

        self.set_xy(self.l_margin, y_id)

        self.set_font(self.default_font, left_font, size)
        self.cell(
            w=left_width,
            h=3,
            text=self.long_field(text=left_text, limit=left_width),
            border=0,
            align="L",
        )

        self.set_font(self.default_font, right_font, size)
        self.cell(
            w=right_width,
            h=3,
            text=self.long_field(text=right_text, limit=right_width),
            border=0,
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    def _draw_centered_text(
        self, text: str, font_style: str = "", size: int = 8, add_ln: float = 0
    ) -> None:
        """Helper para imprimir múltiplos textos centralizados de forma padronizada."""
        if not text:
            return
        self.set_font(self.default_font, font_style, size)
        for line in self._wrap_text(text, self._content_width()):
            self.cell(
                w=0, h=4, text=line, border=0, new_x="LMARGIN", new_y="NEXT", align="C"
            )
        if add_ln:
            self.ln(add_ln)

    def _draw_left_text(
        self, text: str, font_style: str = "", size: int = 8, add_ln: float = 0
    ) -> None:
        """Helper para imprimir múltiplos textos alinhados à esquerda."""
        if not text:
            return
        self.set_font(self.default_font, font_style, size)
        for line in self._wrap_text(text, self._content_width()):
            self.cell(
                w=0, h=3, text=line, border=0, new_x="LMARGIN", new_y="NEXT", align="L"
            )
        if add_ln:
            self.ln(add_ln)

    def _draw_header(self) -> None:
        issuer = self.data["issuer"]

        self._draw_centered_text(issuer["fant"], font_style="B", add_ln=2)
        self._draw_left_text(issuer["name"], add_ln=2)
        self._draw_split_row(
            issuer["id"], f"IE: {issuer['ie']}", left_font="", right_font=""
        )

        self._draw_left_text(f"End.: {issuer['address']}", size=7)
        self._draw_left_text(f"Bairro: {issuer['neighborhood']}", size=7, add_ln=1)

        self._draw_line()
        self._draw_centered_text(self.data["title"], font_style="B", add_ln=1)

    def _draw_items_layout(
        self, code, description, quant, uom, unit_val, total_amount, border=False
    ) -> None:
        self.set_font(self.default_font, "B", 7)
        x0 = self.l_margin
        w = self._content_width()
        h = 3.5
        y0 = self.get_y()

        # Define as larguras máximas para código e descrição
        code_width = 17
        desc_width = w - code_width - 1

        # Quebra os textos para caberem exatamente em suas colunas
        code_lines = self._wrap_text(code, code_width) or [""]
        desc_lines = self._wrap_text(description, desc_width) or [""]

        # Identifica qual coluna consumiu mais linhas para definir a altura do bloco
        num_lines = max(len(code_lines), len(desc_lines))
        total_block_height = (num_lines + 1) * h

        if border:
            self.set_fill_color(242, 242, 242)
            self.rect(x0, y0, w, total_block_height, style="DF")
            self.set_fill_color(255, 255, 255)

        # Renderiza a coluna do Código
        y_temp = y0
        for line in code_lines:
            self.set_xy(x0 + 1, y_temp)
            self.cell(w=code_width, h=h, text=line, align="L")
            y_temp += h

        # Renderiza a coluna da Descrição
        y_temp = y0
        for line in desc_lines:
            self.set_xy(x0 + code_width + 1, y_temp)
            self.cell(w=desc_width, h=h, text=line, align="L")
            y_temp += h

        # Define a posição Y da sublinha (Qtde / Valor)
        y1 = y0 + (num_lines * h)

        col_qtd, col_x, col_vunit, col_eq, col_vtotal = (
            w * 0.15,
            w * 0.12,
            w * 0.24,
            w * 0.06,
            w * 0.25,
        )
        x = x0 + w * 0.18

        self.set_xy(x, y1)
        self.cell(w=col_qtd, h=h, text=f"{quant} {uom}", align="L")
        x += col_qtd
        self.set_xy(x, y1)
        self.cell(w=col_x, h=h, text="x", align="C")
        x += col_x
        self.set_xy(x, y1)
        self.cell(w=col_vunit, h=h, text=unit_val, align="C")
        x += col_vunit
        self.set_xy(x, y1)
        self.cell(w=col_eq, h=h, text="=", align="C")
        x += col_eq
        self.set_xy(x, y1)
        self.cell(w=col_vtotal, h=h, text=total_amount, align="R")

        """
            Atualiza a posição final do cursor para que o item ou
            o totalizador sejam desenhados corretamente
        """
        self.set_y(y1 + h)

    def _draw_items(self) -> None:
        self._draw_items_layout(
            "Código", "Descrição", "Qtde", "Un", "Valor Unitário", "Valor Total", True
        )

        for item in self.data["items"]:
            self._draw_items_layout(
                item["code"],
                item["description"],
                item["quantity"],
                item["unit"],
                item["unit_value"],
                item["total_value"],
            )
            self._draw_line()

    def _draw_totals(self) -> None:
        totals = self.data["totals"]

        self._draw_split_row(
            "QTD. TOTAL DE ITENS", totals["item_quantity"], left_font=""
        )
        self._draw_split_row("VALOR TOTAL R$:", totals["products"], left_font="")

        if totals["increase"]:
            self._draw_split_row("ACRÉSCIMO R$:", totals["increase"], left_font="")

        if totals["discount"]:
            self._draw_split_row("DESCONTO R$:", totals["discount"], left_font="")

        self.ln(1)

    def _draw_payments(self) -> None:
        totals = self.data["totals"]

        self._draw_split_row(
            "FORMA DE PAGAMENTO", "Valor Pago", left_font="B", right_font="B"
        )
        self.ln(2)

        for payment in self.data["payments"]:
            payment_type = TP_PAGAMENTO.get(payment["type"], "Outros")
            self._draw_split_row(
                payment_type, payment["value"], left_font="", right_font="", size=8
            )
            self.ln(2)

        self._draw_left_text(f"(TOTAL PAGO: {totals['invoice']})")
        self._draw_split_row(
            "TROCO R$:", self.data["change"], left_font="B", right_font="B", size=8
        )
        self.ln(2)

        # Resolvido o TODO: Puxando o total de tributos extraído no _parse_xml
        self._draw_split_row(
            "Informação dos Tributos Totais Incidentes",
            totals["taxes"],
            left_font="",
            right_font="",
            size=8,
        )
        self._draw_left_text("(Lei Federal 12.741/2012)", size=8, add_ln=1)

        self._draw_line()

    def _draw_footer(self) -> None:
        self._ensure_space(60)
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

        self._draw_centered_text("Consulta via leitor de QR Code", add_ln=1)

        if footer["qr_code"]:
            box_size = 36
            y_top = self.get_y()
            x_offset = self.l_margin + (self._content_width() - box_size) / 2 - 1
            y_offset = y_top - self.t_margin

            draw_qr_code(
                self,
                footer["qr_code"],
                0,
                x_offset,
                y_offset,
                box_size=box_size,
                border=2,
            )
            self.set_y(y_top + box_size + 4)
        else:
            self.ln(4)

        self._draw_centered_text("Protocolo de Autorização")
        self._draw_centered_text(f"{footer['protocol']}  {footer['authorized_at']}")

    # --- Utilitários da Classe ---

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
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(0.5)
