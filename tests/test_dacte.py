import pytest

from brazilfiscalreport.dacte import (
    Dacte,
    DacteConfig,
    Margins,
    ReceiptPosition,
)
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_dacte(load_xml):
    def _load_dacte(filename, config=None):
        xml_content = load_xml(f"dacte/{filename}")
        return Dacte(xml=xml_content, config=config)

    return _load_dacte


@pytest.fixture(scope="module")
def default_dacte_config(logo_path):
    config = DacteConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        logo=logo_path,
        receipt_pos=ReceiptPosition.TOP,
    )
    return config


def test_dacte_default(tmp_path, load_dacte):
    dacte = load_dacte("dacte_test_1.xml")
    pdf_path = get_pdf_output_path("dacte", "dacte_default")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_without_compl(tmp_path, load_dacte):
    dacte = load_dacte("dacte_test_without_compl.xml")
    pdf_path = get_pdf_output_path("dacte", "dacte_without_compl")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_overload(tmp_path, load_dacte):
    dacte_config = DacteConfig(margins=Margins(top=10, right=10, bottom=10, left=10))
    dacte = load_dacte("dacte_test_overload.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_overload")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_multi_pages(tmp_path, load_dacte):
    dacte = load_dacte("dacte_test_multi_pages.xml")
    pdf_path = get_pdf_output_path("dacte", "dacte_multi_pages")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_default_logo(tmp_path, load_dacte, logo_path):
    dacte_config = DacteConfig(
        logo=logo_path,
    )
    dacte = load_dacte("dacte_test_1.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_default_logo")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_default_aquaviario(tmp_path, load_dacte, logo_path):
    dacte_config = DacteConfig(
        logo=logo_path,
    )
    dacte = load_dacte("dacte_aquaviario_test.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_default_aquaviario")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_default_aereo(tmp_path, load_dacte, logo_path):
    dacte_config = DacteConfig(
        logo=logo_path,
    )
    dacte = load_dacte("dacte_aereo_test.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_default_aereo")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_default_ferroviario(tmp_path, load_dacte, logo_path):
    dacte_config = DacteConfig(
        logo=logo_path,
    )
    dacte = load_dacte("dacte_ferroviario_test.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_default_ferroviario")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_default_dutoviario(tmp_path, load_dacte, logo_path):
    dacte_config = DacteConfig(
        logo=logo_path,
    )
    dacte = load_dacte("dacte_dutoviario_test.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_default_dutoviario")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_default_multimodal(tmp_path, load_dacte, logo_path):
    dacte_config = DacteConfig(
        logo=logo_path,
    )
    dacte = load_dacte("dacte_multimodal_test.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_default_multimodal")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_tomador_outros(tmp_path, load_dacte, logo_path):
    dacte_config = DacteConfig(
        logo=logo_path,
    )
    dacte = load_dacte("dacte_tomador_outros.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_tomador_outros")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_watermark_cancelled_production(tmp_path, load_dacte):
    """Test watermark for cancelled DACTE in production environment"""
    dacte_config = DacteConfig(watermark_cancelled=True)
    dacte = load_dacte("dacte_test_1.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_watermark_cancelled_production")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_watermark_cancelled_homologation(tmp_path, load_dacte):
    """Test watermark for cancelled DACTE in homologation environment"""
    dacte_config = DacteConfig(watermark_cancelled=True)
    dacte = load_dacte("dacte_test_homolog.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_watermark_cancelled_homologation")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_watermark_homologation_only(tmp_path, load_dacte):
    """Test watermark for DACTE in homologation environment without cancellation"""
    dacte_config = DacteConfig(watermark_cancelled=False)
    dacte = load_dacte("dacte_test_homolog.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_watermark_homologation_only")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_reforma_tributaria(tmp_path, load_dacte):
    """Test DACTE with PIS/COFINS and IBS/CBS display (reforma tributária)."""
    dacte_config = DacteConfig(display_ibs_cbs=True)
    dacte = load_dacte("dacte_reforma_tributaria.xml", config=dacte_config)
    pdf_path = get_pdf_output_path("dacte", "dacte_reforma_tributaria")
    assert_pdf_equal(dacte, pdf_path, tmp_path)


def test_dacte_cnpj_alfanumerico(tmp_path, load_dacte):
    dacte = load_dacte("dacte_cnpj_alfanumerico.xml")
    pdf_path = get_pdf_output_path("dacte", "dacte_cnpj_alfanumerico")
    assert_pdf_equal(dacte, pdf_path, tmp_path)
