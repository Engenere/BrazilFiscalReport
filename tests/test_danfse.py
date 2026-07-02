import pytest

from brazilfiscalreport.danfse import (
    Danfse,
    DanfseConfig,
    Margins,
)
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_danfse(load_xml):
    def _load_danfse(filename, config=None):
        xml_content = load_xml(f"danfse/{filename}")
        return Danfse(xml=xml_content, config=config)

    return _load_danfse


def test_danfse_default(tmp_path, load_danfse):
    config = DanfseConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
    )
    danfse = load_danfse("nfse_test_prod.xml", config=config)
    pdf_path = get_pdf_output_path("danfse", "danfse_default_prod")
    assert_pdf_equal(danfse, pdf_path, tmp_path)


def test_danfse_default_hom(tmp_path, load_danfse):
    config = DanfseConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
    )
    danfse = load_danfse("nfse_test_hom.xml", config=config)
    pdf_path = get_pdf_output_path("danfse", "danfse_default_hom")
    assert_pdf_equal(danfse, pdf_path, tmp_path)


def test_danfse_intermediary(tmp_path, load_danfse):
    config = DanfseConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
    )
    danfse = load_danfse("nfse_test_interm.xml", config=config)
    pdf_path = get_pdf_output_path("danfse", "danfse_intermediary")
    assert_pdf_equal(danfse, pdf_path, tmp_path)


def test_danfse_minimal(tmp_path, load_danfse):
    config = DanfseConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
    )
    danfse = load_danfse("nfse_test_minimal.xml", config=config)
    pdf_path = get_pdf_output_path("danfse", "danfse_minimal")
    assert_pdf_equal(danfse, pdf_path, tmp_path)


def test_danfse_rtc(tmp_path, load_danfse):
    config = DanfseConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        display_canhoto=True,
    )
    danfse = load_danfse("nfse_test_rtc.xml", config=config)
    pdf_path = get_pdf_output_path("danfse", "danfse_rtc")
    assert_pdf_equal(danfse, pdf_path, tmp_path)


def test_danfse_replaced(tmp_path, load_danfse):
    config = DanfseConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        watermark_replaced=True,
    )
    danfse = load_danfse("nfse_test_rtc.xml", config=config)
    pdf_path = get_pdf_output_path("danfse", "danfse_replaced")
    assert_pdf_equal(danfse, pdf_path, tmp_path)


def test_danfse_cancelled(tmp_path, load_danfse):
    config = DanfseConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2), watermark_cancelled=True
    )
    danfse = load_danfse("nfse_test_prod.xml", config=config)
    pdf_path = get_pdf_output_path("danfse", "danfse_cancelled_prod")
    assert_pdf_equal(danfse, pdf_path, tmp_path)


def test_danfse_cancelled_hom(tmp_path, load_danfse):
    config = DanfseConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2), watermark_cancelled=True
    )
    danfse = load_danfse("nfse_test_hom.xml", config=config)
    pdf_path = get_pdf_output_path("danfse", "danfse_cancelled_hom")
    assert_pdf_equal(danfse, pdf_path, tmp_path)


def test_danfse_cnpj_alfanumerico(tmp_path, load_danfse):
    config = DanfseConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
    )
    danfse = load_danfse("nfse_test_cnpj_alfanumerico.xml", config=config)
    pdf_path = get_pdf_output_path("danfse", "danfse_cnpj_alfanumerico")
    assert_pdf_equal(danfse, pdf_path, tmp_path)
