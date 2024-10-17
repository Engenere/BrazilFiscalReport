import pytest

from brazilfiscalreport.damdfe import (
    Damdfe,
    DamdfeConfig,
    Margins,
)
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_damdfe(load_xml):
    def _load_damdfe(filename, config=None):
        xml_content = load_xml(filename)
        return Damdfe(xml=xml_content, config=config)

    return _load_damdfe


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


def test_damdfe_default_logo_margins(tmp_path, load_damdfe, logo_path):
    damdfe_config = DamdfeConfig(
        logo=logo_path,
        margins=Margins(top=10, right=10, bottom=10, left=10),
    )
    damdfe = load_damdfe("mdf-e_test_1.xml", config=damdfe_config)
    pdf_path = get_pdf_output_path("damdfe", "damdfe_default_logo_margins")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)
