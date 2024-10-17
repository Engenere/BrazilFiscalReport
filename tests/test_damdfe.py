import pytest

from brazilfiscalreport.damdfe import (
    Damdfe,
    DamdfeConfig,
    Margins,
    ReceiptPosition,
)
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_damdfe(load_xml):
    def _load_damdfe(filename, config=None):
        xml_content = load_xml(filename)
        return Damdfe(xml=xml_content, config=config)

    return _load_damdfe


@pytest.fixture(scope="module")
def default_dacte_config(logo_path):
    config = DamdfeConfig(
        margins=Margins(top=2, right=2, bottom=2, left=2),
        logo=logo_path,
        receipt_pos=ReceiptPosition.TOP,
    )
    return config


def test_damdfe_default(tmp_path, load_damdfe):
    damdfe = load_damdfe("mdf-e_test_1.xml")
    pdf_path = get_pdf_output_path("damdfe", "damdfe_default")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_default_logo(tmp_path, load_damdfe, logo_path):
    damdfe_config = DamdfeConfig(
        logo=logo_path,
    )
    damdfe = load_damdfe("mdf-e_test_1.xml", config=damdfe_config)
    pdf_path = get_pdf_output_path("damdfe", "damdfe_default_logo")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)
