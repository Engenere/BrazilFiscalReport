"""
DANFE in the MOC 7.0 layout, picked by DanfeLayout.AUTO for NF-e issued before
2026-12-01 (all these fixtures). The reference PDFs are the ones of version
1.2.0. Remove this module with danfe_moc_7_0.py.
"""

import warnings

import pytest

from brazilfiscalreport.danfe import (
    Danfe,
    DanfeConfig,
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
from brazilfiscalreport.danfe.danfe_moc_7_0 import DanfeMoc70
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_danfe(load_xml):
    def _load_danfe(filename, config=None):
        xml_content = load_xml(f"danfe/{filename}")
        danfe = Danfe(xml=xml_content, config=config)
        assert isinstance(danfe, DanfeMoc70)
        return danfe

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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_default")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_sn(tmp_path, load_danfe):
    """
    Tests the creation of a DANFE for an Electronic Invoice (NF-e) issued by a company
    opting for the Simples Nacional regime.
    """
    danfe = load_danfe("nfe_test_sn.xml")
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_sn")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_minimal(tmp_path, load_danfe):
    minimal_config = DanfeConfig(
        margins=Margins(top=8, right=8, bottom=8, left=8),
        decimal_config=DecimalConfig(price_precision=2, quantity_precision=2),
    )
    danfe = load_danfe("nfe_test_1.xml", config=minimal_config)
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_minimal")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_multi_page_products_lp(tmp_path, load_danfe, default_danfe_config):
    """
    Tests the creation of a DANFE with more than one page of products in landscape mode.
    """
    danfe = load_danfe(
        "nfe_multi_page_products_landscape.xml", config=default_danfe_config
    )
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_multipage_landscape")
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_add_info_below_prod")
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_add_info_next_page")
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_overload")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_duplicatas_only(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        invoice_display=InvoiceDisplay.DUPLICATES_ONLY,
    )
    danfe = load_danfe("nfe_overload.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_duplicatas_only")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_pis_config(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        display_pis_cofins=True,
    )
    danfe = load_danfe("nfe_test_1.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_pis_confins")
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_branch")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_product_description_with_branch_prefix(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        product_description_config=ProductDescriptionConfig(
            display_branch=True, branch_info_prefix="=>"
        ),
    )
    danfe = load_danfe("nfe_test_branch.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_branch_with_prefix")
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_anp")
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_anvisa")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_product_description_with_xped(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        product_description_config=ProductDescriptionConfig(display_xped=True),
    )
    danfe = load_danfe("nfe_xped.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_xped")
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_with_production_environment")
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
    pdf_path = get_pdf_output_path(
        "danfe_moc_7_0", "danfe_without_production_environment"
    )
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_default_production")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_reforma_tributaria(tmp_path, load_danfe):
    danfe = load_danfe("nfe_reforma_tributaria.xml")
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_reforma_tributaria")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_big_font_size")
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_infcpl_semicolon_newline")
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_mei")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_footer_stamp(tmp_path, load_danfe, logo_path):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        footer_stamp=FooterStamp(logo=logo_path, text="Powered by"),
    )
    danfe = load_danfe("nfe_test_1.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_footer_stamp")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_footer_stamp_text_only(tmp_path, load_danfe):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        footer_stamp=FooterStamp(text="Powered by Engenere"),
    )
    danfe = load_danfe("nfe_test_1.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_footer_stamp_text_only")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_footer_stamp_logo_only(tmp_path, load_danfe, logo_path):
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        footer_stamp=FooterStamp(logo=logo_path),
    )
    danfe = load_danfe("nfe_test_1.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_footer_stamp_logo_only")
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_footer_stamp_multipage")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_default_footer_stamp_emits_no_warning():
    """
    A default (empty) FooterStamp must not emit any warning, even when the
    bottom margin is small.
    """
    config = DanfeConfig(margins=Margins(top=2, right=2, bottom=2, left=2))
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
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_retirada")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_retirada_entrega(tmp_path, load_danfe):
    """
    Tests the creation of a DANFE for an NF-e that has both the pickup
    location group (retirada) and the delivery location group (entrega).
    Both blocks must be rendered in the document. Regression test for
    issue #169.
    """
    danfe = load_danfe("nfe_retirada_entrega.xml")
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_retirada_entrega")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_cnpj_alfanumerico(tmp_path, load_danfe):
    danfe = load_danfe("danfe_cnpj_alfanumerico.xml")
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_cnpj_alfanumerico")
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
        "danfe_moc_7_0", f"danfe_carrier_receipt_{receipt_pos.value}"
    )
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_carrier_receipt_landscape(tmp_path, load_xml):
    xml = load_xml("danfe/nfe_mei.xml").replace("<tpImp>1</tpImp>", "<tpImp>2</tpImp>")
    config = DanfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        carrier_receipt=True,
    )
    danfe = Danfe(xml=xml, config=config)
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_carrier_receipt_landscape")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_carrier_receipt_without_carrier(tmp_path, load_danfe):
    """
    Without a carrier informed in the NF-e, only the regular receipt is
    printed, even with carrier_receipt enabled.
    """
    danfe = load_danfe("nfe_test_1.xml", config=DanfeConfig(carrier_receipt=True))
    assert danfe.receipt_kinds == ["default"]
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_default")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_multiple_volumes(tmp_path, load_danfe):
    """
    With several vol groups, the volumes line sums quantity and weights and
    lists the distinct species (issue #232).
    """
    danfe = load_danfe("nfe_multiple_volumes.xml")
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_multiple_volumes")
    assert_pdf_equal(danfe, pdf_path, tmp_path)


def test_danfe_many_volumes(tmp_path, load_xml):
    """
    Beyond MAX_VOLUME_LINES, the remaining volumes are listed in the
    additional data instead of growing the carrier block.
    """
    xml = load_xml("danfe/nfe_multiple_volumes.xml")
    extra = "".join(
        f"<vol><qVol>{i}</qVol><esp>CAIXA</esp><marca>ACME</marca><nVol>{i:03d}"
        f"</nVol><pesoL>1.000</pesoL><pesoB>1.500</pesoB></vol>"
        for i in range(4, 12)
    )
    xml = xml.replace("</transp>", extra + "</transp>")
    danfe = Danfe(xml=xml)
    assert isinstance(danfe, DanfeMoc70)
    assert len(danfe.volumes) == 11
    pdf_path = get_pdf_output_path("danfe_moc_7_0", "danfe_many_volumes")
    assert_pdf_equal(danfe, pdf_path, tmp_path)
