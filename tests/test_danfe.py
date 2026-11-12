"""
DANFE in the NT 2026.010 layout. Most fixtures were issued before 2026-12-01,
when DanfeLayout.AUTO still picks the MOC 7.0 layout, so these tests force
the new one.
"""

import warnings
from dataclasses import replace

import pytest

from brazilfiscalreport.danfe import (
    Danfe,
    DanfeConfig,
    DanfeLayout,
    DecimalConfig,
    FontSize,
    FontType,
    FooterStamp,
    InvoiceDisplay,
    Margins,
    ProductDescriptionConfig,
    ReceiptPosition,
    TaxConfiguration,
)
from brazilfiscalreport.danfe.danfe import resolve_layout
from brazilfiscalreport.danfe.danfe_moc_7_0 import DanfeMoc70
from brazilfiscalreport.danfe.danfe_nt_2026_010 import DanfeNt2026010
from brazilfiscalreport.danfe.models import LabeledValue
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_danfe(load_xml):
    def _load_danfe(filename, config=None):
        xml_content = load_xml(f"danfe/{filename}")
        config = replace(config or DanfeConfig(), layout=DanfeLayout.NT_2026_010)
        return Danfe(xml=xml_content, config=config)

    return _load_danfe


@pytest.fixture(scope="module")
def default_danfe_config(logo_path):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        logo=logo_path,
        receipt_pos=ReceiptPosition.TOP,
    )
    return config


def test_danfe_default(tmp_path, load_danfe):
    danfe = load_danfe("nfe_test_1.xml")
    pdf_path = get_pdf_output_path("danfe", "danfe_default")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_sn(tmp_path, load_danfe):
    """
    Tests the creation of a DANFE for an Electronic Invoice (NF-e) issued by a company
    opting for the Simples Nacional regime.
    """
    danfe = load_danfe("nfe_test_sn.xml")
    pdf_path = get_pdf_output_path("danfe", "danfe_sn")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_minimal(tmp_path, load_danfe):
    minimal_config = DanfeConfig(
        margins=Margins(top=8, right=8, bottom=8, left=8),
        decimal_config=DecimalConfig(price_precision=2, quantity_precision=2),
    )
    danfe = load_danfe("nfe_test_1.xml", config=minimal_config)
    pdf_path = get_pdf_output_path("danfe", "danfe_minimal")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_multi_page_products_lp(tmp_path, load_danfe, default_danfe_config):
    """
    Tests the creation of a DANFE with more than one page of products in landscape mode.
    """
    danfe = load_danfe(
        "nfe_multi_page_products_landscape.xml", config=default_danfe_config
    )
    pdf_path = get_pdf_output_path("danfe", "danfe_multipage_landscape")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_add_info_below_prod(tmp_path, load_danfe, default_danfe_config):
    """
    Tests the creation of a DANFE where the additional information exceeds the standard
    limit and the continuation is placed below the product table.
    This checks the layout adjustments needed when additional data overflows its usual
    space in the document.
    """
    danfe = load_danfe(
        "nfe_additional_info_continuation_in_product_table.xml",
        config=default_danfe_config,
    )
    pdf_path = get_pdf_output_path("danfe", "danfe_add_info_below_prod")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_add_info_next_page(tmp_path, load_danfe, default_danfe_config):
    """
    Tests the creation of a DANFE where additional information exceeds the available
    space and overflows to the next page. This test ensures that the layout properly
    adjusts to accommodate additional data on a new page when it overflows beyond the
    first page's capacity.
    """
    danfe = load_danfe(
        "nfe_additional_info_continuation_in_next_page.xml", config=default_danfe_config
    )
    pdf_path = get_pdf_output_path("danfe", "danfe_add_info_next_page")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_overload(tmp_path, load_danfe, default_danfe_config, logo_path):
    overload_config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        logo=logo_path,
        receipt_pos=ReceiptPosition.BOTTOM,
        decimal_config=DecimalConfig(price_precision=6, quantity_precision=6),
        tax_configuration=TaxConfiguration.ICMS_ST,
        invoice_display=InvoiceDisplay.FULL_DETAILS,
        font_type=FontType.COURIER,
    )
    danfe = load_danfe("nfe_overload.xml", config=overload_config)
    pdf_path = get_pdf_output_path("danfe", "danfe_overload")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_duplicatas_only(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        invoice_display=InvoiceDisplay.DUPLICATES_ONLY,
    )
    danfe = load_danfe("nfe_overload.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_duplicatas_only")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_pis_config(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        display_pis_cofins=True,
    )
    danfe = load_danfe("nfe_test_1.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_pis_confins")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_product_description_with_branch(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        product_description_config=ProductDescriptionConfig(
            display_branch=True,
            display_additional_info=False,
        ),
    )
    danfe = load_danfe("nfe_test_branch.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_branch")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_product_description_with_branch_prefix(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        product_description_config=ProductDescriptionConfig(
            display_branch=True, branch_info_prefix="=>"
        ),
    )
    danfe = load_danfe("nfe_test_branch.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_branch_with_prefix")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_product_description_with_anp(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        product_description_config=ProductDescriptionConfig(
            display_anp=True,
            display_additional_info=False,
        ),
    )
    danfe = load_danfe("nfe_test_anp.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_anp")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_product_description_with_anvisa(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        product_description_config=ProductDescriptionConfig(
            display_anvisa=True,
            display_additional_info=False,
        ),
    )
    danfe = load_danfe("nfe_test_anvisa.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_anvisa")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_product_description_with_xped(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        product_description_config=ProductDescriptionConfig(display_xped=True),
    )
    danfe = load_danfe("nfe_xped.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_xped")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


@pytest.mark.parametrize(
    "display_xped, n_item_ped, line",
    [
        (True, "<nItemPed>10</nItemPed>", "Pedido: 4500012345 Item: 10"),
        (True, "", "Pedido: 4500012345"),
        (False, "<nItemPed>10</nItemPed>", None),
    ],
)
def test_danfe_xped_in_description(load_xml, display_xped, n_item_ped, line):
    """The purchase order (xPed and nItemPed) is printed only when enabled."""
    xml = load_xml("danfe/nfe_xped.xml").replace("<nItemPed>10</nItemPed>", n_item_ped)
    config = DanfeConfig(
        product_description_config=ProductDescriptionConfig(display_xped=display_xped),
        layout=DanfeLayout.NT_2026_010,
    )
    lines = Danfe(xml=xml, config=config).products[0].description.splitlines()
    if line:
        assert line in lines
    else:
        assert not [text for text in lines if text.startswith("Pedido:")]


def test_danfe_with_production_environment(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        watermark_cancelled=True,
        product_description_config=ProductDescriptionConfig(
            display_anvisa=True,
            display_additional_info=False,
        ),
    )
    danfe = load_danfe("nfe_with_production_environment.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_with_production_environment")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_without_production_environment(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        watermark_cancelled=True,
        product_description_config=ProductDescriptionConfig(
            display_anvisa=True,
            display_additional_info=False,
        ),
    )
    danfe = load_danfe("nfe_without_production_environment.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_without_production_environment")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_default_production(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        product_description_config=ProductDescriptionConfig(
            display_anvisa=True,
            display_additional_info=False,
        ),
    )
    danfe = load_danfe("nfe_with_production_environment.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_default_production")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_reforma_tributaria(tmp_path, load_danfe):
    danfe = load_danfe("nfe_reforma_tributaria.xml")
    pdf_path = get_pdf_output_path("danfe", "danfe_reforma_tributaria")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_rtc(tmp_path, load_danfe):
    """
    Layout of NT 2026.010: CRT in the header, IBS/CBS/IS totals, optional
    FCP/DIFAL and single-phase totals, ISSQN, item taxes (regular and
    effective rates, IS, IPI, exempt and service items) and QR Code.
    """
    danfe = load_danfe("nfe_rtc.xml")
    pdf_path = get_pdf_output_path("danfe", "danfe_rtc")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_rtc_landscape(tmp_path, load_xml):
    xml = load_xml("danfe/nfe_rtc.xml").replace("<tpImp>1</tpImp>", "<tpImp>2</tpImp>")
    danfe = Danfe(xml=xml)
    pdf_path = get_pdf_output_path("danfe", "danfe_rtc_landscape")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


@pytest.mark.parametrize(
    "tp_imp, orientation",
    [
        ("0", "P"),
        ("1", "P"),
        ("2", "L"),
        ("3", "P"),
        ("4", "P"),
        ("5", "P"),
        ("6", "P"),
    ],
)
def test_danfe_orientation_by_tp_imp(load_xml, tp_imp, orientation):
    """
    Only tpImp=2 is the landscape DANFE; the other formats, including the
    DANFE Simplificado Tipo 2 (tpImp=6), print the regular DANFE in portrait.
    """
    xml = load_xml("danfe/nfe_rtc.xml").replace(
        "<tpImp>1</tpImp>", f"<tpImp>{tp_imp}</tpImp>"
    )
    assert Danfe(xml=xml).orientation == orientation


@pytest.mark.parametrize(
    "issue_date, layout",
    [
        ("<dhEmi>2026-11-30T23:59:59-03:00</dhEmi>", DanfeLayout.MOC_7_0),
        ("<dhEmi>2026-12-01T00:00:00-03:00</dhEmi>", DanfeLayout.NT_2026_010),
        # still 2026-11-30 in Brasília
        ("<dhEmi>2026-12-01T02:59:59+00:00</dhEmi>", DanfeLayout.MOC_7_0),
        # without UTC offset, Brasília time
        ("<dhEmi>2026-12-01T00:00:00</dhEmi>", DanfeLayout.NT_2026_010),
        # dEmi of the layouts before 3.10
        ("<dEmi>2026-11-30</dEmi>", DanfeLayout.MOC_7_0),
    ],
)
def test_danfe_layout_by_issue_date(load_xml, issue_date, layout):
    xml = load_xml("danfe/nfe_rtc.xml").replace(
        "<dhEmi>2026-12-01T10:00:00-03:00</dhEmi>", issue_date
    )
    assert resolve_layout(xml) == layout


def test_danfe_auto_layout(load_xml):
    assert isinstance(Danfe(xml=load_xml("danfe/nfe_test_1.xml")), DanfeMoc70)
    assert isinstance(Danfe(xml=load_xml("danfe/nfe_rtc.xml")), DanfeNt2026010)


def test_danfe_forced_layout(load_xml):
    """
    NT_2026_010 prints the new layout before 2026-12-01, for testing;
    MOC_7_0 keeps the old one and warns that it will be removed.
    """
    config = DanfeConfig(layout=DanfeLayout.NT_2026_010)
    danfe = Danfe(xml=load_xml("danfe/nfe_test_1.xml"), config=config)
    assert isinstance(danfe, DanfeNt2026010)

    config = DanfeConfig(layout=DanfeLayout.MOC_7_0)
    with pytest.warns(DeprecationWarning, match="MOC 7.0"):
        danfe = Danfe(xml=load_xml("danfe/nfe_rtc.xml"), config=config)
    assert isinstance(danfe, DanfeMoc70)


def test_danfe_rtc_big_font_size(tmp_path, load_danfe):
    """
    With the big font the item taxes no longer fit two per line, so they are
    printed one per line.
    """
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        font_size=FontSize.BIG,
    )
    danfe = load_danfe("nfe_rtc.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_rtc_big_font_size")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_rtc_item_taxes(load_danfe):
    products = load_danfe("nfe_rtc.xml").products

    # regular rates
    assert products[0].tax_bases == [
        LabeledValue("ICMS", "250,00"),
        LabeledValue("IBS / CBS", "250,00"),
        LabeledValue("IPI", "250,00"),
    ]
    assert products[0].tax_rates == (
        [
            LabeledValue("ICMS", "12,00%"),
            LabeledValue("IBS UF", "0,10%"),
            LabeledValue("IBS MUN", "0,00%"),
        ],
        [LabeledValue("CBS", "0,90%"), LabeledValue("IPI", "5,00%")],
    )
    # with gRed the effective rate (pAliqEfet) is printed
    assert products[1].tax_rates == (
        [
            LabeledValue("ICMS", "12,00%"),
            LabeledValue("IBS UF", "0,04%"),
            LabeledValue("IBS MUN", "0,00%"),
        ],
        [LabeledValue("CBS", "0,36%"), LabeledValue("IS", "10,00%")],
    )
    assert products[1].tax_values == (
        [
            LabeledValue("ICMS", "38,40"),
            LabeledValue("IBS UF", "0,21"),
            LabeledValue("IBS MUN", "0,00"),
        ],
        [LabeledValue("CBS", "1,90"), LabeledValue("IS", "48,00")],
    )
    # single-phase ICMS and IBS/CBS, then an exempt item: nothing to print
    for product in products[2:4]:
        assert product.tax_bases == []
        assert product.tax_rates == ([], [])
        assert product.tax_values == ([], [])
    assert products[3].description.endswith("[NCM 49019900] [cClassTrib 410001]")
    # service item: no ICMS group, so no CST
    assert products[4].cst_cfop == [LabeledValue("CFOP", "6933")]


def test_danfe_rtc_totals(load_danfe):
    danfe = load_danfe("nfe_rtc.xml")
    assert len(danfe._get_icms_ipi_lines()) == 3
    assert danfe._get_ibs_cbs_is_lines() == [
        [
            ("VALOR DA CBS", "6,85"),
            ("VALOR DO IBS UF", "0,76"),
            ("VALOR DO IBS MUNICÍPIO", "0,00"),
            ("VALOR DO IMPOSTO SELETIVO", "48,00"),
        ],
        [
            ("VALOR DO IBS MONOFÁSICO", "2,50"),
            ("VALOR DA CBS MONOFÁSICA", "22,50"),
            ("VALOR DO IBS MONOFÁSICO POR RETENÇÃO", "0,00"),
            ("VALOR DA CBS MONOFÁSICA POR RETENÇÃO", "0,00"),
        ],
    ]


def test_danfe_without_rtc_totals(load_danfe):
    """
    Information absent from the XML is left blank instead of printed as
    zero, and the optional lines are omitted (NT 2026.010, item 4.4).
    """
    danfe = load_danfe("nfe_test_1.xml")
    assert len(danfe._get_icms_ipi_lines()) == 1
    assert danfe._get_ibs_cbs_is_lines() == [
        [
            ("VALOR DA CBS", ""),
            ("VALOR DO IBS UF", ""),
            ("VALOR DO IBS MUNICÍPIO", ""),
            ("VALOR DO IMPOSTO SELETIVO", ""),
        ]
    ]


def test_danfe_big_font_size(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        product_description_config=ProductDescriptionConfig(
            display_anvisa=True,
            display_additional_info=False,
            display_branch=True,
            branch_info_prefix="=>",
            display_anp=True,
        ),
        decimal_config=DecimalConfig(
            price_precision=3,
            quantity_precision=2,
        ),
        font_size=FontSize.BIG,
    )
    danfe = load_danfe("nfe_big_font_size.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_big_font_size")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_infcpl_semicolon_newline(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        product_description_config=ProductDescriptionConfig(
            display_anvisa=True,
            display_additional_info=False,
            display_branch=True,
            branch_info_prefix="=>",
            display_anp=True,
        ),
        decimal_config=DecimalConfig(
            price_precision=3,
            quantity_precision=2,
        ),
        font_size=FontSize.BIG,
        infcpl_semicolon_newline=True,
    )
    danfe = load_danfe("nfe_semicolon_line_break.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_infcpl_semicolon_newline")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_mei(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        product_description_config=ProductDescriptionConfig(
            display_anvisa=True,
            display_additional_info=False,
            display_branch=True,
            branch_info_prefix="=>",
            display_anp=True,
        ),
        decimal_config=DecimalConfig(
            price_precision=3,
            quantity_precision=2,
        ),
        font_size=FontSize.BIG,
        infcpl_semicolon_newline=True,
    )
    danfe = load_danfe("nfe_mei.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_mei")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_footer_stamp(tmp_path, load_danfe, logo_path):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        footer_stamp=FooterStamp(logo=logo_path, text="Powered by"),
    )
    danfe = load_danfe("nfe_test_1.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_footer_stamp")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_footer_stamp_text_only(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        footer_stamp=FooterStamp(text="Powered by Engenere"),
    )
    danfe = load_danfe("nfe_test_1.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_footer_stamp_text_only")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_footer_stamp_logo_only(tmp_path, load_danfe, logo_path):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        footer_stamp=FooterStamp(logo=logo_path),
    )
    danfe = load_danfe("nfe_test_1.xml", config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_footer_stamp_logo_only")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_footer_stamp_multipage(tmp_path, load_danfe, logo_path):
    """
    Footer stamp must appear on all pages, including continuation pages for
    products and for additional data.
    """
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        footer_stamp=FooterStamp(logo=logo_path, text="Powered by"),
    )
    danfe = load_danfe(
        "nfe_additional_info_continuation_in_next_page.xml", config=config
    )
    pdf_path = get_pdf_output_path("danfe", "danfe_footer_stamp_multipage")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_default_footer_stamp_emits_no_warning():
    """
    A default (empty) FooterStamp must not emit any warning, even when the
    bottom margin is small.
    """
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        layout=DanfeLayout.NT_2026_010,
    )
    with open("tests/fixtures/danfe/nfe_test_1.xml", encoding="utf8") as f:
        xml = f.read()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Danfe(xml=xml, config=config)


def test_danfe_retirada(tmp_path, load_danfe):
    """
    Tests the creation of a DANFE for an NF-e that has only the pickup
    location group (retirada), without the delivery location group (entrega).
    """
    danfe = load_danfe("nfe_retirada.xml")
    pdf_path = get_pdf_output_path("danfe", "danfe_retirada")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_retirada_entrega(tmp_path, load_danfe):
    """
    Tests the creation of a DANFE for an NF-e that has both the pickup
    location group (retirada) and the delivery location group (entrega).
    Both blocks must be rendered in the document. Regression test for
    issue #169.
    """
    danfe = load_danfe("nfe_retirada_entrega.xml")
    pdf_path = get_pdf_output_path("danfe", "danfe_retirada_entrega")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_cnpj_alfanumerico(tmp_path, load_danfe):
    danfe = load_danfe("danfe_cnpj_alfanumerico.xml")
    pdf_path = get_pdf_output_path("danfe", "danfe_cnpj_alfanumerico")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


@pytest.mark.parametrize("receipt_pos", [ReceiptPosition.TOP, ReceiptPosition.BOTTOM])
def test_danfe_carrier_receipt(tmp_path, load_danfe, receipt_pos):
    """
    With carrier_receipt enabled and a carrier informed in the NF-e, an extra
    collection receipt (canhoto de coleta) is printed at the page edge, next
    to the delivery receipt (canhoto de entrega). Issue #197.
    """
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        receipt_pos=receipt_pos,
        carrier_receipt=True,
    )
    danfe = load_danfe("nfe_mei.xml", config=config)
    pdf_path = get_pdf_output_path(
        "danfe", f"danfe_carrier_receipt_{receipt_pos.value}"
    )
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_carrier_receipt_landscape(tmp_path, load_xml):
    xml = load_xml("danfe/nfe_mei.xml").replace("<tpImp>1</tpImp>", "<tpImp>2</tpImp>")
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        carrier_receipt=True,
        layout=DanfeLayout.NT_2026_010,
    )
    danfe = Danfe(xml=xml, config=config)
    pdf_path = get_pdf_output_path("danfe", "danfe_carrier_receipt_landscape")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_carrier_receipt_without_carrier(tmp_path, load_danfe):
    """
    Without a carrier informed in the NF-e, only the regular receipt is
    printed, even with carrier_receipt enabled.
    """
    danfe = load_danfe("nfe_test_1.xml", config=DanfeConfig(carrier_receipt=True))
    assert danfe.receipt_kinds == ["default"]
    pdf_path = get_pdf_output_path("danfe", "danfe_default")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_multiple_volumes(tmp_path, load_danfe):
    """
    With several vol groups, the volumes line sums quantity and weights and
    lists the distinct species (issue #232).
    """
    danfe = load_danfe("nfe_multiple_volumes.xml")
    pdf_path = get_pdf_output_path("danfe", "danfe_multiple_volumes")
    assert_pdf_equal(danfe, pdf_path, tmp_path)
