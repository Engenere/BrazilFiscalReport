import pytest

from brazilfiscalreport.danfe import (
    Danfe,
    DanfeConfig,
    DecimalConfig,
    FontSize,
    FontType,
    InvoiceDisplay,
    Margins,
    ProductDescriptionConfig,
    ReceiptPosition,
    TaxConfiguration,
)
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_danfe(load_xml):
    def _load_danfe(filename, config=None):
        xml_content = load_xml(filename)
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
