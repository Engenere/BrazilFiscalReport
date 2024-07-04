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
        xml_content = load_xml(filename)
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
