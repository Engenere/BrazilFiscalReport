# Copyright (C) 2021-2022 Edson Bernardino <edsones at yahoo.com.br>
# Copyright (C) 2024 Engenere - Antônio S. Pereira Neto <neto@engenere.one>

import re
import xml.etree.ElementTree as ET
from itertools import zip_longest
from xml.etree.ElementTree import Element

from fpdf.enums import MethodReturnValue
from qrcode.constants import ERROR_CORRECT_M

from ..generate_qrcode import make_qr_code_image
from ..utils import (
    chunks,
    describe_volumes,
    format_cep,
    format_cpf_cnpj,
    format_number,
    format_phone,
    format_rate,
    get_date_utc,
    get_tag_text,
    merge_if_different,
)
from ..xfpdf import xFPDF
from .config import DanfeConfig, FontSize, InvoiceDisplay, ReceiptPosition
from .danfe_basic_field import DanfeBasicField
from .danfe_block import DanfeBlock
from .danfe_code import DanfeCode
from .danfe_conf import (
    BASE_FONT_SIZES,
    DEFAULT_FIELD_HEIGHT,
    HEIGHT_FONT_BLOCK_DESC,
    MAX_VOLUME_LINES,
    PRODUCT_CELL_PADDING,
    PRODUCT_HEADER_LINE_HEIGHT,
    PRODUCT_LINE_HEIGHT,
    QR_CODE_BLOCK_GAP,
    QR_CODE_BLOCK_WIDTH,
    QR_CODE_BOX_SIZE,
    QR_CODE_SIZE,
    URL,
    VOLUME_LINE_HEIGHT,
)
from .danfe_emit_info import DanfeEmitInfo
from .danfe_ident_info import DanfeIdentInfo
from .danfe_verification_msg import DanfeVerificationMsg
from .models import BaseFieldInfo, LabeledValue, ProductInfo

tp_frete = {
    "0": "0 - Remetente",
    "1": "1 - Destinatário",
    "2": "2 - Terceiros",
    "3": "3 - Próprio/Rem",
    "4": "4 - Próprio/Dest",
    "9": "9 - Sem Frete",
}

crt_description = {
    "1": "1 - SIMPLES NACIONAL",
    "2": "2 - SIMPLES NACIONAL - EXCESSO DE SUBLIMITE DE RECEITA BRUTA",
    "3": "3 - REGIME NORMAL",
    "4": "4 - SIMPLES NACIONAL - MEI",
}

RECEIPT_DEFAULT = "default"
RECEIPT_COLLECTION = "collection"
RECEIPT_DELIVERY = "delivery"

# Segment alignment that marks the gap between the two columns of a cell of
# the product table: drawn as a vertical line instead of text.
COLUMN_SEPARATOR = "column_separator"


def extract_text(node: Element, tag: str) -> str:
    return get_tag_text(node, URL, tag)


def format_optional_number(node: Element, tag: str, precision: int = 2) -> str:
    """
    Format the value of `tag`, leaving the field blank when the tag is absent
    from the XML (NT 2026.010, item 4.4: information that does not exist in the
    XML must not be printed, not even as zero).
    """
    text = extract_text(node, tag)
    return format_number(text, precision) if text else ""


def interleave(lefts, rights):
    """Read two columns line by line: lefts[0], rights[0], lefts[1], ..."""
    return [
        item for pair in zip_longest(lefts, rights) for item in pair if item is not None
    ]


def has_nonzero_value(node: Element, tags) -> bool:
    for tag in tags:
        try:
            if float(extract_text(node, tag) or 0):
                return True
        except ValueError:
            continue
    return False


class DanfeNt2026010(xFPDF):
    def __init__(self, xml, config: DanfeConfig = None):
        super().__init__(unit="mm", format="A4")
        config = config if config is not None else DanfeConfig()
        self.set_margins(
            left=config.margins.left, top=config.margins.top, right=config.margins.right
        )
        self.footer_stamp = config.footer_stamp
        self._has_footer_stamp = bool(self.footer_stamp.logo or self.footer_stamp.text)
        # Reserve space for the footer stamp inside the bottom margin so the
        # content area (eph) shrinks automatically and never overlaps the stamp.
        bottom_margin = config.margins.bottom
        if self._has_footer_stamp:
            bottom_margin += self.footer_stamp.height + self.footer_stamp.spacing
        self.set_auto_page_break(auto=False, margin=bottom_margin)
        self.set_title("DANFE")
        self.logo_image = config.logo
        self.receipt_pos = config.receipt_pos
        self.default_font = config.font_type.value
        self.default_font_factor = (
            config.font_size.value
            if self.default_font == "Times"
            else config.font_size.SMALL.value
        )
        self.price_precision = config.decimal_config.price_precision
        self.quantity_precision = config.decimal_config.quantity_precision
        self.invoice_display = config.invoice_display
        self.display_pis_cofins = config.display_pis_cofins
        self.infcpl_semicolon_newline = config.infcpl_semicolon_newline
        self.product_description_config = config.product_description_config
        self.watermark_cancelled = config.watermark_cancelled

        root = ET.fromstring(xml)
        self.inf_nfe = root.find(f"{URL}infNFe")
        self.prot_nfe = root.find(f"{URL}protNFe")

        self.emit = root.find(f"{URL}emit")
        self.ide = root.find(f"{URL}ide")
        self.dest = root.find(f"{URL}dest")
        self.retirada = root.find(f"{URL}retirada")
        self.entrega = root.find(f"{URL}entrega")
        self.totais = root.find(f"{URL}total")
        self.icms_tot = root.find(f"{URL}ICMSTot")
        self.is_tot = root.find(f"{URL}ISTot")
        self.ibscbs_tot = root.find(f"{URL}IBSCBSTot")
        self.transp = root.find(f"{URL}transp")
        self.volumes = [vol for vol in self.transp.findall(f"{URL}vol") if len(vol)]
        self.cobr = root.find(f"{URL}cobr")
        self.det = root.findall(f"{URL}det")
        self.inf_adic = root.find(f"{URL}infAdic")
        self.issqn_tot = root.find(f"{URL}ISSQNtot")
        self.crt = extract_text(self.emit, "CRT")
        qr_code = (extract_text(root, "qrCode") or "").strip()
        self.qr_code_image = None
        if qr_code:
            # no quiet zone in the image: the box around it provides one;
            # error correction level M as in NT 2026.003, item 4.4.2
            self.qr_code_image = make_qr_code_image(
                qr_code, border=0, error_correction=ERROR_CORRECT_M
            )

        self.total_receipt_height = 19  # TODO need compute

        # extract orientation: only tpImp=2 is the landscape DANFE. The other
        # formats (1 = portrait; 3 to 6 = simplified DANFE, NFC-e and DANFE
        # Simplificado Tipo 2, not generated by this class) print the regular
        # DANFE in portrait.
        tpImp = extract_text(self.ide, "tpImp")
        if tpImp == "2":
            self.orientation = "L"
            # force receipt position
            # landscape support only left receipt
            self.receipt_pos = ReceiptPosition.LEFT
        else:
            self.orientation = "P"

        # Emit. CNPJ/CPF
        self.emit_cnpj_cpf = extract_text(self.emit, "CNPJ")
        self.emit_id_label = "CNPJ"
        if not self.emit_cnpj_cpf:
            self.emit_id_label = "CPF"
            self.emit_cnpj_cpf = extract_text(self.emit, "CPF")
        self.emit_cnpj_cpf = format_cpf_cnpj(self.emit_cnpj_cpf)

        # Dest. CNPJ/CPF
        self.dest_cnpj_cpf = extract_text(self.dest, "CNPJ")
        self.dest_id_label = "CNPJ"
        if not self.dest_cnpj_cpf:
            self.dest_id_label = "CPF"
            self.dest_cnpj_cpf = extract_text(self.dest, "CPF")
        self.dest_cnpj_cpf = format_cpf_cnpj(self.dest_cnpj_cpf)

        # Extra receipt for the carrier to sign on pickup. Only printed when
        # enabled and the NF-e has a carrier (transporta) informed.
        self.receipt_kinds = [RECEIPT_DEFAULT]
        if config.carrier_receipt and self._has_carrier():
            self.receipt_kinds = [RECEIPT_COLLECTION, RECEIPT_DELIVERY]
        self.nr_nota = extract_text(self.ide, "nNF")
        self.serie_nf = extract_text(self.ide, "serie")
        self.tp_nf = extract_text(self.ide, "tpNF")
        self.key_nfe = self.inf_nfe.attrib.get("Id")[3:]
        self.prot_uso = self._get_usage_protocol()
        self.products = self._get_products_info()

        self.add_page(orientation=self.orientation)

        # simulate render for get block sizes.
        addit_data = self._get_additional_data_content()
        with self._disable_writing():
            add_data_lines, max_add_data_lines = self._draw_additional_data(addit_data)
        addit_data_current_page = add_data_lines[:max_add_data_lines]
        join_char = "\n" if self.infcpl_semicolon_newline else " "
        addit_data_current_page = join_char.join(addit_data_current_page)
        addit_data_next_pages = add_data_lines[max_add_data_lines:]
        addit_data_next_pages = join_char.join(addit_data_next_pages)
        with self._disable_writing():
            y_before = self.y
            self._draw_header()
            header_height = self.y - y_before

        # blocks before products
        with self._disable_writing():
            y_before = self.get_y()
            if self.receipt_pos == ReceiptPosition.TOP:
                self._draw_receipts()
            self._draw_header()
            self._draw_recipient_sender()
            self._draw_delivery_location()
            self._draw_billing()
            self._draw_totals()
            self._draw_issqn_calculation()
            self._draw_shipping()
            y_after = self.get_y()
        height_before = y_after - y_before

        # blocks after products
        # DADOS ADICIONAIS
        with self._disable_writing():
            y_before = self.get_y()
            self._draw_additional_data(addit_data_current_page)
            if self.receipt_pos == ReceiptPosition.BOTTOM:
                self._draw_receipts()
            y_after = self.get_y()
        height_after = y_after - y_before

        available_height_product_table = (
            self.eph - height_before - height_after - HEIGHT_FONT_BLOCK_DESC
        )

        (
            products_for_current_page,
            products_for_next_pages,
        ) = self._calculate_product_splits(
            products=self.products,
            height_product_table=available_height_product_table,
        )

        p_addit_data, addit_data_next_pages = self._split_additional_data_in_products(
            available_height_product_table,
            products_for_current_page,
            addit_data_next_pages,
        )

        # If there is a continuation of additional data and there is space left
        # below the products, write the continuation on the same page.
        # if addit_data_next_pages and not products_for_next_pages:

        # draw real pdf (first page)
        self._draw_void_watermark()
        if self.receipt_pos == ReceiptPosition.LEFT:
            self._draw_landscape_receipts()
        if self.receipt_pos == ReceiptPosition.TOP:
            self._draw_receipts()
        self._draw_header()
        self._draw_recipient_sender()
        self._draw_delivery_location()
        self._draw_billing()
        self._draw_totals()
        self._draw_issqn_calculation()
        self._draw_shipping()
        self._draw_products(
            available_height_product_table, products_for_current_page, p_addit_data
        )
        self._draw_additional_data(addit_data_current_page)
        if self.receipt_pos == ReceiptPosition.BOTTOM:
            self._draw_receipts()
        self._draw_footer_stamp()

        # draw next pages, if necessary.
        while products_for_next_pages:
            self.add_page(orientation=self.orientation)
            self._draw_void_watermark()
            self._draw_header()
            height_product_table = self.eph - header_height - HEIGHT_FONT_BLOCK_DESC
            products_for_current_page, products_for_next_pages = (
                self._calculate_product_splits(
                    products=products_for_next_pages,
                    height_product_table=height_product_table,
                )
            )
            # check if have space below products to print additional data
            p_addit_data, addit_data_next_pages = (
                self._split_additional_data_in_products(
                    available_height_product_table,
                    products_for_current_page,
                    addit_data_next_pages,
                )
            )
            self._draw_products(
                height_product_table, products_for_current_page, p_addit_data
            )
            self._draw_footer_stamp()

        while addit_data_next_pages:
            # At this point, there is no product and service block to include the
            # continuation of the additional information, and the continuation is
            # carried out on the next page with the additional data block.
            self.add_page(orientation=self.orientation)
            self._draw_void_watermark()
            self._draw_header()
            height_additional_data = self.eph - header_height
            # simulate render in temp pdf for get block sizes.
            addit_data = self._get_additional_data_content()
            with self._disable_writing():
                add_data_lines, max_add_data_lines = self._draw_additional_data(
                    addit_data_next_pages, height_additional_data
                )
            addit_data_current_page = add_data_lines[:max_add_data_lines]
            join_char = "\n" if self.infcpl_semicolon_newline else " "
            addit_data_current_page = join_char.join(addit_data_current_page)
            addit_data_next_pages = add_data_lines[max_add_data_lines:]
            addit_data_next_pages = join_char.join(addit_data_next_pages)
            self._draw_additional_data(addit_data_current_page, height_additional_data)
            self._draw_footer_stamp()

    @property
    def edw(self):
        """
        Effective danfe width:
        In landscape orientation the page width minus its horizontal margins
        and receipt width.
        """
        if self.orientation == "L" and self.page_no() == 1:
            # TODO get receipt width
            return self.epw - 19 * len(self.receipt_kinds)
        else:
            return self.epw

    def _get_usage_protocol(self):
        dt, hr = get_date_utc(extract_text(self.prot_nfe, "dhRecbto"))
        protocol = extract_text(self.prot_nfe, "nProt")
        prot_text = f"{protocol} - {dt} {hr}"
        return prot_text

    def _has_carrier(self):
        if self.transp is None:
            return False
        transporta = self.transp.find(f"{URL}transporta")
        return any(extract_text(transporta, tag) for tag in ("CNPJ", "CPF", "xNome"))

    def _get_receipt_labels(self, kind):
        """Return (text, date label, signature label) for a receipt kind."""
        text = self._get_receipt_text()
        date_label = "DATA DE RECEBIMENTO"
        sign_label = "IDENTIFICAÇÃO E ASSINATURA DO RECEBEDOR"
        if kind == RECEIPT_COLLECTION:
            transporta = self.transp.find(f"{URL}transporta")
            carrier_id = extract_text(transporta, "CNPJ")
            carrier_id_label = "CNPJ"
            if not carrier_id:
                carrier_id = extract_text(transporta, "CPF")
                carrier_id_label = "CPF"
            carrier = extract_text(transporta, "xNome")
            if carrier_id:
                carrier += f", {carrier_id_label}: {format_cpf_cnpj(carrier_id)}"
            text = f"CANHOTO DE COLETA - {text}. TRANSPORTADOR: {carrier}"
            date_label = "DATA DA COLETA"
            sign_label = "IDENTIFICAÇÃO E ASSINATURA DO TRANSPORTADOR"
        elif kind == RECEIPT_DELIVERY:
            text = f"CANHOTO DE ENTREGA - {text}"
        return text, date_label, sign_label

    def _get_receipt_text(self):
        dt, hr = get_date_utc(extract_text(self.ide, "dhEmi"))
        total_nf = format_number(extract_text(self.totais, "vNF"), precision=2)
        end = (
            f"{extract_text(self.dest,'xNome')} - "
            f"{extract_text(self.dest,'xLgr')}, "
            f"{extract_text(self.dest,'nro')}, "
            f"{extract_text(self.dest,'xBairro')}, "
            f"{extract_text(self.dest,'xMun')} - "
            f"{extract_text(self.dest,'UF')}"
        )
        receipt_text = (
            f"RECEBEMOS DE {extract_text(self.emit,'xNome')} "
            f"OS PRODUTOS/SERVIÇOS CONSTANTES DA NOTA FISCAL INDICADA "
            f"ABAIXO. EMISSÃO: {dt} VALOR TOTAL: {total_nf} DESTINATARIO: {end}"
            f", {self.dest_id_label}: {self.dest_cnpj_cpf}"
        )
        return receipt_text

    def _build_inf_ad_prod(self, prod, inf_ad_prod):
        add_infos = []

        prefix = self.product_description_config.branch_info_prefix
        prefix = f"{prefix} " if prefix else ""
        if self.product_description_config.display_branch:
            _rastros = prod.findall(f"{URL}rastro")
            for _rastro in _rastros:
                n_lote = extract_text(_rastro, "nLote")
                q_lote = format_number(
                    extract_text(_rastro, "qLote"), self.quantity_precision
                )
                d_fab, _ = get_date_utc(extract_text(_rastro, "dFab"))
                d_val, _ = get_date_utc(extract_text(_rastro, "dVal"))
                add_infos.append(
                    f"{prefix}Lote: {n_lote} Qtd: {q_lote} Fab: {d_fab} Val: {d_val}"
                )
        if self.product_description_config.display_anp:
            _combs = prod.findall(f"{URL}comb")
            for _comb in _combs:
                c_prod_anp = extract_text(_comb, "cProdANP")
                desc_anp = extract_text(_comb, "descANP")
                uf_cons = extract_text(_comb, "UFCons")
                add_infos.append(
                    f"cProdANP: {c_prod_anp} descANP: {desc_anp} UFCons: {uf_cons}"
                )
        if self.product_description_config.display_anvisa:
            _meds = prod.findall(f"{URL}med")
            for _med in _meds:
                c_prod_anvisa = extract_text(_med, "cProdANVISA")
                v_pmc = format_number(
                    extract_text(_med, "vPMC"), self.quantity_precision
                )
                add_infos.append(f"cProdANVISA: {c_prod_anvisa} PMC: {v_pmc}")
        cbenef = extract_text(prod, "cBenef")
        ccredpresumido = extract_text(prod, "cCredPresumido")

        if cbenef:
            add_infos.append(f"cBenef: {cbenef}")
        if ccredpresumido:
            add_infos.append(f"cCredPresumido: {ccredpresumido}")
        if self.product_description_config.display_xped:
            x_ped = extract_text(prod, "xPed")
            if x_ped:
                n_item_ped = extract_text(prod, "nItemPed")
                item = f" Item: {n_item_ped}" if n_item_ped else ""
                add_infos.append(f"Pedido: {x_ped}{item}")

        if self.product_description_config.display_additional_info and inf_ad_prod:
            add_infos.append(inf_ad_prod)

        add_infos_text = "\n".join(add_infos)
        return add_infos_text

    def _get_products_info(self):
        products = []
        for _det in self.det:
            el_prod = _det.find(f"{URL}prod")
            el_imp_ICMS = _det.find(f"{URL}ICMS")

            inf_ad_prod = self._build_inf_ad_prod(
                el_prod, extract_text(_det, "infAdProd")
            )
            x_prod = extract_text(el_prod, "xProd")
            description = self._merge_product_description(x_prod, inf_ad_prod)
            # NCM and the IBS/CBS tax classification go to the bottom of the
            # description (NT 2026.010, item 4.3).
            fiscal_ids = f"[NCM {extract_text(el_prod, 'NCM')}]"
            c_class_trib = extract_text(_det, "cClassTrib")
            if c_class_trib:
                fiscal_ids += f" [cClassTrib {c_class_trib}]"
            description += "\n" + fiscal_ids

            u_com = extract_text(el_prod, "uCom")
            q_com = format_number(
                extract_text(el_prod, "qCom"), self.quantity_precision
            )
            v_un_com = format_number(
                extract_text(el_prod, "vUnCom"), self.price_precision
            )

            u_trib = extract_text(el_prod, "uTrib")
            q_trib = format_number(
                extract_text(el_prod, "qTrib"), self.quantity_precision
            )
            v_un_trib = format_number(
                extract_text(el_prod, "vUnTrib"), self.price_precision
            )

            # merge commercial and taxable values
            qty_unit = merge_if_different(f"{q_com}\n{u_com}", f"{q_trib}\n{u_trib}")
            unit_price = merge_if_different(v_un_com, v_un_trib)

            # merge 'origem' with 'CST' of ICMS.
            orig = extract_text(el_imp_ICMS, "orig")
            if self.crt in ["1", "4"]:
                # Regime Simples Nacional
                cst_label = "CSOSN"
                cst = extract_text(el_imp_ICMS, "CSOSN")
            else:
                # Regime Normal
                cst_label = "CST"
                cst = extract_text(el_imp_ICMS, "CST")

            cst_cfop = [LabeledValue("CFOP", extract_text(el_prod, "CFOP"))]
            if orig + cst:
                # items of services (ISSQN) have no ICMS group
                cst_cfop.insert(0, LabeledValue(cst_label, orig + cst))

            tax_bases, tax_rates, tax_values = self._get_product_taxes(_det)
            product = ProductInfo(
                code=extract_text(el_prod, "cProd"),
                description=description,
                cst_cfop=cst_cfop,
                qty_unit=qty_unit,
                unit_price=unit_price,
                total_price=format_number(extract_text(el_prod, "vProd"), 2),
                tax_bases=tax_bases,
                tax_rates=tax_rates,
                tax_values=tax_values,
            )
            products.append(product)
        return products

    def _get_product_taxes(self, det):
        """
        Return the item's tax bases, rates and values (NT 2026.010, item 4.3).

        Only the taxes whose group is present in the item are listed, so a
        NF-e without IBS/CBS/IS keeps a compact row. Rates and values are
        split in the two columns of the reference layout, which prints them
        two per line: ICMS / CBS, IBS UF / IPI and IBS MUN / IS.
        """
        icms = det.find(f"{URL}ICMS")
        ipi = det.find(f"{URL}IPITrib")
        imp_seletivo = det.find(f"{URL}IS")
        ibscbs = det.find(f"{URL}gIBSCBS")
        ibs_uf = ibs_mun = cbs = None
        if ibscbs is not None:
            ibs_uf = ibscbs.find(f"{URL}gIBSUF")
            ibs_mun = ibscbs.find(f"{URL}gIBSMun")
            cbs = ibscbs.find(f"{URL}gCBS")

        bases = []
        if icms is not None:
            bases.append(LabeledValue("ICMS", format_optional_number(icms, "vBC")))
        if ibscbs is not None:
            bases.append(
                LabeledValue("IBS / CBS", format_optional_number(ibscbs, "vBC"))
            )
        if imp_seletivo is not None:
            bases.append(
                LabeledValue("IS", format_optional_number(imp_seletivo, "vBCIS"))
            )
        if ipi is not None:
            bases.append(LabeledValue("IPI", format_optional_number(ipi, "vBC")))
        # e.g. ICMS 40 (exempt) or 02 (single-phase, taxed by quantity) have
        # no base, rate or value to print.
        bases = [base for base in bases if base.value]

        left, right = [], []
        if icms is not None:
            left.append(("ICMS", icms, extract_text(icms, "pICMS"), "vICMS"))
        if ibscbs is not None:
            left.append(
                ("IBS UF", ibs_uf, self._ibscbs_rate(ibs_uf, "pIBSUF"), "vIBSUF")
            )
            left.append(
                ("IBS MUN", ibs_mun, self._ibscbs_rate(ibs_mun, "pIBSMun"), "vIBSMun")
            )
            right.append(("CBS", cbs, self._ibscbs_rate(cbs, "pCBS"), "vCBS"))
        if ipi is not None:
            right.append(("IPI", ipi, extract_text(ipi, "pIPI"), "vIPI"))
        if imp_seletivo is not None:
            right.append(("IS", imp_seletivo, extract_text(imp_seletivo, "pIS"), "vIS"))

        def columns(taxes):
            rates, values = [], []
            for label, group, rate, value_tag in taxes:
                rate = format_rate(rate)
                value = format_optional_number(group, value_tag)
                if rate or value:
                    rates.append(LabeledValue(label, rate))
                    values.append(LabeledValue(label, value))
            return rates, values

        left_rates, left_values = columns(left)
        right_rates, right_values = columns(right)
        return bases, (left_rates, right_rates), (left_values, right_values)

    @staticmethod
    def _ibscbs_rate(group, rate_tag):
        """
        IBS UF, IBS Município and CBS print the effective rate (pAliqEfet)
        when the rate reduction group (gRed) is informed, which also happens
        on government purchases; otherwise the regular rate.
        """
        reduction = group.find(f"{URL}gRed") if group is not None else None
        if reduction is not None:
            return extract_text(reduction, "pAliqEfet")
        return extract_text(group, rate_tag)

    def _get_additional_data_content(self):
        fisco = extract_text(self.inf_adic, "infAdFisco")
        obs = extract_text(self.inf_adic, "infCpl")
        dest_end, cpl, cpl_truncado = self._get_dest_end_text(self.dest)
        if cpl_truncado:
            obs += "Complemento do destinatário: " + cpl + "."
        extra_volumes = self.volumes[MAX_VOLUME_LINES:]
        if extra_volumes:
            obs += (
                f" Volumes {MAX_VOLUME_LINES + 1} a {len(self.volumes)}: "
                f"{describe_volumes(extra_volumes, URL)}."
            )
        if fisco:
            obs = f"{obs} {fisco}\n"

        if self.infcpl_semicolon_newline:
            obs = obs.replace(";", "\n")
        else:
            obs = " ".join(re.split(r"\s+", obs.strip(), flags=re.UNICODE))
        return obs

    def _calculate_product_splits(self, products, height_product_table):
        """
        Splits a list of products into two lists based on the maximum available
        height for a product table, ensuring that the split respects the maximum
        allowed height to prevent overlap or cutting of products in the table
        display.

        During the calculation, writing is temporarily disabled to avoid
        modifications to the current document. This allows for a simulation of
        product drawing to determine how they should be divided between pages.

        Args:
            products (list): A list of products to be drawn in the table.
                Each product should be a data structure containing necessary
                information for drawing the product in the table.
            height_product_table (float):
                The maximum available height for the product table on a single page,
                determining how the products should be divided between pages.

        Returns:
            tuple: Two lists of products, where the first list contains the
                products that fit within the available height of the current page
                and the second list contains the products that should be moved to
                the next pages. Each list contains subsets of the original product
                list, divided based on the maximum allowed height.
        """
        with self._disable_writing():
            rows_heights = self._draw_products(height_product_table, products)[0]
        product_header_height = rows_heights.pop(0)
        actual_height = product_header_height
        product_index = 0
        for i, row_height in enumerate(rows_heights):
            actual_height += row_height
            if actual_height <= height_product_table:
                product_index = i
            else:
                break
        products_for_current_page = products[: product_index + 1]
        products_for_next_pages = products[product_index + 1 :]
        return (
            products_for_current_page,
            products_for_next_pages,
        )

    def _merge_product_description(self, x_prod, inf_ad_prod):
        desc = x_prod
        if inf_ad_prod:
            desc += "\n" + inf_ad_prod
        # normalize
        # desc = " ".join(re.split(r"\s+", desc.strip(), flags=re.UNICODE))
        return desc

    def _split_additional_data_in_products(
        self,
        available_height_product_table,
        products_for_current_page,
        addit_data_next_pages,
    ):
        addit_data = None
        if addit_data_next_pages:
            with self._disable_writing():
                _, current_add_info_lines, max_add_info_lines = self._draw_products(
                    available_height_product_table,
                    products_for_current_page,
                    addit_data_next_pages,
                )
            if max_add_info_lines > 1:
                if len(current_add_info_lines) > max_add_info_lines:
                    # split
                    addit_data = current_add_info_lines[:max_add_info_lines]
                    join_char = "\n" if self.infcpl_semicolon_newline else " "
                    addit_data = join_char.join(addit_data)
                    addit_data_next_pages = current_add_info_lines[max_add_info_lines:]
                    addit_data_next_pages = join_char.join(addit_data_next_pages)
                else:
                    # not split
                    join_char = "\n" if self.infcpl_semicolon_newline else " "
                    addit_data = join_char.join(current_add_info_lines)
                    addit_data_next_pages = []
        return addit_data, addit_data_next_pages

    def _product_col_widths(self) -> tuple[float | None, ...]:
        # CÓDIGO, DESCRIÇÃO, CST/CFOP, QTD/UN, VLR UNIT, VLR TOTAL,
        # BASES DE CÁLCULO, ALÍQUOTAS, VALOR DOS TRIBUTOS
        if self.default_font_factor is FontSize.SMALL.value:
            return (13, None, 13, 15, 15, 15, 25, 28, 36)
        elif self.default_font_factor is FontSize.BIG.value:
            return (15, None, 17, 18, 18, 18, 29, 24, 28)

        raise ValueError(f"Unsupported FontSize: {self.default_font_factor}")

    def _draw_void_watermark(self):
        """
        Draw a watermark on the DANFE when the protocol is not available or
        when the environment is homologation.
        """
        is_production_environment = extract_text(self.ide, "tpAmb") == "1"
        is_protocol_available = self.prot_nfe is not None

        # Exit early if no watermark is needed
        watermark_text = None
        font_size = 60
        if self.watermark_cancelled:
            if is_production_environment:
                watermark_text = "CANCELADA"
            else:
                watermark_text = "CANCELADA - SEM VALOR FISCAL"
                font_size = 45

        elif not is_production_environment or not is_protocol_available:
            watermark_text = "SEM VALOR FISCAL"

        if watermark_text:
            self.set_font(self.default_font, "B", font_size)

            width = self.get_string_width(watermark_text)
            self.set_text_color(r=220, g=150, b=150)
            height = font_size * 0.25
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

    def _draw_landscape_receipts(self):
        # The collection receipt is the outermost one (far left), so the
        # carrier can detach it without removing the delivery receipt.
        x = self.l_margin
        for kind in self.receipt_kinds:
            self._draw_landscape_receipt(kind, x)
            x = self.x

    def _draw_receipts(self):
        # The collection receipt is the outermost one (page edge), so the
        # carrier can detach it without removing the delivery receipt.
        kinds = self.receipt_kinds
        if self.receipt_pos == ReceiptPosition.BOTTOM:
            kinds = reversed(kinds)
        for kind in kinds:
            self._draw_receipt(kind)

    def _draw_landscape_receipt(self, kind, lin):
        h_recibo = 17
        recibo_text, date_label, sign_label = self._get_receipt_labels(kind)
        self.set_dash_pattern(dash=0, gap=0)
        self.rect(x=lin, y=self.t_margin, w=h_recibo, h=self.eph, style="")

        # fields width
        w_number_field = 30
        w_date_field = 40
        w_sign_field = self.eph - w_date_field - w_number_field
        w_desc_field = w_date_field + w_sign_field

        y_number_field = self.t_margin + w_number_field
        # column partition line
        self.line(
            x1=lin,
            y1=y_number_field,
            x2=lin + h_recibo,
            y2=y_number_field,
        )

        # partition recibo in two lines
        x_line = lin + h_recibo / 2
        self.line(
            x1=x_line,
            y1=self.t_margin + w_number_field,
            x2=x_line,
            y2=self.t_margin + w_number_field + w_desc_field,
        )

        w_date_field = 40  # width of field "data de recebimento"
        # line between the field 'data' and 'assinatura'
        line_y = self.t_margin + w_number_field + w_sign_field
        self.line(x1=lin + h_recibo / 2, y1=line_y, x2=lin + h_recibo, y2=line_y)
        self.set_font(self.default_font, "", 5)
        h_text = 2
        self.set_xy(x=lin + 1, y=self.eph + h_text)
        with self.rotation(90):
            self.multi_cell(
                w=w_desc_field, h=h_text, text=recibo_text, border=0, align="L"
            )
        self.set_xy(x=lin + h_recibo / 2 + 0.5, y=self.eph + h_text)
        with self.rotation(90):
            self.cell(
                w=w_date_field,
                h=h_text,
                text=date_label,
                new_x="RIGHT",
                align="L",
            )
            self.cell(
                w=None,
                h=h_text,
                text=sign_label,
                new_x="LEFT",
                align="L",
            )

        # format nf number
        nf = f"{int(self.nr_nota):,}".replace(",", ".")

        self.set_font(self.default_font, "B", 8)
        text = f"NOTA FISCAL\n\nNº {nf}\n" f"\nSÉRIE {self.serie_nf}"
        self.text_box(
            text=text,
            text_align="C",
            w=h_recibo,
            h=w_number_field,
            h_line=3,
            x=lin,
            y=self.t_margin,
        )
        self._draw_dashed_line(distance=lin + h_recibo + 1)
        self.set_xy(x=lin + h_recibo + 2, y=self.t_margin)

    def _draw_receipt(self, kind):
        h_recibo = 17
        recibo_text, date_label, sign_label = self._get_receipt_labels(kind)
        lin = self.y
        if self.receipt_pos == ReceiptPosition.BOTTOM:
            self._draw_dashed_line(distance=self.y + 1)
            lin += 2

        self.set_dash_pattern(dash=0, gap=0)
        self.rect(x=self.l_margin, y=lin, w=self.edw, h=h_recibo, style="")

        # fields width
        w_number_field = 30
        w_date_field = 40
        w_sign_field = self.epw - w_date_field - w_number_field
        w_desc_field = w_date_field + w_sign_field

        x_number_field = self.l_margin + w_desc_field
        # column partition line
        self.line(x1=x_number_field, y1=lin, x2=x_number_field, y2=lin + h_recibo)

        # partition recibo in two lines
        self.line(self.l_margin, lin + h_recibo / 2, x_number_field, lin + 8.5)

        w_date_field = 40  # width of field "data de recebimento"
        # line between the field 'data' and 'assinatura'
        line_y = self.l_margin + w_date_field
        self.line(line_y, lin + h_recibo / 2, line_y, lin + h_recibo)

        self.set_font(self.default_font, "", self.get_font_size("RECEIPT_FONT", True))

        self.set_xy(x=self.l_margin, y=lin + 1)
        self.multi_cell(w=w_desc_field, h=None, text=recibo_text, border=0, align="L")
        self.set_xy(x=self.l_margin, y=lin + h_recibo / 2 + 0.5)
        self.cell(w=w_date_field, h=None, text=date_label, new_x="RIGHT", align="L")
        self.cell(
            w=None,
            h=None,
            text=sign_label,
            new_x="LEFT",
            align="L",
        )

        self.set_font(self.default_font, "B", 10)
        self.set_xy(x=x_number_field, y=lin + 0.5)
        self.cell(
            w=w_number_field,
            h=None,
            text="NF-e",
            new_x="LEFT",
            new_y="NEXT",
            align="C",
        )
        nf = f"{int(self.nr_nota):011,}".replace(",", ".")
        self.cell(
            w=w_number_field,
            h=6,
            text=f"Nº{nf}",
            new_x="LEFT",
            new_y="NEXT",
            align="C",
        )
        self.cell(
            w=w_number_field,
            h=None,
            text=f"SÉRIE {self.serie_nf}",
            align="C",
        )
        if self.receipt_pos == ReceiptPosition.TOP:
            self._draw_dashed_line(distance=lin + h_recibo + 1)
            lin += 2
        self.set_xy(x=self.l_margin, y=lin + h_recibo)

    def _draw_header(self):
        # pre-definitions
        w_ident_box = 33
        w_code_box = 88
        w_emit_box = self.edw - w_ident_box - w_code_box
        h_emit_box = 31
        old_y = self.get_y()
        emit_name = extract_text(self.emit, "xNome")
        cep = format_cep(extract_text(self.emit, "CEP"))
        fone = format_phone(extract_text(self.emit, "fone"))
        xCpl = (
            f"{extract_text(self.emit, 'xCpl')}\n"
            if extract_text(self.emit, "xCpl")
            else ""
        )
        address = (
            f"{extract_text(self.emit,'xLgr')}, "
            f"{extract_text(self.emit,'nro')}\n"
            f"{xCpl}"
            f"{extract_text(self.emit,'xBairro')}\n"
            f"{extract_text(self.emit,'xMun')} - "
            f"{extract_text(self.emit,'UF')}\n"
            f"{cep}\nFone: {fone}"
        )
        b_emit = DanfeBlock(pdf=self)
        e_emit_info = DanfeEmitInfo(
            h=h_emit_box,
            w=w_emit_box,
            new_x="RIGHT",
            new_y="TOP",
            emit=emit_name,
            logo_image=self.logo_image,
            address=address,
            pdf=self,
        )
        b_emit.add_field(e_emit_info)
        e_ident_info = DanfeIdentInfo(
            h=h_emit_box,
            w=w_ident_box,
            new_x="RIGHT",
            new_y="TOP",
            serie_nf=self.serie_nf,
            nr_nota=self.nr_nota,
            tp_nf=self.tp_nf,
            pdf=self,
        )
        b_emit.add_field(e_ident_info)
        e_danfe_code = DanfeCode(
            h=10,
            w=w_code_box,
            new_x="LEFT",
            new_y="BOTTOM",
            key_nfe=self.key_nfe,
            pdf=self,
        )
        b_emit.add_field(e_danfe_code)
        f_chave_acesso = DanfeBasicField(
            w=w_code_box,
            description="CHAVE DE ACESSO",
            content=" ".join(chunks(self.key_nfe, 4)),
            type="chave_acesso",
            new_x="LEFT",
            new_y="BOTTOM",
            pdf=self,
        )
        b_emit.add_field(f_chave_acesso)
        f_autenticidade_msg = DanfeVerificationMsg(
            w=f_chave_acesso.w, h=15, new_x="L_BLOCK", new_y="BOTTOM", pdf=self
        )
        b_emit.add_field(f_autenticidade_msg)

        self.y = old_y + h_emit_box
        text_nat_op = extract_text(self.ide, "natOp")
        f_nat_op = DanfeBasicField(
            w=w_emit_box + w_ident_box,
            description="NATUREZA DA OPERAÇÃO",
            content=text_nat_op,
            pdf=self,
        )
        b_emit.add_field(f_nat_op)
        f_prot = DanfeBasicField(
            w=w_code_box,
            description="PROTOCOLO DE AUTORIZAÇÃO DE USO",
            content=self.prot_uso,
            type="protocolo",
            new_x="L_BLOCK",
            new_y="BOTTOM",
            pdf=self,
        )
        b_emit.add_field(f_prot)
        f_emit_ie = DanfeBasicField(
            w=b_emit.w / 3,
            description="INSCRIÇÃO ESTADUAL",
            content=extract_text(self.emit, "IE"),
            pdf=self,
        )
        b_emit.add_field(f_emit_ie)
        f_emit_ie_st = DanfeBasicField(
            w=b_emit.w / 3,
            description="INSCRIÇÃO ESTADUAL DO SUBST. TRIB",
            content=extract_text(self.emit, "IEST"),
            pdf=self,
        )
        b_emit.add_field(f_emit_ie_st)
        f_emit_cnpj = DanfeBasicField(
            w=b_emit.w - f_emit_ie.w - f_emit_ie_st.w,
            description="CNPJ / CPF",
            content=self.emit_cnpj_cpf,
            pdf=self,
        )
        b_emit.add_field(f_emit_cnpj)
        f_emit_crt = DanfeBasicField(
            w=b_emit.w / 2,
            description="CÓDIGO DO REGIME TRIBUTÁRIO",
            content=crt_description.get(self.crt, self.crt),
            pdf=self,
        )
        b_emit.add_field(f_emit_crt)
        # Reserved by NT 2026.010 (item 4.2): stays blank until a future NT
        # defines the XML tag that carries this information.
        b_emit.add_field(
            DanfeBasicField(
                w=b_emit.w - f_emit_crt.w,
                description="TIPO DE REGIME DE APURAÇÃO DO IBS E DA CBS",
                content="",
                pdf=self,
            )
        )
        b_emit.render()

    def _draw_recipient_sender(self):
        # get content data
        if extract_text(self.ide, "tpAmb") == "1":
            dest_name = extract_text(self.dest, "xNome")
        else:
            dest_name = "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
        dest_cnpj_cpf = extract_text(self.dest, "CNPJ")
        if not dest_cnpj_cpf:
            dest_cnpj_cpf = extract_text(self.dest, "CPF")
        dest_cnpj_cpf = format_cpf_cnpj(dest_cnpj_cpf)
        date_emi, time_emi = get_date_utc(extract_text(self.ide, "dhEmi"))
        dest_end = self._get_dest_end_text(self.dest)[0]
        dest_bairro = extract_text(self.dest, "xBairro")
        dest_cep = extract_text(self.dest, "CEP")
        dest_cep = format_cep(dest_cep)
        date_sai_ent, time_sai_ent = get_date_utc(extract_text(self.ide, "dhSaiEnt"))
        dest_mun = extract_text(self.dest, "xMun")
        dest_fone = extract_text(self.dest, "fone")
        dest_fone = format_phone(dest_fone)
        dest_uf = extract_text(self.dest, "UF")
        dest_ie = extract_text(self.dest, "IE")

        block_dest = DanfeBlock(
            description="DESTINATÁRIO / REMETENTE",
            pdf=self,
        )

        # pre-definitions line 1
        w_dest_cnpj = 35
        w_data_emi = 30
        w_dest_name = block_dest.w - w_dest_cnpj - w_data_emi

        block_dest.add_field(
            DanfeBasicField(
                w=w_dest_name,
                description="NOME / RAZÃO SOCIAL",
                content=dest_name,
                pdf=self,
            )
        )
        block_dest.add_field(
            DanfeBasicField(
                w=w_dest_cnpj, description="CNPJ / CPF", content=dest_cnpj_cpf, pdf=self
            )
        )
        block_dest.add_field(
            DanfeBasicField(
                w=w_data_emi,
                description="DATA DA EMISSÃO",
                content=date_emi,
                new_x="L_BLOCK",
                new_y="BOTTOM",
                pdf=self,
            )
        )

        # pre-definitions line 2
        w_dest_bairro = 50
        w_data_cep = 25
        w_data_ent_sai = 30
        w_dest_end = block_dest.w - w_dest_bairro - w_data_cep - w_data_ent_sai

        block_dest.add_field(
            DanfeBasicField(
                w=w_dest_end,
                description="ENDEREÇO",
                content=self.long_field(
                    text=dest_end,
                    limit=w_dest_end,
                    font_size=self.get_font_size("FONT_SIZE_CONT", True),
                ),
                pdf=self,
            )
        )
        block_dest.add_field(
            DanfeBasicField(
                w=w_dest_bairro,
                description="BAIRRO / DISTRITO",
                content=dest_bairro,
                pdf=self,
            )
        )
        block_dest.add_field(
            DanfeBasicField(w=w_data_cep, description="CEP", content=dest_cep, pdf=self)
        )
        block_dest.add_field(
            DanfeBasicField(
                w=w_data_ent_sai,
                description="DATA DA ENTRADA / SAÍDA",
                content=date_sai_ent,
                new_x="L_BLOCK",
                new_y="BOTTOM",
                pdf=self,
            )
        )

        widths_3 = {"fone": 40, "uf": 10, "ie": 50, "hora_emit": 30}
        width_disponible = block_dest.w - sum(widths_3.values())
        widths_3["municipio"] = width_disponible

        block_dest.add_field(
            DanfeBasicField(
                w=widths_3["municipio"],
                description="MUNICÍPIO",
                content=dest_mun,
                pdf=self,
            )
        )
        block_dest.add_field(
            DanfeBasicField(
                w=widths_3["fone"],
                description="FONE / FAX",
                content=dest_fone,
                pdf=self,
            )
        )
        block_dest.add_field(
            DanfeBasicField(
                w=widths_3["uf"], description="UF", content=dest_uf, pdf=self
            )
        )
        block_dest.add_field(
            DanfeBasicField(
                w=widths_3["ie"],
                description="INSCRIÇÃO ESTADUAL",
                content=dest_ie,
                pdf=self,
            )
        )
        block_dest.add_field(
            DanfeBasicField(
                w=widths_3["hora_emit"],
                description="HORA DE ENTRADA / SAÍDA",
                content=time_sai_ent,
                pdf=self,
            )
        )
        block_dest.render()

    def _draw_delivery_location(self):
        if self.retirada is not None and len(self.retirada):
            self._draw_location_block(self.retirada, "INFORMAÇÕES DO LOCAL DE RETIRADA")
        if self.entrega is not None and len(self.entrega):
            self._draw_location_block(self.entrega, "INFORMAÇÕES DO LOCAL DE ENTREGA")

    def _draw_location_block(self, elem, description):
        # Get Content Data
        name = extract_text(elem, "xNome")
        cnpj_cpf = extract_text(elem, "CNPJ")
        if not cnpj_cpf:
            cnpj_cpf = extract_text(elem, "CPF")
        cnpj_cpf = format_cpf_cnpj(cnpj_cpf)
        ie = extract_text(elem, "IE")
        endereco = self._get_dest_end_text(elem)[0]

        bairro = extract_text(elem, "xBairro")
        cep = extract_text(elem, "CEP")
        cep = format_cep(cep)
        municipio = extract_text(elem, "xMun")
        uf = extract_text(elem, "UF")
        fone = extract_text(elem, "fone")
        fone = format_phone(fone)

        # BLOCO LOCAL DE ENTREGA OU RETIRADA
        block_entrega = DanfeBlock(
            description=description,
            pdf=self,
        )

        # sizes pre-definitions
        widths = {
            "line1": {"cnpj_cpf": 35, "ie": 30},
            "line2": {"bairro": 75, "cep": 30},
            "line3": {
                "fone": 30,
                "uf": 10,
            },
        }
        widths["line1"]["name"] = block_entrega.w - sum(widths["line1"].values())
        widths["line2"]["endereco"] = block_entrega.w - sum(widths["line2"].values())
        widths["line3"]["municipio"] = block_entrega.w - sum(widths["line3"].values())

        block_entrega.add_field(
            DanfeBasicField(
                w=widths["line1"]["name"],
                description="NOME / RAZÃO SOCIAL",
                content=name,
                pdf=self,
            )
        )
        block_entrega.add_field(
            DanfeBasicField(
                w=widths["line1"]["cnpj_cpf"],
                description="CNPJ / CPF",
                content=cnpj_cpf,
                pdf=self,
            )
        )
        block_entrega.add_field(
            DanfeBasicField(
                w=widths["line1"]["ie"],
                description="IE",
                content=ie,
                new_x="L_BLOCK",
                new_y="BOTTOM",
                pdf=self,
            )
        )
        block_entrega.add_field(
            DanfeBasicField(
                w=widths["line2"]["endereco"],
                description="ENDEREÇO",
                content=self.long_field(
                    text=endereco,
                    limit=widths["line2"]["endereco"],
                    font_size=self.get_font_size("FONT_SIZE_CONT", True),
                ),
                pdf=self,
            )
        )
        block_entrega.add_field(
            DanfeBasicField(
                w=widths["line2"]["bairro"],
                description="BAIRRO / DISTRITO",
                content=bairro,
                pdf=self,
            )
        )
        block_entrega.add_field(
            DanfeBasicField(
                w=widths["line2"]["cep"],
                description="CEP",
                new_x="L_BLOCK",
                new_y="BOTTOM",
                content=cep,
                pdf=self,
            )
        )
        block_entrega.add_field(
            DanfeBasicField(
                w=widths["line3"]["municipio"],
                description="MUNICÍPIO",
                content=municipio,
                pdf=self,
            )
        )
        block_entrega.add_field(
            DanfeBasicField(
                w=widths["line3"]["uf"], description="UF", content=uf, pdf=self
            )
        )
        block_entrega.add_field(
            DanfeBasicField(
                w=widths["line3"]["fone"], description="FONE", content=fone, pdf=self
            )
        )
        block_entrega.render()

    def _draw_billing(self):
        if self.cobr is None:
            # Skip
            return

        # Fatura Block
        block_fatura = DanfeBlock(
            description="FATURA / DUPLICATAS",
            pdf=self,
        )

        fat = self.cobr.find(f"{URL}fat")
        dup = self.cobr.findall(f"{URL}dup")

        # Content Data
        numero = extract_text(fat, "nFat")
        valor_original = format_number(extract_text(fat, "vOrig"), 2)
        Valor_desconto = format_number(extract_text(fat, "vDesc"), 2)
        valor_liquido = format_number(extract_text(fat, "vLiq"), 2)

        # Pre Definitions Sizes
        w_numero = w_original = w_desconto = block_fatura.w / 4
        w_liquido = block_fatura.w - w_numero - w_original - w_desconto

        if self.invoice_display == InvoiceDisplay.FULL_DETAILS:
            block_fatura.add_field(
                DanfeBasicField(
                    w=w_numero, description="NÚMERO", content=numero, pdf=self
                )
            )
            block_fatura.add_field(
                DanfeBasicField(
                    w=w_original,
                    type="number",
                    description="VALOR ORIGINAL",
                    content=valor_original,
                    pdf=self,
                )
            )
            block_fatura.add_field(
                DanfeBasicField(
                    w=w_desconto,
                    type="number",
                    description="VALOR DO DESCONTO",
                    content=Valor_desconto,
                    pdf=self,
                )
            )
            block_fatura.add_field(
                DanfeBasicField(
                    w=w_liquido,
                    type="number",
                    description="VALOR LÍQUIDO",
                    content=valor_liquido,
                    pdf=self,
                )
            )
        block_fatura.render()

        if not dup:
            # Skip
            return

        self.set_font(
            self.default_font, "", self.get_font_size("FONT_DUPLICATES", True)
        )
        dups_text = []
        max_width = 0.0

        # Single loop to create `duplicatas` texts and find the maximum width
        for _item_dup in dup:
            num = extract_text(_item_dup, "nDup")
            venc = extract_text(_item_dup, "dVenc")
            venc, hr = get_date_utc(venc)
            valor = extract_text(_item_dup, "vDup")
            valor = format_number(valor, 2)
            dup_text = f"{num}  {venc}  {valor}"
            dups_text.append(dup_text)
            w_dup_text = self.get_string_width(dup_text) + 2
            max_width = max(max_width, w_dup_text)

        # Calculates the number of `duplicatas` that can fit in one line,
        # based on the maximum width
        qty_dup_line = int(block_fatura.w / max_width)

        # Division and display of `duplicatas` by lines
        for i in range(0, len(dups_text), qty_dup_line):
            line_dups = dups_text[i : i + qty_dup_line]
            # Fill the remaining cells of the line with empty text,
            # if necessary
            line_dups += [""] * (qty_dup_line - len(line_dups))
            old_x = self.x
            for _y, dup_text in enumerate(line_dups):
                self.cell(
                    block_fatura.w / qty_dup_line,
                    3,
                    dup_text,
                    border=1,
                    align="L",
                )
            self.ln()  # Line break after each group of `duplicatas`
            self.x = old_x  # fix start left position

    def _draw_totals(self):
        # The reference layout of NT 2026.010 replaces the "CÁLCULO DO IMPOSTO"
        # block by the totals of the note, of ICMS/IPI and, new in item 4.1,
        # of IBS/CBS/IS.
        self._draw_totals_block(
            "TOTAL DOS PRODUTOS E TOTAL DA NOTA", self._get_note_totals_lines()
        )
        self._draw_totals_block("TOTAL DO ICMS / IPI", self._get_icms_ipi_lines())
        self._draw_totals_block("TOTAL DO IBS / CBS / IS", self._get_ibs_cbs_is_lines())

    def _draw_totals_block(self, description, lines):
        block = DanfeBlock(
            description=description,
            rows_heights=(DEFAULT_FIELD_HEIGHT,) * len(lines),
            pdf=self,
        )
        block.add_fields(
            [
                [
                    BaseFieldInfo(
                        w=0, description=label, content=content, type="number"
                    )
                    for label, content in line
                ]
                for line in lines
            ]
        )
        block.render()

    def _get_note_totals_lines(self):
        def total(tag):
            return format_optional_number(self.icms_tot, tag)

        line2 = []
        if extract_text(self.icms_tot, "vTotTrib"):
            line2.append(("VALOR APROX. TRIBUTOS", total("vTotTrib")))
        if self.display_pis_cofins:
            line2.append(("VALOR DO PIS", total("vPIS")))
            line2.append(("VALOR DA COFINS", total("vCOFINS")))
        line2.append(("VALOR TOTAL DA NOTA", total("vNF")))
        return [
            [
                ("VALOR TOTAL DOS PRODUTOS", total("vProd")),
                ("VALOR DO FRETE", total("vFrete")),
                ("VALOR DO SEGURO", total("vSeg")),
                ("DESCONTO", total("vDesc")),
                ("OUTRAS DESPESAS ACESSÓRIAS", total("vOutro")),
            ],
            line2,
        ]

    def _get_icms_ipi_lines(self):
        def total(tag):
            return format_optional_number(self.icms_tot, tag)

        lines = [
            [
                ("BASE DE CÁLCULO DO ICMS", total("vBC")),
                ("VALOR DO ICMS", total("vICMS")),
                ("BASE DE CÁLCULO DO ICMS ST", total("vBCST")),
                ("VALOR DO ICMS ST", total("vST")),
                ("VALOR DO IPI", total("vIPI")),
            ]
        ]
        # Optional lines (NT 2026.010, item 4.4): printed only when the NF-e
        # carries a non-zero value for at least one of their fields.
        fcp_line = [
            ("VALOR DO FCP", "vFCP"),
            ("VALOR DO FCP RETIDO POR ST", "vFCPST"),
            ("VALOR DO DIFAL NA UF DE DESTINO", "vICMSUFDest"),
            ("VALOR DO FCP NA UF DE DESTINO", "vFCPUFDest"),
        ]
        mono_line = [
            ("BC DO ICMS MONOFÁSICO", "qBCMono"),
            ("VALOR DO ICMS MONOFÁSICO", "vICMSMono"),
            ("BC DO ICMS MONOFÁSICO POR RETENÇÃO", "qBCMonoReten"),
            ("VALOR DO ICMS MONOFÁSICO POR RETENÇÃO", "vICMSMonoReten"),
        ]
        for line in (fcp_line, mono_line):
            if has_nonzero_value(self.icms_tot, [tag for _, tag in line]):
                lines.append([(label, total(tag)) for label, tag in line])
        return lines

    def _get_ibs_cbs_is_lines(self):
        def total(tag):
            return format_optional_number(self.ibscbs_tot, tag)

        lines = [
            [
                ("VALOR DA CBS", total("vCBS")),
                ("VALOR DO IBS UF", total("vIBSUF")),
                ("VALOR DO IBS MUNICÍPIO", total("vIBSMun")),
                (
                    "VALOR DO IMPOSTO SELETIVO",
                    format_optional_number(self.is_tot, "vIS"),
                ),
            ]
        ]
        g_mono = None
        if self.ibscbs_tot is not None:
            g_mono = self.ibscbs_tot.find(f"{URL}gMono")
        if g_mono is not None:
            lines.append(
                [
                    ("VALOR DO IBS MONOFÁSICO", total("vIBSMono")),
                    ("VALOR DA CBS MONOFÁSICA", total("vCBSMono")),
                    ("VALOR DO IBS MONOFÁSICO POR RETENÇÃO", total("vIBSMonoReten")),
                    ("VALOR DA CBS MONOFÁSICA POR RETENÇÃO", total("vCBSMonoReten")),
                ]
            )
        return lines

    def _draw_shipping(self):
        block_transporte = DanfeBlock(
            description="TRANSPORTADOR / VOLUMES TRANSPORTADOS",
            pdf=self,
        )
        self.set_font(self.default_font, style="", size=5)

        # Content Data
        tp_frete_text = tp_frete[extract_text(self.transp, "modFrete")]
        transporta = self.transp.find(f"{URL}transporta")
        cnpj_cpf = extract_text(transporta, "CNPJ")
        if not cnpj_cpf:
            cnpj_cpf = extract_text(transporta, "CPF")
        cnpj_cpf = format_cpf_cnpj(cnpj_cpf)
        name = extract_text(transporta, "xNome")
        name = self.long_field(text=name, limit=60)
        ie = extract_text(transporta, "IE")
        ender = extract_text(transporta, "xEnder")
        ender = self.long_field(text=ender, limit=60)
        municipio = extract_text(transporta, "xMun")
        municipio = self.long_field(text=municipio, limit=60)
        uf = extract_text(transporta, "UF")
        veic_transp = self.transp.find(f"{URL}veicTransp")
        veic_placa = extract_text(veic_transp, "placa")
        veic_uf = extract_text(veic_transp, "UF")
        veic_rntc = extract_text(veic_transp, "RNTC")

        fields_line1 = [
            BaseFieldInfo(w=0, description="NOME / RAZÃO SOCIAL", content=name),
            BaseFieldInfo(w=28, description="FRETE POR CONTA", content=tp_frete_text),
            BaseFieldInfo(w=18, description="CÓDIGO ANTT", content=veic_rntc),
            BaseFieldInfo(w=23, description="PLACA DO VEÍCULO", content=veic_placa),
            BaseFieldInfo(w=8, description="UF", content=veic_uf),
            BaseFieldInfo(w=30, description="CNPJ / CPF", content=cnpj_cpf),
        ]

        w_transp_mun = 69
        w_transp_uf = 8
        w_transp_ie = 30
        w_transp_ender = block_transporte.w - w_transp_mun - w_transp_uf - w_transp_ie

        fields_line2 = [
            BaseFieldInfo(
                w=0,
                description="ENDEREÇO",
                content=self.long_field(
                    text=ender,
                    limit=w_transp_ender,
                    font_size=self.get_font_size("FONT_SIZE_CONT", True),
                ),
            ),
            BaseFieldInfo(w=w_transp_mun, description="MUNICÍPIO", content=municipio),
            BaseFieldInfo(w=w_transp_uf, description="UF", content=uf),
            BaseFieldInfo(w=w_transp_ie, description="INSCRIÇÃO ESTADUAL", content=ie),
        ]

        # The carrier and volume details are printed only when the NF-e has
        # them (NT 2026.010, item 4.4); the freight mode is always printed.
        # One line per vol group, as ACBr does: the first one with the labels
        # and the next ones with the values only. Beyond MAX_VOLUME_LINES the
        # volumes go to the additional data.
        lines = [fields_line1]
        if transporta is not None and len(transporta):
            lines.append(fields_line2)
        shown = self.volumes[:MAX_VOLUME_LINES]
        lines.extend(
            self._volume_fields(vol, labels=i == 0) for i, vol in enumerate(shown)
        )
        extra = max(len(shown) - 1, 0)
        block_transporte.rows_heights = (DEFAULT_FIELD_HEIGHT,) * (
            len(lines) - extra
        ) + (VOLUME_LINE_HEIGHT,) * extra
        block_transporte.add_fields(lines)
        block_transporte.render()

    def _volume_fields(self, vol, labels=True):
        def label(text):
            return text if labels else ""

        peso_b = format_number(extract_text(vol, "pesoB"), precision=3)
        peso_l = format_number(extract_text(vol, "pesoL"), precision=3)
        return [
            BaseFieldInfo(
                w=25, description=label("QUANTIDADE"), content=extract_text(vol, "qVol")
            ),
            BaseFieldInfo(
                w=30, description=label("ESPÉCIE"), content=extract_text(vol, "esp")
            ),
            BaseFieldInfo(
                w=30, description=label("MARCA"), content=extract_text(vol, "marca")
            ),
            BaseFieldInfo(
                w=45, description=label("NUMERAÇÃO"), content=extract_text(vol, "nVol")
            ),
            BaseFieldInfo(w=0, description=label("PESO BRUTO"), content=peso_b),
            BaseFieldInfo(w=0, description=label("PESO LÍQUIDO"), content=peso_l),
        ]

    def _draw_products(self, height_product_table, products, additional_data=""):
        DanfeBlock(
            description="DADOS DOS PRODUTOS / SERVIÇOS",
            pdf=self,
        ).render()
        col_widths = self._product_col_widths()
        none_width = self.edw - sum(filter(None, col_widths))
        col_widths = [w if w is not None else none_width for w in col_widths]
        y_before = self.get_y()
        x_before = self.get_x()

        # The cells are padded by PRODUCT_CELL_PADDING, so the text is placed
        # without fpdf2's own interior cell margin.
        c_margin = self.c_margin
        self.c_margin = 0
        rows_heights = [self._draw_product_header(col_widths)]
        for product in products:
            rows_heights.append(self._draw_product_row(product, col_widths))
        self.c_margin = c_margin
        self.x = x_before

        product_height = self.get_y() - y_before
        h = height_product_table - product_height

        old_y = self.get_y()
        add_info_lines = max_add_info_lines = None
        if additional_data:
            add_info_field = DanfeBasicField(
                description="CONTINUAÇÃO DAS INFORMAÇÕES COMPLEMENTARES",
                content=additional_data,
                h=h,
                pdf=self,
                w=self.edw,
                x=self.get_x(),
                y=self.y,
            )
            add_info_field.render()
            add_info_lines = add_info_field.get_content_lines()
            max_add_info_lines = add_info_field.get_max_content_lines()
        else:
            self.rect(x=self.x, y=self.y, w=self.edw, h=h)
        self.y = old_y + h
        self.x = x_before

        return rows_heights, add_info_lines, max_add_info_lines

    def _draw_product_header(self, col_widths):
        cst_title = "CSOSN / CFOP" if self.crt in ["1", "4"] else "CST / CFOP"
        titles = (
            "CÓDIGO",
            "DESCRIÇÃO DO PRODUTO / SERVIÇO",
            cst_title,
            "QTD / UN",
            "VLR UNIT",
            "VLR TOTAL",
            "BASES DE CÁLCULO",
            "ALÍQUOTAS",
            "VALOR DOS TRIBUTOS",
        )
        self.set_font(self.default_font, "B", 5)
        line_h = PRODUCT_HEADER_LINE_HEIGHT
        titles_lines = [
            self._split_text_lines(title, w - 2 * PRODUCT_CELL_PADDING)
            for title, w in zip(titles, col_widths, strict=True)
        ]
        height = (
            max(len(lines) for lines in titles_lines) * line_h
            + 2 * PRODUCT_CELL_PADDING
        )
        x, y = self.get_x(), self.get_y()
        for w, lines in zip(col_widths, titles_lines, strict=True):
            self.rect(x=x, y=y, w=w, h=height)
            # vertically centered
            y_text = y + (height - len(lines) * line_h) / 2
            for i, line in enumerate(lines):
                self.set_xy(x=x, y=y_text + i * line_h)
                self.cell(w=w, h=line_h, text=line, align="C")
            x += w
        self.set_xy(x=x - sum(col_widths), y=y + height)
        return height

    def _draw_product_row(self, product, col_widths):
        self.set_font(
            self.default_font, "", self.get_font_size("PRODUCT_DESCRIPTION", True)
        )
        line_h = PRODUCT_LINE_HEIGHT * self.default_font_factor
        inner_widths = [w - 2 * PRODUCT_CELL_PADDING for w in col_widths]
        (
            w_code,
            w_desc,
            w_cst_cfop,
            w_qty,
            w_unit_price,
            w_total,
            w_bases,
            w_rates,
            w_values,
        ) = inner_widths

        # ALÍQUOTAS and VALOR DOS TRIBUTOS share the same order of taxes, so
        # both are printed in two columns only when both fit that way.
        tax_rates = self._labeled_lines_paired(*product.tax_rates, w_rates)
        tax_values = self._labeled_lines_paired(*product.tax_values, w_values)
        if tax_rates is None or tax_values is None:
            tax_rates = self._labeled_lines(interleave(*product.tax_rates), w_rates)
            tax_values = self._labeled_lines(interleave(*product.tax_values), w_values)

        cells = [
            self._text_lines(product.code, w_code, "L"),
            self._text_lines(product.description, w_desc, "L"),
            self._labeled_lines(product.cst_cfop, w_cst_cfop),
            self._text_lines(product.qty_unit, w_qty, "C"),
            self._text_lines(product.unit_price, w_unit_price, "R"),
            self._text_lines(product.total_price, w_total, "R"),
            self._labeled_lines(product.tax_bases, w_bases),
            tax_rates,
            tax_values,
        ]
        height = max(1, *(len(lines) for lines in cells)) * line_h
        height += 2 * PRODUCT_CELL_PADDING

        x, y = self.get_x(), self.get_y()
        for w, lines in zip(col_widths, cells, strict=True):
            self.rect(x=x, y=y, w=w, h=height)
            x_inner = x + PRODUCT_CELL_PADDING
            separators = set()
            for i, segments in enumerate(lines):
                y_line = y + PRODUCT_CELL_PADDING + i * line_h
                for x_offset, w_segment, text, align in segments:
                    if align == COLUMN_SEPARATOR:
                        separators.add(x_inner + x_offset + w_segment / 2)
                    elif text:
                        self.set_xy(x=x_inner + x_offset, y=y_line)
                        self.cell(w=w_segment, h=line_h, text=text, align=align)
            if separators:
                with self.local_context(line_width=0.1):
                    for x_separator in separators:
                        self.line(x_separator, y, x_separator, y + height)
            x += w
        self.set_xy(x=x - sum(col_widths), y=y + height)
        return height

    def _split_text_lines(self, text, width):
        return self.multi_cell(
            w=width,
            h=1,
            text=text,
            dry_run=True,
            output=MethodReturnValue.LINES,
        )

    def _text_lines(self, text, width, align):
        """Wrap `text` and return its lines as drawable segments."""
        if not text:
            return []
        return [
            [(0, width, line, align)] for line in self._split_text_lines(text, width)
        ]

    def _labeled_width(self, item):
        width = self.get_string_width(item.label)
        if item.value:
            # at least one space between the label and the value
            width += self.get_string_width(" ") + self.get_string_width(item.value)
        return width

    @staticmethod
    def _labeled_segments(item, x, width):
        """Label on the left and value on the right, as in "ICMS   1.234,56"."""
        return [(x, width, item.label, "L"), (x, width, item.value, "R")]

    def _labeled_lines(self, items, width):
        """One labeled value per line; the value wraps if it does not fit."""
        lines = []
        for item in items:
            if self._labeled_width(item) <= width:
                lines.append(self._labeled_segments(item, 0, width))
            else:
                lines.append([(0, width, item.label, "L")])
                if item.value:
                    lines.append([(0, width, item.value, "R")])
        return lines

    def _labeled_lines_paired(self, lefts, rights, width):
        """
        Two columns of labeled values split by a vertical line, as in
        "ICMS  12,00% | CBS  0,90%". Return None when they do not fit in `width`.
        """
        if not lefts or not rights:
            # a single column: no line, values on the right edge
            return self._labeled_lines(lefts or rights, width)
        w_separator = self.get_string_width(" " * 3)
        w_left = max((self._labeled_width(item) for item in lefts), default=0)
        w_right = max((self._labeled_width(item) for item in rights), default=0)
        slack = width - w_left - w_separator - w_right
        if slack < 0:
            return None
        w_left += slack / 2
        x_right = w_left + w_separator
        lines = []
        for left, right in zip_longest(lefts, rights):
            segments = []
            if left is not None:
                segments += self._labeled_segments(left, 0, w_left)
            if left is not None and right is not None:
                segments.append((w_left, w_separator, "", COLUMN_SEPARATOR))
            if right is not None:
                segments += self._labeled_segments(right, x_right, width - x_right)
            lines.append(segments)
        return lines

    def _draw_issqn_calculation(self):
        if self.issqn_tot is None:
            return
        block_issqn = DanfeBlock(
            rows_heights=(DEFAULT_FIELD_HEIGHT,),
            description="CÁLCULO DO ISSQN",
            pdf=self,
        )
        fields = [
            BaseFieldInfo(
                w=0,
                description="INSCRIÇÃO MUNICIPAL",
                content=extract_text(self.emit, "IM"),
            ),
            BaseFieldInfo(
                w=0,
                description="VALOR TOTAL DOS SERVIÇOS",
                content=format_optional_number(self.issqn_tot, "vServ"),
                type="number",
            ),
            BaseFieldInfo(
                w=0,
                description="BASE DE CÁLCULO DO ISSQN",
                content=format_optional_number(self.issqn_tot, "vBC"),
                type="number",
            ),
            BaseFieldInfo(
                w=0,
                description="VALOR DO ISSQN",
                content=format_optional_number(self.issqn_tot, "vISS"),
                type="number",
            ),
        ]
        block_issqn.add_fields([fields])
        block_issqn.render()

    def _draw_additional_data(self, additional_data, continuation_height=None):
        block_adic = DanfeBlock(
            description="DADOS ADICIONAIS",
            pdf=self,
        )
        height = (
            continuation_height - HEIGHT_FONT_BLOCK_DESC if continuation_height else 20
        )
        draw_qr_code = self.qr_code_image is not None and not continuation_height
        if draw_qr_code:
            block_adic.w -= QR_CODE_BLOCK_WIDTH + QR_CODE_BLOCK_GAP
            height = max(height, QR_CODE_BOX_SIZE)
        block_adic.rows_heights = (height,)
        if not continuation_height:
            fields = [
                BaseFieldInfo(
                    w=0,
                    description="INFORMAÇÕES COMPLEMENTARES",
                    content=additional_data,
                    type="info_complementares",
                ),
                BaseFieldInfo(w=70, description="RESERVADO AO FISCO", content=""),
            ]
        else:
            fields = [
                BaseFieldInfo(
                    w=0,
                    description="CONTINUAÇÃO INFORMAÇÕES COMPLEMENTARES",
                    content=additional_data,
                ),
            ]
        block_adic.add_fields([fields])
        block_adic.render()
        if draw_qr_code:
            x_after, y_after = self.get_x(), self.get_y()
            self._draw_qr_code_block(
                x=block_adic.x + block_adic.w + QR_CODE_BLOCK_GAP,
                y=block_adic.y,
                h=HEIGHT_FONT_BLOCK_DESC + height,
            )
            self.set_xy(x=x_after, y=y_after)

        add_data_field = block_adic.fields[0]
        add_data_lines = add_data_field.get_content_lines()
        max_add_data_lines = add_data_field.get_max_content_lines()
        return add_data_lines, max_add_data_lines

    def _draw_qr_code_block(self, x, y, h):
        """QR Code of infNFeSupl/qrCode (NT 2026.010, items 4.4 and 4.5)."""
        w = QR_CODE_BLOCK_WIDTH
        self.set_font(self.default_font, "B", 6)
        self.set_xy(x=x, y=y)
        self.cell(w=w, h=HEIGHT_FONT_BLOCK_DESC, text="QR CODE", align="C")
        y_box = y + HEIGHT_FONT_BLOCK_DESC
        h_box = h - HEIGHT_FONT_BLOCK_DESC
        self.rect(x=x, y=y_box, w=w, h=h_box)
        self.image(
            self.qr_code_image,
            x=x + (w - QR_CODE_SIZE) / 2,
            y=y_box + (h_box - QR_CODE_SIZE) / 2,
            w=QR_CODE_SIZE,
            h=QR_CODE_SIZE,
        )

    def _draw_footer_stamp(self):
        if not self._has_footer_stamp:
            return

        stamp = self.footer_stamp
        # Stamp sits in the strip reserved during __init__: just below the
        # content area, with `stamp.spacing` above and the user's bottom margin
        # below it as visual padding.
        y_top = self.h - self.b_margin + stamp.spacing
        logo_box_w = stamp.logo_max_width if stamp.logo else 0
        x_logo = self.w - self.r_margin - logo_box_w

        if stamp.text:
            self.set_font(self.default_font, style="B", size=7)
            text_w = self.get_string_width(stamp.text)
            text_gap = 2 if stamp.logo else 0
            # cell() reserves c_margin padding inside the cell on both sides;
            # size the cell to include it and right-align so the text right
            # edge lands exactly at (x_logo - text_gap) without overflowing
            # the right margin.
            cell_w = text_w + 2 * self.c_margin
            cell_x = x_logo - text_gap - text_w - self.c_margin
            self.set_xy(cell_x, y_top)
            self.cell(cell_w, stamp.height, stamp.text, align="R")

        if stamp.logo:
            self.image(
                stamp.logo,
                x=x_logo,
                y=y_top,
                w=logo_box_w,
                h=stamp.height,
                keep_aspect_ratio=True,
            )

    def _get_dest_end_text(self, ender):
        logradouro = extract_text(ender, "xLgr")
        numero = extract_text(ender, "nro")
        complemento = extract_text(ender, "xCpl")
        partes = [logradouro, numero]
        if complemento:
            partes.append(complemento)
        dest_end = ", ".join(partes)
        cpl_truncado = False
        if len(dest_end) > 85:
            dest_end = dest_end[:85]
            cpl_truncado = True
        return dest_end, complemento, cpl_truncado

    def get_font_size(self, element_type: str, multiplier=False):
        """Retorna o tamanho da fonte escalado para o tipo de elemento."""
        base_size = BASE_FONT_SIZES.get(element_type)
        if multiplier:
            return base_size * self.default_font_factor
        else:
            return base_size
